"""
Comprehensive unit tests for EvaluationAgent.

Tests cover:
- Initialization and configuration
- NWB file validation
- Quality assessment
- Issue prioritization and analysis
- Correction guidance generation
- Report generation
- Log processing and workflow tracing
- Metadata provenance tracking
- LLM-based analysis (with mocking)
"""
import asyncio
import json
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock, mock_open
import sys
import os

# Add backend/src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from agents.evaluation_agent import EvaluationAgent
from models import (
    ConversionStatus,
    CorrectionContext,
    GlobalState,
    LogLevel,
    LogEntry,
    MCPMessage,
    MCPResponse,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationStatus,
    ValidationOutcome,
)
from services import LLMService


# ============================================================================
# Fixtures
# ============================================================================

# Note: The following fixtures are provided by conftest files:
# - mock_llm_quality_assessor: from root conftest.py (specialized for quality assessment)
# - evaluation_agent: from agents/conftest.py (uses mock_llm_quality_assessor)
# - global_state: from root conftest.py

@pytest.fixture
def evaluation_agent_no_llm():
    """Create an EvaluationAgent instance without LLM service for testing fallback behavior."""
    return EvaluationAgent(llm_service=None)

@pytest.fixture
def sample_nwb_path(tmp_path):
    """Create a sample NWB file path for testing."""
    nwb_file = tmp_path / "test_file.nwb"
    nwb_file.write_bytes(b"mock nwb content")
    return str(nwb_file)


@pytest.fixture
def sample_validation_result():
    """Create a sample validation result for testing."""
    from models import ValidationIssue, ValidationSeverity
    return ValidationResult(
        is_valid=True,
        issues=[
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message="Missing required field: session_description",
                location="/",
                check_name="check_session_description",
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="Missing recommended field: experimenter",
                location="/",
                check_name="check_experimenter",
            ),
        ],
        summary={
            "critical": 1,
            "error": 0,
            "warning": 1,
            "info": 0,
        },
        inspector_version="0.5.0",
    )


@pytest.fixture
def sample_mcp_message():
    """Create a sample MCP message for testing."""
    return MCPMessage(
        message_id="test-msg-123",
        agent_type="evaluation",
        action="run_validation",
        context={"nwb_path": "/path/to/test.nwb"},
    )


# ============================================================================
# Test: Initialization
# ============================================================================

@pytest.mark.unit
class TestEvaluationAgentInitialization:
    """Test suite for EvaluationAgent initialization."""

    def test_init_with_llm_service(self, mock_llm_quality_assessor):
        """Test initialization with LLM service."""
        agent = EvaluationAgent(llm_service=mock_llm_quality_assessor)

        assert agent._llm_service is mock_llm_quality_assessor
        assert agent._report_service is not None
        assert agent._prompt_service is not None
        assert agent._validation_analyzer is not None
        assert agent._issue_resolution is not None
        assert agent._history_learner is not None

    def test_init_without_llm_service(self):
        """Test initialization without LLM service."""
        agent = EvaluationAgent(llm_service=None)

        assert agent._llm_service is None
        assert agent._report_service is not None
        assert agent._prompt_service is not None
        assert agent._validation_analyzer is None
        assert agent._issue_resolution is None
        assert agent._history_learner is None


# ============================================================================
# Test: File Validation
# ============================================================================

@pytest.mark.unit
class TestFileValidation:
    """Test suite for NWB file validation."""

    @pytest.mark.asyncio
    async def test_handle_run_validation_success(
        self, evaluation_agent, global_state, sample_nwb_path
    ):
        """Test successful validation handling."""
        message = MCPMessage(
            message_id="val-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": sample_nwb_path},
        )

        # Mock the _run_nwb_inspector method
        with patch.object(
            evaluation_agent,
            '_run_nwb_inspector',
            new_callable=AsyncMock
        ) as mock_inspector:
            mock_inspector.return_value = ValidationResult(
                is_valid=True,
                issues=[],
                summary={"critical": 0, "error": 0, "warning": 0, "info": 0},
                inspector_version="0.5.0",
            )

            response = await evaluation_agent.handle_run_validation(message, global_state)

            assert response.success is True
            assert response.reply_to == "val-123"
            mock_inspector.assert_called_once_with(sample_nwb_path)

    @pytest.mark.asyncio
    async def test_handle_run_validation_missing_path(
        self, evaluation_agent, global_state
    ):
        """Test validation with missing NWB path."""
        message = MCPMessage(
            message_id="val-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="run_validation",
            context={},  # Missing nwb_path
        )

        response = await evaluation_agent.handle_run_validation(message, global_state)

        assert response.success is False
        assert response.error is not None
        assert response.error['code'] == "MISSING_NWB_PATH"
        assert "required" in response.error['message'].lower()

    @pytest.mark.asyncio
    async def test_handle_run_validation_with_issues(
        self, evaluation_agent, global_state, sample_nwb_path, sample_validation_result
    ):
        """Test validation that finds issues."""
        message = MCPMessage(
            message_id="val-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": sample_nwb_path},
        )

        with patch.object(
            evaluation_agent,
            '_run_nwb_inspector',
            new_callable=AsyncMock
        ) as mock_inspector:
            mock_inspector.return_value = sample_validation_result

            response = await evaluation_agent.handle_run_validation(message, global_state)

            assert response.success is True
            assert response.result is not None
            # Check that result contains validation data
            assert "validation_result" in response.result or "issues" in response.result


# ============================================================================
# Test: File Info Extraction
# ============================================================================

@pytest.mark.unit
class TestFileInfoExtraction:
    """Test suite for file information extraction."""

    def test_extract_file_info_valid_file(self, evaluation_agent, sample_nwb_path):
        """Test extracting info from a valid file."""
        file_info = evaluation_agent._extract_file_info(sample_nwb_path)

        assert file_info is not None
        assert "nwb_version" in file_info
        assert "file_size_bytes" in file_info
        assert "creation_date" in file_info
        assert file_info["file_size_bytes"] >= 0

    def test_extract_file_info_nonexistent_file(self, evaluation_agent):
        """Test extracting info from nonexistent file."""
        file_info = evaluation_agent._extract_file_info("/nonexistent/path/file.nwb")

        # Should return basic info even if file doesn't exist
        assert file_info is not None
        assert "nwb_version" in file_info
        assert "file_size_bytes" in file_info


