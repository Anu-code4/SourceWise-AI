from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    product_or_service: str = Field(min_length=2)
    location: str = Field(min_length=2)
    max_results: int = Field(default=5, ge=1, le=10)


class ApprovalDecision(BaseModel):
    thread_id: str
    decision: str
    comments: str = ""


class ApprovalResponse(BaseModel):
    thread_id: str
    status: str
    message: str
    procurement_result: dict | None = None
    approval_details: dict | None = None