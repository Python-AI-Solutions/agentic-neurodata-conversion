#!/usr/bin/env python
"""
Multi-Agent NWB Conversion Pipeline - Standalone Demonstration Script

This script demonstrates the complete information flow through the entire
multi-agent pipeline WITHOUT requiring Redis (filesystem-only mode).

Usage:
    pixi run python scripts/demo_full_pipeline_standalone.py

Output:
    - Detailed logs of each step
    - Information flow visualization
    - Generated files at each stage
    - Final NWB file and validation report
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.agents.conversion_agent import ConversionAgent
from agentic_neurodata_conversion.agents.evaluation_agent import EvaluationAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage
from agentic_neurodata_conversion.models.session_context import (
    SessionContext,
    WorkflowStage,
)


class PipelineDemo:
    """Demonstration of complete pipeline with detailed logging."""

    def __init__(self):
        """Initialize demo with context manager and agents."""
        self.context_manager = None
        self.conversation_agent = None
        self.conversion_agent = None
        self.evaluation_agent = None
        self.session_id = None

        # Colors for terminal output
        self.BLUE = "\033[94m"
        self.GREEN = "\033[92m"
        self.YELLOW = "\033[93m"
        self.RED = "\033[91m"
        self.BOLD = "\033[1m"
        self.END = "\033[0m"

    def log(self, message: str, level: str = "INFO"):
        """Log with color coding."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if level == "HEADER":
            print(f"\n{self.BOLD}{self.BLUE}{'='*80}{self.END}")
            print(f"{self.BOLD}{self.BLUE}{message}{self.END}")
            print(f"{self.BOLD}{self.BLUE}{'='*80}{self.END}\n")
        elif level == "STEP":
            print(f"\n{self.BOLD}{self.GREEN}[{timestamp}] >> {message}{self.END}")
        elif level == "SUBSTEP":
            print(f"{self.YELLOW}  -> {message}{self.END}")
        elif level == "DATA":
            print(f"     {message}")
        elif level == "ERROR":
            print(f"{self.RED}[ERROR] {message}{self.END}")
        else:
            print(f"[{timestamp}] {message}")

    def log_json(self, data: dict, indent: int = 5):
        """Log JSON data with indentation."""
        json_str = json.dumps(data, indent=2, default=str)
        for line in json_str.split('\n'):
            print(f"{' ' * indent}{line}")

    async def initialize(self):
        """Initialize all components."""
        self.log("PIPELINE INITIALIZATION", "HEADER")

        self.log("Initializing Context Manager (Filesystem-Only Mode)", "STEP")
        self.context_manager = ContextManager(
            redis_url=None,  # Disable Redis
            filesystem_base_path="./demo_sessions",
        )
        # No need to connect for filesystem-only mode
        self.log("Context Manager initialized (Filesystem-Only)", "SUBSTEP")
        self.log(f"Storage: ./demo_sessions/ only (no Redis)", "DATA")

        self.log("Initializing Agents", "STEP")

        # Import configs
        from agentic_neurodata_conversion.config import (
            get_conversation_agent_config,
            get_conversion_agent_config,
            get_evaluation_agent_config,
        )

        self.conversation_agent = ConversationAgent(get_conversation_agent_config())
        self.log("ConversationAgent initialized", "SUBSTEP")
        self.log(f"Capabilities: {self.conversation_agent.get_capabilities()}", "DATA")

        self.conversion_agent = ConversionAgent(get_conversion_agent_config())
        self.log("ConversionAgent initialized", "SUBSTEP")
        self.log(f"Capabilities: {self.conversion_agent.get_capabilities()}", "DATA")

        self.evaluation_agent = EvaluationAgent(get_evaluation_agent_config())
        self.log("EvaluationAgent initialized", "SUBSTEP")
        self.log(f"Capabilities: {self.evaluation_agent.get_capabilities()}", "DATA")

        # Set context manager for all agents
        self.conversation_agent.context_manager = self.context_manager
        self.conversion_agent.context_manager = self.context_manager
        self.evaluation_agent.context_manager = self.context_manager

    async def create_session(self, dataset_path: str):
        """Create initial session."""
        self.log("SESSION CREATION", "HEADER")

        self.log("Creating Session Context", "STEP")
        self.session_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        session = SessionContext(
            session_id=self.session_id,
            workflow_stage=WorkflowStage.INITIALIZED,
        )

        await self.context_manager.create_session(session)
        self.log(f"Session created: {self.session_id}", "SUBSTEP")
        self.log(f"Initial workflow_stage: {WorkflowStage.INITIALIZED.value}", "DATA")
        self.log(f"Storage locations:", "DATA")
        self.log(f"  - Filesystem: ./demo_sessions/sessions/{self.session_id}.json", "DATA")

        return session

    async def run_conversation_agent(self, dataset_path: str):
        """Run conversation agent to extract metadata."""
        self.log("PHASE 1: CONVERSATION AGENT", "HEADER")

        self.log("Preparing MCP Message", "STEP")
        message = MCPMessage(
            message_id="msg-conversation-001",
            session_id=self.session_id,
            source_agent="mcp_server",
            target_agent="conversation_agent",
            payload={
                "action": "initialize_session",
                "dataset_path": dataset_path,
            },
        )
        self.log("Message structure:", "SUBSTEP")
        self.log_json(message.model_dump())

        self.log("Executing Conversation Agent", "STEP")
        self.log("Agent will:", "SUBSTEP")
        self.log("1. Detect dataset format (OpenEphys)", "DATA")
        self.log("2. Validate dataset structure", "DATA")
        self.log("3. Extract metadata from .md files (using LLM)", "DATA")
        self.log("4. Update session context", "DATA")
        self.log("5. Trigger Conversion Agent", "DATA")

        result = await self.conversation_agent.handle_message(message)
        self.log("Conversation Agent completed", "SUBSTEP")
        self.log("Result:", "SUBSTEP")
        self.log_json(result)

        # Show session context
        session = await self.context_manager.get_session(self.session_id)
        self.log("Updated Session Context:", "STEP")
        self.log(f"workflow_stage: {session.workflow_stage.value}", "DATA")
        self.log(f"dataset_info:", "DATA")
        if session.dataset_info:
            self.log_json(session.dataset_info.model_dump(), indent=7)
        self.log(f"metadata:", "DATA")
        if session.metadata:
            self.log_json(session.metadata.model_dump(exclude_none=True), indent=7)

        return result

    async def run_conversion_agent(self):
        """Run conversion agent to generate NWB file."""
        self.log("PHASE 2: CONVERSION AGENT", "HEADER")

        self.log("Preparing MCP Message", "STEP")
        message = MCPMessage(
            message_id="msg-conversion-001",
            session_id=self.session_id,
            source_agent="conversation_agent",
            target_agent="conversion_agent",
            payload={
                "action": "convert_dataset",
            },
        )
        self.log("Message structure:", "SUBSTEP")
        self.log_json(message.model_dump())

        self.log("Executing Conversion Agent", "STEP")
        self.log("Agent will:", "SUBSTEP")
        self.log("1. Get session context (dataset_path, metadata)", "DATA")
        self.log("2. Prepare NWB metadata from session metadata", "DATA")
        self.log("3. Use NeuroConv to convert OpenEphys -> NWB", "DATA")
        self.log("4. Apply gzip compression", "DATA")
        self.log("5. Track conversion duration", "DATA")
        self.log("6. Update session context with conversion_results", "DATA")
        self.log("7. Trigger Evaluation Agent", "DATA")

        result = await self.conversion_agent.handle_message(message)
        self.log("Conversion Agent completed", "SUBSTEP")
        self.log("Result:", "SUBSTEP")
        self.log_json(result)

        # Show session context
        session = await self.context_manager.get_session(self.session_id)
        self.log("Updated Session Context:", "STEP")
        self.log(f"workflow_stage: {session.workflow_stage.value}", "DATA")
        self.log(f"conversion_results:", "DATA")
        if session.conversion_results:
            self.log_json(session.conversion_results.model_dump(exclude_none=True), indent=7)

        # Check if NWB file exists
        if session.conversion_results and session.conversion_results.nwb_file_path:
            nwb_path = Path(session.conversion_results.nwb_file_path)
            if nwb_path.exists():
                size_mb = nwb_path.stat().st_size / (1024 * 1024)
                self.log(f"NWB file created: {nwb_path}", "SUBSTEP")
                self.log(f"File size: {size_mb:.2f} MB", "DATA")

        return result

    async def run_evaluation_agent(self):
        """Run evaluation agent to validate NWB file."""
        self.log("PHASE 3: EVALUATION AGENT", "HEADER")

        self.log("Preparing MCP Message", "STEP")
        message = MCPMessage(
            message_id="msg-evaluation-001",
            session_id=self.session_id,
            source_agent="conversion_agent",
            target_agent="evaluation_agent",
            payload={
                "action": "validate_nwb",
            },
        )
        self.log("Message structure:", "SUBSTEP")
        self.log_json(message.model_dump())

        self.log("Executing Evaluation Agent", "STEP")
        self.log("Agent will:", "SUBSTEP")
        self.log("1. Get session context (NWB file path)", "DATA")
        self.log("2. Validate NWB file using NWB Inspector", "DATA")
        self.log("3. Categorize issues by severity", "DATA")
        self.log("4. Calculate metadata completeness score", "DATA")
        self.log("5. Calculate best practices score", "DATA")
        self.log("6. Generate JSON validation report", "DATA")
        self.log("7. Generate LLM validation summary", "DATA")
        self.log("8. Update session context with validation_results", "DATA")
        self.log("9. Set workflow_stage to COMPLETED", "DATA")

        result = await self.evaluation_agent.handle_message(message)
        self.log("Evaluation Agent completed", "SUBSTEP")
        self.log("Result:", "SUBSTEP")
        self.log_json(result)

        # Show session context
        session = await self.context_manager.get_session(self.session_id)
        self.log("Updated Session Context:", "STEP")
        self.log(f"workflow_stage: {session.workflow_stage.value}", "DATA")
        self.log(f"validation_results:", "DATA")
        if session.validation_results:
            validation_dict = session.validation_results.model_dump(exclude_none=True)
            # Truncate issues list for readability
            if "issues" in validation_dict and len(validation_dict["issues"]) > 5:
                validation_dict["issues"] = (
                    validation_dict["issues"][:5]
                    + [f"... and {len(validation_dict['issues']) - 5} more issues"]
                )
            self.log_json(validation_dict, indent=7)

        # Check if validation report exists
        if session.validation_results and session.validation_results.validation_report_path:
            report_path = Path(session.validation_results.validation_report_path)
            if report_path.exists():
                self.log(f"Validation report created: {report_path}", "SUBSTEP")
                size_kb = report_path.stat().st_size / 1024
                self.log(f"Report size: {size_kb:.2f} KB", "DATA")

        return result

    async def show_final_results(self):
        """Show final results and generated files."""
        self.log("FINAL RESULTS", "HEADER")

        session = await self.context_manager.get_session(self.session_id)

        self.log("Workflow Summary", "STEP")
        self.log(f"Session ID: {session.session_id}", "DATA")
        self.log(f"Final Stage: {session.workflow_stage.value}", "DATA")
        self.log(f"Total Duration: {(session.last_updated - session.created_at).total_seconds():.2f}s", "DATA")

        self.log("Generated Files", "STEP")

        files_created = []

        # Session file
        session_file = Path(f"./demo_sessions/sessions/{self.session_id}.json")
        if session_file.exists():
            files_created.append(("Session Context", session_file))

        # NWB file
        if session.conversion_results and session.conversion_results.nwb_file_path:
            nwb_file = Path(session.conversion_results.nwb_file_path)
            if nwb_file.exists():
                files_created.append(("NWB File", nwb_file))

        # Validation report
        if session.validation_results and session.validation_results.validation_report_path:
            report_file = Path(session.validation_results.validation_report_path)
            if report_file.exists():
                files_created.append(("Validation Report", report_file))

        for i, (name, path) in enumerate(files_created, 1):
            size = path.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.2f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.2f} KB"
            else:
                size_str = f"{size} bytes"

            self.log(f"{i}. {name}", "SUBSTEP")
            self.log(f"Path: {path}", "DATA")
            self.log(f"Size: {size_str}", "DATA")

        self.log("Information Flow Summary", "STEP")
        self.log("1. User Request -> MCP Server", "DATA")
        self.log("2. MCP Server -> Conversation Agent (metadata extraction)", "DATA")
        self.log("3. Conversation Agent -> Session Context (dataset_info, metadata)", "DATA")
        self.log("4. Conversation Agent -> Conversion Agent (handoff)", "DATA")
        self.log("5. Conversion Agent -> Session Context (conversion_results)", "DATA")
        self.log("6. Conversion Agent -> Evaluation Agent (handoff)", "DATA")
        self.log("7. Evaluation Agent -> Session Context (validation_results)", "DATA")
        self.log("8. Session Context -> User (final results)", "DATA")

        self.log("Data Storage Locations", "STEP")
        self.log(f"Filesystem: ./demo_sessions/sessions/{self.session_id}.json", "DATA")
        self.log(f"NWB Output: {session.conversion_results.nwb_file_path if session.conversion_results else 'N/A'}", "DATA")
        self.log(f"Report: {session.validation_results.validation_report_path if session.validation_results else 'N/A'}", "DATA")

    async def cleanup(self):
        """Cleanup resources."""
        self.log("CLEANUP", "HEADER")
        # Filesystem-only mode doesn't need disconnection
        self.log("No cleanup needed (Filesystem-Only Mode)", "SUBSTEP")

    async def run(self, dataset_path: str):
        """Run complete demonstration."""
        try:
            await self.initialize()
            await self.create_session(dataset_path)
            await self.run_conversation_agent(dataset_path)
            await self.run_conversion_agent()
            await self.run_evaluation_agent()
            await self.show_final_results()
        except Exception as e:
            self.log(f"Error occurred: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()


async def main():
    """Main entry point."""
    print("\n")
    print("=" * 80)
    print("  Multi-Agent NWB Conversion Pipeline - Full Demonstration".center(80))
    print("  (Standalone Mode - No Redis Required)".center(80))
    print("=" * 80)
    print("\n")

    # Use test dataset
    dataset_path = "./tests/data/synthetic_openephys"

    print(f"Using dataset: {dataset_path}\n")

    demo = PipelineDemo()
    await demo.run(dataset_path)

    print("\n")
    print("=" * 80)
    print("  Demonstration Complete!".center(80))
    print("=" * 80)
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
