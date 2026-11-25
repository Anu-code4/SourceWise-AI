from types import SimpleNamespace

import pytest

from app.services import supplier_verification as verification


class FakeTavilyClient:

    def __init__(self, api_key):
        self.api_key = api_key

    def search(self, **kwargs):
        return {
            "results": [
                {
                    "title": "CK Pumps Industrial Water Pumps Jaipur",
                    "content": (
                        "CK Pumps supplies industrial water pumps "
                        "in Jaipur, Rajasthan."
                    ),
                    "url": "https://www.ckpumps.com"
                }
            ]
        }


def setup_mock_tavily(monkeypatch, results=None):

    monkeypatch.setattr(
        verification,
        "settings",
        SimpleNamespace(TAVILY_API_KEY="test-api-key")
    )

    class MockTavilyClient:

        def __init__(self, api_key):
            self.api_key = api_key

        def search(self, **kwargs):
            return {"results": results or []}

    monkeypatch.setattr(
        verification,
        "TavilyClient",
        MockTavilyClient
    )


def test_supplier_fully_verified(monkeypatch):

    setup_mock_tavily(
        monkeypatch,
        results=[
            {
                "title": "CK Pumps Industrial Water Pumps Jaipur",
                "content": "CK Pumps supplies industrial water pumps in Jaipur.",
                "url": "https://www.ckpumps.com"
            }
        ]
    )

    result = verification.verify_supplier(
        supplier_name="CK Pumps",
        product_or_service="industrial water pumps",
        location="Jaipur",
        website="https://ckpumps.com"
    )

    assert result.name_match is True
    assert result.product_relevance is True
    assert result.location_relevance is True
    assert result.website_match is True

    assert result.evidence_score == 100
    assert result.verification_status == "Evidence Supported"
    assert len(result.evidence_sources) == 1


def test_supplier_partially_verified(monkeypatch):

    setup_mock_tavily(
        monkeypatch,
        results=[
            {
                "title": "CK Pumps Company",
                "content": "Information about CK Pumps.",
                "url": "https://www.ckpumps.com"
            }
        ]
    )

    result = verification.verify_supplier(
        supplier_name="CK Pumps",
        product_or_service="industrial water pumps",
        location="Jaipur"
    )

    assert result.name_match is True
    assert result.product_relevance is False
    assert result.location_relevance is False

    assert result.verification_status == "Partially Supported"
    assert result.evidence_score == 40


def test_supplier_unverified(monkeypatch):

    setup_mock_tavily(
        monkeypatch,
        results=[
            {
                "title": "Other Company",
                "content": "Manufacturing equipment.",
                "url": "https://example.com"
            }
        ]
    )

    result = verification.verify_supplier(
        supplier_name="CK Pumps",
        product_or_service="industrial water pumps",
        location="Jaipur"
    )

    assert result.name_match is False
    assert result.verification_status == "Unverified"
    assert result.evidence_score == 0


def test_no_search_evidence(monkeypatch):

    setup_mock_tavily(monkeypatch, results=[])

    result = verification.verify_supplier(
        supplier_name="CK Pumps",
        product_or_service="industrial water pumps",
        location="Jaipur"
    )

    assert result.verification_status == "Unverified"
    assert result.evidence_score == 0
    assert result.evidence_sources == []


def test_missing_tavily_api_key(monkeypatch):

    monkeypatch.setattr(
        verification,
        "settings",
        SimpleNamespace(TAVILY_API_KEY=None)
    )

    with pytest.raises(ValueError, match="Missing Tavily API key"):
        verification.verify_supplier(
            supplier_name="CK Pumps",
            product_or_service="industrial water pumps",
            location="Jaipur"
        )


def test_get_domain():

    assert (
        verification.get_domain("https://www.ckpumps.com")
        == "ckpumps.com"
    )

    assert (
        verification.get_domain("ckpumps.com")
        == "ckpumps.com"
    )

    assert verification.get_domain(None) == ""