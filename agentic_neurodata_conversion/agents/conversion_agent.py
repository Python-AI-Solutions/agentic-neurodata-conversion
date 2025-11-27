"""Conversion Agent implementation.

Responsible for:
- Format detection
- NWB conversion using NeuroConv
- Pure technical conversion logic (no user interaction)

Week 4 Refactoring:
This agent has been refactored into 4 focused modules:
- FormatDetector: Format detection and validation (84+ formats)
- ConversionHelpers: Utilities and metadata mapping
- ConversionErrorHandler: Error explanations and recovery
- ConversionRunner: NeuroConv conversion execution

The ConversionAgent now serves as a thin coordinator that delegates
to these specialized modules.
"""

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from services.llm_service import LLMService

logger = logging.getLogger(__name__)

from agentic_neurodata_conversion.agents.conversion import (
    ConversionErrorHandler,
    ConversionHelpers,
    ConversionRunner,
    FormatDetector,
)
from agentic_neurodata_conversion.models import GlobalState, MCPMessage, MCPResponse


class ConversionAgent:
    """Conversion agent for format detection and NWB conversion.

    This agent handles all technical conversion operations by delegating
    to specialized modules:
    - FormatDetector: Handles format detection with LLM and pattern matching
    - ConversionHelpers: Provides utilities for metadata mapping and narration
    - ConversionErrorHandler: Manages error explanations and reconversion
    - ConversionRunner: Executes NeuroConv conversion for 84+ formats

    Week 4 Refactoring:
    Reduced from 1,922 lines to ~250 lines by extracting functionality
    into 4 focused modules (1,836 lines total).
    """

    def __init__(self, llm_service: Optional["LLMService"] = None):
        """Initialize the conversion agent.

        Args:
            llm_service: Optional LLM service for intelligent features
        """
        self._llm_service = llm_service

        # Initialize all modular components
        self._format_detector = FormatDetector(llm_service)
        self._helpers = ConversionHelpers(llm_service)
        self._error_handler = ConversionErrorHandler(llm_service)
        self._runner = ConversionRunner(llm_service, helpers=self._helpers)

        logger.info("ConversionAgent initialized with 4 modular components")

    async def handle_detect_format(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Detect the data format of uploaded files.

        Delegates to FormatDetector module for:
        - LLM-first intelligent detection
        - Confidence threshold validation (>70%)
        - Hallucination prevention (validates against NeuroConv list)
        - Hardcoded pattern matching fallback

        Args:
            message: MCP message with context containing 'input_path'
            state: Global state

        Returns:
            MCPResponse with detected format or error
        """
        return await self._format_detector.handle_detect_format(message, state)

    async def handle_run_conversion(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Run NWB conversion using NeuroConv.

        Delegates to ConversionRunner module for:
        - Format-to-interface mapping (84+ formats)
        - Dynamic interface loading
        - Format-specific initialization
        - Progress monitoring via file size tracking
        - LLM parameter optimization
        - Checksum calculation
        - Comprehensive error recovery

        Args:
            message: MCP message with context containing conversion parameters
            state: Global state

        Returns:
            MCPResponse with conversion result or error
        """
        return await self._runner.handle_run_conversion(message, state)

    async def handle_apply_corrections(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Apply corrections and reconvert NWB file.

        Delegates to ConversionErrorHandler module for:
        - Merging automatic fixes with user input
        - File versioning before reconversion
        - Correction attempt tracking
        - Checksum verification
        - Reconversion orchestration (via ConversionRunner)

        Args:
            message: MCP message with correction context
            state: Global state

        Returns:
            MCPResponse with reconversion result
        """
        return await self._error_handler.handle_apply_corrections(
            message,
            state,
            self._runner,
        )


def register_conversion_agent(mcp_server, llm_service: Optional["LLMService"] = None) -> ConversionAgent:
    """Register Conversion Agent handlers with MCP server.

    Creates a ConversionAgent instance and registers its handlers:
    - detect_format: Format detection
    - run_conversion: NWB conversion
    - apply_corrections: Reconversion with corrections

    Args:
        mcp_server: MCP server instance
        llm_service: Optional LLM service for intelligent features

    Returns:
        ConversionAgent instance
    """
    agent = ConversionAgent(llm_service=llm_service)

    mcp_server.register_handler(
        "conversion",
        "detect_format",
        agent.handle_detect_format,
    )

    mcp_server.register_handler(
        "conversion",
        "run_conversion",
        agent.handle_run_conversion,
    )

    mcp_server.register_handler(
        "conversion",
        "apply_corrections",
        agent.handle_apply_corrections,
    )

    logger.info(
        "ConversionAgent registered with MCP server (3 handlers: detect_format, run_conversion, apply_corrections)"
    )

    return agent
