
import pytest

pytestmark = pytest.mark.skip(
    reason='Blockchain anchoring and verification logic is intentionally excluded from this public source distribution.',
)

import json
from datetime import timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from web3 import EthereumTesterProvider, Web3

from app.blockchain.evm import EVMBlockchainProvider
from app.blockchain.provider import AnchorPayload, BlockchainProviderError
from app.core.config import Settings
from app.db.session import Database
from app.models.auth import User
from app.models.blockchain import BlockchainRecord
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.services.blockchain import BlockchainService, DIGEST_VERSION
from tests.test_payments import _transfer, payment_world

_ARTIFACT_PATH = Path(__file__).parents[1] / "contracts" / "artifacts" / "LedgerAnchorRegistry.json"


def _deploy_registry(web3: Web3) -> Any:
    artifact = json.loads(_ARTIFACT_PATH.read_text(encoding="utf-8"))
    web3.eth.default_account = web3.eth.accounts[0]
    factory = web3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    receipt = web3.eth.wait_for_transaction_receipt(factory.constructor().transact())
    return web3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])


def _provider_settings(
    web3: Web3,
    address: str,
    *,
    confirmations: int = 1,
    chain_id: int | None = None,
    signer_index: int = 0,
) -> Settings:
    private_key = web3.provider.ethereum_tester.backend.account_keys[signer_index].to_hex()
    return Settings(
        _env_file=None,
        environment="test",
        blockchain_enabled=True,
        blockchain_provider="evm",
        blockchain_network="local-evm-test",
        blockchain_chain_id=chain_id or int(web3.eth.chain_id),
        blockchain_rpc_url="http://127.0.0.1:8545",
        blockchain_signer_private_key=private_key,
        blockchain_contract_address=address,
        blockchain_confirmation_depth=confirmations,
    )


def test_evm_provider_submits_confirms_and_reads_the_real_contract() -> None:
    web3 = Web3(EthereumTesterProvider())
    contract = _deploy_registry(web3)
    provider = EVMBlockchainProvider(
        _provider_settings(web3, contract.address, confirmations=2),
        web3=web3,
    )
    ledger_id = UUID("00000000-0000-0000-0000-000000000123")
    payload = AnchorPayload(ledger_id, DIGEST_VERSION, "12" * 32)

    assert provider.health_check().status == "available"
    submitted = provider.anchor_ledger_transaction(payload, idempotency_key="record-123")
    assert submitted.status == "submitted"
    assert submitted.transaction_hash is not None
    assert submitted.contract_address == contract.address
    assert submitted.contract_version == "1.0.0"

    pending = provider.get_transaction(submitted.transaction_hash)
    assert pending is not None and pending.status == "submitted"
    web3.provider.ethereum_tester.mine_blocks(1)
    confirmed = provider.get_transaction(submitted.transaction_hash)
    assert confirmed is not None and confirmed.status == "confirmed"
    assert confirmed.block_number is not None
    assert confirmed.confirmed_at is not None and confirmed.confirmed_at.tzinfo == timezone.utc

    anchor = provider.verify_anchor(payload.digest)
    assert anchor is not None
    assert anchor.digest == payload.digest
    assert anchor.reference_id == f"0x{ledger_id.int:064x}"
    assert anchor.anchored_at.tzinfo == timezone.utc
    assert provider.verify_anchor("34" * 32) is None


def test_evm_provider_rejects_wrong_chain_configuration() -> None:
    web3 = Web3(EthereumTesterProvider())
    contract = _deploy_registry(web3)
    provider = EVMBlockchainProvider(
        _provider_settings(web3, contract.address, chain_id=int(web3.eth.chain_id) + 1),
        web3=web3,
    )

    assert provider.health_check().status == "unavailable"
    with pytest.raises(BlockchainProviderError) as error:
        provider.anchor_ledger_transaction(
            AnchorPayload(UUID(int=1), DIGEST_VERSION, "ab" * 32),
            idempotency_key="wrong-chain",
        )
    assert error.value.code == "PROVIDER_INVALID_RESPONSE"


