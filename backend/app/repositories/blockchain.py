from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.account import Organization
from app.models.asset import Asset, AssetEvent, Product
from app.models.blockchain import BlockchainRecord
from app.models.ledger import LedgerTransaction
from app.models.payment import Payment
from app.models.supply_chain import InventoryBatch, InventoryShipment, InventoryShipmentEvent
from sqlalchemy.orm import aliased


class BlockchainRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_ledger_transaction(self, ledger_transaction_id: UUID) -> BlockchainRecord | None:
        return self.session.scalar(
            select(BlockchainRecord).where(BlockchainRecord.ledger_transaction_id == ledger_transaction_id)
        )

    def get_by_asset_event(self, asset_event_id: UUID) -> BlockchainRecord | None:
        return self.session.scalar(
            select(BlockchainRecord).where(BlockchainRecord.asset_event_id == asset_event_id)
        )

    def get_by_shipment_event(self, shipment_event_id: UUID) -> BlockchainRecord | None:
        return self.session.scalar(
            select(BlockchainRecord).where(BlockchainRecord.shipment_event_id == shipment_event_id)
        )

    def get(self, record_id: UUID) -> BlockchainRecord | None:
        return self.session.get(BlockchainRecord, record_id)

    def add(self, record: BlockchainRecord) -> None:
        self.session.add(record)

    def asset_records_for_user(self, organization_ids: list[UUID], *, limit: int) -> list[tuple[BlockchainRecord, AssetEvent, Asset]]:
        if not organization_ids:
            return []
        return [
            tuple(row)
            for row in self.session.execute(
                select(BlockchainRecord, AssetEvent, Asset)
                .join(AssetEvent, AssetEvent.id == BlockchainRecord.asset_event_id)
                .join(Asset, Asset.id == AssetEvent.asset_id)
                .where(
                    or_(
                        Asset.organization_id.in_(organization_ids),
                        Asset.current_owner_organization_id.in_(organization_ids),
                        Asset.current_custodian_organization_id.in_(organization_ids),
                        AssetEvent.actor_organization_id.in_(organization_ids),
                    )
                )
                .order_by(BlockchainRecord.updated_at.desc(), BlockchainRecord.id.desc())
                .limit(limit)
            ).all()
        ]

    def shipment_records_for_user(
        self, organization_ids: list[UUID], *, limit: int
    ) -> list[tuple[BlockchainRecord, InventoryShipmentEvent, InventoryShipment, Organization, Organization, Product, InventoryBatch]]:
        if not organization_ids:
            return []
        sender = aliased(Organization)
        recipient = aliased(Organization)
        return [
            tuple(row)
            for row in self.session.execute(
                select(BlockchainRecord, InventoryShipmentEvent, InventoryShipment, sender, recipient, Product, InventoryBatch)
                .join(InventoryShipmentEvent, InventoryShipmentEvent.id == BlockchainRecord.shipment_event_id)
                .join(InventoryShipment, InventoryShipment.id == InventoryShipmentEvent.shipment_id)
                .join(sender, sender.id == InventoryShipment.sender_organization_id)
                .join(recipient, recipient.id == InventoryShipment.recipient_organization_id)
                .join(Product, Product.id == InventoryShipment.product_id)
                .join(InventoryBatch, InventoryBatch.id == InventoryShipment.batch_id)
                .where(
                    InventoryShipment.sender_organization_id.in_(organization_ids)
                    | InventoryShipment.recipient_organization_id.in_(organization_ids)
                )
                .order_by(BlockchainRecord.updated_at.desc(), BlockchainRecord.id.desc())
                .limit(limit)
            ).all()
        ]

    def payment_records_for_user(
        self, user_id: UUID, organization_ids: list[UUID], *, limit: int
    ) -> list[tuple[BlockchainRecord, LedgerTransaction, Payment]]:
        visibility = [Payment.sender_user_id == user_id]
        if organization_ids:
            visibility.extend(
                [Payment.sender_organization_id.in_(organization_ids), Payment.recipient_organization_id.in_(organization_ids)]
            )
        return [
            tuple(row)
            for row in self.session.execute(
                select(BlockchainRecord, LedgerTransaction, Payment)
                .join(LedgerTransaction, LedgerTransaction.id == BlockchainRecord.ledger_transaction_id)
                .join(Payment, Payment.id == LedgerTransaction.payment_id)
                .where(or_(*visibility))
                .order_by(BlockchainRecord.updated_at.desc(), BlockchainRecord.id.desc())
                .limit(limit)
            ).all()
        ]


__all__ = ["BlockchainRepository"]
