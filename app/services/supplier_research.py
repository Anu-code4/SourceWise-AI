import logging
import re
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
# STEP 1: URL and domain utilities
# --------------------------------

BLOCKED_DOMAINS = {
    "google.com",
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "wikipedia.org",
    "indiamart.com",
    "justdial.com",
    "tradeindia.com",
    "exportersindia.com",
    "alibaba.com",
    "amazon.com",
    "bbb.org",
}


def get_domain(url):

    if not url:
        return ""

    try:
        parsed = urlparse(
            url if "://" in url else f"https://{url}"
        )

        return parsed.netloc.lower().removeprefix("www.")

    except Exception:
        return ""


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


def domain_to_name(domain):

    """
    Derive a readable candidate name from a company domain.
    This is a candidate label, not proof of legal identity.
    """

    if not domain:
        return ""

    name = domain.split(".")[0]

    name = re.sub(r"[-_]+", " ", name)

    return name.title().strip()


# --------------------------------
# STEP 2: Gemini retry mechanism
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
# STEP 3: Relevance checks
# --------------------------------

def is_relevant_evidence(
    text,
    product_or_service,
    location
):

    text = text.casefold()

    product_words = [
        word.casefold()
        for word in re.findall(
            r"[a-zA-Z0-9]+",
            product_or_service
        )
        if len(word) > 2
    ]

    location_words = [
        word.casefold()
        for word in re.findall(
            r"[a-zA-Z]+",
            location
        )
        if len(word) > 2
    ]

    product_match = any(
        word in text for word in product_words
    )

    location_match = any(
        word in text for word in location_words
    )

    return product_match and location_match


# --------------------------------
# STEP 4: Tavily fallback extraction
# --------------------------------

def create_fallback_suppliers(
    sources,
    product_or_service,
    location
):

    candidates = {}
    
    for item in sources:

        url = item.get("url", "").strip()
        title = item.get("title", "").strip()
        content = item.get("content", "").strip()

        domain = get_domain(url)

        if not domain or not is_valid_url(url):
            continue

        # Reject directories and social platforms

        if any(
            domain == blocked or domain.endswith("." + blocked)
            for blocked in BLOCKED_DOMAINS
        ):
            continue

        evidence_text = f"{title} {content}"

        # Require product and location relevance

        if not is_relevant_evidence(
            evidence_text,
            product_or_service,
            location
        ):
            continue

        # Derive a candidate label from the domain

        supplier_name = domain_to_name(domain)

        if not supplier_name:
            continue

        # Keep only one candidate per domain

        if domain in candidates:
            candidates[domain].source_urls.append(url)
            continue

        candidates[domain] = SupplierProfile(
            supplier_name=supplier_name,
            website=f"https://{domain}",
            description=(
                "Potential supplier identified through "
                "Tavily search. Gemini extraction was "
                "unavailable. This candidate has not "
                "been independently verified."
            ),
            products_services=[product_or_service],
            certifications=[],
            location=location,
            source_urls=[url]
        )

    logger.info(
        "Tavily fallback produced %s candidates.",
        len(candidates)
    )

    return list(candidates.values())


# --------------------------------
# STEP 5: Main supplier research
# --------------------------------

def research_suppliers(
    product_or_service: str,
    location: str,
    max_results: int = 5
):

    if not settings.TAVILY_API_KEY:
        raise ValueError("Missing Tavily API key.")

    # Prepare targeted search query

    search_query = (
        f"{product_or_service} "
        f"manufacturers suppliers dealers "
        f"{location} India company website"
    )

    tavily = TavilyClient(
        api_key=settings.TAVILY_API_KEY
    )

    search_data = tavily.search(
        query=search_query,
        search_depth="advanced",
        max_results=max(10, max_results * 2)
    )

    results = search_data.get("results", [])

    if not results:

        return SupplierResearchResponse(
            search_query=search_query,
            suppliers=[],
            sources_found=0
        )

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
        item["url"] for item in sources
    }

    # --------------------------------
    # Gemini unavailable: Tavily fallback
    # --------------------------------

    def use_fallback():

        suppliers = create_fallback_suppliers(
            sources,
            product_or_service,
            location
        )

        return SupplierResearchResponse(
            search_query=search_query,
            suppliers=suppliers[:max_results],
            sources_found=len(allowed_urls)
        )

    if not settings.GEMINI_API_KEY:

        logger.warning(
            "Gemini API key missing. Using Tavily fallback."
        )

        return use_fallback()

    # --------------------------------
    # Gemini structured extraction
    # --------------------------------

    prompt = f"""
You are a professional procurement research assistant.

Find genuine companies supplying the requested product.

Product: {product_or_service}
Target location: {location}, India

Use only the provided search evidence.

Rules:
1. Extract actual company names, not article titles.
2. Prefer manufacturers, distributors and dealers.
3. Check product relevance.
4. Prefer companies serving the requested location.
5. Never invent company names or websites.
6. Only use URLs in the supplied evidence.
7. Include source URLs supporting each company.
8. Do not invent certifications.
9. Return an empty list if evidence is insufficient.

Search evidence:
{sources}
"""

    try:

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        response = generate_with_retry(
            client,
            prompt
        )

        if not response or not response.text:

            logger.warning(
                "Gemini returned an empty response."
            )

            return use_fallback()

        extracted = SupplierExtraction.model_validate_json(
            response.text
        )

    except Exception as error:

        status_code = (
            getattr(error, "code", None)
            or getattr(error, "status_code", None)
        )

        if status_code not in (429, 503):

            logger.exception(
                "Gemini extraction failed."
            )

            raise

        logger.warning(
            "Gemini unavailable (HTTP %s). "
            "Switching to Tavily fallback.",
            status_code
        )

        return use_fallback()

    # --------------------------------
    # STEP 6: Validate extracted suppliers
    # --------------------------------

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

        supplier.source_urls = [
            url
            for url in supplier.source_urls
            if url in allowed_urls
        ]

        if not supplier.source_urls:
            continue

        key = name.casefold()

        if key not in unique_suppliers:
            unique_suppliers[key] = supplier

    final_suppliers = list(
        unique_suppliers.values()
    )[:max_results]

    logger.info(
        "Supplier research completed. "
        "Sources=%s, Candidates=%s",
        len(allowed_urls),
        len(final_suppliers)
    )

    return SupplierResearchResponse(
        search_query=search_query,
        suppliers=final_suppliers,
        sources_found=len(allowed_urls)
    )