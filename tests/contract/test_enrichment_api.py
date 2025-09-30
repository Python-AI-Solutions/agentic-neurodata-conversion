"""
Contract tests for enrichment API endpoint.

These tests verify the enrichment API contract compliance before implementation.
All tests MUST FAIL initially (TDD requirement).
"""

import pytest
import httpx


class TestEnrichmentApiContract:
    """Contract tests for POST /datasets/{id}/enrich endpoint"""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def client(self):
        return httpx.AsyncClient(base_url=self.BASE_URL)

    @pytest.fixture
    def enrichment_payload(self):
        return {
            "sources": ["NCBITaxon", "NIFSTD", "UBERON"],
            "confidence_threshold": 0.8,
            "require_review": True
        }

    @pytest.mark.asyncio
    async def test_enrichment_endpoint_exists(self, client):
        """Test that POST /datasets/{id}/enrich endpoint exists"""
        # This test MUST fail initially
        response = await client.post("/datasets/dataset_001/enrich")
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_enrichment_with_human_review_required(self, client, enrichment_payload):
        """Test enrichment suggestions require human review"""
        # This test MUST fail initially
        response = await client.post("/datasets/dataset_001/enrich", json=enrichment_payload)
        assert response.status_code == 200

        data = response.json()
        assert "suggestions" in data
        for suggestion in data["suggestions"]:
            assert suggestion["requires_review"] is True

    @pytest.mark.asyncio
    async def test_enrichment_timeout_compliance(self, client, enrichment_payload):
        """Test enrichment respects 30-second timeout"""
        import time
        start_time = time.time()

        # This test MUST fail initially
        response = await client.post("/datasets/dataset_001/enrich", json=enrichment_payload)

        execution_time = time.time() - start_time
        assert execution_time <= 30