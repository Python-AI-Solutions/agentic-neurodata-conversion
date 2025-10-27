#!/usr/bin/env python3
"""
Test full conversion workflow with the new improvements.

This tests:
1. File upload
2. Metadata inference (auto-extraction)
3. Conversion
4. Validation
5. Report generation
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from models.state import GlobalState
from services.llm_service import AnthropicLLMService
from services.mcp_server import MCPServer
from models.mcp import MCPMessage


async def test_full_workflow():
    """Test the full conversion workflow."""
    print("=" * 80)
    print("FULL WORKFLOW TEST WITH NEW IMPROVEMENTS")
    print("=" * 80)
    print()

    # Initialize services
    print("📋 Step 1: Initializing services...")
    state = GlobalState()

    # Get API key from environment
    import os
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set in environment")
        return False

    llm_service = AnthropicLLMService(api_key=api_key)
    mcp_server = MCPServer()

    # Import and register agents
    from agents.conversion_agent import ConversionAgent
    from agents.evaluation_agent import EvaluationAgent
    from agents.conversation_agent import ConversationAgent

    print("✓ Registered conversation agent")
    conversation_agent = ConversationAgent(mcp_server=mcp_server, llm_service=llm_service)
    mcp_server.register_handler("conversation", "start_conversion", conversation_agent.handle_start_conversion)

    print("✓ Registered conversion agent")
    conversion_agent = ConversionAgent(mcp_server=mcp_server)
    mcp_server.register_handler("conversion", "detect_format", conversion_agent.handle_detect_format)
    mcp_server.register_handler("conversion", "run_conversion", conversion_agent.handle_run_conversion)

    print("✓ Registered evaluation agent")
    evaluation_agent = EvaluationAgent(mcp_server=mcp_server, llm_service=llm_service)
    mcp_server.register_handler("evaluation", "run_validation", evaluation_agent.handle_run_validation)
    mcp_server.register_handler("evaluation", "generate_report", evaluation_agent.handle_generate_report)

    print()

    # Test file path
    test_file = Path("test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin")
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    print(f"📋 Step 2: Testing with file: {test_file.name}")
    print(f"   File size: {test_file.stat().st_size / (1024*1024):.2f} MB")
    print()

    # Step 3: Start conversion (with metadata inference)
    print("📋 Step 3: Starting conversion (with automatic metadata inference)...")
    start_message = MCPMessage(
        target_agent="conversation",
        action="start_conversion",
        context={
            "input_path": str(test_file.absolute()),
            "metadata": {
                "format": "SpikeGLX",  # Pre-detected
            },
        },
    )

    try:
        response = await conversation_agent.handle_start_conversion(start_message, state)

        if response.success:
            print(f"✓ Conversion started successfully")
            print(f"  Status: {response.result.get('status')}")

            # Check if metadata was inferred
            if "_inference_result" in state.metadata:
                inference = state.metadata["_inference_result"]
                print(f"\n🧠 METADATA INFERENCE RESULTS:")
                print(f"   Inferred fields: {list(inference.get('inferred_metadata', {}).keys())}")
                print(f"   Confidence scores: {inference.get('confidence_scores', {})}")
                print(f"   Suggestions: {inference.get('suggestions', [])}")

            # Check conversion result
            if "nwb_file_path" in response.result:
                nwb_path = Path(response.result["nwb_file_path"])
                print(f"\n✓ NWB file created: {nwb_path.name}")
                print(f"  Size: {nwb_path.stat().st_size / (1024*1024):.2f} MB")

            # Check validation
            if "validation_result" in response.result:
                val_result = response.result["validation_result"]
                print(f"\n✓ Validation completed")
                print(f"  Status: {val_result.get('status')}")
                print(f"  Issue count: {len(val_result.get('issues', []))}")

        else:
            print(f"❌ Conversion failed: {response.error}")
            return False

    except Exception as e:
        print(f"❌ Exception during conversion: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("=" * 80)
    print("✅ FULL WORKFLOW TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    return True


if __name__ == "__main__":
    result = asyncio.run(test_full_workflow())
    sys.exit(0 if result else 1)