def _ledger_id(world: dict[str, Any], payment: Any) -> UUID:
    database = world["database"]
    assert isinstance(database, Database)
    with database.session_factory() as session:
        transaction = session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.reference == payment.json()["reference"])
        )
        assert transaction is not None
        return transaction.id


def test_ledger_to_contract_verification_detects_a_tampered_offchain_digest(
    payment_world: dict[str, Any],
) -> None:
    payment = _transfer(payment_world)
    assert payment.status_code == 201, payment.text
    ledger_id = _ledger_id(payment_world, payment)
    web3 = Web3(EthereumTesterProvider())
    contract = _deploy_registry(web3)
    provider = EVMBlockchainProvider(_provider_settings(web3, contract.address), web3=web3)
    database = payment_world["database"]
    assert isinstance(database, Database)

    with database.session_factory() as session:
        user = session.get(User, payment_world["sender_user_id"])
        assert user is not None
        service = BlockchainService(
            session,
            _provider_settings(web3, contract.address),
            provider,
        )
        submitted = service.anchor(ledger_id, user)
        assert submitted.status == "submitted"
        assert submitted.contract_address == contract.address

        confirmed = service.get_record(submitted.id, user)
        assert confirmed.status == "confirmed"
        assert confirmed.transaction_hash == submitted.transaction_hash
        assert confirmed.block_number is not None

        verified = service.verify(ledger_id, user)
        assert verified.result == "ANCHORED_MATCH"
        assert verified.current_digest == confirmed.digest
        assert verified.anchored_digest == confirmed.digest
        assert verified.integrity_warning is False

        repeated = service.anchor(ledger_id, user)
        assert repeated.id == confirmed.id
        assert repeated.transaction_hash == confirmed.transaction_hash

        entry = session.scalar(
            select(LedgerEntry).where(LedgerEntry.ledger_transaction_id == ledger_id)
        )
        assert entry is not None
        entry.amount += Decimal("0.01")
        session.commit()

        mismatch = service.verify(ledger_id, user)
        assert mismatch.result == "ANCHORED_MISMATCH"
        assert mismatch.integrity_warning is True
        assert mismatch.current_digest != mismatch.anchored_digest

        stored = session.get(BlockchainRecord, confirmed.id)
        assert stored is not None and stored.status == "confirmed"


def test_evm_settings_require_complete_and_valid_provider_credentials() -> None:
    with pytest.raises(ValueError, match="CHAIN_ID"):
        Settings(_env_file=None, environment="test", blockchain_provider="evm")

    with pytest.raises(ValueError, match="HTTPS"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="not-the-default",
            database_url="postgresql+psycopg://user:pass@db.example/ledger",
            blockchain_provider="evm",
            blockchain_network="sepolia",
            blockchain_chain_id=11155111,
            blockchain_rpc_url="http://rpc.example",
            blockchain_signer_private_key="0x" + "12" * 32,
            blockchain_contract_address="0x" + "34" * 20,
        )


def test_local_evm_revert_is_reported_as_a_chain_failure() -> None:
    web3 = Web3(EthereumTesterProvider())
    contract = _deploy_registry(web3)
    provider = EVMBlockchainProvider(_provider_settings(web3, contract.address), web3=web3)
    unauthorized = web3.eth.accounts[1]
    private_key = web3.provider.ethereum_tester.backend.account_keys[1].to_hex()
    transaction = contract.functions.anchorRecord(
        bytes.fromhex("cd" * 32), bytes.fromhex(f"{2:064x}")
    ).build_transaction(
        {
            "from": unauthorized,
            "nonce": web3.eth.get_transaction_count(unauthorized),
            "chainId": web3.eth.chain_id,
            "gas": 150_000,
            "gasPrice": web3.eth.gas_price,
        }
    )
    signed = web3.eth.account.sign_transaction(transaction, private_key=private_key)
    transaction_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    reverted_receipt = web3.eth.wait_for_transaction_receipt(transaction_hash)
    assert reverted_receipt.status == 0

    reverted = provider.get_transaction(transaction_hash.hex())
    assert reverted is not None
    assert reverted.status == "failed"
    assert reverted.failure_code == "PROVIDER_TRANSACTION_REVERTED"
    assert reverted.confirmed_at is not None
