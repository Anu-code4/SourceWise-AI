import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.schemas.approval import (
    ApprovalRequest,
    ApprovalDecision,
    ApprovalResponse
)

from app.services.approval_workflow import (
    start_approval_workflow,
    resume_approval_workflow
)

router = APIRouter(
    prefix="/api/procurement",
    tags=["Human Approval"]
)

logger = logging.getLogger(__name__)


@router.post(
    "/approval/start",
    response_model=ApprovalResponse
)
async def start_approval(request: ApprovalRequest):

    thread_id = str(uuid4())

    try:

        result = await start_approval_workflow(
            product_or_service=request.product_or_service,
            location=request.location,
            max_results=request.max_results,
            thread_id=thread_id
        )

        return ApprovalResponse(
            thread_id=thread_id,
            status="pending_approval",
            message="Procurement workflow paused for human approval.",
            procurement_result=result.get("procurement_result")
        )

    except Exception:

        logger.exception("Approval workflow failed")

        raise HTTPException(
            status_code=502,
            detail="Unable to start approval workflow."
        )


@router.post(
    "/approval/decision",
    response_model=ApprovalResponse
)
async def submit_approval(request: ApprovalDecision):

    decision = request.decision.lower().strip()

    if decision not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be approved or rejected."
        )

    try:

        result = await resume_approval_workflow(
            thread_id=request.thread_id,
            decision=decision,
            comments=request.comments
        )

        return ApprovalResponse(
            thread_id=request.thread_id,
            status=result.get("approval_status", "unknown"),
            message=f"Human decision recorded: {decision}.",
            procurement_result=result.get("procurement_result"),
            approval_details={
                "decision": decision,
                "comments": request.comments
            }
        )

    except Exception:

        logger.exception("Approval decision failed")

        raise HTTPException(
            status_code=400,
            detail="Unable to resume approval workflow. Check the thread ID and workflow state."
        )