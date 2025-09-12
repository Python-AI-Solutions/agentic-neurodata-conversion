"""Core service layer for agentic neurodata conversion.

This module provides the transport-agnostic business logic for the MCP server,
including data models, conversion operations, agent management, and workflow orchestration.
All business logic is contained here without any transport dependencies.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
import logging
from pathlib import Path
from typing import Any
import uuid

from pydantic import BaseModel, Field, field_validator

from .config import CoreConfig, configure_logging, get_config
from .exceptions import (
    AgentError,
    ConversionError,
    DataProcessingError,
    ValidationError,
)

# ============================================================================
# Data Models
# ============================================================================


class ConversionStatus(str, Enum):
    """Status enumeration for conversion operations."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Status enumeration for agent lifecycle."""

    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class ConversionRequest(BaseModel):
    """Transport-agnostic conversion request model."""

    dataset_dir: str = Field(..., description="Path to dataset directory")
    files_map: dict[str, str] | None = Field(
        None, description="Optional mapping of file types to specific paths"
    )
    use_llm: bool = Field(
        False, description="Whether to use LLM for metadata extraction"
    )
    output_nwb_path: str | None = Field(None, description="Output NWB file path")
    session_id: str | None = Field(None, description="Session ID for tracking")

    @field_validator("dataset_dir")
    @classmethod
    def validate_dataset_dir(cls, v: str) -> str:
        """Validate dataset directory exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Dataset directory does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Dataset path is not a directory: {v}")
        return str(path.resolve())


class ConversionResponse(BaseModel):
    """Transport-agnostic conversion response model."""

    status: ConversionStatus = Field(..., description="Operation status")
    data: dict[str, Any] = Field(default_factory=dict, description="Response data")
    session_id: str = Field(..., description="Session ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = Field(None, description="Error message if failed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    execution_time: float | None = Field(None, description="Execution time in seconds")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SessionState(BaseModel):
    """Internal session state management."""

    session_id: str = Field(..., description="Unique session identifier")
    status: ConversionStatus = Field(default=ConversionStatus.PENDING)
    current_step: str | None = Field(None, description="Current pipeline step")
    steps_completed: list[str] = Field(default_factory=list)
    steps_failed: list[str] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = Field(None)
    dataset_dir: str | None = Field(None)
    files_map: dict[str, str] | None = Field(None)
    use_llm: bool = Field(False)
    output_nwb_path: str | None = Field(None)
    results: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentInfo(BaseModel):
    """Agent information and metadata."""

    name: str = Field(..., description="Agent name")
    agent_type: str = Field(..., description="Agent type identifier")
    status: AgentStatus = Field(default=AgentStatus.INITIALIZING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: datetime | None = Field(None)
    total_executions: int = Field(default=0)
    successful_executions: int = Field(default=0)
    failed_executions: int = Field(default=0)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentResult(BaseModel):
    """Result from agent execution."""

    status: ConversionStatus = Field(..., description="Execution status")
    data: dict[str, Any] = Field(default_factory=dict, description="Result data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata"
    )
    provenance: dict[str, Any] = Field(
        default_factory=dict, description="Provenance information"
    )
    execution_time: float | None = Field(None, description="Execution time in seconds")
    agent_id: str = Field(..., description="Agent identifier")
    error: str | None = Field(None, description="Error message if failed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Agent Management
# ============================================================================


class AgentManager:
    """Manages agent lifecycle and coordination."""

    def __init__(self, config: CoreConfig):
        """Initialize agent manager with configuration.

        Args:
            config: Application configuration settings
        """
        self.config = config
        self.agents: dict[str, AgentInfo] = {}
        self.logger = logging.getLogger(__name__)
        self._initialization_lock = asyncio.Lock()
        self._agent_instances: dict[str, Any] = {}  # Store actual agent instances

    async def initialize_agents(self) -> None:
        """Initialize all configured agents."""
        async with self._initialization_lock:
            agent_types = ["conversation", "conversion", "evaluation"]

            for agent_type in agent_types:
                try:
                    self.logger.info(f"Initializing {agent_type} agent...")

                    # Create agent info (placeholder for now)
                    agent_info = AgentInfo(
                        name=agent_type,
                        agent_type=agent_type,
                        status=AgentStatus.READY,
                        created_at=datetime.now(timezone.utc),
                    )

                    self.agents[agent_type] = agent_info
                    self.logger.info(f"Successfully initialized {agent_type} agent")

                except Exception as e:
                    self.logger.error(f"Failed to initialize {agent_type} agent: {e}")
                    # Create error state agent info
                    self.agents[agent_type] = AgentInfo(
                        name=agent_type,
                        agent_type=agent_type,
                        status=AgentStatus.ERROR,
                        created_at=datetime.now(timezone.utc),
                    )

    async def get_agent_status(self, agent_type: str | None = None) -> dict[str, Any]:
        """Get status of agents.

        Args:
            agent_type: Specific agent type to get status for, or None for all

        Returns:
            Dictionary containing agent status information
        """
        if agent_type:
            agent_info = self.agents.get(agent_type)
            if not agent_info:
                return {"error": f"Agent {agent_type} not found"}

            return {
                "name": agent_info.name,
                "type": agent_info.agent_type,
                "status": agent_info.status.value,
                "created_at": agent_info.created_at.isoformat(),
                "last_used": agent_info.last_used.isoformat()
                if agent_info.last_used
                else None,
                "statistics": {
                    "total_executions": agent_info.total_executions,
                    "successful_executions": agent_info.successful_executions,
                    "failed_executions": agent_info.failed_executions,
                    "success_rate": agent_info.success_rate,
                },
            }
        else:
            # Return status for all agents
            return {
                agent_type: {
                    "name": info.name,
                    "status": info.status.value,
                    "total_executions": info.total_executions,
                    "success_rate": info.success_rate,
                }
                for agent_type, info in self.agents.items()
            }

    async def execute_agent_task(self, agent_type: str, **kwargs) -> AgentResult:
        """Execute task using specified agent.

        Args:
            agent_type: Type of agent to execute
            **kwargs: Arguments to pass to the agent

        Returns:
            AgentResult containing execution results
        """
        agent_info = self.agents.get(agent_type)

        if not agent_info:
            raise AgentError(
                f"Agent {agent_type} not found",
                agent_name=agent_type,
                agent_operation="execute_task",
            )

        if agent_info.status != AgentStatus.READY:
            raise AgentError(
                f"Agent {agent_type} is not ready (status: {agent_info.status.value})",
                agent_name=agent_type,
                agent_operation="execute_task",
            )

        # Update agent status
        agent_info.status = AgentStatus.BUSY
        agent_info.last_used = datetime.now(timezone.utc)
        start_time = datetime.now(timezone.utc)

        try:
            # Execute agent task (placeholder implementation)
            result_data = await self._execute_agent_operation(agent_type, **kwargs)

            # Update statistics
            agent_info.total_executions += 1
            agent_info.successful_executions += 1

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return AgentResult(
                status=ConversionStatus.COMPLETED,
                data=result_data,
                metadata={
                    "agent_type": agent_type,
                    "execution_timestamp": datetime.now(timezone.utc).isoformat(),
                },
                provenance={
                    "agent_name": agent_info.name,
                    "agent_version": "1.0.0",  # TODO: Get from actual agent
                    "execution_context": kwargs,
                },
                execution_time=execution_time,
                agent_id=agent_type,
            )

        except Exception as e:
            self.logger.error(f"Agent {agent_type} execution failed: {e}")
            agent_info.failed_executions += 1

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return AgentResult(
                status=ConversionStatus.FAILED,
                data={},
                metadata={
                    "agent_type": agent_type,
                    "execution_timestamp": datetime.now(timezone.utc).isoformat(),
                },
                provenance={"agent_name": agent_info.name, "execution_context": kwargs},
                execution_time=execution_time,
                agent_id=agent_type,
                error=str(e),
            )

        finally:
            # Reset agent status
            agent_info.status = AgentStatus.READY

    async def _execute_agent_operation(
        self, agent_type: str, **kwargs
    ) -> dict[str, Any]:
        """Execute the actual agent operation (placeholder implementation).

        This method will be replaced with actual agent implementations.

        Args:
            agent_type: Type of agent to execute
            **kwargs: Arguments for the agent

        Returns:
            Dictionary containing operation results
        """
        # Placeholder implementation - will be replaced with actual agent calls
        if agent_type == "conversation":
            return await self._execute_conversation_agent(**kwargs)
        elif agent_type == "conversion":
            return await self._execute_conversion_agent(**kwargs)
        elif agent_type == "evaluation":
            return await self._execute_evaluation_agent(**kwargs)
        else:
            raise AgentError(f"Unknown agent type: {agent_type}")

    async def _execute_conversation_agent(self, **kwargs) -> dict[str, Any]:
        """Placeholder for conversation agent execution."""
        dataset_dir = kwargs.get("dataset_dir")
        use_llm = kwargs.get("use_llm", False)

        # Simulate processing time
        await asyncio.sleep(0.1)

        return {
            "analysis_type": "dataset_analysis",
            "dataset_path": dataset_dir,
            "metadata_extracted": True,
            "llm_used": use_llm,
            "detected_formats": ["open_ephys", "spikeglx"],
            "file_count": 42,
            "total_size_mb": 1024.5,
            "normalized_metadata": {
                "subject_id": "test_subject",
                "session_id": "test_session",
                "experiment_description": "Test experiment",
            },
        }

    async def _execute_conversion_agent(self, **kwargs) -> dict[str, Any]:
        """Placeholder for conversion agent execution."""
        # Placeholder for conversion agent execution - parameters available if needed
        # normalized_metadata = kwargs.get("normalized_metadata", {})
        # files_map = kwargs.get("files_map", {})

        # Simulate processing time
        await asyncio.sleep(0.2)

        return {
            "conversion_type": "neuroconv_script_generation",
            "script_generated": True,
            "output_path": kwargs.get("output_nwb_path", "output.nwb"),
            "conversion_successful": True,
            "file_size_mb": 256.7,
            "processing_time_seconds": 45.2,
        }

    async def _execute_evaluation_agent(self, **kwargs) -> dict[str, Any]:
        """Placeholder for evaluation agent execution."""
        nwb_path = kwargs.get("nwb_path")
        generate_report = kwargs.get("generate_report", True)

        # Simulate processing time
        await asyncio.sleep(0.15)

        return {
            "evaluation_type": "nwb_validation",
            "nwb_file_path": nwb_path,
            "validation_passed": True,
            "report_generated": generate_report,
            "quality_score": 0.95,
            "issues_found": [],
            "recommendations": ["Consider adding more metadata"],
        }

    async def shutdown_agents(self) -> None:
        """Shutdown all agents gracefully."""
        for agent_type, agent_info in self.agents.items():
            try:
                self.logger.info(f"Shutting down {agent_type} agent...")
                agent_info.status = AgentStatus.SHUTDOWN
                self.logger.info(f"Successfully shut down {agent_type} agent")
            except Exception as e:
                self.logger.error(f"Error shutting down {agent_type} agent: {e}")


# ============================================================================
# Workflow Orchestration
# ============================================================================


class WorkflowOrchestrator:
    """Orchestrates multi-step conversion workflows."""

    def __init__(self, agent_manager: AgentManager):
        """Initialize workflow orchestrator.

        Args:
            agent_manager: Agent manager instance for executing agents
        """
        self.agent_manager = agent_manager
        self.active_sessions: dict[str, SessionState] = {}
        self.logger = logging.getLogger(__name__)

    async def start_pipeline_execution(
        self,
        session_id: str,
        dataset_dir: str,
        files_map: dict[str, str] | None = None,
        use_llm: bool = False,
        output_nwb_path: str | None = None,
    ) -> str:
        """Start full pipeline execution.

        Args:
            session_id: Unique session identifier
            dataset_dir: Path to dataset directory
            files_map: Optional file mapping
            use_llm: Whether to use LLM for processing
            output_nwb_path: Optional output path for NWB file

        Returns:
            Task ID for tracking the pipeline execution
        """
        # Initialize session state
        session_state = SessionState(
            session_id=session_id,
            status=ConversionStatus.RUNNING,
            current_step="initialization",
            dataset_dir=dataset_dir,
            files_map=files_map,
            use_llm=use_llm,
            output_nwb_path=output_nwb_path,
        )

        self.active_sessions[session_id] = session_state

        # Start pipeline execution as background task
        task_id = f"pipeline_{session_id}"
        asyncio.create_task(self._execute_pipeline(session_id))

        return task_id

    async def _execute_pipeline(self, session_id: str) -> None:
        """Execute complete pipeline workflow.

        Args:
            session_id: Session identifier for the pipeline
        """
        session = self.active_sessions[session_id]

        try:
            # Step 1: Dataset Analysis
            session.current_step = "analysis"
            self.logger.info(f"Session {session_id}: Starting dataset analysis")

            analysis_result = await self.agent_manager.execute_agent_task(
                "conversation",
                dataset_dir=session.dataset_dir,
                use_llm=session.use_llm,
                session_id=session_id,
            )

            if analysis_result.status == ConversionStatus.FAILED:
                raise ConversionError(
                    f"Dataset analysis failed: {analysis_result.error}",
                    conversion_stage="analysis",
                )

            session.steps_completed.append("analysis")
            session.results["analysis"] = analysis_result.data

            # Step 2: Conversion Script Generation
            session.current_step = "conversion"
            self.logger.info(f"Session {session_id}: Starting conversion")

            conversion_result = await self.agent_manager.execute_agent_task(
                "conversion",
                normalized_metadata=analysis_result.data.get("normalized_metadata", {}),
                files_map=session.files_map or {},
                output_nwb_path=session.output_nwb_path,
                session_id=session_id,
            )

            if conversion_result.status == ConversionStatus.FAILED:
                raise ConversionError(
                    f"Conversion failed: {conversion_result.error}",
                    conversion_stage="conversion",
                )

            session.steps_completed.append("conversion")
            session.results["conversion"] = conversion_result.data

            # Step 3: Evaluation
            session.current_step = "evaluation"
            self.logger.info(f"Session {session_id}: Starting evaluation")

            nwb_path = conversion_result.data.get("output_path")
            if nwb_path:
                evaluation_result = await self.agent_manager.execute_agent_task(
                    "evaluation",
                    nwb_path=nwb_path,
                    generate_report=True,
                    include_visualizations=True,
                    session_id=session_id,
                )

                if evaluation_result.status == ConversionStatus.FAILED:
                    # Evaluation failure is not critical - log warning but continue
                    self.logger.warning(f"Evaluation failed: {evaluation_result.error}")
                    session.warnings.append(
                        f"Evaluation failed: {evaluation_result.error}"
                    )
                else:
                    session.steps_completed.append("evaluation")
                    session.results["evaluation"] = evaluation_result.data

            # Pipeline completed successfully
            session.status = ConversionStatus.COMPLETED
            session.current_step = "completed"
            session.end_time = datetime.now(timezone.utc)

            self.logger.info(f"Session {session_id}: Pipeline completed successfully")

        except Exception as e:
            self.logger.error(f"Session {session_id}: Pipeline failed: {e}")
            session.status = ConversionStatus.FAILED
            session.current_step = "failed"
            session.end_time = datetime.now(timezone.utc)
            session.errors.append(str(e))

            if session.current_step not in session.steps_failed:
                session.steps_failed.append(session.current_step)

    async def get_session_status(self, session_id: str) -> dict[str, Any] | None:
        """Get status of conversion session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary containing session status or None if not found
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "status": session.status.value,
            "current_step": session.current_step,
            "steps_completed": session.steps_completed,
            "steps_failed": session.steps_failed,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "results": session.results,
            "errors": session.errors,
            "warnings": session.warnings,
            "progress": len(session.steps_completed) / 3.0,  # 3 total steps
        }

    async def cancel_session(self, session_id: str) -> bool:
        """Cancel ongoing conversion session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was cancelled, False if not found
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return False

        if session.status in [ConversionStatus.COMPLETED, ConversionStatus.FAILED]:
            return False  # Cannot cancel completed sessions

        session.status = ConversionStatus.CANCELLED
        session.current_step = "cancelled"
        session.end_time = datetime.now(timezone.utc)

        self.logger.info(f"Session {session_id}: Cancelled by user request")
        return True


# ============================================================================
# Core Conversion Service
# ============================================================================


class ConversionService:
    """Core conversion service with all business logic."""

    def __init__(self, config: CoreConfig | None = None):
        """Initialize conversion service.

        Args:
            config: Optional configuration settings (uses global config if None)
        """
        self.config = config or get_config()

        # Configure logging based on config
        configure_logging(self.config.logging)

        self.agent_manager = AgentManager(self.config)
        self.workflow_orchestrator = WorkflowOrchestrator(self.agent_manager)
        self.logger = logging.getLogger(__name__)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the conversion service and all components."""
        if self._initialized:
            return

        self.logger.info("Initializing conversion service...")
        await self.agent_manager.initialize_agents()
        self._initialized = True
        self.logger.info("Conversion service initialized successfully")

    async def dataset_analysis(
        self, dataset_dir: str, use_llm: bool = False, session_id: str | None = None
    ) -> ConversionResponse:
        """Analyze dataset structure and extract metadata.

        Args:
            dataset_dir: Path to dataset directory
            use_llm: Whether to use LLM for metadata extraction
            session_id: Optional session ID for tracking

        Returns:
            ConversionResponse containing analysis results
        """
        if not self._initialized:
            await self.initialize()

        session_id = session_id or str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            # Validate dataset directory
            dataset_path = Path(dataset_dir)
            if not dataset_path.exists():
                raise DataProcessingError(
                    f"Dataset directory does not exist: {dataset_dir}",
                    processing_stage="validation",
                    file_path=dataset_dir,
                )

            # Execute analysis through agent manager
            result = await self.agent_manager.execute_agent_task(
                "conversation",
                dataset_dir=dataset_dir,
                use_llm=use_llm,
                session_id=session_id,
            )

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            if result.status == ConversionStatus.FAILED:
                return ConversionResponse(
                    status=ConversionStatus.FAILED,
                    data={},
                    session_id=session_id,
                    error=result.error,
                    warnings=result.warnings,
                    execution_time=execution_time,
                )

            return ConversionResponse(
                status=ConversionStatus.COMPLETED,
                data=result.data,
                session_id=session_id,
                warnings=result.warnings,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.logger.error(f"Dataset analysis failed: {e}")

            return ConversionResponse(
                status=ConversionStatus.FAILED,
                data={},
                session_id=session_id,
                error=str(e),
                execution_time=execution_time,
            )

    async def conversion_orchestration(
        self,
        normalized_metadata: dict[str, Any],
        files_map: dict[str, str],
        output_nwb_path: str | None = None,
        session_id: str | None = None,
    ) -> ConversionResponse:
        """Generate and execute NeuroConv conversion script.

        Args:
            normalized_metadata: Normalized metadata from analysis
            files_map: Mapping of file types to paths
            output_nwb_path: Optional output NWB file path
            session_id: Optional session ID for tracking

        Returns:
            ConversionResponse containing conversion results
        """
        if not self._initialized:
            await self.initialize()

        session_id = session_id or str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            # Validate inputs
            if not normalized_metadata:
                raise ValidationError(
                    "Normalized metadata is required for conversion",
                    validation_type="input_validation",
                    field_name="normalized_metadata",
                )

            if not files_map:
                raise ValidationError(
                    "Files map is required for conversion",
                    validation_type="input_validation",
                    field_name="files_map",
                )

            # Execute conversion through agent manager
            result = await self.agent_manager.execute_agent_task(
                "conversion",
                normalized_metadata=normalized_metadata,
                files_map=files_map,
                output_nwb_path=output_nwb_path,
                session_id=session_id,
            )

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            if result.status == ConversionStatus.FAILED:
                return ConversionResponse(
                    status=ConversionStatus.FAILED,
                    data={},
                    session_id=session_id,
                    error=result.error,
                    warnings=result.warnings,
                    execution_time=execution_time,
                )

            return ConversionResponse(
                status=ConversionStatus.COMPLETED,
                data=result.data,
                session_id=session_id,
                warnings=result.warnings,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.logger.error(f"Conversion orchestration failed: {e}")

            return ConversionResponse(
                status=ConversionStatus.FAILED,
                data={},
                session_id=session_id,
                error=str(e),
                execution_time=execution_time,
            )

    async def evaluate_nwb_file(
        self,
        nwb_path: str,
        generate_report: bool = True,
        include_visualizations: bool = True,
        session_id: str | None = None,
    ) -> ConversionResponse:
        """Evaluate NWB file quality and generate reports.

        Args:
            nwb_path: Path to NWB file to evaluate
            generate_report: Whether to generate evaluation report
            include_visualizations: Whether to include visualizations
            session_id: Optional session ID for tracking

        Returns:
            ConversionResponse containing evaluation results
        """
        if not self._initialized:
            await self.initialize()

        session_id = session_id or str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            # Validate NWB file
            nwb_file_path = Path(nwb_path)
            if not nwb_file_path.exists():
                raise DataProcessingError(
                    f"NWB file does not exist: {nwb_path}",
                    processing_stage="validation",
                    file_path=nwb_path,
                )

            # Execute evaluation through agent manager
            result = await self.agent_manager.execute_agent_task(
                "evaluation",
                nwb_path=nwb_path,
                generate_report=generate_report,
                include_visualizations=include_visualizations,
                session_id=session_id,
            )

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            if result.status == ConversionStatus.FAILED:
                return ConversionResponse(
                    status=ConversionStatus.FAILED,
                    data={},
                    session_id=session_id,
                    error=result.error,
                    warnings=result.warnings,
                    execution_time=execution_time,
                )

            return ConversionResponse(
                status=ConversionStatus.COMPLETED,
                data=result.data,
                session_id=session_id,
                warnings=result.warnings,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.logger.error(f"NWB evaluation failed: {e}")

            return ConversionResponse(
                status=ConversionStatus.FAILED,
                data={},
                session_id=session_id,
                error=str(e),
                execution_time=execution_time,
            )

    async def run_full_pipeline(self, request: ConversionRequest) -> ConversionResponse:
        """Run complete conversion pipeline.

        Args:
            request: Conversion request with all parameters

        Returns:
            ConversionResponse containing pipeline results
        """
        if not self._initialized:
            await self.initialize()

        session_id = request.session_id or str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            # Start pipeline execution
            task_id = await self.workflow_orchestrator.start_pipeline_execution(
                session_id=session_id,
                dataset_dir=request.dataset_dir,
                files_map=request.files_map,
                use_llm=request.use_llm,
                output_nwb_path=request.output_nwb_path,
            )

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return ConversionResponse(
                status=ConversionStatus.RUNNING,
                data={
                    "task_id": task_id,
                    "message": "Pipeline execution started",
                    "session_id": session_id,
                },
                session_id=session_id,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.logger.error(f"Pipeline execution failed to start: {e}")

            return ConversionResponse(
                status=ConversionStatus.FAILED,
                data={},
                session_id=session_id,
                error=str(e),
                execution_time=execution_time,
            )

    async def get_session_status(self, session_id: str) -> dict[str, Any] | None:
        """Get status of conversion session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary containing session status or None if not found
        """
        return await self.workflow_orchestrator.get_session_status(session_id)

    async def cancel_session(self, session_id: str) -> bool:
        """Cancel ongoing conversion session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was cancelled, False if not found
        """
        return await self.workflow_orchestrator.cancel_session(session_id)

    async def get_agent_status(self, agent_type: str | None = None) -> dict[str, Any]:
        """Get status of agents.

        Args:
            agent_type: Specific agent type or None for all agents

        Returns:
            Dictionary containing agent status information
        """
        return await self.agent_manager.get_agent_status(agent_type)

    async def shutdown(self) -> None:
        """Shutdown the conversion service and all components."""
        if not self._initialized:
            return

        self.logger.info("Shutting down conversion service...")
        await self.agent_manager.shutdown_agents()
        self._initialized = False
        self.logger.info("Conversion service shutdown complete")


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "ConversionStatus",
    "AgentStatus",
    # Data Models
    "ConversionRequest",
    "ConversionResponse",
    "SessionState",
    "AgentInfo",
    "AgentResult",
    # Core Classes
    "AgentManager",
    "WorkflowOrchestrator",
    "ConversionService",
]
