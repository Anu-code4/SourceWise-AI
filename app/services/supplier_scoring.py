from app.schemas.scoring import SupplierScoringRequest, SupplierScore


def calculate_supplier_score(
    supplier: SupplierScoringRequest
):

    # Verification contributes 40%
    verification_points = (
        supplier.verification_score * 0.40
    )

    # Product relevance contributes 25%
    product_points = (
        25 if supplier.product_relevance else 0
    )

    # Location relevance contributes 15%
    location_points = (
        15 if supplier.location_relevance else 0
    )

    # Website verification contributes 10%
    website_points = (
        10 if supplier.website_verified else 0
    )

    # Evidence availability contributes 10%
    evidence_points = (
        10 if supplier.evidence_available else 0
    )

    total_score = (
        verification_points
        + product_points
        + location_points
        + website_points
        + evidence_points
    )

    if total_score >= 80:
        rating = "Excellent"
        recommendation = "Strong candidate for procurement evaluation."

    elif total_score >= 60:
        rating = "Good"
        recommendation = "Suitable for further supplier assessment."

    elif total_score >= 40:
        rating = "Average"
        recommendation = "Additional verification is recommended."

    else:
        rating = "Poor"
        recommendation = "Insufficient evidence for recommendation."

    return SupplierScore(
        supplier_name=supplier.supplier_name,
        overall_score=round(total_score, 2),
        supplier_rating=rating,
        score_breakdown={
            "verification": round(verification_points, 2),
            "product_relevance": product_points,
            "location_relevance": location_points,
            "website_verification": website_points,
            "evidence_availability": evidence_points
        },
        recommendation=recommendation
    )


def rank_suppliers(suppliers):

    scored_suppliers = [
        calculate_supplier_score(supplier)
        for supplier in suppliers
    ]

    scored_suppliers.sort(
        key=lambda item: item.overall_score,
        reverse=True
    )

    for index, supplier in enumerate(
        scored_suppliers, start=1
    ):
        supplier.ranking = index

    return scored_suppliers