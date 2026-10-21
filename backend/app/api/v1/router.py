from fastapi import APIRouter

from app.api import health
from app.api.v1 import activity, assets, auth, blockchain, demo_funding, finance, inventory, ledger, payments, supply_chain, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(assets.router)
api_router.include_router(inventory.router)
api_router.include_router(supply_chain.router)
api_router.include_router(users.router)
api_router.include_router(payments.router)
api_router.include_router(demo_funding.router)
api_router.include_router(finance.router)
api_router.include_router(activity.router)
api_router.include_router(ledger.router)
api_router.include_router(blockchain.router)
