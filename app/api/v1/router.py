from fastapi import APIRouter

from app.api.v1.routes.outlets import router as outlets_router
from app.api.v1.routes.products import router as products_router
from app.api.v1.routes.retailer_product_mappings import router as mappings_router

router = APIRouter()
router.include_router(products_router)
router.include_router(outlets_router)
router.include_router(mappings_router)
