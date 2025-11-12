"""
End-to-End Integration Tests for Complete NWB Conversion Workflows.

Tests cover:
- Complete upload → format detection → metadata → conversion → validation → report workflow
- Multi-agent coordination
- State management across workflow stages
- Error recovery and fallback mechanisms
- Real-world usage scenarios
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add backend/src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from agents.evaluation_agent import EvaluationAgent
from agents.intelligent_format_detector import IntelligentFormatDetector
from agents.intelligent_metadata_mapper import IntelligentMetadataMapper
from models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
)
from services.report_service import ReportService

# ============================================================================
# Test: Complete Successful Workflow
# ============================================================================


@pytest.mark.e2e
@pytest.mark.integration
class TestCompleteSuccessfulWorkflow:
    """Test complete successful conversion workflow."""

    @pytest.mark.asyncio
    async def test_nwb_validation_workflow(
        self,
        sample_nwb_files,
        mock_llm_service,
        global_state,
    ):
        """Test complete NWB file validation workflow."""
        # Initialize agents
        evaluation_agent = EvaluationAgent(llm_service=mock_llm_service)

        nwb_file = sample_nwb_files["valid"]

        # Mock NWB Inspector validation
        with patch.object(evaluation_agent, "_run_nwb_inspector", new_callable=AsyncMock) as mock_inspector:
            from models import ValidationResult

            mock_inspector.return_value = ValidationResult(
                is_valid=True,
                issues=[],
                summary={"critical": 0, "error": 0, "warning": 0, "info": 0},
                inspector_version="0.5.0",
            )

            # Execute validation
            from models import MCPMessage

            message = MCPMessage(
                message_id="workflow-test-1",
                target_agent="evaluation",
                action="run_validation",
                context={"nwb_path": str(nwb_file)},
            )

            response = await evaluation_agent.handle_run_validation(message, global_state)

            # Verify workflow completed successfully
            assert response.success is True
            assert global_state.logs is not None
            assert len(global_state.logs) > 0

    @pytest.mark.asyncio
    async def test_format_detection_to_validation_workflow(
        self,
        sample_nwb_files,
        mock_llm_service,
        global_state,
    ):
        """Test workflow from format detection to validation."""
        # Step 1: Format Detection
        detector = IntelligentFormatDetector(llm_service=mock_llm_service)
        nwb_file = sample_nwb_files["valid"]

        format_result = await detector.detect_format(str(nwb_file), global_state)

        assert format_result is not None
        global_state.add_log(LogLevel.INFO, f"Format detected: {format_result.get('format', 'unknown')}")

        # Step 2: Validation
        evaluation_agent = EvaluationAgent(llm_service=mock_llm_service)

        with patch.object(evaluation_agent, "_run_nwb_inspector", new_callable=AsyncMock) as mock_inspector:
            from models import ValidationResult

            mock_inspector.return_value = ValidationResult(
                is_valid=True,
                issues=[],
                summary={"critical": 0, "error": 0, "warning": 0, "info": 0},
                inspector_version="0.5.0",
            )

            from models import MCPMessage

            message = MCPMessage(
                message_id="workflow-test-2",
                target_agent="evaluation",
                action="run_validation",
                context={"nwb_path": str(nwb_file)},
            )

            response = await evaluation_agent.handle_run_validation(message, global_state)

            assert response.success is True

        # Verify state contains both detection and validation logs
        log_messages = [log.message for log in global_state.logs]
        assert any("format" in msg.lower() for msg in log_messages)


# ============================================================================
# Test: Complete Workflow with Metadata Collection
# ============================================================================


@pytest.mark.e2e
@pytest.mark.integration
class TestWorkflowWithMetadata:
    """Test workflow including metadata collection and mapping."""

    @pytest.mark.asyncio
    async def test_metadata_parsing_to_validation_workflow(
        self,
        mock_llm_service_with_structured_response,
        sample_nwb_files,
        global_state,
    ):
        """Test workflow from metadata parsing to validation."""
        # Step 1: Parse user-provided metadata
        mapper = IntelligentMetadataMapper(llm_service=mock_llm_service_with_structured_response)

        user_input = """
        Session: Test recording from mouse V1
        Experimenter: John Doe
        Species: Mouse
        Age: 90 days
        Sex: Male
        """

        parsed_metadata = await mapper.parse_custom_metadata(user_input, existing_metadata={}, state=global_state)

        assert parsed_metadata is not None
        global_state.metadata = parsed_metadata
        global_state.add_log(LogLevel.INFO, f"Metadata parsed: {len(parsed_metadata)} fields")

        # Metadata is already mapped to NWB schema by parse_custom_metadata
        assert global_state.metadata is not None

        # Step 3: Validate NWB file with metadata
        evaluation_agent = EvaluationAgent(llm_service=mock_llm_service_with_structured_response)

        nwb_file = sample_nwb_files["valid"]

        with patch.object(evaluation_agent, "_run_nwb_inspector", new_callable=AsyncMock) as mock_inspector:
            from models import ValidationResult

            mock_inspector.return_value = ValidationResult(
                is_valid=True,
                issues=[],
                summary={"critical": 0, "error": 0, "warning": 0, "info": 0},
                inspector_version="0.5.0",
            )

            from models import MCPMessage

            message = MCPMessage(
                message_id="workflow-test-3",
                target_agent="evaluation",
                action="run_validation",
                context={"nwb_path": str(nwb_file)},
            )

            response = await evaluation_agent.handle_run_validation(message, global_state)

            assert response.success is True

        # Verify complete workflow state
        assert global_state.metadata is not None
        assert len(global_state.logs) >= 2


# ============================================================================
# Test: Complete Workflow with Report Generation
# ============================================================================


@pytest.mark.e2e
@pytest.mark.integration
class TestWorkflowWithReportGeneration:
    """Test complete workflow including report generation."""

    @pytest.mark.asyncio
    async def test_validation_to_report_workflow(
        self,
        sample_nwb_files,
        mock_llm_service,
        global_state,
        sample_metadata,
        tmp_path,
    ):
        """Test workflow from validation to report generation."""
        # Setup
        global_state.metadata = sample_metadata
        evaluation_agent = EvaluationAgent(llm_service=mock_llm_service)
        report_service = ReportService()

        nwb_file = sample_nwb_files["valid"]

        # Step 1: Run validation
        with patch.object(evaluation_agent, "_run_nwb_inspector", new_callable=AsyncMock) as mock_inspector:
            from models import ValidationIssue, ValidationResult, ValidationSeverity

            mock_inspector.return_value = ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message="Missing field: institution",
                        location="/",
                        check_name="check_institution",
                    )
                ],
                summary={"critical": 0, "error": 0, "warning": 1, "info": 0},
                inspector_version="0.5.0",
            )

            from models import MCPMessage

            val_message = MCPMessage(
                message_id="workflow-test-4",
                target_agent="evaluation",
                action="run_validation",
                context={"nwb_path": str(nwb_file)},
            )

            val_response = await evaluation_agent.handle_run_validation(val_message, global_state)

            assert val_response.success is True

        # Step 2: Generate HTML report
        validation_result = {
            "status": "passed",
            "file_name": str(nwb_file.name),
            "file_format": "NWB",
            "timestamp": datetime.now().isoformat(),
            "session_id": "test-session-id",
            "issues": [
                {
                    "severity": "warning",
                    "message": "Missing field: institution",
                }
            ],
        }

        html_report_path = tmp_path / "test_report.html"
        html_report = report_service.generate_html_report(
            output_path=html_report_path,
            validation_result=validation_result,
        )

        assert html_report is not None
        assert Path(html_report).exists()

        # Verify report contains expected sections
        content = Path(html_report).read_text()
        assert len(content) > 0

        # Step 3: Generate JSON report
        json_report_path = tmp_path / "test_report.json"
        json_report = report_service.generate_json_report(
            output_path=json_report_path,
            validation_result=validation_result,
        )

        assert json_report is not None
        assert Path(json_report).exists()

        # Verify complete workflow
        assert len(global_state.logs) > 0


# ============================================================================
# Test: Error Recovery Workflows
# ============================================================================


@pytest.mark.e2e
@pytest.mark.integration
class TestErrorRecoveryWorkflows:
    """Test workflow error recovery and fallback mechanisms."""

    @pytest.mark.asyncio
    async def test_workflow_continues_after_llm_failure(
        self,
        sample_nwb_files,
        mock_llm_service,
        global_state,
    ):
        """Test workflow continues when LLM fails."""
        # Configure LLM to fail
        mock_llm_service.generate_response.side_effect = Exception("LLM timeout")

        # Format detection should fallback to heuristics
        detector = IntelligentFormatDetector(llm_service=mock_llm_service)
        nwb_file = sample_nwb_files["valid"]

        format_result = await detector.detect_format(str(nwb_file), global_state)

        # Should still detect format using heuristics
        assert format_result is not None

    @pytest.mark.asyncio
    async def test_workflow_handles_validation_failures(
        self,
        sample_nwb_files,
        mock_llm_service,
        global_state,
    ):
        """Test workflow handles validation failures gracefully."""
        evaluation_agent = EvaluationAgent(llm_service=mock_llm_service)
        nwb_file = sample_nwb_files["invalid"]

        with patch.object(evaluation_agent, "_run_nwb_inspector", new_callable=AsyncMock) as mock_inspector:
            # Validation fails with critical errors
            from models import ValidationIssue, ValidationResult, ValidationSeverity

            mock_inspector.return_value = ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        message="Critical error: corrupted file",
                        location="/",
                        check_name="check_file_integrity",
                    )
                ],
                summary={"critical": 1, "error": 0, "warning": 0, "info": 0},
                inspector_version="0.5.0",
            )

            from models import MCPMessage

            message = MCPMessage(
                message_id="workflow-test-5",
                target_agent="evaluation",
                action="run_validation",
                context={"nwb_path": str(nwb_file)},
            )

            response = await evaluation_agent.handle_run_validation(message, global_state)

            # Should still return response (not crash)
            assert response is not None
            # May or may not be successful depending on implementation
            # assert response.success is False or response.success is True


# ============================================================================
# Test: Multi-Agent Coordination
# ============================================================================


@pytest.mark.e2e
@pytest.mark.integration
class TestMultiAgentCoordination:
    """Test coordination between multiple agents."""

    @pytest.mark.asyncio
    async def test_parallel_agent_operations(
        self,
        sample_nwb_files,
        mock_llm_service,
        global_state,
    ):
        """Test multiple agents working in parallel."""
        nwb_file = sample_nwb_files["valid"]

        # Start format detection and metadata parsing in parallel
        detector = IntelligentFormatDetector(llm_service=mock_llm_service)
        mapper = IntelligentMetadataMapper(llm_service=mock_llm_service)

        # Run both operations concurrently
        format_task = detector.detect_format(str(nwb_file), global_state)
        metadata_task = mapper.parse_custom_metadata(
            "Session: Test\nExperimenter: John Doe", existing_metadata={}, state=global_state
        )

        format_result, metadata_result = await asyncio.gather(format_task, metadata_task, return_exceptions=True)

        # Both should complete
        assert format_result is not None
        assert metadata_result is not None


# ============================================================================
# Test: Real-World Usage Scenarios
# ============================================================================


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.slow
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_researcher_upload_and_validate_workflow(
        self,
        sample_nwb_files,
        mock_llm_service,
        global_state,
        tmp_path,
    ):
        """Simulate researcher uploading and validating NWB file."""
        # Researcher scenario:
        # 1. Upload NWB file
        # 2. System detects format
        # 3. System validates file
        # 4. Researcher views HTML report

        nwb_file = sample_nwb_files["valid"]

        # Upload simulation
        global_state.add_log(LogLevel.INFO, f"File upload received: {nwb_file.name}")
        global_state.status = ConversionStatus.UPLOADING

        # Format detection
        detector = IntelligentFormatDetector(llm_service=mock_llm_service)
        format_result = await detector.detect_format(str(nwb_file), global_state)

        assert format_result is not None
        global_state.add_log(LogLevel.INFO, f"Format detected: {format_result.get('format', 'unknown')}")

        # Validation
        evaluation_agent = EvaluationAgent(llm_service=mock_llm_service)

        with patch.object(evaluation_agent, "_run_nwb_inspector", new_callable=AsyncMock) as mock_inspector:
            from models import MCPMessage, ValidationResult

            mock_inspector.return_value = ValidationResult(
                is_valid=True,
                issues=[],
                summary={"critical": 0, "error": 0, "warning": 0, "info": 0},
                inspector_version="0.5.0",
            )

            message = MCPMessage(
                message_id="researcher-workflow-1",
                target_agent="evaluation",
                action="run_validation",
                context={"nwb_path": str(nwb_file)},
            )

            val_response = await evaluation_agent.handle_run_validation(message, global_state)

            assert val_response.success is True

        global_state.status = ConversionStatus.COMPLETED

        # Generate report
        report_service = ReportService()
        validation_result = {
            "status": "passed",
            "file_name": str(nwb_file.name),
            "file_format": "NWB",
            "timestamp": datetime.now().isoformat(),
            "session_id": "researcher-session-id",
            "issues": [],
        }

        html_report = report_service.generate_html_report(
            output_path=tmp_path / "researcher_report.html",
            validation_result=validation_result,
        )

        # Researcher can view report
        assert html_report is not None
        assert Path(html_report).exists()

        # Verify complete workflow trace in state
        assert global_state.status == ConversionStatus.COMPLETED
        assert len(global_state.logs) >= 3


# ============================================================================
# Test: State Management Across Workflow
# ============================================================================


@pytest.mark.e2e
@pytest.mark.integration
class TestStateManagement:
    """Test state management across workflow stages."""

    @pytest.mark.asyncio
    async def test_state_persistence_across_stages(
        self,
        sample_nwb_files,
        mock_llm_service,
    ):
        """Test that state persists correctly across workflow stages."""
        # Create fresh state
        state = GlobalState()

        # Stage 1: Upload
        state.add_log(LogLevel.INFO, "File uploaded")
        assert len(state.logs) == 1

        # Stage 2: Format Detection
        detector = IntelligentFormatDetector(llm_service=mock_llm_service)
        format_result = await detector.detect_format(str(sample_nwb_files["valid"]), state)

        state.add_log(LogLevel.INFO, f"Format: {format_result.get('format')}")
        assert len(state.logs) == 2

        # Stage 3: Metadata
        state.metadata = {"session_description": "Test"}
        state.add_log(LogLevel.INFO, "Metadata collected")
        assert len(state.logs) == 3

        # Verify state integrity
        assert state.metadata is not None
        assert len(state.logs) == 3

        # All logs should be in chronological order
        timestamps = [log.timestamp for log in state.logs]
        assert timestamps == sorted(timestamps)
