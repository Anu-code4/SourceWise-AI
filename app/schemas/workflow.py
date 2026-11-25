from pydantic import BaseModel, Field, ConfigDict


class ProcurementWorkflowRequest(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    product_or_service: str = Field(
        min_length=2,
        max_length=120
    )

    location: str = Field(
        min_length=2,
        max_length=100
    )

    max_results: int = Field(
        default=5,
        ge=1,
        le=10
    )


class ProcurementWorkflowResponse(BaseModel):

    search_query: str
    sources_found: int
    suppliers_researched: int
    verification_results: list
    ranked_suppliers: list