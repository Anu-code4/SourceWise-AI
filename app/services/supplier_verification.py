from urllib.parse import urlparse

from tavily import TavilyClient

from app.config import settings
from app.schemas.verification import VerificationResult


def get_domain(url):
    if not url:
        return ""

    parsed_url = url if "://" in url else f"https://{url}"

    return (
        urlparse(parsed_url)
        .netloc.lower()
        .removeprefix("www.")
    )


def verify_supplier(
    supplier_name: str,
    product_or_service: str,
    location: str,
    website: str | None = None
):

    if not settings.TAVILY_API_KEY:
        raise ValueError("Missing Tavily API key.")

    client = TavilyClient(
        api_key=settings.TAVILY_API_KEY
    )

    query = f'"{supplier_name}" {product_or_service} {location}'

    search_data = client.search(
        query=query,
        search_depth="basic",
        max_results=5
    )

    results = search_data.get("results", [])

    if not results:
        return VerificationResult(
            supplier_name=supplier_name,
            verification_status="Unverified",
            evidence_score=0,
            name_match=False,
            product_relevance=False,
            location_relevance=False,
            website_match=False,
            verification_notes=[
                "No supporting search evidence found."
            ]
        )

    search_text = " ".join(
        f"{item.get('title', '')} {item.get('content', '')}"
        for item in results
    ).casefold()

    name_match = supplier_name.casefold() in search_text
    product_relevance = product_or_service.casefold() in search_text
    location_relevance = location.casefold() in search_text

    website_domain = get_domain(website)

    website_match = False

    if website_domain:
        website_match = any(
            get_domain(item.get("url", "")) == website_domain
            for item in results
        )

    score = (
        (40 if name_match else 0)
        + (25 if product_relevance else 0)
        + (20 if location_relevance else 0)
        + (15 if website_match else 0)
    )

    if name_match and product_relevance and location_relevance:
        status = "Evidence Supported"
    elif name_match:
        status = "Partially Supported"
    else:
        status = "Unverified"

    notes = []

    if name_match:
        notes.append("Supplier name found in search evidence.")
    else:
        notes.append("Supplier name not found in search evidence.")

    if product_relevance:
        notes.append("Product relevance found.")

    if location_relevance:
        notes.append("Location relevance found.")

    if website_match:
        notes.append("Website found in search results.")
    elif website:
        notes.append("Website not matched in search results.")

    sources = [
        item.get("url", "")
        for item in results
        if item.get("url")
    ]

    return VerificationResult(
        supplier_name=supplier_name,
        verification_status=status,
        evidence_score=score,
        name_match=name_match,
        product_relevance=product_relevance,
        location_relevance=location_relevance,
        website_match=website_match,
        evidence_sources=sources,
        verification_notes=notes
    )