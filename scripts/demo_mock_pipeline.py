#!/usr/bin/env python
"""
Multi-Agent NWB Conversion Pipeline - Mock Demonstration Script

This script demonstrates the complete information flow through the entire
multi-agent pipeline using MOCK data (no Redis, no LLM API keys required).

Usage:
    pixi run python scripts/demo_mock_pipeline.py

Output:
    - Detailed logs of each step
    - Information flow visualization
    - Mock session state changes
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class Colors:
    """ANSI color codes for terminal output."""
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


class MockPipelineDemo:
    """Mock demonstration of complete pipeline with detailed logging."""

    def __init__(self):
        """Initialize demo."""
        self.session_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.start_time = datetime.now()
        self.session_state = {
            "session_id": self.session_id,
            "workflow_stage": "initialized",
            "created_at": self.start_time.isoformat(),
            "last_updated": self.start_time.isoformat(),
        }

    def log(self, message: str, level: str = "INFO"):
        """Log with color coding."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if level == "HEADER":
            print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")
        elif level == "STEP":
            print(f"\n{Colors.BOLD}{Colors.GREEN}[{timestamp}] >> {message}{Colors.END}")
        elif level == "SUBSTEP":
            print(f"{Colors.YELLOW}  -> {message}{Colors.END}")
        elif level == "DATA":
            print(f"     {message}")
        elif level == "FILE":
            print(f"{Colors.BOLD}     FILE: {message}{Colors.END}")
        elif level == "SUCCESS":
            print(f"{Colors.GREEN}  [OK] {message}{Colors.END}")
        else:
            print(f"[{timestamp}] {message}")

    def log_json(self, data: dict, indent: int = 5):
        """Log JSON data with indentation."""
        json_str = json.dumps(data, indent=2, default=str)
        for line in json_str.split('\n'):
            print(f"{' ' * indent}{line}")

    def update_session_state(self, **kwargs):
        """Update session state."""
        self.session_state.update(kwargs)
        self.session_state["last_updated"] = datetime.now().isoformat()

    def phase_0_initialization(self):
        """Phase 0: System Initialization."""
        self.log("PHASE 0: SYSTEM INITIALIZATION", "HEADER")

        self.log("Starting MCP Server", "STEP")
        self.log("Loading configuration from environment", "SUBSTEP")
        self.log("REDIS_URL: localhost:6379", "DATA")
        self.log("FILESYSTEM_BASE_PATH: ./sessions", "DATA")
        self.log("MCP server configuration loaded", "SUCCESS")

        self.log("Initializing Context Manager", "STEP")
        self.log("Connecting to Redis (localhost:6379)", "SUBSTEP")
        self.log("Redis connection established", "SUCCESS")
        self.log("Filesystem storage initialized: ./sessions/", "SUCCESS")

        self.log("Registering Agents", "STEP")

        agents = [
            ("ConversationAgent", ["extract_metadata", "clarify_metadata"]),
            ("ConversionAgent", ["convert_to_nwb"]),
            ("EvaluationAgent", ["validate_nwb", "generate_report"]),
        ]

        for agent_name, capabilities in agents:
            self.log(f"Registering {agent_name}", "SUBSTEP")
            self.log(f"Capabilities: {', '.join(capabilities)}", "DATA")
            self.log(f"{agent_name} registered", "SUCCESS")

        self.log("MCP Server ready on http://localhost:8000", "SUCCESS")

    def phase_1_session_creation(self, dataset_path: str):
        """Phase 1: Session Initialization."""
        self.log("PHASE 1: SESSION INITIALIZATION", "HEADER")

        self.log("Incoming HTTP Request", "STEP")
        self.log("POST /api/v1/sessions/initialize", "DATA")
        request = {"dataset_path": dataset_path}
        self.log_json(request)

        self.log("Processing Request", "STEP")
        self.log(f"Generated session_id: {self.session_id}", "SUBSTEP")
        self.log("Creating SessionContext object", "SUBSTEP")

        self.update_session_state(
            workflow_stage="initialized",
            dataset_info=None,
            metadata=None,
            conversion_results=None,
            validation_results=None,
        )

        self.log("Session State:", "DATA")
        self.log_json(self.session_state)

        self.log("Persisting Session", "STEP")
        self.log(f"Writing to Redis: session:{self.session_id}", "SUBSTEP")
        self.log(f"Writing to Filesystem: ./sessions/{self.session_id}.json", "SUBSTEP")
        self.log(f"./sessions/{self.session_id}.json", "FILE")
        self.log("Session persisted successfully", "SUCCESS")

        self.log("Creating MCP Message for Conversation Agent", "STEP")
        mcp_message = {
            "message_id": "msg-001",
            "session_id": self.session_id,
            "source_agent": "mcp_server",
            "target_agent": "conversation_agent",
            "payload": {
                "action": "initialize_session",
                "dataset_path": dataset_path,
            },
        }
        self.log_json(mcp_message)

        self.log("Routing Message", "STEP")
        self.log("POST /internal/route_message -> ConversationAgent", "SUBSTEP")

        self.log("HTTP Response", "STEP")
        response = {
            "session_id": self.session_id,
            "workflow_stage": "initialized",
            "message": "Session initialized successfully",
        }
        self.log_json(response)

    def phase_2_conversation_agent(self, dataset_path: str):
        """Phase 2: Conversation Agent (Metadata Extraction)."""
        self.log("PHASE 2: CONVERSATION AGENT - METADATA EXTRACTION", "HEADER")

        self.log("ConversationAgent Received MCP Message", "STEP")
        self.log("action: initialize_session", "DATA")
        self.log(f"dataset_path: {dataset_path}", "DATA")

        self.log("Step 1: Dataset Format Detection", "STEP")
        self.log("Scanning dataset directory...", "SUBSTEP")
        self.log(f"Found files:", "DATA")
        mock_files = [
            "100_CH1.continuous",
            "100_CH2.continuous",
            "100_CH3.continuous",
            "100_CH4.continuous",
            "settings.xml",
            "README.md",
        ]
        for f in mock_files:
            self.log(f"  - {f}", "DATA")

        self.log("Pattern detection:", "SUBSTEP")
        self.log("  + Found .continuous files -> OpenEphys format detected", "DATA")
        self.log("  + Found settings.xml -> Confirmed OpenEphys", "DATA")
        self.log("Dataset format: OpenEphys", "SUCCESS")

        self.log("Step 2: Dataset Validation", "STEP")
        self.log("Validating OpenEphys structure...", "SUBSTEP")
        self.log("  + settings.xml present", "DATA")
        self.log("  + Channel count: 4", "DATA")
        self.log("  + .continuous files found: 4", "DATA")
        self.log("Dataset structure valid", "SUCCESS")

        dataset_info = {
            "format": "openephys",
            "file_count": 6,
            "total_size_mb": 15.3,
            "channels": 4,
        }

        self.log("Step 3: Metadata Extraction", "STEP")
        self.log("Reading README.md...", "SUBSTEP")
        self.log("./tests/data/synthetic_openephys/README.md", "FILE")

        readme_content = """# Synthetic OpenEphys Dataset
Subject: mouse-001
Species: Mus musculus
Experimenter: Dr. Jane Smith
Experiment: Visual cortex recording during passive viewing"""

        self.log("README.md content:", "DATA")
        for line in readme_content.strip().split('\n'):
            self.log(f"  {line}", "DATA")

        self.log("Calling LLM for metadata extraction...", "SUBSTEP")
        self.log("Provider: Anthropic Claude", "DATA")
        self.log("Model: claude-3-5-sonnet-20241022", "DATA")

        llm_prompt = """Extract NWB metadata from this markdown:
{readme_content}

Return JSON with: subject_id, species, experimenter, experiment_description"""

        self.log("LLM Prompt:", "DATA")
        for line in llm_prompt.strip().split('\n'):
            self.log(f"  {line}", "DATA")

        self.log("LLM Response received (0.8s)", "SUBSTEP")

        metadata = {
            "subject_id": "mouse-001",
            "species": "Mus musculus",
            "experimenter": "Dr. Jane Smith",
            "experiment_description": "Visual cortex recording during passive viewing",
            "session_description": "Synthetic OpenEphys recording session",
        }

        self.log("Extracted metadata:", "DATA")
        self.log_json(metadata)
        self.log("Metadata extraction complete", "SUCCESS")

        self.log("Step 4: Update Session Context", "STEP")
        self.update_session_state(
            workflow_stage="collecting_metadata",
            dataset_info=dataset_info,
            metadata=metadata,
        )

        self.log("Updated session state:", "DATA")
        self.log_json(self.session_state)

        self.log("Persisting to Redis and Filesystem...", "SUBSTEP")
        self.log(f"./sessions/{self.session_id}.json", "FILE")
        self.log("Session updated successfully", "SUCCESS")

        self.log("Step 5: Trigger Conversion Agent", "STEP")
        handoff_message = {
            "message_id": "msg-002",
            "session_id": self.session_id,
            "source_agent": "conversation_agent",
            "target_agent": "conversion_agent",
            "payload": {
                "action": "convert_dataset",
            },
        }
        self.log("Creating handoff MCP message:", "SUBSTEP")
        self.log_json(handoff_message)
        self.log("POST /internal/route_message -> ConversionAgent", "SUBSTEP")
        self.log("Handoff complete", "SUCCESS")

    def phase_3_conversion_agent(self):
        """Phase 3: Conversion Agent (NWB Generation)."""
        self.log("PHASE 3: CONVERSION AGENT - NWB FILE GENERATION", "HEADER")

        self.log("ConversionAgent Received MCP Message", "STEP")
        self.log("action: convert_dataset", "DATA")

        self.log("Step 1: Retrieve Session Context", "STEP")
        self.log(f"GET session:{self.session_id} from Redis", "SUBSTEP")
        self.log("Retrieved dataset_path and metadata", "SUCCESS")
        self.log(f"Dataset: {self.session_state.get('dataset_info', {}).get('format', 'N/A')}", "DATA")
        self.log(f"Subject: {self.session_state.get('metadata', {}).get('subject_id', 'N/A')}", "DATA")

        self.log("Step 2: Prepare NWB Metadata", "STEP")
        nwb_metadata = {
            "NWBFile": {
                "session_description": "Visual cortex recording during passive viewing",
                "identifier": self.session_id,
                "session_start_time": self.start_time.isoformat(),
            },
            "Subject": {
                "subject_id": "mouse-001",
                "species": "Mus musculus",
            },
        }
        self.log("NWB metadata structure:", "SUBSTEP")
        self.log_json(nwb_metadata)
        self.log("Metadata prepared for NeuroConv", "SUCCESS")

        self.log("Step 3: Execute Conversion with NeuroConv", "STEP")
        self.log("Using OpenEphysRecordingInterface...", "SUBSTEP")
        self.log("Loading OpenEphys data (4 channels)...", "DATA")
        self.log("Creating NWB file structure...", "DATA")
        self.log("Writing electrical series data...", "DATA")
        self.log("Adding metadata to NWB file...", "DATA")
        self.log("Applying gzip compression...", "DATA")

        output_path = f"./output/nwb_files/{self.session_id}.nwb"
        self.log(f"Writing to: {output_path}", "SUBSTEP")
        self.log(output_path, "FILE")

        conversion_duration = 2.3
        self.log(f"Conversion completed in {conversion_duration}s", "SUCCESS")
        self.log(f"Output file size: 1.8 MB", "DATA")

        self.log("Step 4: Update Session Context", "STEP")
        conversion_results = {
            "nwb_file_path": output_path,
            "conversion_duration_seconds": conversion_duration,
            "warnings": [],
            "errors": [],
        }

        self.update_session_state(
            workflow_stage="converting",
            conversion_results=conversion_results,
            output_nwb_path=output_path,
        )

        self.log("Updated session state:", "DATA")
        self.log_json(conversion_results)
        self.log(f"./sessions/{self.session_id}.json", "FILE")
        self.log("Session updated successfully", "SUCCESS")

        self.log("Step 5: Trigger Evaluation Agent", "STEP")
        handoff_message = {
            "message_id": "msg-003",
            "session_id": self.session_id,
            "source_agent": "conversion_agent",
            "target_agent": "evaluation_agent",
            "payload": {
                "action": "validate_nwb",
            },
        }
        self.log("Creating handoff MCP message:", "SUBSTEP")
        self.log_json(handoff_message)
        self.log("POST /internal/route_message -> EvaluationAgent", "SUBSTEP")
        self.log("Handoff complete", "SUCCESS")

    def phase_4_evaluation_agent(self):
        """Phase 4: Evaluation Agent (Validation)."""
        self.log("PHASE 4: EVALUATION AGENT - NWB VALIDATION", "HEADER")

        self.log("EvaluationAgent Received MCP Message", "STEP")
        self.log("action: validate_nwb", "DATA")

        self.log("Step 1: Retrieve Session Context", "STEP")
        nwb_path = self.session_state.get("conversion_results", {}).get("nwb_file_path")
        self.log(f"NWB file path: {nwb_path}", "SUBSTEP")
        self.log("Session context retrieved", "SUCCESS")

        self.log("Step 2: Validate NWB File with NWB Inspector", "STEP")
        self.log(f"Running: inspect_nwbfile('{nwb_path}')", "SUBSTEP")
        self.log("Inspecting file structure...", "DATA")
        self.log("Checking required fields...", "DATA")
        self.log("Validating data types...", "DATA")
        self.log("Checking best practices...", "DATA")

        self.log("NWB Inspector found 3 issues:", "SUBSTEP")

        issues = [
            {
                "severity": "BEST_PRACTICE_SUGGESTION",
                "message": "Consider adding institution metadata",
                "location": "/general/institution",
            },
            {
                "severity": "BEST_PRACTICE_SUGGESTION",
                "message": "Consider adding keywords",
                "location": "/general/keywords",
            },
            {
                "severity": "BEST_PRACTICE_VIOLATION",
                "message": "Missing device metadata",
                "location": "/general/devices",
            },
        ]

        for i, issue in enumerate(issues, 1):
            self.log(f"{i}. [{issue['severity']}] {issue['message']}", "DATA")

        issue_count = {
            "CRITICAL": 0,
            "BEST_PRACTICE_VIOLATION": 1,
            "BEST_PRACTICE_SUGGESTION": 2,
        }

        self.log("Issue summary:", "SUBSTEP")
        self.log_json(issue_count, indent=7)
        self.log("Validation complete", "SUCCESS")

        self.log("Step 3: Calculate Scores", "STEP")

        self.log("Calculating metadata completeness score...", "SUBSTEP")
        metadata_score = 80.0
        self.log(f"Metadata score: {metadata_score}/100", "DATA")
        self.log("  + session_description present", "DATA")
        self.log("  + identifier present", "DATA")
        self.log("  + session_start_time present", "DATA")
        self.log("  + subject_id present", "DATA")
        self.log("  - institution missing", "DATA")

        self.log("Calculating best practices score...", "SUBSTEP")
        best_practices_score = 95.0
        self.log(f"Best practices score: {best_practices_score}/100", "DATA")
        self.log("  Score = 100 - (0*15 + 1*5 + 2*2) = 91", "DATA")

        self.log("Step 4: Generate Validation Report", "STEP")
        report_path = f"./reports/{self.session_id}_validation.json"

        validation_report = {
            "session_id": self.session_id,
            "nwb_file_path": nwb_path,
            "overall_status": "passed_with_warnings",
            "issue_count": issue_count,
            "issues": issues,
            "metadata_completeness_score": metadata_score,
            "best_practices_score": best_practices_score,
            "validation_timestamp": datetime.now().isoformat(),
        }

        self.log(f"Writing report to: {report_path}", "SUBSTEP")
        self.log(report_path, "FILE")
        self.log("Validation report:", "DATA")
        self.log_json(validation_report)
        self.log("Report generated successfully", "SUCCESS")

        self.log("Step 5: Generate LLM Validation Summary", "STEP")
        self.log("Calling LLM for user-friendly summary...", "SUBSTEP")
        self.log("Provider: Anthropic Claude", "DATA")

        llm_summary = """The NWB file passed validation with minor suggestions for improvement.
The file structure is correct and all required fields are present. Consider adding
institution metadata and device information to improve compliance with best practices."""

        self.log("LLM Summary:", "DATA")
        for line in llm_summary.strip().split('\n'):
            self.log(f"  {line}", "DATA")
        self.log("Summary generated (0.6s)", "SUCCESS")

        self.log("Step 6: Update Session Context (Final)", "STEP")
        validation_results = {
            "overall_status": "passed_with_warnings",
            "issue_count": issue_count,
            "issues": issues,
            "metadata_completeness_score": metadata_score,
            "best_practices_score": best_practices_score,
            "llm_validation_summary": llm_summary,
            "validation_report_path": report_path,
        }

        self.update_session_state(
            workflow_stage="completed",
            validation_results=validation_results,
            output_report_path=report_path,
        )

        self.log("Final session state:", "DATA")
        self.log_json(self.session_state)
        self.log(f"./sessions/{self.session_id}.json", "FILE")
        self.log("Session completed successfully", "SUCCESS")

    def phase_5_result_retrieval(self):
        """Phase 5: Result Retrieval."""
        self.log("PHASE 5: RESULT RETRIEVAL", "HEADER")

        self.log("Incoming HTTP Request", "STEP")
        self.log(f"GET /api/v1/sessions/{self.session_id}/result", "DATA")

        self.log("Retrieving Session from Storage", "STEP")
        self.log(f"GET session:{self.session_id} from Redis", "SUBSTEP")
        self.log("Session retrieved successfully", "SUCCESS")

        self.log("Building Response", "STEP")
        response = {
            "session_id": self.session_id,
            "workflow_stage": "completed",
            "nwb_file_path": self.session_state.get("conversion_results", {}).get("nwb_file_path"),
            "validation_report_path": self.session_state.get("validation_results", {}).get("validation_report_path"),
            "overall_status": "passed_with_warnings",
            "llm_validation_summary": self.session_state.get("validation_results", {}).get("llm_validation_summary"),
            "validation_issues": self.session_state.get("validation_results", {}).get("issues", []),
        }

        self.log("HTTP Response (200 OK):", "STEP")
        self.log_json(response)

    def show_final_summary(self):
        """Show final summary."""
        self.log("PIPELINE SUMMARY", "HEADER")

        duration = (datetime.now() - self.start_time).total_seconds()

        self.log("Execution Summary", "STEP")
        self.log(f"Session ID: {self.session_id}", "DATA")
        self.log(f"Total Duration: {duration:.2f}s", "DATA")
        self.log(f"Final Stage: completed", "DATA")
        self.log(f"Overall Status: passed_with_warnings", "DATA")

        self.log("Information Flow Summary", "STEP")
        flow_steps = [
            "1. User -> MCP Server: POST /api/v1/sessions/initialize",
            "2. MCP Server -> ConversationAgent: initialize_session",
            "3. ConversationAgent -> Session Context: dataset_info + metadata",
            "4. ConversationAgent -> ConversionAgent: convert_dataset (handoff)",
            "5. ConversionAgent -> Session Context: conversion_results",
            "6. ConversionAgent -> EvaluationAgent: validate_nwb (handoff)",
            "7. EvaluationAgent -> Session Context: validation_results",
            "8. EvaluationAgent -> Session Context: workflow_stage = completed",
            "9. User -> MCP Server: GET /api/v1/sessions/{id}/result",
            "10. MCP Server -> User: Final results with NWB file + report",
        ]
        for step in flow_steps:
            self.log(step, "DATA")

        self.log("Files Created", "STEP")
        files = [
            f"1. ./sessions/{self.session_id}.json (Session Context)",
            f"2. ./output/nwb_files/{self.session_id}.nwb (NWB File - 1.8 MB)",
            f"3. ./reports/{self.session_id}_validation.json (Validation Report)",
        ]
        for f in files:
            self.log(f, "DATA")

        self.log("Storage Locations", "STEP")
        self.log("Primary: Redis (localhost:6379)", "DATA")
        self.log(f"  - Key: session:{self.session_id}", "DATA")
        self.log("Backup: Filesystem", "DATA")
        self.log(f"  - Path: ./sessions/{self.session_id}.json", "DATA")

        self.log("Agent Interactions", "STEP")
        self.log("Total MCP Messages: 3", "DATA")
        self.log("  1. mcp_server -> conversation_agent", "DATA")
        self.log("  2. conversation_agent -> conversion_agent", "DATA")
        self.log("  3. conversion_agent -> evaluation_agent", "DATA")

        self.log("External Service Calls", "STEP")
        self.log("LLM Calls: 2", "DATA")
        self.log("  1. Metadata extraction (0.8s)", "DATA")
        self.log("  2. Validation summary (0.6s)", "DATA")
        self.log("NeuroConv Operations: 1", "DATA")
        self.log("  1. OpenEphys -> NWB conversion (2.3s)", "DATA")
        self.log("NWB Inspector Operations: 1", "DATA")
        self.log("  1. NWB file validation (0.4s)", "DATA")

    def run(self, dataset_path: str):
        """Run complete demonstration."""
        self.phase_0_initialization()
        self.phase_1_session_creation(dataset_path)
        self.phase_2_conversation_agent(dataset_path)
        self.phase_3_conversion_agent()
        self.phase_4_evaluation_agent()
        self.phase_5_result_retrieval()
        self.show_final_summary()


def main():
    """Main entry point."""
    print("\n")
    print("=" * 80)
    print("  Multi-Agent NWB Conversion Pipeline - Mock Demonstration".center(80))
    print("  (No Redis or LLM API Keys Required)".center(80))
    print("=" * 80)
    print("\n")

    dataset_path = "./tests/data/synthetic_openephys"
    print(f"Using dataset: {dataset_path}\n")

    demo = MockPipelineDemo()
    demo.run(dataset_path)

    print("\n")
    print("=" * 80)
    print("  Demonstration Complete!".center(80))
    print("=" * 80)
    print("\n")
    print("For full documentation, see: docs/INFORMATION_FLOW.md")
    print("To run actual tests: pixi run pytest tests/e2e/test_full_pipeline.py -v")
    print("\n")


if __name__ == "__main__":
    main()
