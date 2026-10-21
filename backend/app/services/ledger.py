from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import ConflictError, InternalError, NotFoundError
from app.models.account import Organization
from app.models.asset import AssetEvent, Product
from app.models.auth import User
from app.models.finance import FinanceBudget, PaymentRequest, PaymentRequestEvent
from app.models.inventory import InventoryMovement
from app.models.supply_chain import InventoryBatch, InventoryShipment, InventoryShipmentEvent
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.models.payment import Payment
from app.repositories.asset import AssetRepository
from app.repositories.blockchain import BlockchainRepository
from app.repositories.inventory import InventoryRepository
from app.repositories.ledger import LedgerRepository
from app.repositories.payment import PaymentAccountRepository
from app.schemas.inventory import InventoryActivityResponse
from app.schemas.ledger import (
    ActivityItem,
    ActivityPage,
    ActivityResponse,
    AssetActivityResponse,
    BlockchainActivityResponse,
    FinanceActivityResponse,
    LedgerEntryResponse,
    LedgerTransactionResponse,
    ShipmentActivityResponse,
)


class LedgerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.ledger = LedgerRepository(session)
        self.accounts = PaymentAccountRepository(session)

    def post_payment(self, payment: Payment) -> LedgerTransaction:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )

    def get_transaction(self, transaction_id: UUID, user: User) -> LedgerTransactionResponse:
        found = self.ledger.get_with_payment(transaction_id)
        if found is None:
            raise NotFoundError("The ledger transaction was not found.", code="LEDGER_TRANSACTION_NOT_FOUND")
        transaction, payment = found
        allowed = payment.sender_user_id == user.id or self.ledger.has_membership(
            user.id, payment.sender_organization_id
        ) or self.ledger.has_membership(user.id, payment.recipient_organization_id)
        if not allowed:
            raise NotFoundError("The ledger transaction was not found.", code="LEDGER_TRANSACTION_NOT_FOUND")
        if transaction.status != "posted" or transaction.posted_at is None:
            raise NotFoundError("The ledger transaction was not found.", code="LEDGER_TRANSACTION_NOT_FOUND")
        entries = self.ledger.entries_for_transaction(transaction.id)
        return LedgerTransactionResponse(
            id=transaction.id,
            payment_id=payment.id,
            reference=transaction.reference,
            transaction_type="payment_transfer",
            status="posted",
            amount=transaction.amount,
            currency="INR",
            created_at=transaction.created_at,
            posted_at=transaction.posted_at,
            entries=[
                LedgerEntryResponse(
                    id=entry.id,
                    account_id=entry.account_id,
                    direction=entry.direction,
                    amount=entry.amount,
                    currency="INR",
                    timestamp=entry.created_at,
                    description=entry.description,
                )
                for entry in entries
            ],
        )

    def list_activity(
        self, user: User, *, limit: int, offset: int, activity_type: str | None = None
    ) -> ActivityPage:
        organization_ids = self.accounts.organization_ids_for_user(user.id)
        window = limit + offset + 1
        records: list[tuple[datetime, str, ActivityItem]] = []

        if activity_type in (None, "payment"):
            payment_rows = self.ledger.activity_for_user(
                user.id, organization_ids, activity_type="payment", limit=window, offset=0
            )
            for payment, transaction, sender in payment_rows:
                outgoing = payment.sender_user_id == user.id or payment.sender_organization_id in organization_ids
                counterparty_name = payment.recipient_name if outgoing else sender.name
                counterparty_account = payment.recipient_account_number if outgoing else payment.sender_account_number
                activity = ActivityResponse(
                    id=transaction.id,
                    type="payment",
                    status="completed",
                    title="Payment sent" if outgoing else "Payment received",
                    summary=(
                        f"Payment to {counterparty_name} completed"
                        if outgoing
                        else f"Payment from {counterparty_name} received"
                    ),
                    direction="outgoing" if outgoing else "incoming",
                    amount=payment.amount,
                    currency="INR",
                    counterparty=counterparty_name,
                    counterparty_account=counterparty_account,
                    timestamp=payment.completed_at or transaction.posted_at or transaction.created_at,
                    reference=payment.reference,
                    payment_id=payment.id,
                    ledger_transaction_id=transaction.id,
                )
                records.append((activity.timestamp, str(activity.id), activity))

        if activity_type in (None, "finance") and organization_ids:
            finance_rows = self.session.execute(
                select(PaymentRequestEvent, PaymentRequest)
                .join(PaymentRequest, PaymentRequest.id == PaymentRequestEvent.payment_request_id)
                .where(PaymentRequest.organization_id.in_(organization_ids))
                .order_by(PaymentRequestEvent.created_at.desc(), PaymentRequestEvent.id.desc())
                .limit(window)
            ).all()
            finance_titles = {
                "DRAFT": "Payment request created",
                "SUBMITTED": "Payment request submitted",
                "APPROVED": "Payment request approved",
                "REJECTED": "Payment request rejected",
                "PAYMENT_CREATED": "Payment created",
                "COMPLETED": "Payment request completed",
            }
            for event, request in finance_rows:
                status = "completed" if event.to_status == "COMPLETED" else "failed" if event.to_status == "REJECTED" else "pending"
                title = finance_titles.get(event.to_status, "Payment request updated")
                activity = FinanceActivityResponse(
                    id=event.id,
                    finance_record_type="payment_request",
                    status=status,
                    title=title,
                    summary=f"₹{request.amount:.2f} request to {request.recipient_name} {event.to_status.lower().replace('_', ' ')}.",
                    timestamp=event.created_at,
                    reference=str(request.id),
                    payment_request_id=request.id,
                    payment_id=request.payment_id,
                    budget_id=request.budget_id,
                    request_status=request.status,
                    event_status=event.to_status,
                    sequence_number=event.sequence_number,
                    recipient_name=request.recipient_name,
                    recipient_account=request.recipient_account_number,
                    amount=request.amount,
                    currency="INR",
                    actor_user_id=event.actor_user_id,
                    actor_organization_id=request.organization_id,
                    detail=event.detail,
                )
                records.append((activity.timestamp, f"finance:{request.id}:{event.sequence_number:010d}", activity))

            budget_rows = self.session.scalars(
                select(FinanceBudget)
                .where(FinanceBudget.organization_id.in_(organization_ids))
                .order_by(FinanceBudget.created_at.desc(), FinanceBudget.id.desc())
                .limit(window)
            ).all()
            for budget in budget_rows:
                activity = FinanceActivityResponse(
                    id=budget.id,
                    finance_record_type="budget",
                    status="completed",
                    title="Budget created",
                    summary=f"{budget.name} budget created with ₹{budget.allocated_amount:.2f} allocated.",
                    timestamp=budget.created_at,
                    reference=str(budget.id),
                    budget_id=budget.id,
                    budget_name=budget.name,
                    budget_category=budget.category,
                    budget_period_start=budget.period_start,
                    budget_period_end=budget.period_end,
                    event_status="CREATED",
                    sequence_number=1,
                    amount=budget.allocated_amount,
                    currency="INR",
                    actor_user_id=budget.created_by_user_id,
                    actor_organization_id=budget.organization_id,
                )
                records.append((activity.timestamp, f"budget:{budget.id}", activity))

        if activity_type in (None, "shipment") and organization_ids:
            sender = aliased(Organization)
            recipient = aliased(Organization)
            shipment_rows = self.session.execute(
                select(InventoryShipmentEvent, InventoryShipment, sender, recipient, Product, InventoryBatch)
                .join(InventoryShipment, InventoryShipment.id == InventoryShipmentEvent.shipment_id)
                .join(sender, sender.id == InventoryShipment.sender_organization_id)
                .join(recipient, recipient.id == InventoryShipment.recipient_organization_id)
                .join(Product, Product.id == InventoryShipment.product_id)
                .join(InventoryBatch, InventoryBatch.id == InventoryShipment.batch_id)
                .where(
                    or_(
                        InventoryShipment.sender_organization_id.in_(organization_ids),
                        InventoryShipment.recipient_organization_id.in_(organization_ids),
                    )
                )
                .order_by(InventoryShipmentEvent.created_at.desc(), InventoryShipmentEvent.id.desc())
                .limit(window)
            ).all()
            shipment_titles = {
                "PREPARED": "Shipment prepared",
                "DISPATCHED": "Batch dispatched",
                "IN_TRANSIT": "Batch in transit",
                "RECEIVED": "Batch received",
                "REJECTED": "Shipment rejected",
            }
            for event, shipment, sender_org, recipient_org, product, batch in shipment_rows:
                status = "completed" if event.to_status == "RECEIVED" else "failed" if event.to_status == "REJECTED" else "pending"
                title = shipment_titles.get(event.to_status, "Shipment updated")
                quantity = f"{shipment.quantity:.3f}".rstrip("0").rstrip(".")
                unit = f" {product.unit}" if product.unit else ""
                activity = ShipmentActivityResponse(
                    id=event.id,
                    status=status,
                    title=title,
                    summary=f"{quantity}{unit} of {product.name} · lot {batch.batch_code}: {sender_org.name} to {recipient_org.name}.",
                    timestamp=event.created_at,
                    reference=str(shipment.id),
                    shipment_id=shipment.id,
                    shipment_status=shipment.status,
                    event_status=event.to_status,
                    sequence_number=event.sequence_number,
                    actor_user_id=event.actor_user_id,
                    actor_organization_id=event.actor_organization_id,
                    sender_organization_id=sender_org.id,
                    sender_name=sender_org.name,
                    sender_account_number=sender_org.account_number,
                    recipient_organization_id=recipient_org.id,
                    recipient_name=recipient_org.name,
                    recipient_account_number=recipient_org.account_number,
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    batch_id=batch.id,
                    batch_code=batch.batch_code,
                    quantity=shipment.quantity,
                    unit=product.unit,
                    source_location=shipment.source_location,
                    destination_location=shipment.destination_location,
                    detail=event.detail,
                )
                records.append((activity.timestamp, f"shipment:{shipment.id}:{event.sequence_number:010d}", activity))

        if activity_type in (None, "inventory"):
            movements = InventoryRepository(self.session).movements_for_activity(organization_ids, limit=window)
            for movement, product, actor in movements:
                amount = movement.adjustment_delta if movement.movement_type == "adjustment" else movement.quantity
                unit = f" {product.unit}" if product.unit else ""
                if movement.movement_type == "stock_in":
                    title = "Stock received"
                    summary = f"{amount}{unit} of {product.name} received at {movement.destination_location}."
                elif movement.movement_type == "stock_out":
                    title = "Stock dispatched"
                    summary = f"{amount}{unit} of {product.name} dispatched from {movement.source_location}."
                elif movement.movement_type == "movement":
                    title = "Stock moved"
                    summary = f"{amount}{unit} of {product.name} moved from {movement.source_location} to {movement.destination_location}."
                else:
                    title = "Inventory adjusted"
                    summary = f"{product.name} at {movement.destination_location} adjusted by {amount}{unit}."
                activity = InventoryActivityResponse(
                    id=movement.id,
                    title=title,
                    summary=summary,
                    timestamp=movement.created_at,
                    reference=str(movement.id),
                    organization_id=movement.organization_id,
                    product_id=product.id,
                    sku=product.sku,
                    product_name=product.name,
                    movement_type=movement.movement_type,
                    quantity=movement.quantity,
                    unit=product.unit,
                    source_location=movement.source_location,
                    destination_location=movement.destination_location,
                    adjustment_delta=movement.adjustment_delta,
                    reason=movement.reason,
                    actor_user_id=actor.id,
                )
                records.append((activity.timestamp, str(activity.id), activity))

        if activity_type in (None, "asset"):
            events = AssetRepository(self.session).events_for_activity(organization_ids, limit=window)
            titles = {
                "REGISTERED": ("Asset registered", "registered"),
                "TRANSFERRED": ("Ownership transferred", "had ownership transferred"),
                "CUSTODY_CHANGED": ("Custody changed", "had its custody changed"),
                "RETIRED": ("Asset retired", "was retired"),
                "PROVENANCE_RECORDED": ("Provenance recorded", "had provenance recorded"),
            }
            for event, asset, _actor in events:
                title, action = titles.get(event.event_type, ("Asset event", "was updated"))
                activity = AssetActivityResponse(
                    id=event.id,
                    title=title,
                    summary=f"{asset.name} ({asset.asset_identifier}) {action}.",
                    timestamp=event.created_at,
                    reference=str(event.id),
                    asset_id=asset.id,
                    asset_name=asset.name,
                    asset_identifier=asset.asset_identifier,
                    event_type=event.event_type,
                    sequence_number=event.sequence_number,
                    actor_user_id=event.actor_user_id,
                    actor_organization_id=event.actor_organization_id,
                    previous_state=event.previous_state,
                    resulting_state=event.resulting_state,
                    metadata=event.metadata_json,
                )
                records.append((activity.timestamp, f"asset:{asset.id}:{event.sequence_number:010d}", activity))

        if activity_type in (None, "blockchain"):
            blockchain = BlockchainRepository(self.session)
            anchor_rows = [
                *blockchain.asset_records_for_user(organization_ids, limit=window),
                *blockchain.shipment_records_for_user(organization_ids, limit=window),
                *blockchain.payment_records_for_user(user.id, organization_ids, limit=window),
            ]
            for row in anchor_rows:
                record = row[0]
                if record.asset_event_id is not None:
                    event, asset = row[1], row[2]
                    subject = f"{asset.name} event {event.sequence_number}"
                elif record.shipment_event_id is not None:
                    event, shipment = row[1], row[2]
                    subject = f"Shipment {shipment.id} event {event.sequence_number}"
                else:
                    transaction, payment = row[1], row[2]
                    subject = f"Payment {payment.reference}"
                if record.status == "simulated":
                    state = "simulated in development; no public-chain transaction was created"
                    activity_status = "completed"
                elif record.status == "confirmed":
                    state = f"confirmed on {record.network}"
                    activity_status = "completed"
                elif record.status in {"failed", "submission_failed"}:
                    state = "failed and requires attention"
                    activity_status = "failed"
                else:
                    state = "submitted; confirmation pending" if record.status == "submitted" else "submission in progress"
                    activity_status = "pending"
                activity = BlockchainActivityResponse(
                    id=record.id,
                    status=activity_status,
                    title="Blockchain anchor " + ("confirmed" if record.status == "confirmed" else "recorded" if record.status == "simulated" else "updated"),
                    summary=f"{subject} anchor {state} via {record.provider}.",
                    timestamp=record.updated_at,
                    reference=str(record.id),
                    anchor_status=record.status,
                    provider=record.provider,
                    network=record.network,
                    digest=record.digest,
                    digest_version=record.digest_version,
                    asset_event_id=record.asset_event_id,
                    shipment_event_id=record.shipment_event_id,
                    ledger_transaction_id=record.ledger_transaction_id,
                    transaction_hash=record.transaction_hash,
                    block_number=record.block_number,
                    confirmed_at=record.confirmed_at,
                )
                records.append((activity.timestamp, str(activity.id), activity))

        records.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
        has_more = len(records) > offset + limit
        items = [entry[2] for entry in records[offset : offset + limit]]
        return ActivityPage(items=items, limit=limit, offset=offset, has_more=has_more)

    def _assert_balanced(self, transaction_id: UUID, expected_amount: Decimal) -> None:
        raise ServiceUnavailableError(
            "This workflow is intentionally unavailable in the public source release. "
            "The deployed LedgerChain application is separate from this source distribution.",
            code="PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE",
            retryable=False,
        )


__all__ = ["LedgerService"]
