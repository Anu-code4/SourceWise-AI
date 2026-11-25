import asyncio
import logging

from app.services.supplier_research import research_suppliers
from app.services.supplier_verification import verify_supplier
from app.services.supplier_scoring import rank_suppliers

from app.schemas.scoring import SupplierScoringRequest
from app.schemas.workflow import ProcurementWorkflowResponse

logger = logging.getLogger(__name__)

# Reliability configuration
RESEARCH_TIMEOUT = 90
VERIFICATION_TIMEOUT = 30
MAX_CONCURRENT_VERIFICATIONS = 3

verification_semaphore = asyncio.Semaphore(
    MAX_CONCURRENT_VERIFICATIONS
)


async def verify_supplier_async(
    supplier,
    product_or_service,
    location
):

    async with verification_semaphore:

        try:

            result = await asyncio.wait_for(
                asyncio.to_thread(
                    verify_supplier,
                    supplier.supplier_name,
                    product_or_service,
                    location,
                    supplier.website
                ),
                timeout=VERIFICATION_TIMEOUT
            )

            return result

        except asyncio.TimeoutError:

            logger.warning(
                "Verification timed out: %s",
                supplier.supplier_name
            )

            return None

        except Exception:

            logger.exception(
                "Verification failed: %s",
                supplier.supplier_name
            )

            return None


async def run_procurement_workflow(
    product_or_service: str,
    location: str,
    max_results: int = 5
):

    # STEP 1: Research with timeout

    try:

        research = await asyncio.wait_for(
            asyncio.to_thread(
                research_suppliers,
                product_or_service,
                location,
                max_results
            ),
            timeout=RESEARCH_TIMEOUT
        )

    except asyncio.TimeoutError:

        logger.error("Supplier research timed out")

        raise TimeoutError(
            "Supplier research exceeded the time limit."
        )

    suppliers = research.suppliers

    if not suppliers:

        return ProcurementWorkflowResponse(
            search_query=research.search_query,
            sources_found=research.sources_found,
            suppliers_researched=0,
            verification_results=[],
            ranked_suppliers=[]
        )

    # STEP 2: Verify suppliers concurrently

    verification_tasks = [
        verify_supplier_async(
            supplier,
            product_or_service,
            location
        )
        for supplier in suppliers
    ]

    verification_results = await asyncio.gather(
        *verification_tasks
    )

    # STEP 3: Prepare scoring inputs

    scoring_inputs = []
    valid_verifications = []

    for supplier, result in zip(
        suppliers,
        verification_results
    ):

        if result is None:
            continue

        valid_verifications.append(result)

        scoring_inputs.append(
            SupplierScoringRequest(
                supplier_name=supplier.supplier_name,
                verification_score=result.evidence_score,
                product_relevance=result.product_relevance,
                location_relevance=result.location_relevance,
                website_verified=result.website_match,
                evidence_available=bool(
                    result.evidence_sources
                )
            )
        )

    # STEP 4: Rank suppliers

    ranked_suppliers = rank_suppliers(
        scoring_inputs
    )

    logger.info(
        "Procurement workflow completed. "
        "Researched=%s, Verified=%s, Ranked=%s",
        len(suppliers),
        len(valid_verifications),
        len(ranked_suppliers)
    )

    # STEP 5: Return response

    return ProcurementWorkflowResponse(
        search_query=research.search_query,
        sources_found=research.sources_found,
        suppliers_researched=len(suppliers),
        verification_results=valid_verifications,
        ranked_suppliers=ranked_suppliers
    )