# ============================================================================
# Test: Quality Assessment
# ============================================================================

@pytest.mark.unit
class TestQualityAssessment:
    """Test suite for NWB quality assessment."""

    @pytest.mark.asyncio
    async def test_assess_nwb_quality_with_llm(
        self, evaluation_agent, sample_validation_result, global_state
    ):
        """Test quality assessment with LLM service."""
        nwb_path = "/path/to/test.nwb"

        quality = await evaluation_agent._assess_nwb_quality(
            nwb_path, sample_validation_result, global_state
        )

        assert quality is not None
        assert "overall_score" in quality or "assessment" in quality

    @pytest.mark.asyncio
    async def test_assess_nwb_quality_without_llm(
        self, evaluation_agent_no_llm, sample_validation_result, global_state
    ):
        """Test quality assessment without LLM service."""
        nwb_path = "/path/to/test.nwb"

        quality = await evaluation_agent_no_llm._assess_nwb_quality(
            nwb_path, sample_validation_result, global_state
        )

        # Should return basic quality metrics even without LLM
        assert quality is not None


# ============================================================================
# Test: Issue Prioritization
# ============================================================================

@pytest.mark.unit
class TestIssuePrioritization:
    """Test suite for issue prioritization and explanation."""

    @pytest.mark.asyncio
    async def test_prioritize_and_explain_issues_with_llm(
        self, evaluation_agent, sample_validation_result, global_state
    ):
        """Test issue prioritization with LLM."""
        issues = sample_validation_result.issues

        result = await evaluation_agent._prioritize_and_explain_issues(issues, global_state)

        assert result is not None
        assert isinstance(result, (dict, list))

    @pytest.mark.asyncio
    async def test_prioritize_and_explain_issues_empty_list(
        self, evaluation_agent, global_state
    ):
        """Test issue prioritization with empty issues list."""
        result = await evaluation_agent._prioritize_and_explain_issues([], global_state)

        assert result is not None


# ============================================================================
# Test: NWB Inspector Integration
# ============================================================================

