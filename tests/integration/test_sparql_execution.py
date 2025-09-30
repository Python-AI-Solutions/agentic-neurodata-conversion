"""
Integration tests for SPARQL query execution with timeout.

These tests verify SPARQL query execution performance and timeout handling.
All tests MUST FAIL initially (TDD requirement).
"""

import pytest
import httpx
import time


class TestSparqlExecutionIntegration:
    """Integration tests for SPARQL query execution"""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def client(self):
        return httpx.AsyncClient(base_url=self.BASE_URL, timeout=35.0)

    @pytest.mark.asyncio
    async def test_sparql_30_second_timeout_compliance(self, client):
        """Test SPARQL queries respect 30-second timeout limit"""
        # Complex query that might take time
        complex_query = """
        SELECT ?dataset ?session ?subject ?device ?protocol WHERE {
            ?dataset rdf:type kg:Dataset .
            ?dataset kg:hasSession ?session .
            ?session kg:hasSubject ?subject .
            ?session kg:usesDevice ?device .
            ?dataset kg:followsProtocol ?protocol .
            ?subject kg:hasSpecies ?species .
            ?device kg:hasCalibration ?calibration .
        }
        """

        payload = {"query": complex_query}

        start_time = time.time()

        # This test MUST fail initially
        response = await client.post("/sparql", json=payload)

        execution_time = time.time() - start_time

        # Should either complete within 30s or return timeout
        if response.status_code == 200:
            assert execution_time <= 30, f"Query took {execution_time}s, exceeds 30s limit"
        elif response.status_code == 408:  # Timeout
            assert "timeout" in response.json().get("error", "").lower()
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    @pytest.mark.asyncio
    async def test_sparql_simple_query_performance(self, client):
        """Test simple queries complete within 200ms requirement"""
        simple_query = "SELECT ?type WHERE { ?x rdf:type ?type } LIMIT 10"

        start_time = time.time()

        # This test MUST fail initially
        response = await client.post("/sparql", json={"query": simple_query})

        execution_time = time.time() - start_time

        assert response.status_code == 200
        assert execution_time < 0.2, f"Simple query took {execution_time}s, should be <200ms"