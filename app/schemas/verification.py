from pydantic import BaseModel, Field


class SupplierVerificationRequest(BaseModel):
    supplier_name: str = Field(min_length=2)
    product_or_service: str = Field(min_length=2)
    location: str = Field(min_length=2)
    website: str | None = None


class VerificationResult(BaseModel):
    supplier_name: str
    verification_status: str
    evidence_score: int
    name_match: bool
    product_relevance: bool
    location_relevance: bool
    website_match: bool
    evidence_sources: list[str] = Field(default_factory=list)
    verification_notes: list[str] = Field(default_factory=list)