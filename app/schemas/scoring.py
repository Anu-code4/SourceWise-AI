from pydantic import BaseModel, Field


class SupplierScoringRequest(BaseModel):
    supplier_name: str
    verification_score: int = Field(ge=0, le=100)
    product_relevance: bool
    location_relevance: bool
    website_verified: bool
    evidence_available: bool


class SupplierScore(BaseModel):
    supplier_name: str
    overall_score: float
    supplier_rating: str
    ranking: int | None = None
    score_breakdown: dict[str, float]
    recommendation: str