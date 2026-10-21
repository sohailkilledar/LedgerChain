
import pytest

pytestmark = pytest.mark.skip(
    reason='Inventory mutation workflow logic is intentionally excluded from this public source distribution.',
)

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.inventory import InventoryMovement, InventoryStock
from tests.test_assets import payment_world
from tests.test_payments import _headers


def _product(client: TestClient, world: dict[str, Any]) -> str:
    response = client.post(
        "/api/v1/products",
        headers=_headers(client),
        json={
            "organization_id": str(world["sender_organization_id"]),
            "sku": "INV-001",
            "name": "Traceable cotton roll",
            "category": "textile",
            "unit": "roll",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _movement(client: TestClient, organization_id: str, product_id: str, key: str, **values: object):
    return client.post(
        "/api/v1/inventory/movements",
        headers=_headers(client, key),
        json={"organization_id": organization_id, "product_id": product_id, **values},
    )


def test_inventory_receipt_dispatch_movement_adjustment_and_activity(payment_world: dict[str, Any]) -> None:
    client = payment_world["sender"]
    assert isinstance(client, TestClient)
    organization_id = str(payment_world["sender_organization_id"])
    product_id = _product(client, payment_world)

    received = _movement(
        client, organization_id, product_id, "inventory-receive-0001",
        movement_type="stock_in", quantity="12.000", destination_location="Dock A", low_stock_threshold="3",
    )
    assert received.status_code == 201, received.text
    movement_id = received.json()["id"]
    retry = _movement(
        client, organization_id, product_id, "inventory-receive-0001",
        movement_type="stock_in", quantity="12.000", destination_location="Dock A", low_stock_threshold="3",
    )
    assert retry.status_code == 201 and retry.json()["id"] == movement_id
    key_conflict = _movement(
        client, organization_id, product_id, "inventory-receive-0001",
        movement_type="stock_in", quantity="13.000", destination_location="Dock A", low_stock_threshold="3",
    )
    assert key_conflict.status_code == 409

    dispatched = _movement(
        client, organization_id, product_id, "inventory-dispatch-0001",
        movement_type="stock_out", quantity="4", source_location="Dock A",
    )
    assert dispatched.status_code == 201, dispatched.text
    moved = _movement(
        client, organization_id, product_id, "inventory-move-0001",
        movement_type="movement", quantity="3", source_location="Dock A", destination_location="Warehouse B",
    )
    assert moved.status_code == 201, moved.text
    adjusted = _movement(
        client, organization_id, product_id, "inventory-adjust-0001",
        movement_type="adjustment", quantity="1", adjustment_delta="-1", destination_location="Warehouse B",
        reason="Cycle count correction",
    )
    assert adjusted.status_code == 201, adjusted.text

    stocks = client.get("/api/v1/inventory/stocks").json()["items"]
    balances = {stock["location"]: stock["quantity"] for stock in stocks}
    assert balances == {"Dock A": "5.000", "Warehouse B": "2.000"}
    dock = next(stock for stock in stocks if stock["location"] == "Dock A")
    warehouse = next(stock for stock in stocks if stock["location"] == "Warehouse B")
    assert dock["low_stock_threshold"] == "3.000" and dock["is_low_stock"] is False
    assert warehouse["is_low_stock"] is False

    insufficient = _movement(
        client, organization_id, product_id, "inventory-dispatch-low-0001",
        movement_type="stock_out", quantity="3", source_location="Warehouse B",
    )
    assert insufficient.status_code == 409
    assert len(client.get("/api/v1/inventory/movements").json()["items"]) == 4

    activity = client.get("/api/v1/activity?limit=20").json()["items"]
    assert sum(item["type"] == "inventory" for item in activity) == 4
    assert any(item["id"] == movement_id and item["movement_type"] == "stock_in" for item in activity)


def test_inventory_requires_csrf_organization_membership_and_active_product(payment_world: dict[str, Any]) -> None:
    sender = payment_world["sender"]
    outsider = payment_world["outsider"]
    assert isinstance(sender, TestClient) and isinstance(outsider, TestClient)
    organization_id = str(payment_world["sender_organization_id"])
    product_id = _product(sender, payment_world)

    no_csrf = sender.post(
        "/api/v1/inventory/movements",
        json={
            "organization_id": organization_id,
            "product_id": product_id,
            "movement_type": "stock_in",
            "quantity": "2",
            "destination_location": "Dock A",
        },
    )
    assert no_csrf.status_code == 403

    cross_organization = _movement(
        outsider, organization_id, product_id, "inventory-outsider-0001",
        movement_type="stock_in", quantity="2", destination_location="Dock A",
    )
    assert cross_organization.status_code == 404
    assert outsider.get("/api/v1/inventory/stocks").json()["items"] == []

    invalid = _movement(
        sender, organization_id, product_id, "inventory-invalid-0001",
        movement_type="movement", quantity="1", source_location="Dock A", destination_location="Dock A",
    )
    assert invalid.status_code == 422
    with payment_world["database"].session_factory() as session:
        assert session.scalar(select(InventoryMovement)) is None
        assert session.scalar(select(InventoryStock)) is None


def test_inventory_activity_is_organization_scoped(payment_world: dict[str, Any]) -> None:
    sender = payment_world["sender"]
    outsider = payment_world["outsider"]
    assert isinstance(sender, TestClient) and isinstance(outsider, TestClient)
    organization_id = str(payment_world["sender_organization_id"])
    product_id = _product(sender, payment_world)
    response = _movement(
        sender, organization_id, product_id, "inventory-visible-0001",
        movement_type="stock_in", quantity="2", destination_location="Dock A",
    )
    assert response.status_code == 201

    visible = sender.get("/api/v1/activity?type=inventory").json()["items"]
    hidden = outsider.get("/api/v1/activity?type=inventory").json()["items"]
    assert len(visible) == 1 and visible[0]["type"] == "inventory"
    assert hidden == []
