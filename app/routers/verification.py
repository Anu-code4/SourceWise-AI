import logging

from fastapi import APIRouter, HTTPException

from app.schemas.verification import (
    SupplierVerificationRequest,
    VerificationResult
)

from app.services.supplier_verification import verify_supplier


router = APIRouter(
    prefix="/api/suppliers",
    tags=["Supplier Verification"]
)

logger = logging.getLogger(__name__)


@router.post(
    "/verify",
    response_model=VerificationResult
)
def verify_supplier_api(request: SupplierVerificationRequest):

    try:
        return verify_supplier(
            supplier_name=request.supplier_name,
            product_or_service=request.product_or_service,
            location=request.location,
            website=request.website
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception:
        logger.exception("Supplier verification failed")

        raise HTTPException(
            status_code=502,
            detail="Supplier verification service is temporarily unavailable."
        )