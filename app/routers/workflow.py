import logging

from fastapi import APIRouter, HTTPException

from app.utils.monitoring import monitor_execution

from app.schemas.workflow import (
    ProcurementWorkflowRequest,
    ProcurementWorkflowResponse
)

from app.services.procurement_workflow import (
    run_procurement_workflow
)

router = APIRouter(
    prefix="/api/procurement",
    tags=["Procurement Workflow"]
)

logger = logging.getLogger(__name__)


@router.post(
    "/execute",
    response_model=ProcurementWorkflowResponse
)
@monitor_execution
async def execute_procurement_workflow(
    request: ProcurementWorkflowRequest
):

    try:

        return await run_procurement_workflow(
            product_or_service=request.product_or_service,
            location=request.location,
            max_results=request.max_results
        )

    except TimeoutError as exc:

        raise HTTPException(
            status_code=504,
            detail=str(exc)
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception:

        logger.exception(
            "Procurement workflow failed"
        )

        raise HTTPException(
            status_code=502,
            detail="Procurement workflow temporarily unavailable."
        )