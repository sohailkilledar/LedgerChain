"""Import ORM models so Alembic and metadata-based tests see every table."""

from app.models.account import NotificationPreferences, Organization, OrganizationMembership, UserSettings
from app.models.asset import Asset, AssetEvent, AssetOwnership, Product
from app.models.auth import AuthSession, AuthToken, User
from app.models.blockchain import BlockchainRecord
from app.models.demo_funding import DemoFunding
from app.models.finance import FinanceBudget, PaymentRequest, PaymentRequestEvent
from app.models.inventory import InventoryMovement, InventoryStock
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.models.payment import Payment
from app.models.supply_chain import InventoryBatch, InventoryShipment, InventoryShipmentEvent

__all__ = [
    "Asset", "AssetEvent", "AssetOwnership", "AuthSession", "AuthToken", "BlockchainRecord",
    "DemoFunding", "FinanceBudget", "InventoryBatch", "InventoryMovement", "InventoryShipment",
    "InventoryShipmentEvent", "InventoryStock", "LedgerEntry", "LedgerTransaction",
    "NotificationPreferences", "Organization", "OrganizationMembership", "Payment", "PaymentRequest",
    "PaymentRequestEvent", "Product", "User", "UserSettings",
]
