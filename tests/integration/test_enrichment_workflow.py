"""
Integration tests for dataset creation and enrichment workflow.

These tests verify end-to-end enrichment workflow integration.
All tests MUST FAIL initially (TDD requirement).
"""

import pytest
import httpx
from typing import Dict, Any


class TestEnrichmentWorkflowIntegration:
    """Integration tests for complete enrichment workflow"""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def client(self):
        return httpx.AsyncClient(base_url=self.BASE_URL)

    @pytest.mark.asyncio
    async def test_complete_enrichment_workflow(self, client):
        """Test complete dataset creation and enrichment workflow"""
        # Step 1: Create dataset
        dataset_payload = {
            "title": "Integration Test Dataset",
            "description": "Dataset for workflow testing",
            "nwb_files": ["test_session.nwb"],
            "lab_id": "lab_integration_test"
        }

        # This test MUST fail initially
        create_response = await client.post("/datasets", json=dataset_payload)
        assert create_response.status_code == 201

        dataset_id = create_response.json()["dataset_id"]

        # Step 2: Validate LinkML compliance
        validation_payload = {
            "data": create_response.json(),
            "schema_version": "2.6.0"
        }

        validate_response = await client.post("/validation/linkml", json=validation_payload)
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

        # Step 3: Generate enrichment suggestions
        enrich_payload = {
            "sources": ["NCBITaxon", "NIFSTD"],
            "confidence_threshold": 0.0,
            "require_review": True
        }

        enrich_response = await client.post(f"/datasets/{dataset_id}/enrich", json=enrich_payload)
        assert enrich_response.status_code == 200

        suggestions = enrich_response.json()["suggestions"]
        # All suggestions must require human review per constitutional requirements
        for suggestion in suggestions:
            assert suggestion["requires_review"] is True

    @pytest.mark.asyncio
    async def test_human_review_workflow(self, client):
        """Test human review workflow for enrichment suggestions"""
        # This test MUST fail initially - tests human review integration
        # Create dataset and generate suggestions first
        dataset_payload = {
            "title": "Review Test Dataset",
            "nwb_files": ["review_test.nwb"]
        }

        create_response = await client.post("/datasets", json=dataset_payload)
        dataset_id = create_response.json()["dataset_id"]

        # Generate suggestions
        enrich_response = await client.post(f"/datasets/{dataset_id}/enrich", json={})
        suggestions = enrich_response.json()["suggestions"]

        # Test review workflow
        review_payload = {
            "suggestions": [
                {
                    "suggestion_id": suggestions[0]["id"],
                    "action": "approve",
                    "reviewer_notes": "Approved after manual verification"
                }
            ]
        }

        review_response = await client.post(f"/datasets/{dataset_id}/review", json=review_payload)
        assert review_response.status_code == 200