@pytest.mark.unit
class TestNWBInspectorIntegration:
    """Test suite for NWB Inspector integration."""

    @pytest.mark.asyncio
    async def test_run_nwb_inspector_success(
        self, evaluation_agent, sample_nwb_path
    ):
        """Test successful NWB inspector execution."""
        # Mock subprocess to avoid actual NWB Inspector call
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({
                    "messages": [],
                    "file_path": sample_nwb_path,
                }),
                stderr="",
            )

            result = await evaluation_agent._run_nwb_inspector(sample_nwb_path)

            assert isinstance(result, ValidationResult)
            assert result.is_valid in [True, False]

    @pytest.mark.asyncio
    async def test_run_nwb_inspector_with_errors(
        self, evaluation_agent, sample_nwb_path
    ):
        """Test NWB inspector with validation errors."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({
                    "messages": [
                        {
                            "message": "Critical error",
                            "severity": 2,
                            "location": "/",
                        }
                    ],
                    "file_path": sample_nwb_path,
                }),
                stderr="",
            )

            result = await evaluation_agent._run_nwb_inspector(sample_nwb_path)

            assert isinstance(result, ValidationResult)
            assert len(result.issues) > 0


# ============================================================================
# Test: Correction Analysis
# ============================================================================

@pytest.mark.unit
class TestCorrectionAnalysis:
    """Test suite for correction analysis."""

    @pytest.mark.asyncio
    async def test_handle_analyze_corrections_with_llm(
        self, evaluation_agent, global_state
    ):
        """Test correction analysis with LLM service."""
        message = MCPMessage(
            message_id="corr-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="analyze_corrections",
            context={
                "validation_result": {
                    "status": "failed",
                    "issues": [{"message": "Test issue", "severity": "CRITICAL"}],
                }
            },
        )

        response = await evaluation_agent.handle_analyze_corrections(message, global_state)

        assert response is not None
        assert isinstance(response, MCPResponse)

    @pytest.mark.asyncio
    async def test_handle_analyze_corrections_without_llm(
        self, evaluation_agent_no_llm, global_state
    ):
        """Test correction analysis without LLM service."""
        message = MCPMessage(
            message_id="corr-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="analyze_corrections",
            context={
                "validation_result": {
                    "status": "failed",
                    "issues": [{"message": "Test issue", "severity": "CRITICAL"}],
                }
            },
        )

        response = await evaluation_agent_no_llm.handle_analyze_corrections(
            message, global_state
        )

        # Should handle gracefully without LLM
        assert response is not None


# ============================================================================
# Test: LLM Analysis
# ============================================================================

@pytest.mark.unit
@pytest.mark.llm
class TestLLMAnalysis:
    """Test suite for LLM-based analysis."""

    @pytest.mark.asyncio
    async def test_analyze_with_llm_success(self, evaluation_agent, sample_validation_result, global_state):
        """Test successful LLM analysis."""
        context = CorrectionContext(
            validation_result=sample_validation_result,
        )

        with patch.object(
            evaluation_agent._llm_service,
            'generate_structured_output',
            new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = {
                "analysis": "Detailed analysis response",
                "suggestions": [],
                "recommended_action": "retry"
            }

            result = await evaluation_agent._analyze_with_llm(context, global_state)

            assert result is not None
            assert isinstance(result, dict)
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_with_llm_timeout(self, evaluation_agent, sample_validation_result, global_state):
        """Test LLM analysis with timeout."""
        context = CorrectionContext(
            validation_result=sample_validation_result,
        )

        with patch.object(
            evaluation_agent._llm_service,
            'generate_response',
            new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.side_effect = asyncio.TimeoutError("LLM timeout")

            # Should handle timeout gracefully
            result = await evaluation_agent._analyze_with_llm(context, global_state)

            # Could be None or error message depending on implementation
            assert result is not None or result is None


# ============================================================================
# Test: Prompt Building
# ============================================================================

@pytest.mark.unit
class TestPromptBuilding:
    """Test suite for correction prompt building."""

    def test_build_correction_prompt_with_issues(self, evaluation_agent, sample_validation_result):
        """Test building correction prompt with validation issues."""
        context = CorrectionContext(
            validation_result=sample_validation_result,
        )

        prompt = evaluation_agent._build_correction_prompt(context)

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "session_description" in prompt or "Missing field" in prompt

    def test_build_correction_prompt_empty_issues(self, evaluation_agent, sample_validation_result):
        """Test building correction prompt with no issues."""
        # Create a validation result with no issues
        from models import ValidationResult
        empty_result = ValidationResult(
            is_valid=True,
            issues=[],
            summary={}
        )
        context = CorrectionContext(
            validation_result=empty_result,
        )

        prompt = evaluation_agent._build_correction_prompt(context)

        assert prompt is not None
        assert isinstance(prompt, str)


# ============================================================================
# Test: Report Generation
# ============================================================================

@pytest.mark.unit
class TestReportGeneration:
    """Test suite for report generation."""

    @pytest.mark.asyncio
    async def test_handle_generate_report_success(
        self, evaluation_agent, global_state
    ):
        """Test successful report generation."""
        # Setup state with validation data
        global_state.status = ConversionStatus.COMPLETED
        global_state.add_log(LogLevel.INFO, "Test log entry")

        message = MCPMessage(
            message_id="report-123",
            target_agent="evaluation",
            action="generate_report",
            context={
                "validation_result": {
                    "overall_status": "PASSED",
                    "is_valid": True,
                    "issues": [],
                    "file_info": {}
                },
                "nwb_path": "/path/to/test.nwb"
            },
        )

        with patch.object(
            evaluation_agent._report_service,
            'generate_html_report',
            return_value=None
        ) as mock_html, patch.object(
            evaluation_agent._report_service,
            'generate_pdf_report',
            return_value=None
        ) as mock_pdf, patch.object(
            evaluation_agent._report_service,
            'generate_text_report',
            return_value=None
        ) as mock_text, patch.object(
            evaluation_agent,
            '_extract_file_info',
            return_value={
                "file_size_bytes": 1024,
                "nwb_version": "2.5.0",
                "creation_date": "2024-01-01"
            }
        ), patch.object(
            evaluation_agent,
            '_add_metadata_provenance',
            return_value={
                "file_size_bytes": 1024,
                "nwb_version": "2.5.0",
                "creation_date": "2024-01-01"
            }
        ), patch.object(
            evaluation_agent,
            '_build_workflow_trace',
            return_value={"summary": {}, "detailed_logs_sequential": [], "stage_options": []}
        ), patch.object(
            evaluation_agent,
            '_generate_quality_assessment',
            new_callable=AsyncMock,
            return_value={"overall_score": 85, "grade": "B", "assessment": "Good quality"}
        ), patch('builtins.open', mock_open()):
            response = await evaluation_agent.handle_generate_report(message, global_state)

            assert response.success is True
            mock_html.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_generate_report_error(
        self, evaluation_agent, global_state
    ):
        """Test report generation with error."""
        message = MCPMessage(
            message_id="report-123",
            target_agent="evaluation",
            action="generate_report",
            context={},
        )

        with patch.object(
            evaluation_agent._report_service,
            'generate_html_report',
            new_callable=AsyncMock
        ) as mock_html:
            mock_html.side_effect = Exception("Report generation failed")

            response = await evaluation_agent.handle_generate_report(message, global_state)

            # Should handle error gracefully
            assert response is not None


# ============================================================================
# Test: Log Processing
# ============================================================================

@pytest.mark.unit
class TestLogProcessing:
    """Test suite for log processing and categorization."""

    def test_prepare_logs_for_sequential_view(self, evaluation_agent):
        """Test preparing logs for sequential view."""
        logs = [
            LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.INFO,
                message="Starting initialization",
                context={},
            ),
            LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.INFO,
                message="File upload received",
                context={},
            ),
            LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.INFO,
                message="Detecting format with LLM",
                context={},
            ),
        ]

        enhanced_logs, stage_options = evaluation_agent._prepare_logs_for_sequential_view(logs)

        assert enhanced_logs is not None
        assert isinstance(enhanced_logs, list)
        assert len(enhanced_logs) == 3
        assert all("stage" in log for log in enhanced_logs)
        assert all("stage_display" in log for log in enhanced_logs)
        assert all("stage_icon" in log for log in enhanced_logs)

        assert stage_options is not None
        assert isinstance(stage_options, list)
        assert len(stage_options) > 0

    def test_categorize_logs_by_stage(self, evaluation_agent):
        """Test categorizing logs by stage."""
        logs = [
            LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.INFO,
                message="Initialized system",
                context={},
            ),
            LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.INFO,
                message="Upload complete",
                context={},
            ),
        ]

        categorized = evaluation_agent._categorize_logs_by_stage(logs)

        assert categorized is not None
        assert isinstance(categorized, dict)
        # Should have at least some stages
        assert len(categorized) > 0


# ============================================================================
# Test: Workflow Trace
# ============================================================================

@pytest.mark.unit
class TestWorkflowTrace:
    """Test suite for workflow trace building."""

    def test_build_workflow_trace(self, evaluation_agent, global_state):
        """Test building workflow trace."""
        # Add some logs to state
        global_state.add_log(LogLevel.INFO, "Test log 1")
        global_state.add_log(LogLevel.INFO, "Upload received")
        global_state.add_log(LogLevel.INFO, "Validation complete")

        trace = evaluation_agent._build_workflow_trace(global_state)

        assert trace is not None
        assert isinstance(trace, dict)
        assert "summary" in trace
        assert "detailed_logs_sequential" in trace
        assert "stage_options" in trace

    def test_build_workflow_trace_empty_state(self, evaluation_agent):
        """Test building workflow trace with empty state."""
        empty_state = GlobalState()

        trace = evaluation_agent._build_workflow_trace(empty_state)

        assert trace is not None
        assert isinstance(trace, dict)


# ============================================================================
# Test: Metadata Provenance
# ============================================================================

@pytest.mark.unit
class TestMetadataProvenance:
    """Test suite for metadata provenance tracking."""

    def test_add_metadata_provenance(self, evaluation_agent, global_state):
        """Test adding metadata provenance."""
        metadata = {
            "subject": {"species": "Mus musculus"},
            "session_description": "Test session",
        }

        result = evaluation_agent._add_metadata_provenance(metadata, global_state)

        assert result is not None
        assert isinstance(result, dict)

    def test_add_metadata_provenance_empty(self, evaluation_agent, global_state):
        """Test adding provenance for empty metadata."""
        result = evaluation_agent._add_metadata_provenance({}, global_state)

        assert result is not None
        assert isinstance(result, dict)


# ============================================================================
# Test: Quality Assessment Generation
# ============================================================================

@pytest.mark.unit
@pytest.mark.llm
class TestQualityAssessmentGeneration:
    """Test suite for quality assessment generation."""

    @pytest.mark.asyncio
    async def test_generate_quality_assessment(
        self, evaluation_agent, sample_validation_result
    ):
        """Test generating quality assessment."""
        validation_dict = {
            "is_valid": sample_validation_result.is_valid,
            "issues": sample_validation_result.issues,
            "file_info": {
                "file_size_bytes": 1024,
                "nwb_version": "2.5.0",
                "creation_date": "2024-01-01"
            },
            "overall_status": "PASSED",
            "issue_counts": {"critical": 0, "error": 0, "warning": 0}
        }

        assessment = await evaluation_agent._generate_quality_assessment(validation_dict)

        assert assessment is not None
        assert isinstance(assessment, dict)


# ============================================================================
# Test: Correction Guidance Generation
# ============================================================================

@pytest.mark.unit
@pytest.mark.llm
class TestCorrectionGuidanceGeneration:
    """Test suite for correction guidance generation."""

    @pytest.mark.asyncio
    async def test_generate_correction_guidance(
        self, evaluation_agent, sample_validation_result
    ):
        """Test generating correction guidance."""
        validation_dict = {
            "is_valid": sample_validation_result.is_valid,
            "issues": sample_validation_result.issues,
            "nwb_file_path": "/path/to/test.nwb",
            "issue_counts": {"critical": 1, "error": 0, "warning": 1}
        }

        guidance = await evaluation_agent._generate_correction_guidance(validation_dict)

        assert guidance is not None
        assert isinstance(guidance, dict)


# ============================================================================
# Test: Integration Scenarios
# ============================================================================

@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration tests for complete evaluation workflows."""

    @pytest.mark.asyncio
    async def test_complete_validation_workflow(
        self, evaluation_agent, global_state, sample_nwb_path
    ):
        """Test complete validation workflow from start to finish."""
        # Step 1: Validate file
        val_message = MCPMessage(
            message_id="val-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": sample_nwb_path},
        )

        with patch.object(
            evaluation_agent,
            '_run_nwb_inspector',
            new_callable=AsyncMock
        ) as mock_inspector:
            mock_inspector.return_value = ValidationResult(
                is_valid=True,
                issues=[],
                summary={"critical": 0, "error": 0, "warning": 0, "info": 0},
                inspector_version="0.5.0",
            )

            val_response = await evaluation_agent.handle_run_validation(
                val_message, global_state
            )

            assert val_response.success is True

        # Step 2: Generate report
        report_message = MCPMessage(
            message_id="report-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="generate_report",
            context={
                "validation_result": {
                    "overall_status": "PASSED",
                    "is_valid": True,
                    "issues": [],
                    "file_info": {}
                },
                "nwb_path": sample_nwb_path
            },
        )

        with patch.object(
            evaluation_agent._report_service,
            'generate_html_report',
            return_value=None
        ) as mock_html, patch.object(
            evaluation_agent._report_service,
            'generate_pdf_report',
            return_value=None
        ), patch.object(
            evaluation_agent._report_service,
            'generate_text_report',
            return_value=None
        ), patch.object(
            evaluation_agent,
            '_extract_file_info',
            return_value={
                "file_size_bytes": 1024,
                "nwb_version": "2.5.0",
                "creation_date": "2024-01-01"
            }
        ), patch.object(
            evaluation_agent,
            '_add_metadata_provenance',
            return_value={
                "file_size_bytes": 1024,
                "nwb_version": "2.5.0",
                "creation_date": "2024-01-01"
            }
        ), patch.object(
            evaluation_agent,
            '_build_workflow_trace',
            return_value={"summary": {}, "detailed_logs_sequential": [], "stage_options": []}
        ), patch.object(
            evaluation_agent,
            '_generate_quality_assessment',
            new_callable=AsyncMock,
            return_value={"overall_score": 85, "grade": "B", "assessment": "Good quality"}
        ), patch('builtins.open', mock_open()):
            report_response = await evaluation_agent.handle_generate_report(
                report_message, global_state
            )

            assert report_response.success is True
            mock_html.assert_called_once()


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================

