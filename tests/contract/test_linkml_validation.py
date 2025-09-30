"""
Contract tests for LinkML validation endpoint.

These tests verify the LinkML validation contract compliance before implementation.
All tests MUST FAIL initially (TDD requirement).
"""

import pytest
import httpx


class TestLinkmlValidationContract:
    """Contract tests for POST /validation/linkml endpoint"""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def client(self):
        return httpx.AsyncClient(base_url=self.BASE_URL)

    @pytest.mark.asyncio
    async def test_linkml_validation_endpoint_exists(self, client):
        """Test that POST /validation/linkml endpoint exists"""
        # This test MUST fail initially
        response = await client.post("/validation/linkml")
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_linkml_schema_compliance(self, client):
        """Test LinkML validation against NWB-LinkML schema"""
        payload = {
            "data": {"neurodata_type": "Dataset", "title": "Test"},
            "schema_version": "2.6.0"
        }

        # This test MUST fail initially
        response = await client.post("/validation/linkml", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "valid" in data
        assert isinstance(data["valid"], bool)