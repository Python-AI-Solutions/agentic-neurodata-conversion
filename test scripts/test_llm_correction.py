"""
Test script to verify LLM correction analysis.

This creates an NWB file with intentional validation errors
to trigger the LLM correction workflow.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from dateutil.tz import tzlocal

# Load .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from pynwb import NWBFile, NWBHDF5IO
from pynwb.file import Subject


def create_bad_nwb_file():
    """Create an NWB file with intentional validation issues."""
    output_path = Path("test_data/bad_example.nwb")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create NWB file with problematic data that will fail validation
    nwbfile = NWBFile(
        session_description="a",  # Too short - will trigger error
        identifier="bad-test-123",
        session_start_time=datetime.now(tzlocal()),
        experimenter=[""],  # Empty string - validation error
        lab="",  # Empty string - validation error
        institution="",  # Empty string - validation error
    )

    # Add subject with empty/invalid fields
    nwbfile.subject = Subject(
        subject_id="",  # Empty subject_id - validation error
        species="",  # Empty species - validation error
        age="",  # Empty age - validation error
        sex="invalid",  # Invalid sex value - validation error
    )

    # Write file
    with NWBHDF5IO(str(output_path), "w") as io:
        io.write(nwbfile)

    print(f"Created NWB file with validation issues: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    return output_path


async def test_llm_correction():
    """Test the LLM correction analysis."""
    from services import AnthropicLLMService
    from agents.evaluation_agent import EvaluationAgent
    from models import GlobalState, MCPMessage
    import os

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        print("Please set the environment variable or add to .env file")
        return

    # Create NWB file with issues
    nwb_path = create_bad_nwb_file()

    # Initialize LLM service
    llm_service = AnthropicLLMService(api_key=api_key)

    # Initialize evaluation agent
    eval_agent = EvaluationAgent(llm_service=llm_service)

    # Create state
    state = GlobalState(input_path=str(nwb_path))

    print("\n" + "="*60)
    print("Running NWB Inspector validation...")
    print("="*60)

    # Run validation
    validation_message = MCPMessage(
        target_agent="evaluation",
        action="run_validation",
        context={"nwb_path": str(nwb_path)},
    )

    validation_response = await eval_agent.handle_run_validation(validation_message, state)

    if not validation_response.success:
        print(f"Validation failed: {validation_response.error}")
        return

    validation_result = validation_response.result["validation_result"]
    print(f"\nValidation completed:")
    print(f"  Valid: {validation_result['is_valid']}")
    print(f"  Issues found: {len(validation_result['issues'])}")
    print(f"  Summary: {validation_result['summary']}")

    # For testing purposes, run LLM analysis even if validation passes
    # to demonstrate the LLM correction feature
    if validation_result['is_valid'] and len(validation_result['issues']) < 5:
        print("\nNo significant validation issues found - LLM correction not needed")
        print("(Need more serious validation errors to trigger correction workflow)")
        return

    print(f"\nProceeding with LLM analysis for {len(validation_result['issues'])} issues...")

    print("\n" + "="*60)
    print("Analyzing corrections with LLM...")
    print("="*60)

    # Analyze corrections with LLM
    analysis_message = MCPMessage(
        target_agent="evaluation",
        action="analyze_corrections",
        context={
            "validation_result": validation_result,
            "input_metadata": {"session_description": "Test"},
            "conversion_parameters": {},
        },
    )

    analysis_response = await eval_agent.handle_analyze_corrections(analysis_message, state)

    if not analysis_response.success:
        print(f"Analysis failed: {analysis_response.error}")
        return

    corrections = analysis_response.result["corrections"]

    print(f"\n✅ LLM Analysis Complete!")
    print(f"\nAnalysis: {corrections.get('analysis', 'N/A')}")
    print(f"\nRecommended Action: {corrections.get('recommended_action', 'N/A')}")
    print(f"\nSuggestions ({len(corrections.get('suggestions', []))}):")

    for i, suggestion in enumerate(corrections.get("suggestions", []), 1):
        print(f"\n  {i}. [{suggestion.get('severity', 'N/A')}] {suggestion.get('issue', 'N/A')}")
        print(f"     Suggestion: {suggestion.get('suggestion', 'N/A')}")
        print(f"     Actionable: {suggestion.get('actionable', False)}")

    print("\n" + "="*60)
    print("Test completed successfully!")
    print("="*60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_llm_correction())
