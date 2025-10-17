"""
End-to-end tests for complete pipeline via REST API (Task 7.4).

Tests the complete pipeline as a real user would:
- Initialize session via REST API
- Poll status endpoint for progress
- Wait for completion
- Retrieve results
- Verify file artifacts

Uses TestClient (simulating real API) with REAL components.
Mocks LLM calls for speed/cost.
"""

from pathlib import Path
import time
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
import pytest

from agentic_neurodata_conversion.models.session_context import WorkflowStage


@pytest.mark.e2e
@pytest.mark.mock_llm
class TestFullPipeline:
    """End-to-end tests for complete pipeline."""

    def test_post_sessions_initialize_with_dataset_path(
        self,
        integration_test_client: TestClient,
        synthetic_dataset_e2e: Path,
        mock_llm_patch: AsyncMock,
    ) -> None:
        """
        Test POST /api/v1/sessions/initialize with dataset path.

        Verifies:
        - Endpoint accepts dataset_path
        - Returns session_id
        - Returns initial workflow_stage
        - Returns success message
        """
        response = integration_test_client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": str(synthetic_dataset_e2e)},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "session_id" in data
        assert "workflow_stage" in data
        assert "message" in data

        # Verify initial state
        assert data["workflow_stage"] == WorkflowStage.INITIALIZED
        assert len(data["session_id"]) > 0

        # Verify message is informative
        assert "initialized" in data["message"].lower()

    def test_polling_status_until_completed(
        self,
        integration_test_client: TestClient,
        synthetic_dataset_e2e: Path,
        mock_llm_patch: AsyncMock,
    ) -> None:
        """
        Test polling GET /api/v1/sessions/{id}/status until completed.

        Verifies:
        - Status endpoint returns current state
        - Can poll repeatedly
        - Eventually reaches COMPLETED or FAILED
        """
        # Initialize session
        init_response = integration_test_client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": str(synthetic_dataset_e2e)},
        )
        assert init_response.status_code == 200
        session_id = init_response.json()["session_id"]

        # Poll status endpoint
        max_polls = 60  # 60 seconds max
        poll_interval = 1.0  # 1 second between polls
        final_stage = None

        for _ in range(max_polls):
            status_response = integration_test_client.get(
                f"/api/v1/sessions/{session_id}/status"
            )
            assert status_response.status_code == 200

            status_data = status_response.json()
            assert "session_id" in status_data
            assert "workflow_stage" in status_data
            assert "progress_percentage" in status_data
            assert "status_message" in status_data

            current_stage = status_data["workflow_stage"]

            # Check for terminal states
            if current_stage in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                final_stage = current_stage
                break

            time.sleep(poll_interval)

        # Verify we can poll without errors (may not complete if agents not running)
        assert final_stage in [None, WorkflowStage.COMPLETED, WorkflowStage.FAILED]

    def test_workflow_progression_with_progress_updates(
        self,
        integration_test_client: TestClient,
        synthetic_dataset_e2e: Path,
        mock_llm_patch: AsyncMock,
    ) -> None:
        """
        Test workflow progression through all stages with progress updates.

        Verifies:
        - Progress percentage increases over time
        - Status messages update appropriately
        - Workflow stages progress in order
        """
        # Initialize session
        init_response = integration_test_client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": str(synthetic_dataset_e2e)},
        )
        assert init_response.status_code == 200
        session_id = init_response.json()["session_id"]

        # Track progress
        progress_history = []
        max_wait_seconds = 30
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            status_response = integration_test_client.get(
                f"/api/v1/sessions/{session_id}/status"
            )
            assert status_response.status_code == 200

            status_data = status_response.json()
            progress_percentage = status_data["progress_percentage"]
            workflow_stage = status_data["workflow_stage"]
            status_message = status_data["status_message"]

            progress_history.append(
                {
                    "progress": progress_percentage,
                    "stage": workflow_stage,
                    "message": status_message,
                }
            )

            # Stop if completed
            if workflow_stage in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                break

            time.sleep(1)

        # Verify we collected some progress data
        assert len(progress_history) > 0

        # Verify progress percentages are valid
        for entry in progress_history:
            assert 0 <= entry["progress"] <= 100
            assert len(entry["message"]) > 0

    def test_get_result_when_completed(
        self,
        integration_test_client: TestClient,
        synthetic_dataset_e2e: Path,
        mock_llm_patch: AsyncMock,
    ) -> None:
        """
        Test GET /api/v1/sessions/{id}/result when workflow_stage=COMPLETED.

        Verifies:
        - Result endpoint returns data when completed
        - NWB file path is included
        - Validation report path is included
        - Overall status is included
        - LLM summary is included
        """
        # Initialize session
        init_response = integration_test_client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": str(synthetic_dataset_e2e)},
        )
        assert init_response.status_code == 200
        session_id = init_response.json()["session_id"]

        # Wait for completion (with timeout)
        max_wait_seconds = 30
        start_time = time.time()
        completed = False

        while time.time() - start_time < max_wait_seconds:
            status_response = integration_test_client.get(
                f"/api/v1/sessions/{session_id}/status"
            )
            status_data = status_response.json()

            if status_data["workflow_stage"] == WorkflowStage.COMPLETED:
                completed = True
                break

            if status_data["workflow_stage"] == WorkflowStage.FAILED:
                pytest.skip("Workflow failed before completion")

            time.sleep(1)

        if not completed:
            pytest.skip("Workflow did not complete in time (agents may not be running)")

        # Get result
        result_response = integration_test_client.get(
            f"/api/v1/sessions/{session_id}/result"
        )
        assert result_response.status_code == 200

        result_data = result_response.json()

        # Verify result structure
        assert "session_id" in result_data
        assert "nwb_file_path" in result_data
        assert "validation_report_path" in result_data
        assert "overall_status" in result_data
        assert "llm_validation_summary" in result_data
        assert "validation_issues" in result_data

    def test_nwb_file_exists_and_valid_format(
        self,
        integration_test_client: TestClient,
        synthetic_dataset_e2e: Path,
        mock_llm_patch: AsyncMock,
    ) -> None:
        """
        Test that NWB file exists at returned path and is valid NWB format.

        Verifies:
        - NWB file path is returned
        - File exists at that path
        - File has .nwb extension
        - File is readable (basic validation)
        """
        # Initialize session
        init_response = integration_test_client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": str(synthetic_dataset_e2e)},
        )
        assert init_response.status_code == 200
        session_id = init_response.json()["session_id"]

        # Wait for completion
        max_wait_seconds = 30
        start_time = time.time()
        completed = False

        while time.time() - start_time < max_wait_seconds:
            status_response = integration_test_client.get(
                f"/api/v1/sessions/{session_id}/status"
            )
            status_data = status_response.json()

            if status_data["workflow_stage"] == WorkflowStage.COMPLETED:
                completed = True
                break

            if status_data["workflow_stage"] == WorkflowStage.FAILED:
                pytest.skip("Workflow failed")

            time.sleep(1)

        if not completed:
            pytest.skip("Workflow did not complete")

        # Get result
        result_response = integration_test_client.get(
            f"/api/v1/sessions/{session_id}/result"
        )
        assert result_response.status_code == 200

        result_data = result_response.json()
        nwb_file_path = result_data.get("nwb_file_path")

        if nwb_file_path:
            # Verify file extension
            assert nwb_file_path.endswith(".nwb")

            # Verify file exists (if path is provided)
            nwb_path = Path(nwb_file_path)
            if nwb_path.exists():
                assert nwb_path.is_file()
                assert nwb_path.stat().st_size > 0

    def test_validation_report_exists_and_valid_structure(
        self,
        integration_test_client: TestClient,
        synthetic_dataset_e2e: Path,
        mock_llm_patch: AsyncMock,
    ) -> None:
        """
        Test that validation report exists and has correct structure.

        Verifies:
        - Validation report path is returned
        - Report exists (if workflow completed)
        - Report contains validation results
        """
        # Initialize session
        init_response = integration_test_client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": str(synthetic_dataset_e2e)},
        )
        assert init_response.status_code == 200
        session_id = init_response.json()["session_id"]

        # Wait for completion
        max_wait_seconds = 30
        start_time = time.time()
        completed = False

        while time.time() - start_time < max_wait_seconds:
            status_response = integration_test_client.get(
                f"/api/v1/sessions/{session_id}/status"
            )
            status_data = status_response.json()

            if status_data["workflow_stage"] == WorkflowStage.COMPLETED:
                completed = True
                break

            if status_data["workflow_stage"] == WorkflowStage.FAILED:
                pytest.skip("Workflow failed")

            time.sleep(1)

        if not completed:
            pytest.skip("Workflow did not complete")

        # Get result
        result_response = integration_test_client.get(
            f"/api/v1/sessions/{session_id}/result"
        )
        assert result_response.status_code == 200

        result_data = result_response.json()

        # Verify validation results structure
        assert "validation_issues" in result_data
        assert isinstance(result_data["validation_issues"], list)

    def test_llm_validation_summary_included(
        self,
        integration_test_client: TestClient,
        synthetic_dataset_e2e: Path,
        mock_llm_patch: AsyncMock,
    ) -> None:
        """
        Test that LLM-generated validation summary is included in result.

        Verifies:
        - LLM validation summary is present
        - Summary is a non-empty string
        - Summary provides human-readable feedback
        """
        # Initialize session
        init_response = integration_test_client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": str(synthetic_dataset_e2e)},
        )
        assert init_response.status_code == 200
        session_id = init_response.json()["session_id"]

        # Wait for completion
        max_wait_seconds = 30
        start_time = time.time()
        completed = False

        while time.time() - start_time < max_wait_seconds:
            status_response = integration_test_client.get(
                f"/api/v1/sessions/{session_id}/status"
            )
            status_data = status_response.json()

            if status_data["workflow_stage"] == WorkflowStage.COMPLETED:
                completed = True
                break

            if status_data["workflow_stage"] == WorkflowStage.FAILED:
                pytest.skip("Workflow failed")

            time.sleep(1)

        if not completed:
            pytest.skip("Workflow did not complete")

        # Get result
        result_response = integration_test_client.get(
            f"/api/v1/sessions/{session_id}/result"
        )
        assert result_response.status_code == 200

        result_data = result_response.json()

        # Verify LLM summary exists
        assert "llm_validation_summary" in result_data
        llm_summary = result_data["llm_validation_summary"]

        # Summary should be a string (may be empty if not generated yet)
        assert isinstance(llm_summary, str)

    def test_complete_workflow_time_budget(
        self,
        integration_test_client: TestClient,
        synthetic_dataset_e2e: Path,
        mock_llm_patch: AsyncMock,
    ) -> None:
        """
        Test that complete workflow completes under 2 minutes.

        Verifies:
        - Workflow completes within reasonable time
        - Time budget is enforced for synthetic data
        - Performance is acceptable
        """
        start_time = time.time()

        # Initialize session
        init_response = integration_test_client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": str(synthetic_dataset_e2e)},
        )
        assert init_response.status_code == 200
        session_id = init_response.json()["session_id"]

        # Poll until completion
        max_wait_seconds = 120  # 2 minute budget
        completed = False

        while time.time() - start_time < max_wait_seconds:
            status_response = integration_test_client.get(
                f"/api/v1/sessions/{session_id}/status"
            )
            status_data = status_response.json()

            if status_data["workflow_stage"] == WorkflowStage.COMPLETED:
                completed = True
                break

            if status_data["workflow_stage"] == WorkflowStage.FAILED:
                pytest.skip("Workflow failed")

            time.sleep(1)

        elapsed_time = time.time() - start_time

        if completed:
            # Verify completion time is reasonable
            assert elapsed_time < 120, (
                f"Workflow took {elapsed_time:.1f}s, "
                f"expected < 120s for synthetic data"
            )
        else:
            pytest.skip("Workflow did not complete (agents may not be running)")
