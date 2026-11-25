import logging
import time

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from tavily import TavilyClient

from app.config import settings

from app.schemas.supplier import (
    SupplierProfile,
    SupplierExtraction,
    SupplierResearchResponse
)

logger = logging.getLogger(__name__)


# --------------------------------
# STEP 1: Gemini retry mechanism
# --------------------------------

def generate_with_retry(client, prompt):

    for attempt in range(3):

        try:
            logger.info(
                "Gemini attempt %s/3",
                attempt + 1
            )

            return client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SupplierExtraction,
                    temperature=0
                )
            )

        except ServerError as error:

            if error.code != 503 or attempt == 2:
                raise

            wait_time = 2 ** (attempt + 1)

            logger.warning(
                "Gemini unavailable. Retrying in %s seconds.",
                wait_time
            )

            time.sleep(wait_time)


# --------------------------------
# STEP 2: Tavily fallback
# --------------------------------

def create_fallback_suppliers(sources):

    fallback_suppliers = []

    for item in sources:

        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        content = item.get("content", "").strip()

        if not title or not url:
            continue

        fallback_suppliers.append(
            SupplierProfile(
                supplier_name=title,
                website=None,
                description=(
                    "Unverified search candidate. "
                    "Gemini extraction was unavailable. "
                    + content[:300]
                ),
                products_services=[],
                certifications=[],
                location=None,
                source_urls=[url]
            )
        )

    return fallback_suppliers


# --------------------------------
# STEP 3: Main supplier research
# --------------------------------

def research_suppliers(
    product_or_service: str,
    location: str,
    max_results: int = 5
):

    # Validate API keys

    if not settings.TAVILY_API_KEY:
        raise ValueError("Missing Tavily API key.")

    if not settings.GEMINI_API_KEY:
        raise ValueError("Missing Gemini API key.")

    # Prepare search query

    search_query = (
        f"suppliers or manufacturers of "
        f"{product_or_service} in {location}"
    )

    # Tavily search

    tavily = TavilyClient(
        api_key=settings.TAVILY_API_KEY
    )

    search_data = tavily.search(
        query=search_query,
        search_depth="basic",
        max_results=max_results
    )

    results = search_data.get("results", [])

    if not results:

        return SupplierResearchResponse(
            search_query=search_query,
            suppliers=[],
            sources_found=0
        )

    # Prepare sources

    sources = []

    for result in results:

        sources.append({
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "content": result.get("content", "")[:1500]
        })

    allowed_urls = {
        item["url"]
        for item in sources
        if item["url"]
    }

    # Prepare Gemini prompt

    prompt = f"""
    You are a procurement supplier research assistant.

    Extract supplier information using ONLY the
    provided search results.

    Product: {product_or_service}
    Location: {location}

    Instructions:

    1. Extract actual supplier names.
    2. Extract available products and services.
    3. Extract certifications only when mentioned.
    4. Include supplier websites only when supported.
    5. Use only URLs provided in search results.
    6. Do not invent information.
    7. Leave unavailable information empty.

    Search Results:
    {sources}
    """

    # Gemini client

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY
    )

    # Generate structured extraction

    try:

        response = generate_with_retry(
            client,
            prompt
        )

    except Exception as error:

      status_code = getattr(error, "code", None)

    if status_code not in (429, 503):
        raise

    logger.warning(
        "Gemini unavailable (HTTP %s). "
        "Using Tavily fallback.",
        status_code
    )

    fallback_suppliers = create_fallback_suppliers(sources)

    return SupplierResearchResponse(
        search_query=search_query,
        suppliers=fallback_suppliers,
        sources_found=len(allowed_urls)
    )

    logger.warning(
            "Gemini unavailable after retries. "
            "Switching to Tavily fallback."
        )

    fallback_suppliers = create_fallback_suppliers(
            sources
        )

    return SupplierResearchResponse(
            search_query=search_query,
            suppliers=fallback_suppliers,
            sources_found=len(allowed_urls)
        )

    if not response.text:

        logger.warning(
            "Gemini returned empty response. "
            "Switching to Tavily fallback."
        )

        fallback_suppliers = create_fallback_suppliers(
            sources
        )

        return SupplierResearchResponse(
            search_query=search_query,
            suppliers=fallback_suppliers,
            sources_found=len(allowed_urls)
        )

    # Validate Gemini response

    extracted = SupplierExtraction.model_validate_json(
        response.text
    )

    # Remove duplicates and unsupported names

    unique_suppliers = {}

    search_text = " ".join(
        item["title"] + " " + item["content"]
        for item in sources
    ).casefold()

    for supplier in extracted.suppliers:

        name = supplier.supplier_name.strip()

        if not name:
            continue

        if name.casefold() not in search_text:
            continue

        # Keep only URLs returned by Tavily

        supplier.source_urls = [
            url
            for url in supplier.source_urls
            if url in allowed_urls
        ]

        key = name.casefold()

        if key not in unique_suppliers:

            unique_suppliers[key] = supplier

    # Return final response

    return SupplierResearchResponse(
        search_query=search_query,
        suppliers=list(unique_suppliers.values()),
        sources_found=len(allowed_urls)
    )