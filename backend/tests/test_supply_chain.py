
import pytest

pytestmark = pytest.mark.skip(
    reason='Supply-chain batch/shipment mutation logic is intentionally excluded from this public source distribution.',
)

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.inventory import InventoryMovement, InventoryStock
from app.models.supply_chain import InventoryBatch, InventoryShipmentEvent
from tests.test_assets import payment_world
from tests.test_payments import _headers


def _create_product(client: TestClient, world: dict[str, Any]) -> str:
    response = client.post(
        "/api/v1/products",
        headers=_headers(client),
        json={
            "organization_id": str(world["sender_organization_id"]),
            "sku": "TRACE-001",
            "name": "Traceable cotton roll",
            "category": "textile",
            "unit": "roll",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_batch(client: TestClient, world: dict[str, Any], product_id: str, code: str = "LOT-2026-09") -> str:
    response = client.post(
        "/api/v1/inventory/batches",
        headers=_headers(client),
        json={
            "organization_id": str(world["sender_organization_id"]),
            "product_id": product_id,
            "batch_code": code,
            "manufactured_on": "2026-09-01",
            "expires_on": "2027-09-01",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _movement(client: TestClient, organization_id: str, product_id: str, batch_id: str, key: str, **values: object):
    return client.post(
        "/api/v1/inventory/movements",
        headers=_headers(client, key),
        json={"organization_id": organization_id, "product_id": product_id, "batch_id": batch_id, **values},
    )


def test_batch_dispatch_transit_and_receipt_preserve_trace(payment_world: dict[str, Any]) -> None:
    sender = payment_world["sender"]
    recipient = payment_world["recipient"]
    assert isinstance(sender, TestClient) and isinstance(recipient, TestClient)
    product_id = _create_product(sender, payment_world)
    batch_id = _create_batch(sender, payment_world, product_id)
    stock = _movement(
        sender,
        str(payment_world["sender_organization_id"]),
        product_id,
        batch_id,
        "trace-stock-in-0001",
        movement_type="stock_in",
        quantity="12.000",
        destination_location="Mill A",
    )
    assert stock.status_code == 201, stock.text
    assert stock.json()["batch_code"] == "LOT-2026-09"

    payload = {
        "organization_id": str(payment_world["sender_organization_id"]),
        "recipient_account_number": payment_world["recipient_account_number"],
        "product_id": product_id,
        "batch_id": batch_id,
        "quantity": "5.000",
        "source_location": "Mill A",
        "destination_location": "Warehouse B",
        "note": "Supplier transfer",
    }
    prepared = sender.post("/api/v1/inventory/shipments", headers=_headers(sender, "shipment-create-0001"), json=payload)
    assert prepared.status_code == 201, prepared.text
    shipment = prepared.json()
    assert shipment["status"] == "PREPARED" and len(shipment["events"]) == 1
    retry = sender.post("/api/v1/inventory/shipments", headers=_headers(sender, "shipment-create-0001"), json=payload)
    assert retry.status_code == 201 and retry.json()["id"] == shipment["id"]

    dispatch = sender.post(
        f"/api/v1/inventory/shipments/{shipment['id']}/dispatch",
        headers=_headers(sender, "shipment-dispatch-0001"),
    )
    assert dispatch.status_code == 200, dispatch.text
    assert dispatch.json()["status"] == "DISPATCHED"
    transit = sender.post(
        f"/api/v1/inventory/shipments/{shipment['id']}/transit",
        headers=_headers(sender, "shipment-transit-0001"),
    )
    assert transit.status_code == 200 and transit.json()["status"] == "IN_TRANSIT"
    received = recipient.post(
        f"/api/v1/inventory/shipments/{shipment['id']}/receive",
        headers=_headers(recipient, "shipment-receive-0001"),
        json={"destination_location": "Receiving Bay 3"},
    )
    assert received.status_code == 200, received.text
    data = received.json()
    assert data["status"] == "RECEIVED" and data["receiver_user_id"] == str(payment_world["recipient_user_id"])
    assert [event["to_status"] for event in data["events"]] == ["PREPARED", "DISPATCHED", "IN_TRANSIT", "RECEIVED"]
    assert [event["sequence_number"] for event in data["events"]] == [1, 2, 3, 4]

    sender_stocks = sender.get("/api/v1/inventory/stocks").json()["items"]
    receiver_stocks = recipient.get("/api/v1/inventory/stocks").json()["items"]
    sender_stock = next(row for row in sender_stocks if row["batch_id"] == batch_id)
    received_stock = next(row for row in receiver_stocks if row["batch_id"] == batch_id)
    assert sender_stock["quantity"] == "7.000"
    assert received_stock["quantity"] == "5.000" and received_stock["location"] == "Receiving Bay 3"
    assert len(recipient.get("/api/v1/inventory/shipments").json()["items"]) == 1
    assert payment_world["outsider"].get("/api/v1/inventory/shipments").json()["items"] == []
    sender_events = sender.get("/api/v1/activity?type=shipment").json()["items"]
    recipient_events = recipient.get("/api/v1/activity?type=shipment").json()["items"]
    assert [item["event_status"] for item in reversed(sender_events)] == ["PREPARED", "DISPATCHED", "IN_TRANSIT", "RECEIVED"]
    assert [item["shipment_id"] for item in recipient_events] == [shipment["id"]] * 4
    assert payment_world["outsider"].get("/api/v1/activity?type=shipment").json()["items"] == []

    with payment_world["database"].session_factory() as session:
        assert len(session.scalars(select(InventoryShipmentEvent)).all()) == 4
        assert len(session.scalars(select(InventoryMovement)).all()) == 3
        assert len(session.scalars(select(InventoryBatch)).all()) == 1
        assert len(session.scalars(select(InventoryStock)).all()) == 2


def test_shipment_event_anchor_is_shared_provider_idempotent_and_scoped(payment_world: dict[str, Any]) -> None:
    sender = payment_world["sender"]
    outsider = payment_world["outsider"]
    assert isinstance(sender, TestClient) and isinstance(outsider, TestClient)
    organization_id = str(payment_world["sender_organization_id"])
    product_id = _create_product(sender, payment_world)
    batch_id = _create_batch(sender, payment_world, product_id, "ANCHOR-LOT-1")
    _movement(
        sender, organization_id, product_id, batch_id, "anchor-stock-in-0001",
        movement_type="stock_in", quantity="4", destination_location="Dock A",
    )
    created = sender.post("/api/v1/inventory/shipments", headers=_headers(sender, "anchor-shipment-0001"), json={
        "organization_id": organization_id,
        "recipient_account_number": payment_world["recipient_account_number"],
        "product_id": product_id,
        "batch_id": batch_id,
        "quantity": "2",
        "source_location": "Dock A",
        "destination_location": "Dock B",
    })
    assert created.status_code == 201, created.text
    shipment_id = created.json()["id"]
    dispatched = sender.post(
        f"/api/v1/inventory/shipments/{shipment_id}/dispatch",
        headers=_headers(sender, "anchor-dispatch-0001"),
    )
    assert dispatched.status_code == 200, dispatched.text
    event_id = dispatched.json()["events"][1]["id"]
    endpoint = f"/api/v1/blockchain/shipments/{shipment_id}/events/{event_id}"

    denied = outsider.post(f"{endpoint}/anchor", headers=_headers(outsider, "anchor-outsider-0001"))
    assert denied.status_code == 404
    first = sender.post(f"{endpoint}/anchor", headers=_headers(sender, "anchor-shipment-event-0001"))
    replay = sender.post(f"{endpoint}/anchor", headers=_headers(sender, "anchor-shipment-event-0002"))
    assert first.status_code == replay.status_code == 200, first.text
    anchor = first.json()
    assert anchor["shipment_event_id"] == event_id
    assert anchor["digest_version"] == "ledgerchain-shipment-event-v1"
    assert anchor["status"] == "simulated"
    assert anchor["transaction_hash"] is None and anchor["block_number"] is None
    assert replay.json()["id"] == anchor["id"]

    verification = sender.get(f"{endpoint}/verify")
    assert verification.status_code == 200, verification.text
    assert verification.json()["history_consistent"] is True
    assert verification.json()["blockchain_status"] == "SIMULATED"
    assert verification.json()["anchor_record"]["id"] == anchor["id"]

    shipments = sender.get("/api/v1/inventory/shipments").json()["items"]
    shipment = next(item for item in shipments if item["id"] == shipment_id)
    anchored_event = next(event for event in shipment["events"] if event["id"] == event_id)
    assert anchored_event["blockchain_record"]["id"] == anchor["id"]
    blockchain_activity = sender.get("/api/v1/activity?type=blockchain").json()["items"]
    assert any(item["shipment_event_id"] == event_id and item["status"] == "completed" for item in blockchain_activity)
    assert outsider.get("/api/v1/blockchain/transactions/" + anchor["id"]).status_code == 404


def test_rejected_dispatched_shipment_returns_stock_and_is_idempotent(payment_world: dict[str, Any]) -> None:
    sender = payment_world["sender"]
    recipient = payment_world["recipient"]
    assert isinstance(sender, TestClient) and isinstance(recipient, TestClient)
    product_id = _create_product(sender, payment_world)
    batch_id = _create_batch(sender, payment_world, product_id)
    _movement(
        sender,
        str(payment_world["sender_organization_id"]),
        product_id,
        batch_id,
        "reject-stock-in-0001",
        movement_type="stock_in",
        quantity="3",
        destination_location="Dock A",
    )
    payload = {
        "organization_id": str(payment_world["sender_organization_id"]),
        "recipient_account_number": payment_world["recipient_account_number"],
        "product_id": product_id,
        "batch_id": batch_id,
        "quantity": "2",
        "source_location": "Dock A",
        "destination_location": "Dock B",
    }
    created = sender.post("/api/v1/inventory/shipments", headers=_headers(sender, "reject-create-0001"), json=payload)
    assert created.status_code == 201, created.text
    shipment_id = created.json()["id"]
    dispatched = sender.post(
        f"/api/v1/inventory/shipments/{shipment_id}/dispatch",
        headers=_headers(sender, "reject-dispatch-0001"),
    )
    assert dispatched.status_code == 200, dispatched.text
    rejected = recipient.post(
        f"/api/v1/inventory/shipments/{shipment_id}/reject",
        headers=_headers(recipient, "reject-action-0001"),
        json={"reason": "Packaging damaged"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "REJECTED"
    replay = recipient.post(
        f"/api/v1/inventory/shipments/{shipment_id}/reject",
        headers=_headers(recipient, "reject-action-0001"),
        json={"reason": "Packaging damaged"},
    )
    assert replay.status_code == 200 and replay.json()["status"] == "REJECTED"
    stocks = sender.get("/api/v1/inventory/stocks").json()["items"]
    assert next(row for row in stocks if row["batch_id"] == batch_id)["quantity"] == "3.000"


def test_batch_and_shipment_routes_enforce_organization_and_stock(payment_world: dict[str, Any]) -> None:
    sender = payment_world["sender"]
    outsider = payment_world["outsider"]
    assert isinstance(sender, TestClient) and isinstance(outsider, TestClient)
    product_id = _create_product(sender, payment_world)
    batch_id = _create_batch(sender, payment_world, product_id)
    no_stock = sender.post(
        "/api/v1/inventory/shipments",
        headers=_headers(sender, "shipment-no-stock-0001"),
        json={
            "organization_id": str(payment_world["sender_organization_id"]),
            "recipient_account_number": payment_world["recipient_account_number"],
            "product_id": product_id,
            "batch_id": batch_id,
            "quantity": "1",
            "source_location": "Empty Dock",
            "destination_location": "Warehouse B",
        },
    )
    assert no_stock.status_code == 201, no_stock.text
    shipment_id = no_stock.json()["id"]
    insufficient = sender.post(
        f"/api/v1/inventory/shipments/{shipment_id}/dispatch",
        headers=_headers(sender, "shipment-no-stock-dispatch-0001"),
    )
    assert insufficient.status_code == 409
    cross_org = outsider.post(
        f"/api/v1/inventory/shipments/{shipment_id}/dispatch",
        headers=_headers(outsider, "shipment-outsider-action-0001"),
    )
    assert cross_org.status_code == 404
    assert outsider.get("/api/v1/inventory/batches").json() == []
