from pydantic import BaseModel, Field


# User input
class SupplierResearchRequest(BaseModel):
    product_or_service: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=100)
    max_results: int = Field(default=5, ge=1, le=10)


# Individual supplier information
class SupplierProfile(BaseModel):
    supplier_name: str
    website: str | None = None
    description: str = ""
    products_services: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    location: str | None = None
    source_urls: list[str] = Field(default_factory=list)


# Gemini extraction response
class SupplierExtraction(BaseModel):
    suppliers: list[SupplierProfile] = Field(default_factory=list)


# Final API response
class SupplierResearchResponse(BaseModel):
    search_query: str
    suppliers: list[SupplierProfile]
    sources_found: int