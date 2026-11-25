from app.schemas.scoring import SupplierScoringRequest
from app.services.supplier_scoring import (
    calculate_supplier_score,
    rank_suppliers
)


def test_supplier_scoring():

    supplier = SupplierScoringRequest(
        supplier_name="CK Pumps",
        verification_score=85,
        product_relevance=True,
        location_relevance=True,
        website_verified=True,
        evidence_available=True
    )

    result = calculate_supplier_score(supplier)

    assert result.overall_score == 94
    assert result.supplier_rating == "Excellent"


def test_supplier_ranking():

    suppliers = [
        SupplierScoringRequest(
            supplier_name="Supplier A",
            verification_score=60,
            product_relevance=True,
            location_relevance=True,
            website_verified=False,
            evidence_available=True
        ),

        SupplierScoringRequest(
            supplier_name="Supplier B",
            verification_score=90,
            product_relevance=True,
            location_relevance=True,
            website_verified=True,
            evidence_available=True
        )
    ]

    results = rank_suppliers(suppliers)

    assert results[0].supplier_name == "Supplier B"
    assert results[0].ranking == 1
    assert results[1].ranking == 2