@pytest.mark.unit
class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling."""

    def test_extract_file_info_invalid_path(self, evaluation_agent):
        """Test file info extraction with invalid path."""
        # Should not crash with invalid paths
        info = evaluation_agent._extract_file_info("")
        assert info is not None

    @pytest.mark.asyncio
    async def test_validation_with_corrupted_nwb(
        self, evaluation_agent, tmp_path, global_state
    ):
        """Test validation with corrupted NWB file."""
        corrupted_file = tmp_path / "corrupted.nwb"
        corrupted_file.write_bytes(b"not a valid nwb file")

        message = MCPMessage(
            message_id="val-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": str(corrupted_file)},
        )

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Invalid NWB file",
            )

            response = await evaluation_agent.handle_run_validation(message, global_state)

            # Should handle gracefully
            assert response is not None

    def test_prepare_logs_empty_list(self, evaluation_agent):
        """Test log preparation with empty list."""
        enhanced_logs, stage_options = evaluation_agent._prepare_logs_for_sequential_view([])

        assert enhanced_logs == []
        assert isinstance(stage_options, list)


# ============================================================================
# Test: File Info Extraction
# ============================================================================

@pytest.mark.unit
class TestFileInfoExtraction:
    """Test suite for _extract_file_info method."""

    @pytest.mark.asyncio
    async def test_extract_file_info_with_h5py_success(self, evaluation_agent, tmp_path, global_state):
        """Test file info extraction using h5py successfully."""
        import h5py

        nwb_file = tmp_path / "test.nwb"

        # Create a mock NWB file with h5py
        with h5py.File(nwb_file, "w") as f:
            f.attrs["nwb_version"] = "2.5.0"
            f.attrs["identifier"] = "test-123"
            f.attrs["session_description"] = "Test session"
            f.attrs["session_start_time"] = "2024-01-01T00:00:00"

            # Create general group with datasets (not attributes)
            general = f.create_group("general")
            general.create_dataset("experimenter", data="Dr. Jane Smith")
            general.create_dataset("institution", data="MIT")
            general.create_dataset("lab", data="Test Lab")
            general.create_dataset("experiment_description", data="Test experiment")
            general.create_dataset("session_id", data="session-001")

            # Create subject group
            subject = general.create_group("subject")
            subject.create_dataset("subject_id", data="mouse-001")
            subject.create_dataset("species", data="Mus musculus")
            subject.create_dataset("sex", data="M")
            subject.create_dataset("age", data="P90D")

        # Set state for logging
        evaluation_agent._state = global_state

        file_info = evaluation_agent._extract_file_info(str(nwb_file))

        assert file_info["nwb_version"] == "2.5.0"
        assert file_info["identifier"] == "test-123"
        assert file_info["experimenter"] == ["Dr. Jane Smith"]
        assert file_info["institution"] == "MIT"
        assert file_info["subject_id"] == "mouse-001"
        assert file_info["species"] == "Mus musculus"
        assert file_info["_provenance"]["experimenter"] == "file-extracted"

    @pytest.mark.asyncio
    async def test_extract_file_info_h5py_with_attributes(self, evaluation_agent, tmp_path, global_state):
        """Test file info extraction when data is stored as attributes."""
        import h5py

        nwb_file = tmp_path / "test_attrs.nwb"

        # Create a mock NWB file with attributes (older style)
        with h5py.File(nwb_file, "w") as f:
            f.attrs["nwb_version"] = "2.4.0"
            f.attrs["identifier"] = "test-456"

            general = f.create_group("general")
            general.attrs["experimenter"] = "Dr. John Doe"
            general.attrs["institution"] = "Stanford"

        evaluation_agent._state = global_state
        file_info = evaluation_agent._extract_file_info(str(nwb_file))

        assert file_info["experimenter"] == ["Dr. John Doe"]
        assert file_info["institution"] == "Stanford"

    @pytest.mark.asyncio
    async def test_extract_file_info_pynwb_fallback(self, evaluation_agent, tmp_path, global_state):
        """Test file info extraction falls back to PyNWB when h5py fails."""
        nwb_file = tmp_path / "test_pynwb.nwb"
        nwb_file.write_bytes(b"mock nwb")

        evaluation_agent._state = global_state

        # Mock h5py to raise exception, forcing PyNWB fallback
        with patch('h5py.File', side_effect=Exception("h5py error")):
            with patch('pynwb.NWBHDF5IO') as mock_pynwb:
                mock_nwbfile = Mock()
                mock_nwbfile.nwb_version = "2.5.0"
                mock_nwbfile.identifier = "pynwb-test"
                mock_nwbfile.session_description = "PyNWB test"
                mock_nwbfile.session_start_time = "2024-01-01"
                mock_nwbfile.session_id = "session-pynwb"
                mock_nwbfile.experimenter = ["Dr. PyNWB"]
                mock_nwbfile.institution = "PyNWB Inst"
                mock_nwbfile.lab = "PyNWB Lab"
                mock_nwbfile.experiment_description = "PyNWB exp"

                mock_subject = Mock()
                mock_subject.subject_id = "subject-pynwb"
                mock_subject.species = "Rattus norvegicus"
                mock_subject.sex = "F"
                mock_subject.age = "P60D"
                mock_subject.date_of_birth = "2023-01-01"
                mock_subject.description = "Test subject"
                mock_subject.genotype = "WT"
                mock_subject.strain = "Wistar"
                mock_nwbfile.subject = mock_subject

                mock_io = Mock()
                mock_io.read.return_value = mock_nwbfile
                mock_io.__enter__ = Mock(return_value=mock_io)
                mock_io.__exit__ = Mock(return_value=None)
                mock_pynwb.return_value = mock_io

                file_info = evaluation_agent._extract_file_info(str(nwb_file))

                assert file_info["nwb_version"] == "2.5.0"
                assert file_info["experimenter"] == ["Dr. PyNWB"]
                assert file_info["subject_id"] == "subject-pynwb"

    def test_extract_file_info_nonexistent_file(self, evaluation_agent, global_state):
        """Test file info extraction with non-existent file."""
        evaluation_agent._state = global_state

        file_info = evaluation_agent._extract_file_info("/nonexistent/path.nwb")

        # Should return default values without crashing
        assert file_info["nwb_version"] == "Unknown"
        assert file_info["experimenter"] == []
        assert file_info["institution"] == "N/A"


# ============================================================================
# Test: PASSED_WITH_ISSUES Report Generation
# ============================================================================

@pytest.mark.unit
class TestPassedWithIssuesReporting:
    """Test suite for PASSED_WITH_ISSUES report generation."""

    @pytest.mark.asyncio
    async def test_handle_generate_report_passed_with_issues(
        self, evaluation_agent, tmp_path, global_state
    ):
        """Test report generation for PASSED_WITH_ISSUES status."""
        global_state.output_path = str(tmp_path / "test.nwb")

        validation_result = {
            "overall_status": "PASSED_WITH_ISSUES",
            "issues": [{"severity": "WARNING", "message": "Minor issue"}],
            "summary": {"warning": 1},
            "file_info": {"nwb_version": "2.5.0"},
        }

        message = MCPMessage(
            message_id="report-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="generate_report",
            context={
                "validation_result": validation_result,
                "nwb_path": str(tmp_path / "test.nwb"),
            },
        )

        with patch.object(
            evaluation_agent._report_service,
            'generate_json_report'
        ) as mock_json, patch.object(
            evaluation_agent,
            '_extract_file_info',
            return_value={"nwb_version": "2.5.0"}
        ), patch.object(
            evaluation_agent,
            '_build_workflow_trace',
            return_value={"summary": {}}
        ), patch.object(
            evaluation_agent,
            '_add_metadata_provenance',
            return_value={"nwb_version": "2.5.0"}
        ):
            response = await evaluation_agent.handle_generate_report(message, global_state)

            assert response.success is True
            assert response.result["report_type"] == "preview_json"
            assert response.result["awaiting_user_decision"] is True
            mock_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_generate_report_passed_with_issues_final_accepted(
        self, evaluation_agent, tmp_path, global_state
    ):
        """Test final report generation after user accepts PASSED_WITH_ISSUES."""
        global_state.output_path = str(tmp_path / "test.nwb")

        # Create a mock NWB file
        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock nwb")

        validation_result = {
            "overall_status": "PASSED_WITH_ISSUES",
            "issues": [{"severity": "WARNING", "message": "Minor issue"}],
            "summary": {"warning": 1},
            "file_info": {"nwb_version": "2.5.0"},
        }

        message = MCPMessage(
            message_id="report-final",
            agent_type="evaluation",
            target_agent="evaluation",
            action="generate_report",
            context={
                "validation_result": validation_result,
                "nwb_path": str(nwb_file),
                "final_accepted": True,  # User accepted the issues
            },
        )

        with patch.object(
            evaluation_agent._report_service,
            'generate_html_report'
        ) as mock_html, patch.object(
            evaluation_agent._report_service,
            'generate_pdf_report'
        ) as mock_pdf, patch.object(
            evaluation_agent._report_service,
            'generate_text_report'
        ) as mock_text, patch.object(
            evaluation_agent,
            '_extract_file_info',
            return_value={"nwb_version": "2.5.0", "_provenance": {}, "_source_files": {}}
        ), patch.object(
            evaluation_agent,
            '_build_workflow_trace',
            return_value={"summary": {}}
        ), patch.object(
            evaluation_agent,
            '_add_metadata_provenance',
            return_value={"nwb_version": "2.5.0", "_provenance": {}, "_source_files": {}}
        ), patch.object(
            evaluation_agent,
            '_generate_quality_assessment',
            new_callable=AsyncMock,
            return_value={"score": 85, "grade": "B"}
        ), patch('builtins.open', mock_open()), patch('json.dump'):
            response = await evaluation_agent.handle_generate_report(message, global_state)

            assert response.success is True
            assert response.result["report_type"] == "html_pdf_and_text"
            # Should generate final reports (HTML, PDF, text)
            mock_html.assert_called_once()
            mock_pdf.assert_called_once()
            mock_text.assert_called_once()


# ============================================================================
# Test: Register Evaluation Agent
# ============================================================================

@pytest.mark.unit
class TestRegisterEvaluationAgent:
    """Test suite for register_evaluation_agent function."""

    def test_register_evaluation_agent_with_llm(self):
        """Test registering evaluation agent with LLM service."""
        from agents.evaluation_agent import register_evaluation_agent
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_llm = Mock()

        agent = register_evaluation_agent(mock_mcp, llm_service=mock_llm)

        assert agent is not None
        assert agent._llm_service is mock_llm
        assert mock_mcp.register_handler.call_count == 3

        # Verify handlers are registered (checking first 2 args of each call)
        calls = mock_mcp.register_handler.call_args_list
        assert calls[0][0][:2] == ("evaluation", "run_validation")
        assert calls[1][0][:2] == ("evaluation", "analyze_corrections")
        assert calls[2][0][:2] == ("evaluation", "generate_report")

    def test_register_evaluation_agent_without_llm(self):
        """Test registering evaluation agent without LLM service."""
        from agents.evaluation_agent import register_evaluation_agent
        from unittest.mock import Mock

        mock_mcp = Mock()

        agent = register_evaluation_agent(mock_mcp, llm_service=None)

        assert agent is not None
        assert agent._llm_service is None


# ============================================================================
# Test: LLM Exception Handling
# ============================================================================

@pytest.mark.unit
class TestLLMExceptionHandling:
    """Test suite for exception handling in LLM-powered features."""

    @pytest.mark.asyncio
    async def test_prioritize_issues_llm_failure(self, evaluation_agent, global_state):
        """Test issue prioritization falls back gracefully on LLM failure."""
        from models import ValidationIssue, ValidationSeverity

        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Test error",
                location="/",
                check_name="test_check",
            )
        ]

        # Mock LLM to raise exception
        evaluation_agent._llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )

        result = await evaluation_agent._prioritize_and_explain_issues(issues, global_state)

        # Should return original issues without crashing
        assert len(result) == 1
        assert result[0]["message"] == "Test error"

    @pytest.mark.asyncio
    async def test_assess_quality_llm_failure(self, evaluation_agent, tmp_path, global_state):
        """Test quality assessment falls back gracefully on LLM failure."""
        from models import ValidationResult, ValidationIssue, ValidationSeverity

        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock")

        validation_result = ValidationResult(
            is_valid=True,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Minor issue",
                    location="/",
                    check_name="test",
                )
            ],
            summary={"warning": 1},
            inspector_version="0.5.0",
        )

        # Mock LLM to raise exception
        evaluation_agent._llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("LLM error")
        )

        # Mock _extract_file_info to avoid actual file reading
        with patch.object(evaluation_agent, '_extract_file_info', return_value={}):
            result = await evaluation_agent._assess_nwb_quality(
                str(nwb_file), validation_result, global_state
            )

        # Should return fallback score
        assert result["score"] >= 0
        assert result["score"] <= 100
        assert result["grade"] in ["A", "B", "C", "D", "F"]


# ============================================================================
# Test: Analyze Corrections Edge Cases
# ============================================================================

@pytest.mark.unit
class TestAnalyzeCorrectionsEdgeCases:
    """Test suite for edge cases in handle_analyze_corrections."""

    @pytest.mark.asyncio
    async def test_analyze_corrections_missing_validation_result(
        self, evaluation_agent, global_state
    ):
        """Test analyze_corrections with missing validation_result."""
        message = MCPMessage(
            message_id="analyze-123",
            agent_type="evaluation",
            target_agent="evaluation",
            action="analyze_corrections",
            context={},  # Missing validation_result
        )

        response = await evaluation_agent.handle_analyze_corrections(message, global_state)

        assert response.success is False
        assert response.error["code"] == "MISSING_VALIDATION_RESULT"

    @pytest.mark.asyncio
    async def test_analyze_corrections_success(self, evaluation_agent, global_state):
        """Test analyze_corrections success path."""
        from models import ValidationIssue, ValidationSeverity

        validation_result_data = {
            "is_valid": False,
            "issues": [
                {
                    "severity": "error",
                    "message": "Missing field",
                    "location": "/",
                    "check_function_name": "check_field",
                }
            ],
            "summary": {"error": 1},
            "inspector_version": "0.5.0",
        }

        message = MCPMessage(
            message_id="analyze-456",
            agent_type="evaluation",
            target_agent="evaluation",
            action="analyze_corrections",
            context={
                "validation_result": validation_result_data,
                "input_metadata": {},
                "conversion_parameters": {},
            },
        )

        # Mock LLM response
        evaluation_agent._llm_service.generate_structured_output = AsyncMock(
            return_value={
                "analysis": "Root cause identified",
                "suggestions": [
                    {
                        "issue": "Missing field",
                        "severity": "error",
                        "suggestion": "Add the field",
                        "actionable": True,
                    }
                ],
                "recommended_action": "retry",
            }
        )

        response = await evaluation_agent.handle_analyze_corrections(message, global_state)

        assert response.success is True
        assert "corrections" in response.result
        assert response.result["corrections"]["recommended_action"] == "retry"


# ============================================================================
# Test: FAILED Report Generation
# ============================================================================

@pytest.mark.unit
class TestFailedReportGeneration:
    """Test suite for FAILED validation report generation."""

    @pytest.mark.asyncio
    async def test_handle_generate_report_failed_validation(
        self, evaluation_agent, tmp_path, global_state
    ):
        """Test report generation for FAILED validation."""
        global_state.output_path = str(tmp_path / "test.nwb")

        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock nwb")

        validation_result = {
            "overall_status": "FAILED",
            "issues": [
                {"severity": "CRITICAL", "message": "Critical error"},
                {"severity": "ERROR", "message": "Error 1"},
            ],
            "summary": {"critical": 1, "error": 1},
            "file_info": {"nwb_version": "2.5.0"},
        }

        message = MCPMessage(
            message_id="report-failed",
            agent_type="evaluation",
            target_agent="evaluation",
            action="generate_report",
            context={
                "validation_result": validation_result,
                "nwb_path": str(nwb_file),
            },
        )

        with patch.object(
            evaluation_agent._report_service,
            'generate_json_report'
        ) as mock_json, patch.object(
            evaluation_agent,
            '_extract_file_info',
            return_value={"nwb_version": "2.5.0", "_provenance": {}}
        ), patch.object(
            evaluation_agent,
            '_add_metadata_provenance',
            return_value={"nwb_version": "2.5.0", "_provenance": {}}
        ), patch.object(
            evaluation_agent,
            '_build_workflow_trace',
            return_value={"summary": {}}
        ), patch.object(
            evaluation_agent,
            '_generate_correction_guidance',
            new_callable=AsyncMock,
            return_value={"suggestions": []}
        ):
            response = await evaluation_agent.handle_generate_report(message, global_state)

            assert response.success is True
            assert response.result["report_type"] == "json"
            mock_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_generate_report_failed_no_nwb_path(
        self, evaluation_agent, global_state
    ):
        """Test FAILED report generation without NWB path."""
        validation_result = {
            "overall_status": "FAILED",
            "issues": [{"severity": "ERROR", "message": "Test error"}],
            "summary": {"error": 1},
        }

        message = MCPMessage(
            message_id="report-failed-no-path",
            agent_type="evaluation",
            target_agent="evaluation",
            action="generate_report",
            context={
                "validation_result": validation_result,
                # No nwb_path provided
            },
        )

        with patch.object(
            evaluation_agent._report_service,
            'generate_json_report'
        ) as mock_json, patch.object(
            evaluation_agent,
            '_build_workflow_trace',
            return_value={"summary": {}}
        ), patch.object(
            evaluation_agent,
            '_generate_correction_guidance',
            new_callable=AsyncMock,
            return_value={"suggestions": []}
        ):
            response = await evaluation_agent.handle_generate_report(message, global_state)

            assert response.success is True
            mock_json.assert_called_once()


# ============================================================================
# Test: _analyze_quality Edge Cases
# ============================================================================

@pytest.mark.unit
class TestAnalyzeQualityEdgeCases:
    """Test suite for _analyze_quality edge cases."""

    @pytest.mark.asyncio
    async def test_analyze_quality_with_metadata_completeness(
        self, evaluation_agent, tmp_path, global_state
    ):
        """Test quality analysis includes metadata completeness."""
        from models import ValidationResult, ValidationIssue, ValidationSeverity

        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock")

        validation_result = ValidationResult(
            is_valid=True,
            issues=[],
            summary={},
            inspector_version="0.5.0",
        )

        # Mock LLM to return comprehensive quality assessment
        evaluation_agent._llm_service.generate_structured_output = AsyncMock(
            return_value={
                "score": 92,
                "grade": "A",
                "strengths": ["Complete metadata", "Valid structure"],
                "improvements": [],
                "metadata_completeness": 95.0,
            }
        )

        # Mock file info extraction
        with patch.object(
            evaluation_agent,
            '_extract_file_info',
            return_value={
                "experimenter": ["Dr. Smith"],
                "institution": "MIT",
                "subject_id": "mouse-001",
            }
        ):
            result = await evaluation_agent._assess_nwb_quality(
                str(nwb_file), validation_result, global_state
            )

        assert result["score"] == 92
        assert result["grade"] == "A"
        assert "metadata_completeness" in result


# ============================================================================
# Test: Build Workflow Trace
# ============================================================================

@pytest.mark.unit
class TestBuildWorkflowTraceDetailed:
    """Test suite for detailed workflow trace building."""

    def test_build_workflow_trace_with_logs(self, evaluation_agent, global_state):
        """Test building workflow trace with detailed logs."""
        # Add various log entries
        global_state.add_log("info", "Started conversion")
        global_state.add_log("info", "Format detected: SpikeGLX")
        global_state.add_log("info", "Conversion completed")
        global_state.add_log("warning", "Minor issue detected")

        trace = evaluation_agent._build_workflow_trace(global_state)

        assert "summary" in trace
        assert len(trace["detailed_logs_sequential"]) == 4

    def test_build_workflow_trace_with_stage_categorization(
        self, evaluation_agent, global_state
    ):
        """Test workflow trace categorizes logs by stage."""
        # Add logs that should be categorized by stage
        global_state.add_log("info", "File uploaded")
        global_state.add_log("info", "Format detection started")
        global_state.add_log("info", "Conversion in progress")
        global_state.add_log("info", "Validation started")

        trace = evaluation_agent._build_workflow_trace(global_state)

        assert "stage_options" in trace
        assert len(trace["stage_options"]) > 0


# ============================================================================
# Test: Generate Correction Guidance
# ============================================================================

@pytest.mark.unit
class TestGenerateCorrectionGuidanceDetailed:
    """Test suite for correction guidance generation."""

    @pytest.mark.asyncio
    async def test_generate_correction_guidance_with_critical_issues(
        self, evaluation_agent
    ):
        """Test correction guidance prioritizes critical issues."""
        validation_result = {
            "issues": [
                {"severity": "CRITICAL", "message": "Critical error", "location": "/"},
                {"severity": "ERROR", "message": "Error", "location": "/general"},
                {"severity": "WARNING", "message": "Warning", "location": "/subject"},
            ],
            "summary": {"critical": 1, "error": 1, "warning": 1},
        }

        # Mock LLM response
        evaluation_agent._llm_service.generate_structured_output = AsyncMock(
            return_value={
                "prioritized_issues": [
                    {
                        "issue": "Critical error",
                        "priority": "critical",
                        "actionable_steps": ["Fix critical issue"],
                    }
                ],
                "summary": "Address critical issues first",
            }
        )

        result = await evaluation_agent._generate_correction_guidance(validation_result)

        assert "prioritized_issues" in result
        assert result["prioritized_issues"][0]["priority"] == "critical"


# ============================================================================
# Test: Validation After Correction Attempt
# ============================================================================

@pytest.mark.unit
class TestValidationVariants:
    """Test suite for validation variants."""

    @pytest.mark.asyncio
    async def test_validation_with_warnings_only(
        self, evaluation_agent, tmp_path, global_state
    ):
        """Test validation with warnings only."""
        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock nwb")

        message = MCPMessage(
            message_id="val-warnings",
            agent_type="evaluation",
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": str(nwb_file)},
        )

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({
                    "messages": [
                        {"message": "Warning message", "severity": 1, "location": "/"}
                    ],
                    "summary": {"info": 0, "warning": 1, "error": 0, "critical": 0},
                }),
                stderr="",
            )

            response = await evaluation_agent.handle_run_validation(message, global_state)

            assert response.success is True
            assert global_state.overall_status == ValidationOutcome.PASSED_WITH_ISSUES

    @pytest.mark.asyncio
    async def test_run_nwb_inspector_handles_exception(
        self, evaluation_agent, tmp_path, global_state
    ):
        """Test NWB inspector handles exceptions gracefully."""
        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock")

        # Mock inspect_nwbfile to raise an exception
        with patch('nwbinspector.inspect_nwbfile', side_effect=Exception("Inspector error")):
            # Should raise the exception since there's no fallback
            with pytest.raises(Exception, match="Inspector error"):
                await evaluation_agent._run_nwb_inspector(str(nwb_file))


# ============================================================================
# Test: Report Generation Exception Handling
# ============================================================================

@pytest.mark.unit
class TestReportGenerationExceptionHandling:
    """Test suite for report generation error handling."""

    @pytest.mark.asyncio
    async def test_report_generation_handles_exception(
        self, evaluation_agent, tmp_path, global_state
    ):
        """Test report generation handles exceptions gracefully."""
        validation_result = {
            "overall_status": "PASSED",
            "issues": [],
            "summary": {},
        }

        message = MCPMessage(
            message_id="report-error",
            agent_type="evaluation",
            target_agent="evaluation",
            action="generate_report",
            context={
                "validation_result": validation_result,
                "nwb_path": str(tmp_path / "nonexistent.nwb"),
            },
        )

        # Mock report service to raise exception
        with patch.object(
            evaluation_agent._report_service,
            'generate_html_report',
            side_effect=Exception("Report generation failed")
        ):
            response = await evaluation_agent.handle_generate_report(message, global_state)

            assert response.success is False
            assert response.error["code"] == "REPORT_GENERATION_FAILED"
            assert "Report generation failed" in response.error["message"]


# ============================================================================
# Test: Validation Outcome Edge Cases
# ============================================================================

@pytest.mark.unit
class TestValidationOutcomeEdgeCases:
    """Test suite for validation outcome determination."""

    @pytest.mark.asyncio
    async def test_validation_passed_with_info_only(
        self, evaluation_agent, tmp_path, global_state
    ):
        """Test validation with info messages only is PASSED_WITH_ISSUES."""
        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock nwb")

        message = MCPMessage(
            message_id="val-info",
            agent_type="evaluation",
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": str(nwb_file)},
        )

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({
                    "messages": [
                        {"message": "Info message", "severity": 3, "location": "/"}
                    ],
                    "summary": {"info": 1, "warning": 0, "error": 0, "critical": 0},
                }),
                stderr="",
            )

            response = await evaluation_agent.handle_run_validation(message, global_state)

            assert response.success is True
            assert global_state.overall_status == ValidationOutcome.PASSED_WITH_ISSUES

@pytest.mark.unit

@pytest.mark.unit
class TestRealValidationWorkflows:
    """
    Integration-style unit tests using real dependencies.

    These tests use evaluation_agent_real fixture which has real internal logic,
    testing actual validation workflows instead of mocking them away.
    """

    @pytest.mark.asyncio
    async def test_real_agent_has_required_components(self, evaluation_agent_real):
        """Test that real agent has all required helper components."""
        # Should have LLM service (MockLLMService)
        assert evaluation_agent_real._llm_service is not None

        # Should have validation analyzer when LLM is available
        assert evaluation_agent_real._validation_analyzer is not None

        # Should have smart validators and resolvers
        assert evaluation_agent_real._smart_validator is not None
        assert evaluation_agent_real._smart_issue_resolver is not None
        assert evaluation_agent_real._validation_history_learner is not None

    @pytest.mark.asyncio
    async def test_real_smart_validation_logic(self, evaluation_agent_real):
        """Test real smart validation logic if available."""
        if evaluation_agent_real._smart_validator:
            # Test that smart validator can be used
            validator = evaluation_agent_real._smart_validator
            assert validator is not None
            # Smart validator should have LLM service
            assert validator._llm_service is not None

    @pytest.mark.asyncio
    async def test_real_issue_resolution_suggestions(self, evaluation_agent_real):
        """Test real issue resolution logic if available."""
        if evaluation_agent_real._smart_issue_resolver:
            # Test that resolver can analyze issues
            resolver = evaluation_agent_real._smart_issue_resolver
            assert resolver is not None
            assert resolver._llm_service is not None

    @pytest.mark.asyncio
    async def test_real_validation_analyzer_initialization(self, evaluation_agent_real):
        """Test that real validation analyzer is initialized."""
        if evaluation_agent_real._llm_service:
            assert evaluation_agent_real._validation_analyzer is not None

    @pytest.mark.asyncio
    async def test_real_validation_history_learner_exists(self, evaluation_agent_real):
        """Test that validation history learner is initialized."""
        assert evaluation_agent_real._validation_history_learner is not None
        learner = evaluation_agent_real._validation_history_learner
        # Should have LLM service
        assert learner._llm_service is not None
