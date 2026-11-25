import logging

from fastapi import APIRouter, HTTPException

from app.schemas.supplier import (
    SupplierResearchRequest,
    SupplierResearchResponse
)

from app.services.supplier_research import research_suppliers


router = APIRouter(
    prefix="/api/suppliers",
    tags=["Suppliers"]
)

logger = logging.getLogger(__name__)


@router.post(
    "/research",
    response_model=SupplierResearchResponse
)
def search_suppliers(request: SupplierResearchRequest):

    try:

        result = research_suppliers(
            product_or_service=request.product_or_service,
            location=request.location,
            max_results=request.max_results
        )

        return result

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:

        logger.exception("Supplier research failed")

        raise HTTPException(
            status_code=502,
            detail="Supplier research service is temporarily unavailable."
        )