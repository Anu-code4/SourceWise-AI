from fastapi import APIRouter, HTTPException

from app.schemas.scoring import (
    SupplierScoringRequest,
    SupplierScore
)

from app.services.supplier_scoring import calculate_supplier_score


router = APIRouter(
    prefix="/api/suppliers",
    tags=["Supplier Scoring"]
)


@router.post(
    "/score",
    response_model=SupplierScore
)
def score_supplier(request: SupplierScoringRequest):

    try:
        return calculate_supplier_score(request)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Supplier scoring failed."
        )


@router.post(
    "/rank",
    response_model=list[SupplierScore]
)
def rank_supplier_list(
    requests: list[SupplierScoringRequest]
):

    try:
        from app.services.supplier_scoring import rank_suppliers

        return rank_suppliers(requests)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Supplier ranking failed."
        )