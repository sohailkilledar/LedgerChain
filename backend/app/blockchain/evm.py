import json
from datetime import datetime, timezone
from pathlib import Path
import re
import socket
from threading import Lock
from uuid import UUID

import requests
from web3 import HTTPProvider, Web3
from web3.exceptions import TransactionNotFound

from app.blockchain.provider import (
    AnchorPayload,
    BlockchainProviderError,
    SUPPORTED_DIGEST_VERSIONS,
    ProviderAnchor,
    ProviderHealth,
    ProviderTransaction,
)
from app.core.config import Settings

_ARTIFACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "artifacts" / "LedgerAnchorRegistry.json"
_NONCE_LOCKS: dict[tuple[int, str], Lock] = {}
_NONCE_LOCKS_GUARD = Lock()
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _nonce_lock(chain_id: int, address: str) -> Lock:
    key = (chain_id, address.lower())
    with _NONCE_LOCKS_GUARD:
        return _NONCE_LOCKS.setdefault(key, Lock())


def _reference_id(ledger_transaction_id: UUID) -> bytes:
    return bytes.fromhex(ledger_transaction_id.hex).rjust(32, b"\x00")


class EVMBlockchainProvider:
    """Backend-only signer and client for the configured LedgerAnchorRegistry deployment."""

    provider_id = "evm"

    def __init__(self, settings: Settings, *, web3: Web3 | None = None) -> None:
        if settings.blockchain_chain_id is None or settings.blockchain_contract_address is None:
            raise BlockchainProviderError("PROVIDER_UNAVAILABLE")
        if settings.blockchain_rpc_url is None or settings.blockchain_signer_private_key is None:
            raise BlockchainProviderError("PROVIDER_UNAVAILABLE")
        if not _ARTIFACT_PATH.is_file():
            raise BlockchainProviderError("PROVIDER_UNAVAILABLE")

        try:
            self._settings = settings
            self.network = settings.blockchain_network
            self.chain_id = settings.blockchain_chain_id
            self.contract_address = Web3.to_checksum_address(settings.blockchain_contract_address)
            self.w3 = web3 or Web3(
                HTTPProvider(
                    settings.blockchain_rpc_url.get_secret_value(),
                    request_kwargs={"timeout": settings.blockchain_rpc_timeout_seconds},
                )
            )
            private_key = settings.blockchain_signer_private_key.get_secret_value()
            self.account = self.w3.eth.account.from_key(private_key)
            self.confirmations = settings.blockchain_confirmation_depth
            artifact = json.loads(_ARTIFACT_PATH.read_text(encoding="utf-8"))
            if artifact.get("contractName") != "LedgerAnchorRegistry":
                raise ValueError("Unexpected contract artifact")
            self.contract_version = settings.blockchain_contract_version
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=artifact["abi"])
            self._nonce_lock = _nonce_lock(self.chain_id, self.account.address)
        except BlockchainProviderError:
            raise
        except Exception as exc:
            raise BlockchainProviderError("PROVIDER_INVALID_RESPONSE") from exc

    def anchor_ledger_transaction(
        self, payload: AnchorPayload, *, idempotency_key: str
    ) -> ProviderTransaction:
        del idempotency_key
        if payload.digest_version not in SUPPORTED_DIGEST_VERSIONS:
            raise BlockchainProviderError("PROVIDER_INVALID_RESPONSE")
        digest = self._digest_bytes(payload.digest)
        reference_id = _reference_id(payload.ledger_transaction_id)
        try:
            self._assert_network()
            function = self.contract.functions.anchorRecord(digest, reference_id)
            with self._nonce_lock:
                nonce = self.w3.eth.get_transaction_count(self.account.address, "pending")
                gas = function.estimate_gas({"from": self.account.address})
                transaction = function.build_transaction(
                    {
                        "from": self.account.address,
                        "nonce": nonce,
                        "chainId": self.chain_id,
                        "gas": max(gas + gas // 5, gas + 10_000),
                        "gasPrice": self.w3.eth.gas_price,
                    }
                )
                signed = self.w3.eth.account.sign_transaction(
                    transaction, private_key=self._private_key()
                )
                transaction_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            return ProviderTransaction(
                status="submitted",
                transaction_hash=transaction_hash.hex(),
                submitted_at=datetime.now(timezone.utc),
                contract_address=self.contract_address,
                contract_version=self.contract_version,
            )
        except BlockchainProviderError:
            raise
        except (requests.exceptions.Timeout, TimeoutError, socket.timeout) as exc:
            raise BlockchainProviderError("PROVIDER_TIMEOUT") from exc
        except (requests.exceptions.ConnectionError, OSError) as exc:
            raise BlockchainProviderError("PROVIDER_UNAVAILABLE") from exc
        except Exception as exc:
            raise BlockchainProviderError("PROVIDER_SUBMISSION_FAILED") from exc

    def get_transaction(self, transaction_hash: str) -> ProviderTransaction | None:
        try:
            self._assert_network()
            try:
                receipt = self.w3.eth.get_transaction_receipt(transaction_hash)
            except TransactionNotFound:
                return None

            block_number = int(receipt["blockNumber"])
            block = self.w3.eth.get_block(block_number)
            mined_at = datetime.fromtimestamp(int(block["timestamp"]), tz=timezone.utc)
            if int(receipt["status"]) == 0:
                return ProviderTransaction(
                    status="failed",
                    transaction_hash=transaction_hash,
                    block_number=block_number,
                    confirmed_at=mined_at,
                    failure_code="PROVIDER_TRANSACTION_REVERTED",
                    contract_address=self.contract_address,
                    contract_version=self.contract_version,
                )

            latest_block = int(self.w3.eth.block_number)
            if latest_block - block_number + 1 < self.confirmations:
                return ProviderTransaction(
                    status="submitted",
                    transaction_hash=transaction_hash,
                    block_number=block_number,
                    contract_address=self.contract_address,
                    contract_version=self.contract_version,
                )
            return ProviderTransaction(
                status="confirmed",
                transaction_hash=transaction_hash,
                block_number=block_number,
                confirmed_at=mined_at,
                contract_address=self.contract_address,
                contract_version=self.contract_version,
            )
        except BlockchainProviderError:
            raise
        except (requests.exceptions.Timeout, TimeoutError, socket.timeout) as exc:
            raise BlockchainProviderError("PROVIDER_TIMEOUT") from exc
        except (requests.exceptions.ConnectionError, OSError) as exc:
            raise BlockchainProviderError("PROVIDER_UNAVAILABLE") from exc
        except Exception as exc:
            raise BlockchainProviderError("PROVIDER_INVALID_RESPONSE") from exc

    def verify_anchor(self, digest: str) -> ProviderAnchor | None:
        digest_bytes = self._digest_bytes(digest)
        try:
            self._assert_network()
            exists, reference_id, timestamp, submitter = self.contract.functions.getAnchor(
                digest_bytes
            ).call()
            if not exists:
                return None
            return ProviderAnchor(
                digest=digest,
                reference_id=Web3.to_hex(reference_id),
                anchored_at=datetime.fromtimestamp(int(timestamp), tz=timezone.utc),
                submitter=Web3.to_checksum_address(submitter),
            )
        except BlockchainProviderError:
            raise
        except (requests.exceptions.Timeout, TimeoutError, socket.timeout) as exc:
            raise BlockchainProviderError("PROVIDER_TIMEOUT") from exc
        except (requests.exceptions.ConnectionError, OSError) as exc:
            raise BlockchainProviderError("PROVIDER_UNAVAILABLE") from exc
        except Exception as exc:
            raise BlockchainProviderError("PROVIDER_INVALID_RESPONSE") from exc

    def health_check(self) -> ProviderHealth:
        try:
            self._assert_network()
            deployed_bytecode = self.w3.eth.get_code(self.contract_address)
            if not deployed_bytecode:
                return ProviderHealth(status="unavailable")
            deployed_version = self.contract.functions.CONTRACT_VERSION().call()
            signer_authorized = self.contract.functions.authorizedSubmitters(self.account.address).call()
            if deployed_version != self.contract_version or not signer_authorized:
                return ProviderHealth(status="unavailable")
            return ProviderHealth(status="available")
        except Exception:
            return ProviderHealth(status="unavailable")

    def _assert_network(self) -> None:
        if not self.w3.is_connected():
            raise BlockchainProviderError("PROVIDER_UNAVAILABLE")
        if int(self.w3.eth.chain_id) != self.chain_id:
            raise BlockchainProviderError("PROVIDER_INVALID_RESPONSE")

    def _private_key(self) -> str:
        settings = self._settings
        if settings.blockchain_signer_private_key is None:
            raise BlockchainProviderError("PROVIDER_UNAVAILABLE")
        return settings.blockchain_signer_private_key.get_secret_value()

    @staticmethod
    def _digest_bytes(digest: str) -> bytes:
        if not _DIGEST_PATTERN.fullmatch(digest):
            raise BlockchainProviderError("PROVIDER_INVALID_RESPONSE")
        return bytes.fromhex(digest)


__all__ = ["EVMBlockchainProvider"]
