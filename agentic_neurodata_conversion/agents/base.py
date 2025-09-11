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

"""
Base agent interface and common functionality for the agentic neurodata conversion system.

This module defines the abstract base class for all agents, providing a consistent
interface for agent lifecycle management, error handling, logging, and metrics tracking.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import logging
import time
from typing import Any, Optional
import uuid

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status."""

    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentResult:
    """Standardized agent result format."""

    status: AgentStatus
    data: dict[str, Any]
    metadata: dict[str, Any]
    provenance: dict[str, Any]
    execution_time: float
    agent_id: str
    error: Optional[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, config: "AgentConfig", agent_type: str):
        self.config = config
        self.agent_type = agent_type
        self.agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"
        self.logger = logging.getLogger(f"agent.{agent_type}")
        self.status = AgentStatus.IDLE
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
        }

    async def execute(self, **kwargs) -> AgentResult:
        """Execute agent with standardized error handling and metrics."""
        start_time = time.time()
        self.status = AgentStatus.PROCESSING

        try:
            # Validate inputs
            validated_inputs = await self._validate_inputs(**kwargs)

            # Execute agent-specific logic
            result_data = await self._execute_internal(**validated_inputs)

            # Process results
            processed_result = await self._process_results(
                result_data, **validated_inputs
            )

            # Create successful result
            execution_time = time.time() - start_time
            result = AgentResult(
                status=AgentStatus.COMPLETED,
                data=processed_result,
                metadata=self._generate_metadata(**validated_inputs),
                provenance=self._generate_provenance(**validated_inputs),
                execution_time=execution_time,
                agent_id=self.agent_id,
            )

            # Update metrics
            self._update_metrics(execution_time, success=True)
            self.status = AgentStatus.COMPLETED

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Agent execution failed: {e}", exc_info=True)

            result = AgentResult(
                status=AgentStatus.ERROR,
                data={},
                metadata=self._generate_metadata(**kwargs),
                provenance=self._generate_provenance(**kwargs),
                execution_time=execution_time,
                agent_id=self.agent_id,
                error=str(e),
            )

            self._update_metrics(execution_time, success=False)
            self.status = AgentStatus.ERROR

            return result

    @abstractmethod
    async def _validate_inputs(self, **kwargs) -> dict[str, Any]:
        """Validate and normalize inputs."""
        pass

    @abstractmethod
    async def _execute_internal(self, **kwargs) -> dict[str, Any]:
        """Execute agent-specific logic."""
        pass

    async def _process_results(
        self, result_data: dict[str, Any], **kwargs
    ) -> dict[str, Any]:
        """Process and format results. Override if needed."""
        return result_data

    def _generate_metadata(self, **kwargs) -> dict[str, Any]:
        """Generate execution metadata."""
        return {
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "timestamp": time.time(),
            "config_version": getattr(self.config, "version", "1.0"),
            "inputs": {k: type(v).__name__ for k, v in kwargs.items()},
        }

    def _generate_provenance(self, **kwargs) -> dict[str, Any]:
        """Generate provenance information."""
        return {
            "agent": self.agent_type,
            "agent_id": self.agent_id,
            "execution_timestamp": time.time(),
            "input_sources": self._identify_input_sources(**kwargs),
            "processing_steps": self._get_processing_steps(),
            "external_services": self._get_external_services_used(),
        }

    def _identify_input_sources(self, **kwargs) -> dict[str, str]:
        """Identify sources of input data."""
        return dict.fromkeys(kwargs.keys(), "user_provided")

    def _get_processing_steps(self) -> list[str]:
        """Get list of processing steps performed."""
        return [f"{self.agent_type}_processing"]

    def _get_external_services_used(self) -> list[str]:
        """Get list of external services used."""
        return []

    def _update_metrics(self, execution_time: float, success: bool):
        """Update agent performance metrics."""
        self.metrics["total_executions"] += 1
        if success:
            self.metrics["successful_executions"] += 1
        else:
            self.metrics["failed_executions"] += 1

        # Update average execution time
        total = self.metrics["total_executions"]
        current_avg = self.metrics["average_execution_time"]
        self.metrics["average_execution_time"] = (
            current_avg * (total - 1) + execution_time
        ) / total

    def get_metrics(self) -> dict[str, Any]:
        """Get agent performance metrics."""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful_executions"] / self.metrics["total_executions"]
                if self.metrics["total_executions"] > 0
                else 0.0
            ),
            "current_status": self.status.value,
        }


class AgentConfig:
    """Configuration class for agents."""

    def __init__(
        self,
        version: str = "1.0",
        llm_config: Optional[dict[str, Any]] = None,
        use_llm: bool = False,
        conversion_timeout: int = 300,
        **kwargs,
    ):
        self.version = version
        self.llm_config = llm_config or {}
        self.use_llm = use_llm
        self.conversion_timeout = conversion_timeout

        # Store any additional configuration
        for key, value in kwargs.items():
            setattr(self, key, value)
