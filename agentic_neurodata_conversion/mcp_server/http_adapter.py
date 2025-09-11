# Copyright (c) 2025 Agentic Neurodata Conversion Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""FastAPI HTTP adapter layer for agentic neurodata conversion.

This module provides an HTTP adapter that exposes the same core service functionality
as the MCP adapter, demonstrating the transport-agnostic design of the layered architecture.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from ..core.config import CoreConfig, get_config
from ..core.exceptions import AgentError, ConversionError, ValidationError
from ..core.service import ConversionRequest, ConversionService
from ..core.tools import ConversionToolSystem, ToolCategory

# ============================================================================
# HTTP Request/Response Models
# ============================================================================


class HTTPToolParameter(BaseModel):
    """HTTP representation of tool parameter."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Any | None = None
    enum: list[Any] | None = None
    minimum: float | None = None
    maximum: float | None = None
    pattern: str | None = None


class HTTPToolDefinition(BaseModel):
    """HTTP representation of tool definition."""

    name: str
    description: str
    category: str
    parameters: list[HTTPToolParameter]
    returns: str
    examples: list[dict[str, Any]]
    tags: list[str]
    version: str
    timeout_seconds: int


class HTTPToolExecution(BaseModel):
    """HTTP representation of tool execution."""

    execution_id: str
    tool_name: str
    parameters: dict[str, Any]
    status: str
    start_time: datetime
    end_time: datetime | None = None
    execution_time: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HTTPToolMetrics(BaseModel):
    """HTTP representation of tool metrics."""

    tool_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    timeout_executions: int
    cancelled_executions: int
    success_rate: float
    failure_rate: float
    average_execution_time: float
    min_execution_time: float | None
    max_execution_time: float | None
    last_execution: datetime | None


class HTTPAgentStatus(BaseModel):
    """HTTP representation of agent status."""

    name: str
    type: str
    status: str
    created_at: datetime
    last_used: datetime | None
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float


class HTTPSessionStatus(BaseModel):
    """HTTP representation of session status."""

    session_id: str
    status: str
    current_step: str | None
    steps_completed: list[str]
    steps_failed: list[str]
    start_time: datetime
    end_time: datetime | None
    results: dict[str, Any]
    errors: list[str]
    warnings: list[str]
    progress: float


# Request Models
class DatasetAnalysisRequest(BaseModel):
    """Request model for dataset analysis."""

    dataset_dir: str = Field(..., description="Path to dataset directory")
    use_llm: bool = Field(
        False, description="Whether to use LLM for metadata extraction"
    )
    session_id: str | None = Field(None, description="Optional session ID for tracking")


class ConversionOrchestrationRequest(BaseModel):
    """Request model for conversion orchestration."""

    normalized_metadata: dict[str, Any] = Field(
        ..., description="Normalized metadata from analysis"
    )
    files_map: dict[str, str] = Field(..., description="Mapping of file types to paths")
    output_nwb_path: str | None = Field(None, description="Output path for NWB file")
    session_id: str | None = Field(None, description="Optional session ID for tracking")


class EvaluateNWBRequest(BaseModel):
    """Request model for NWB evaluation."""

    nwb_path: str = Field(..., description="Path to NWB file to evaluate")
    generate_report: bool = Field(
        True, description="Whether to generate detailed report"
    )
    include_visualizations: bool = Field(
        True, description="Whether to include visualizations"
    )
    session_id: str | None = Field(None, description="Optional session ID for tracking")


class FullPipelineRequest(BaseModel):
    """Request model for full pipeline execution."""

    dataset_dir: str = Field(..., description="Path to dataset directory")
    files_map: dict[str, str] | None = Field(None, description="Optional file mapping")
    use_llm: bool = Field(
        False, description="Whether to use LLM for metadata extraction"
    )
    output_nwb_path: str | None = Field(
        None, description="Optional output path for NWB file"
    )
    session_id: str | None = Field(None, description="Optional session ID for tracking")


class ToolExecutionRequest(BaseModel):
    """Generic tool execution request."""

    tool_name: str = Field(..., description="Name of tool to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    execution_id: str | None = Field(None, description="Optional execution ID")


# Response Models
class HTTPConversionResponse(BaseModel):
    """HTTP conversion response model."""

    status: str
    data: dict[str, Any]
    session_id: str
    timestamp: datetime
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    execution_time: float | None = None


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    agents: dict[str, str]
    tools: int
    active_sessions: int


# ============================================================================
# FastAPI HTTP Adapter
# ============================================================================


class HTTPAdapter:
    """FastAPI HTTP adapter that exposes core service functionality via HTTP."""

    def __init__(
        self,
        conversion_service: ConversionService | None = None,
        config: CoreConfig | None = None,
    ):
        """Initialize HTTP adapter.

        Args:
            conversion_service: Optional conversion service instance
            config: Optional configuration (uses global config if None)
        """
        self.config = config or get_config()
        self.conversion_service = conversion_service or ConversionService(self.config)
        self.tool_system: ConversionToolSystem | None = None

        # Create FastAPI app with configuration
        self.app = FastAPI(
            title=self.config.http.openapi_title,
            description="HTTP API for neuroscience data conversion using agentic workflows",
            version=self.config.http.openapi_version,
            docs_url="/docs" if self.config.http.enable_openapi else None,
            redoc_url="/redoc" if self.config.http.enable_openapi else None,
        )
        self.logger = logging.getLogger(__name__)
        self.start_time = datetime.now()

        # Configure CORS
        if self.config.security.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.security.allowed_origins,
                allow_credentials=self.config.http.cors_allow_credentials,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Register routes
        self._register_routes()

        # Register exception handlers
        self._register_exception_handlers()

    async def initialize(self) -> None:
        """Initialize the adapter and core services."""
        await self.conversion_service.initialize()
        self.tool_system = ConversionToolSystem(self.conversion_service)
        self.logger.info("HTTP adapter initialized successfully")

    def _register_exception_handlers(self) -> None:
        """Register custom exception handlers."""

        @self.app.exception_handler(ValidationError)
        async def validation_error_handler(_request, exc: ValidationError):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Validation Error",
                    "message": exc.message,
                    "error_code": exc.error_code,
                    "context": exc.context,
                },
            )

        @self.app.exception_handler(AgentError)
        async def agent_error_handler(_request, exc: AgentError):
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Agent Error",
                    "message": exc.message,
                    "error_code": exc.error_code,
                    "context": exc.context,
                },
            )

        @self.app.exception_handler(ConversionError)
        async def conversion_error_handler(_request, exc: ConversionError):
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Conversion Error",
                    "message": exc.message,
                    "error_code": exc.error_code,
                    "context": exc.context,
                },
            )

    def _register_routes(self) -> None:
        """Register all HTTP routes."""

        # Health and status endpoints
        @self.app.get("/health", response_model=HealthCheckResponse)
        async def health_check():
            """Health check endpoint."""
            if not self.conversion_service._initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")

            uptime = (datetime.now() - self.start_time).total_seconds()
            agent_status = await self.conversion_service.get_agent_status()

            return HealthCheckResponse(
                status="healthy",
                timestamp=datetime.now(),
                version="1.0.0",
                uptime_seconds=uptime,
                agents={name: info["status"] for name, info in agent_status.items()},
                tools=len(self.tool_system.registry.list_tools())
                if self.tool_system
                else 0,
                active_sessions=len(
                    self.conversion_service.workflow_orchestrator.active_sessions
                ),
            )

        @self.app.get("/agents", response_model=dict[str, HTTPAgentStatus])
        async def get_agents():
            """Get status of all agents."""
            agent_status = await self.conversion_service.get_agent_status()

            result = {}
            for name, info in agent_status.items():
                result[name] = HTTPAgentStatus(
                    name=info["name"],
                    type=info.get("type", name),
                    status=info["status"],
                    created_at=datetime.fromisoformat(
                        info.get("created_at", datetime.now().isoformat())
                    ),
                    last_used=(
                        datetime.fromisoformat(info["last_used"])
                        if info.get("last_used")
                        else None
                    ),
                    total_executions=info["statistics"]["total_executions"],
                    successful_executions=info["statistics"]["successful_executions"],
                    failed_executions=info["statistics"]["failed_executions"],
                    success_rate=info["statistics"]["success_rate"],
                )

            return result

        # Tool management endpoints
        @self.app.get("/tools", response_model=list[HTTPToolDefinition])
        async def list_tools(category: str | None = None):
            """List available tools."""
            if not self.tool_system:
                raise HTTPException(
                    status_code=503, detail="Tool system not initialized"
                )

            tool_category = None
            if category:
                try:
                    tool_category = ToolCategory(category.lower())
                except ValueError:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid category: {category}"
                    ) from None

            tools = self.tool_system.registry.list_tools(category=tool_category)

            result = []
            for tool in tools:
                http_params = []
                for param in tool.parameters:
                    http_params.append(
                        HTTPToolParameter(
                            name=param.name,
                            type=param.type.value,
                            description=param.description,
                            required=param.required,
                            default=param.default,
                            enum=param.enum,
                            minimum=param.minimum,
                            maximum=param.maximum,
                            pattern=param.pattern,
                        )
                    )

                result.append(
                    HTTPToolDefinition(
                        name=tool.name,
                        description=tool.description,
                        category=tool.category.value,
                        parameters=http_params,
                        returns=tool.returns,
                        examples=tool.examples,
                        tags=tool.tags,
                        version=tool.version,
                        timeout_seconds=tool.timeout_seconds,
                    )
                )

            return result

        @self.app.get("/tools/{tool_name}", response_model=HTTPToolDefinition)
        async def get_tool(tool_name: str):
            """Get specific tool definition."""
            if not self.tool_system:
                raise HTTPException(
                    status_code=503, detail="Tool system not initialized"
                )

            tool = self.tool_system.registry.get_tool(tool_name)
            if not tool:
                raise HTTPException(
                    status_code=404, detail=f"Tool not found: {tool_name}"
                )

            http_params = []
            for param in tool.parameters:
                http_params.append(
                    HTTPToolParameter(
                        name=param.name,
                        type=param.type.value,
                        description=param.description,
                        required=param.required,
                        default=param.default,
                        enum=param.enum,
                        minimum=param.minimum,
                        maximum=param.maximum,
                        pattern=param.pattern,
                    )
                )

            return HTTPToolDefinition(
                name=tool.name,
                description=tool.description,
                category=tool.category.value,
                parameters=http_params,
                returns=tool.returns,
                examples=tool.examples,
                tags=tool.tags,
                version=tool.version,
                timeout_seconds=tool.timeout_seconds,
            )

        @self.app.post("/tools/execute", response_model=HTTPToolExecution)
        async def execute_tool(request: ToolExecutionRequest):
            """Execute a tool with given parameters."""
            if not self.tool_system:
                raise HTTPException(
                    status_code=503, detail="Tool system not initialized"
                )

            execution = await self.tool_system.executor.execute_tool(
                request.tool_name, request.parameters, request.execution_id
            )

            return HTTPToolExecution(
                execution_id=execution.execution_id,
                tool_name=execution.tool_name,
                parameters=execution.parameters,
                status=execution.status.value,
                start_time=execution.start_time,
                end_time=execution.end_time,
                execution_time=execution.execution_time,
                result=execution.result,
                error=execution.error,
                warnings=execution.warnings,
                metadata=execution.metadata,
            )

        @self.app.get("/tools/metrics", response_model=dict[str, HTTPToolMetrics])
        async def get_tool_metrics():
            """Get performance metrics for all tools."""
            if not self.tool_system:
                raise HTTPException(
                    status_code=503, detail="Tool system not initialized"
                )

            metrics = self.tool_system.registry.get_all_metrics()

            result = {}
            for name, m in metrics.items():
                result[name] = HTTPToolMetrics(
                    tool_name=m.tool_name,
                    total_executions=m.total_executions,
                    successful_executions=m.successful_executions,
                    failed_executions=m.failed_executions,
                    timeout_executions=m.timeout_executions,
                    cancelled_executions=m.cancelled_executions,
                    success_rate=m.success_rate,
                    failure_rate=m.failure_rate,
                    average_execution_time=m.average_execution_time,
                    min_execution_time=m.min_execution_time,
                    max_execution_time=m.max_execution_time,
                    last_execution=m.last_execution,
                )

            return result

        # Conversion operation endpoints
        @self.app.post("/analyze", response_model=HTTPConversionResponse)
        async def analyze_dataset(request: DatasetAnalysisRequest):
            """Analyze dataset structure and extract metadata."""
            response = await self.conversion_service.dataset_analysis(
                dataset_dir=request.dataset_dir,
                use_llm=request.use_llm,
                session_id=request.session_id,
            )

            return HTTPConversionResponse(
                status=response.status.value,
                data=response.data,
                session_id=response.session_id,
                timestamp=response.timestamp,
                error=response.error,
                warnings=response.warnings,
                execution_time=response.execution_time,
            )

        @self.app.post("/convert", response_model=HTTPConversionResponse)
        async def orchestrate_conversion(request: ConversionOrchestrationRequest):
            """Generate and execute NeuroConv conversion script."""
            response = await self.conversion_service.conversion_orchestration(
                normalized_metadata=request.normalized_metadata,
                files_map=request.files_map,
                output_nwb_path=request.output_nwb_path,
                session_id=request.session_id,
            )

            return HTTPConversionResponse(
                status=response.status.value,
                data=response.data,
                session_id=response.session_id,
                timestamp=response.timestamp,
                error=response.error,
                warnings=response.warnings,
                execution_time=response.execution_time,
            )

        @self.app.post("/evaluate", response_model=HTTPConversionResponse)
        async def evaluate_nwb(request: EvaluateNWBRequest):
            """Evaluate NWB file quality and generate reports."""
            response = await self.conversion_service.evaluate_nwb_file(
                nwb_path=request.nwb_path,
                generate_report=request.generate_report,
                include_visualizations=request.include_visualizations,
                session_id=request.session_id,
            )

            return HTTPConversionResponse(
                status=response.status.value,
                data=response.data,
                session_id=response.session_id,
                timestamp=response.timestamp,
                error=response.error,
                warnings=response.warnings,
                execution_time=response.execution_time,
            )

        @self.app.post("/pipeline", response_model=HTTPConversionResponse)
        async def run_full_pipeline(request: FullPipelineRequest):
            """Execute complete conversion pipeline."""
            conversion_request = ConversionRequest(
                dataset_dir=request.dataset_dir,
                files_map=request.files_map,
                use_llm=request.use_llm,
                output_nwb_path=request.output_nwb_path,
                session_id=request.session_id,
            )

            response = await self.conversion_service.run_full_pipeline(
                conversion_request
            )

            return HTTPConversionResponse(
                status=response.status.value,
                data=response.data,
                session_id=response.session_id,
                timestamp=response.timestamp,
                error=response.error,
                warnings=response.warnings,
                execution_time=response.execution_time,
            )

        # Session management endpoints
        @self.app.get("/sessions", response_model=list[str])
        async def list_sessions():
            """List active conversion sessions."""
            return list(
                self.conversion_service.workflow_orchestrator.active_sessions.keys()
            )

        @self.app.get("/sessions/{session_id}", response_model=HTTPSessionStatus)
        async def get_session_status(session_id: str):
            """Get status of a specific conversion session."""
            session_status = await self.conversion_service.get_session_status(
                session_id
            )

            if session_status is None:
                raise HTTPException(
                    status_code=404, detail=f"Session not found: {session_id}"
                )

            return HTTPSessionStatus(
                session_id=session_status["session_id"],
                status=session_status["status"],
                current_step=session_status["current_step"],
                steps_completed=session_status["steps_completed"],
                steps_failed=session_status["steps_failed"],
                start_time=datetime.fromisoformat(session_status["start_time"]),
                end_time=(
                    datetime.fromisoformat(session_status["end_time"])
                    if session_status["end_time"]
                    else None
                ),
                results=session_status["results"],
                errors=session_status["errors"],
                warnings=session_status["warnings"],
                progress=session_status["progress"],
            )

        @self.app.delete("/sessions/{session_id}")
        async def cancel_session(session_id: str):
            """Cancel an active conversion session."""
            success = await self.conversion_service.cancel_session(session_id)

            if not success:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session not found or cannot be cancelled: {session_id}",
                )

            return {"message": f"Session {session_id} cancelled successfully"}

    async def run_server(
        self, host: str = "127.0.0.1", port: int = 8000, **kwargs
    ) -> None:
        """Run the HTTP server.

        Args:
            host: Server host address
            port: Server port number
            **kwargs: Additional uvicorn configuration
        """
        await self.initialize()

        config = uvicorn.Config(
            app=self.app, host=host, port=port, log_level="info", **kwargs
        )

        server = uvicorn.Server(config)
        self.logger.info(f"Starting HTTP server on {host}:{port}")

        try:
            await server.serve()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the adapter and core services."""
        if self.conversion_service:
            await self.conversion_service.shutdown()
        self.logger.info("HTTP adapter shutdown complete")


# ============================================================================
# HTTP Server Entry Point
# ============================================================================


async def main():
    """Main entry point for HTTP server."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Agentic Neurodata Conversion HTTP Server")

    # Use default settings for now - TODO: implement proper settings loading
    adapter = HTTPAdapter()

    try:
        await adapter.run_server(
            host="localhost",
            port=8000,
            reload=True,
        )
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("HTTP server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
