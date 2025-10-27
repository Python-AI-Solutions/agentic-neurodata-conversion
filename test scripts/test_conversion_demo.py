#!/usr/bin/env python
"""
Demo script to run complete SpikeGLX conversion with auto-apply metadata.
This demonstrates the full conversion workflow and report generation.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from models import GlobalState, ConversionStatus
from services import MCPServer, create_llm_service
from agents import (
    register_conversation_agent,
    register_conversion_agent,
    register_evaluation_agent,
)


async def run_conversion_demo():
    """Run complete conversion with auto-apply metadata."""

    print("=" * 80)
    print("SPIKEGLX CONVERSION DEMO WITH AUTO-APPLY METADATA")
    print("=" * 80)
    print()

    # Initialize services
    print("📦 Initializing services...")
    mcp_server = MCPServer()

    # Get API key from environment
    import os
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  Warning: ANTHROPIC_API_KEY not set - LLM features disabled")
        llm_service = None
    else:
        llm_service = create_llm_service(provider="anthropic", api_key=api_key)
        print("✅ LLM service initialized")

    # Register agents
    register_conversion_agent(mcp_server, llm_service=llm_service)
    register_evaluation_agent(mcp_server, llm_service=llm_service)
    register_conversation_agent(mcp_server, llm_service=llm_service)
    print("✅ All agents registered\n")

    # Prepare test data path
    test_data_path = Path(__file__).parent / "test_data" / "spikeglx"
    print(f"📁 Test data: {test_data_path}")
    print(f"   Files: {list(test_data_path.glob('*'))}\n")

    # Set auto-apply metadata (minimal but valid)
    metadata = {
        "experimenter": "Demo User",
        "institution": "Test Institution",
        "experiment_description": "SpikeGLX demo conversion with auto-applied metadata",
        "session_description": "Demo session for report generation testing",
        "subject_id": "demo_subject_001",
        "species": "Mus musculus",
        "sex": "U",
        "age": "P90D",
    }

    print("📝 Auto-applying metadata:")
    for key, value in metadata.items():
        print(f"   {key}: {value}")
    print()

    # Start conversion
    print("🚀 Starting conversion...\n")

    from models import MCPMessage

    # Step 1: Detect format
    print("Step 1: Format Detection")
    print("-" * 40)
    detect_msg = MCPMessage(
        target_agent="conversion",
        action="detect_format",
        context={"input_path": str(test_data_path)},
    )

    detect_response = await mcp_server.route_message(detect_msg, mcp_server.global_state)
    detected_format = detect_response.result.get("format")
    print(f"✅ Detected format: {detected_format}")
    print(f"   Confidence: {detect_response.result.get('confidence', 'N/A')}")
    print()

    # Step 2: Run conversion
    print("Step 2: NWB Conversion")
    print("-" * 40)

    # Update state with metadata
    mcp_server.global_state.metadata.update(metadata)
    mcp_server.global_state.input_path = str(test_data_path)

    convert_msg = MCPMessage(
        target_agent="conversion",
        action="run_conversion",
        context={
            "input_path": str(test_data_path),
            "format": detected_format,
            "metadata": metadata,
        },
    )

    convert_response = await mcp_server.route_message(convert_msg, mcp_server.global_state)

    if convert_response.result.get("status") == "completed":
        output_path = convert_response.result.get("output_path")
        print(f"✅ Conversion successful!")
        print(f"   Output NWB file: {output_path}")
        print(f"   File size: {Path(output_path).stat().st_size / 1024 / 1024:.2f} MB")
        print()
    else:
        print(f"❌ Conversion failed: {convert_response.result.get('error')}")
        return

    # Step 3: Validate NWB file
    print("Step 3: NWB Validation")
    print("-" * 40)

    validate_msg = MCPMessage(
        target_agent="evaluation",
        action="run_validation",
        context={
            "nwb_file_path": output_path,
        },
    )

    validate_response = await mcp_server.route_message(validate_msg, mcp_server.global_state)
    validation_result = validate_response.result.get("validation_result", {})

    print(f"✅ Validation complete")
    print(f"   Status: {validation_result.get('status', 'unknown')}")

    summary = validation_result.get('summary', {})
    print(f"   Total issues: {summary.get('total_issues', 0)}")
    print(f"   - Critical: {summary.get('critical', 0)}")
    print(f"   - Best practice violations: {summary.get('best_practice_violation', 0)}")
    print(f"   - Best practice suggestions: {summary.get('best_practice_suggestion', 0)}")
    print()

    # Step 4: Generate reports
    print("Step 4: Report Generation")
    print("-" * 40)

    report_msg = MCPMessage(
        target_agent="evaluation",
        action="generate_report",
        context={
            "nwb_file_path": output_path,
            "validation_result": validation_result,
            "output_dir": str(Path(output_path).parent),
        },
    )

    report_response = await mcp_server.route_message(report_msg, mcp_server.global_state)

    pdf_report = report_response.result.get("pdf_report")
    json_report = report_response.result.get("json_report")
    text_report = report_response.result.get("text_report")

    print(f"✅ Reports generated:")
    if pdf_report and Path(pdf_report).exists():
        print(f"   📄 PDF: {pdf_report} ({Path(pdf_report).stat().st_size / 1024:.1f} KB)")
    if json_report and Path(json_report).exists():
        print(f"   📊 JSON: {json_report} ({Path(json_report).stat().st_size / 1024:.1f} KB)")
    if text_report and Path(text_report).exists():
        print(f"   📝 Text: {text_report} ({Path(text_report).stat().st_size / 1024:.1f} KB)")
    print()

    # Display report summary
    print("=" * 80)
    print("REPORT SUMMARY")
    print("=" * 80)
    print()

    if json_report and Path(json_report).exists():
        with open(json_report, 'r') as f:
            report_data = json.load(f)

        print("📊 Validation Summary:")
        print(f"   File: {report_data.get('nwb_file')}")
        print(f"   Validation Status: {report_data.get('validation_status')}")
        print(f"   Total Issues: {report_data.get('total_issues', 0)}")
        print()

        print("📋 Issues by Severity:")
        for severity, count in report_data.get('issues_by_severity', {}).items():
            print(f"   {severity}: {count}")
        print()

        print("🔬 Workflow Trace:")
        workflow = report_data.get('workflow_trace', {})
        print(f"   Format: {workflow.get('input_format')}")
        print(f"   Conversion Time: {workflow.get('conversion_duration_seconds', 0):.2f}s")
        print(f"   Technologies Used:")
        for tech in workflow.get('technologies_used', []):
            print(f"      - {tech}")
        print()

        # Show first few issues
        issues = report_data.get('issues', [])
        if issues:
            print(f"📌 Sample Issues (showing first 3 of {len(issues)}):")
            for i, issue in enumerate(issues[:3], 1):
                print(f"   {i}. [{issue.get('severity')}] {issue.get('message', 'No message')}")
                print(f"      Location: {issue.get('location', 'Unknown')}")
            print()

    # Read and display text report excerpt
    if text_report and Path(text_report).exists():
        print("=" * 80)
        print("TEXT REPORT EXCERPT")
        print("=" * 80)
        with open(text_report, 'r') as f:
            lines = f.readlines()
            print("".join(lines[:50]))  # First 50 lines
            if len(lines) > 50:
                print(f"\n... ({len(lines) - 50} more lines)")

    print()
    print("=" * 80)
    print("✅ DEMO COMPLETE")
    print("=" * 80)
    print()
    print(f"📁 All outputs saved to: {Path(output_path).parent}")
    print()
    print("Generated files:")
    output_dir = Path(output_path).parent
    for file in sorted(output_dir.glob("*")):
        if file.is_file():
            size = file.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size / 1024 / 1024:.2f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.2f} KB"
            else:
                size_str = f"{size} B"
            print(f"   {file.name}: {size_str}")


if __name__ == "__main__":
    asyncio.run(run_conversion_demo())
