import logging
import time
from urllib.parse import urlparse

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
# STEP 2: URL validation
# --------------------------------

def is_valid_url(url):

    if not url:
        return False

    try:

        parsed = urlparse(url)

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )

    except Exception:

        return False


# --------------------------------
# STEP 3: Conservative fallback
# --------------------------------

def create_fallback_suppliers(
    sources,
    product_or_service,
    location
):

    """
    Do not convert arbitrary search-result titles
    into supplier names.

    Without Gemini extraction, return no supplier
    profiles rather than misleading users.
    """

    logger.warning(
        "Gemini unavailable. Raw Tavily results "
        "will not be presented as verified suppliers. "
        "Product=%s Location=%s Sources=%s",
        product_or_service,
        location,
        len(sources)
    )

    return []


# --------------------------------
# STEP 4: Main supplier research
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
        f"{product_or_service} manufacturers suppliers "
        f"dealers in {location}, India"
    )

    # Tavily search

    tavily = TavilyClient(
        api_key=settings.TAVILY_API_KEY
    )

    search_data = tavily.search(
        query=search_query,
        search_depth="advanced",
        max_results=max_results
    )

    results = search_data.get("results", [])

    if not results:

        return SupplierResearchResponse(
            search_query=search_query,
            suppliers=[],
            sources_found=0
        )

    # Prepare search evidence

    sources = []

    for result in results:

        title = result.get("title", "").strip()
        url = result.get("url", "").strip()
        content = result.get("content", "").strip()

        if not title or not is_valid_url(url):
            continue

        sources.append({
            "title": title,
            "url": url,
            "content": content[:1500]
        })

    allowed_urls = {
        item["url"]
        for item in sources
    }

    if not sources:

        return SupplierResearchResponse(
            search_query=search_query,
            suppliers=[],
            sources_found=0
        )

    # Prepare Gemini prompt

    prompt = f"""
You are an experienced procurement supplier
research assistant.

Your task is to identify genuine companies
that supply the requested product or service.

PRODUCT: {product_or_service}

TARGET LOCATION: {location}, India

Use ONLY the supplied search evidence.

STRICT INSTRUCTIONS:

1. Extract actual company or supplier names.
2. Do not use article titles as supplier names.
3. Do not use directory names as supplier names.
4. Do not use advertisements as supplier names.
5. Do not use headings or generic phrases as company names.
6. Prefer suppliers operating in the requested location.
7. Include a supplier only when its identity is
   explicitly supported by the evidence.
8. Product relevance must be supported by the evidence.
9. Never invent websites, locations or certifications.
10. Only include source URLs supplied below.
11. If no genuine supplier can be identified,
    return an empty suppliers list.
12. Do not manufacture results to reach a target count.

SEARCH EVIDENCE:

{sources}
"""

    # Initialize Gemini

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

        status_code = (
            getattr(error, "code", None)
            or getattr(error, "status_code", None)
        )

        if status_code not in (429, 503):
            raise

        logger.warning(
            "Gemini unavailable (HTTP %s). "
            "Using conservative fallback.",
            status_code
        )

        fallback_suppliers = create_fallback_suppliers(
            sources,
            product_or_service,
            location
        )

        return SupplierResearchResponse(
            search_query=search_query,
            suppliers=fallback_suppliers,
            sources_found=len(allowed_urls)
        )

    # Handle empty Gemini response

    if not response or not response.text:

        logger.warning(
            "Gemini returned an empty response."
        )

        return SupplierResearchResponse(
            search_query=search_query,
            suppliers=[],
            sources_found=len(allowed_urls)
        )

    # Validate structured response

    extracted = SupplierExtraction.model_validate_json(
        response.text
    )

    # Validate extracted suppliers

    unique_suppliers = {}

    search_text = " ".join(
        item["title"] + " " + item["content"]
        for item in sources
    ).casefold()

    for supplier in extracted.suppliers:

        name = supplier.supplier_name.strip()

        if not name:
            continue

        # Supplier name must be supported by evidence

        if name.casefold() not in search_text:
            logger.warning(
                "Discarding unsupported supplier: %s",
                name
            )
            continue

        # Validate source URLs

        supplier.source_urls = [
            url
            for url in supplier.source_urls
            if url in allowed_urls
        ]

        # Require at least one supporting source

        if not supplier.source_urls:
            logger.warning(
                "Discarding supplier without supporting URL: %s",
                name
            )
            continue

        # Remove duplicates

        key = name.casefold()

        if key not in unique_suppliers:

            unique_suppliers[key] = supplier

    final_suppliers = list(
        unique_suppliers.values()
    )[:max_results]

    logger.info(
        "Supplier research completed. "
        "Sources=%s, Suppliers extracted=%s",
        len(allowed_urls),
        len(final_suppliers)
    )

    return SupplierResearchResponse(
        search_query=search_query,
        suppliers=final_suppliers,
        sources_found=len(allowed_urls)
    )