
import pytest

pytestmark = pytest.mark.skip(
    reason='Backend-to-contract verification workflow is intentionally excluded from this public source distribution.',
)

import json
from pathlib import Path

import pytest
from eth_tester.exceptions import TransactionFailed
from web3 import EthereumTesterProvider, Web3

_ARTIFACT_PATH = Path(__file__).parents[1] / "contracts" / "artifacts" / "LedgerAnchorRegistry.json"


def _deploy_contract() -> tuple[Web3, object]:
    artifact = json.loads(_ARTIFACT_PATH.read_text(encoding="utf-8"))
    web3 = Web3(EthereumTesterProvider())
    web3.eth.default_account = web3.eth.accounts[0]
    factory = web3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    receipt = web3.eth.wait_for_transaction_receipt(factory.constructor().transact())
    contract = web3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])
    return web3, contract


def test_authorized_anchor_is_stored_and_emits_only_the_anchor_event() -> None:
    web3, contract = _deploy_contract()
    owner = web3.eth.accounts[0]
    digest = bytes.fromhex("11" * 32)
    reference = bytes.fromhex("22" * 32)

    receipt = web3.eth.wait_for_transaction_receipt(
        contract.functions.anchorRecord(digest, reference).transact({"from": owner})
    )
    assert receipt.status == 1
    assert contract.functions.verifyRecord(digest, reference).call()
    assert not contract.functions.verifyRecord(digest, bytes.fromhex("33" * 32)).call()
    block = web3.eth.get_block(receipt.blockNumber)
    assert tuple(contract.functions.getAnchor(digest).call()) == (True, reference, block.timestamp, owner)
    events = contract.events.RecordAnchored().process_receipt(receipt)
    assert len(events) == 1
    assert bytes(events[0]["args"]["digest"]) == digest
    assert bytes(events[0]["args"]["referenceId"]) == reference
    assert events[0]["args"]["submitter"] == owner


def test_unauthorized_empty_and_duplicate_anchors_are_rejected_without_mutation() -> None:
    web3, contract = _deploy_contract()
    owner, unauthorized = web3.eth.accounts[:2]
    digest = bytes.fromhex("44" * 32)
    reference = bytes.fromhex("55" * 32)

    with pytest.raises(TransactionFailed):
        contract.functions.anchorRecord(digest, reference).transact({"from": unauthorized})
    with pytest.raises(TransactionFailed):
        contract.functions.anchorRecord(bytes(32), reference).transact({"from": owner})
    with pytest.raises(TransactionFailed):
        contract.functions.anchorRecord(digest, bytes(32)).transact({"from": owner})

    first_receipt = web3.eth.wait_for_transaction_receipt(
        contract.functions.anchorRecord(digest, reference).transact({"from": owner})
    )
    original = contract.functions.getAnchor(digest).call()
    assert tuple(contract.functions.anchorRecord(digest, reference).call({"from": owner})) == (
        original[2],
        False,
    )
    duplicate_receipt = web3.eth.wait_for_transaction_receipt(
        contract.functions.anchorRecord(digest, reference).transact({"from": owner})
    )
    assert duplicate_receipt.status == 1
    assert not contract.events.RecordAnchored().process_receipt(duplicate_receipt)
    assert contract.functions.getAnchor(digest).call() == original
    assert first_receipt.status == 1

    with pytest.raises(TransactionFailed):
        contract.functions.anchorRecord(bytes.fromhex("66" * 32), reference).transact({"from": owner})
    with pytest.raises(TransactionFailed):
        contract.functions.anchorRecord(digest, bytes.fromhex("77" * 32)).transact({"from": owner})
    assert contract.functions.getAnchor(digest).call() == original


def test_owner_controls_submitter_authorization_and_owner_event() -> None:
    web3, contract = _deploy_contract()
    owner, submitter, outsider = web3.eth.accounts[:3]
    digest = bytes.fromhex("88" * 32)
    reference = bytes.fromhex("99" * 32)

    with pytest.raises(TransactionFailed):
        contract.functions.setAuthorizedSubmitter(submitter, True).transact({"from": outsider})
    with pytest.raises(TransactionFailed):
        contract.functions.setAuthorizedSubmitter("0x0000000000000000000000000000000000000000", True).transact(
            {"from": owner}
        )

    receipt = web3.eth.wait_for_transaction_receipt(
        contract.functions.setAuthorizedSubmitter(submitter, True).transact({"from": owner})
    )
    authorization_events = contract.events.SubmitterAuthorizationUpdated().process_receipt(receipt)
    assert len(authorization_events) == 1
    assert authorization_events[0]["args"]["submitter"] == submitter
    assert authorization_events[0]["args"]["authorized"] is True
    assert contract.functions.authorizedSubmitters(submitter).call()

    anchored = web3.eth.wait_for_transaction_receipt(
        contract.functions.anchorRecord(digest, reference).transact({"from": submitter})
    )
    assert anchored.status == 1
    web3.eth.wait_for_transaction_receipt(
        contract.functions.setAuthorizedSubmitter(submitter, False).transact({"from": owner})
    )
    with pytest.raises(TransactionFailed):
        contract.functions.anchorRecord(bytes.fromhex("aa" * 32), bytes.fromhex("bb" * 32)).transact(
            {"from": submitter}
        )
    assert contract.functions.getAnchor(digest).call()[0]
