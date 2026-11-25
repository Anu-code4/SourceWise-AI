from fastapi.testclient import TestClient

from app.main import app
from app.schemas.workflow import ProcurementWorkflowResponse

from unittest.mock import AsyncMock, patch


client = TestClient(app)


def test_health_endpoint():

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_invalid_workflow_request():

    response = client.post(
        "/api/procurement/execute",
        json={
            "product_or_service": "Pumps",
            "location": "Jaipur",
            "max_results": 50,
            "unexpected_field": "test"
        }
    )

    assert response.status_code == 422


def test_workflow_api():

    mock_result = ProcurementWorkflowResponse(
        search_query="Industrial water pumps in Jaipur",
        sources_found=5,
        suppliers_researched=2,
        verification_results=[],
        ranked_suppliers=[]
    )

    with patch(
        "app.routers.workflow.run_procurement_workflow",
        new_callable=AsyncMock
    ) as mock_workflow:

        mock_workflow.return_value = mock_result

        response = client.post(
            "/api/procurement/execute",
            json={
                "product_or_service": "Industrial water pumps",
                "location": "Jaipur, India",
                "max_results": 5
            }
        )

    assert response.status_code == 200
    assert response.json()["suppliers_researched"] == 2