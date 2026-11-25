import asyncio
import time
from types import SimpleNamespace

import pytest

from app.services import procurement_workflow as workflow


def test_empty_supplier_results(monkeypatch):

    # Synchronous mock because production uses asyncio.to_thread()
    def mock_research(*args, **kwargs):
        return SimpleNamespace(
            search_query="Industrial pumps Jaipur",
            sources_found=0,
            suppliers=[]
        )

    monkeypatch.setattr(
        workflow,
        "research_suppliers",
        mock_research
    )

    result = asyncio.run(
        workflow.run_procurement_workflow(
            "Industrial pumps",
            "Jaipur",
            5
        )
    )

    assert result.suppliers_researched == 0
    assert result.verification_results == []
    assert result.ranked_suppliers == []


def test_individual_verification_failure(monkeypatch):

    def mock_research(*args, **kwargs):
        return SimpleNamespace(
            search_query="Industrial pumps Jaipur",
            sources_found=1,
            suppliers=[
                SimpleNamespace(
                    supplier_name="CK Pumps",
                    website="https://ckpumps.com"
                )
            ]
        )

    def mock_verification(*args, **kwargs):
        raise RuntimeError(
            "Verification service unavailable"
        )

    monkeypatch.setattr(
        workflow,
        "research_suppliers",
        mock_research
    )

    monkeypatch.setattr(
        workflow,
        "verify_supplier",
        mock_verification
    )

    result = asyncio.run(
        workflow.run_procurement_workflow(
            "Industrial pumps",
            "Jaipur",
            5
        )
    )

    assert result.suppliers_researched == 1
    assert result.verification_results == []
    assert result.ranked_suppliers == []


def test_research_timeout(monkeypatch):

    def slow_research(*args, **kwargs):
        time.sleep(0.2)

    monkeypatch.setattr(
        workflow,
        "research_suppliers",
        slow_research
    )

    monkeypatch.setattr(
        workflow,
        "RESEARCH_TIMEOUT",
        0.01
    )

    with pytest.raises(
        TimeoutError,
        match="Supplier research exceeded the time limit"
    ):

        asyncio.run(
            workflow.run_procurement_workflow(
                "Industrial pumps",
                "Jaipur",
                5
            )
        )