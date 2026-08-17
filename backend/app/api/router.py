"""API v1 router aggregator."""
from fastapi import APIRouter

from app.api.v1 import (
    accounting,
    auth,
    banking,
    bir,
    business,
    fixed_assets,
    inventory,
    purchases,
    reports,
    sales,
    tax,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(business.router)
api_router.include_router(accounting.router)
api_router.include_router(tax.router)
api_router.include_router(sales.router)
api_router.include_router(purchases.router)
api_router.include_router(banking.router)
api_router.include_router(bir.router)
api_router.include_router(inventory.router)
api_router.include_router(fixed_assets.router)
api_router.include_router(reports.router)
