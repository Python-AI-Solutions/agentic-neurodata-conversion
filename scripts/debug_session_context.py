"""Debug script to test session context creation performance."""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.models import SessionContext, DatasetInfo, WorkflowStage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_session_context_performance():
    """Test session context creation and retrieval performance."""

    logger.info("="*80)
    logger.info("SESSION CONTEXT PERFORMANCE TEST")
    logger.info("="*80)

    # 1. Initialize context manager
    logger.info("\n[1/4] Initializing ContextManager...")
    start_time = time.time()

    manager = ContextManager(redis_url="redis://localhost:6379")
    await manager.connect()

    elapsed = time.time() - start_time
    logger.info(f"  [OK] Connected in {elapsed:.2f}s")

    # 2. Create test dataset info
    logger.info("\n[2/4] Creating test dataset info...")
    dataset_info = DatasetInfo(
        dataset_path="./tests/data/synthetic_openephys",
        format="openephys",
        total_size_bytes=1024 * 1024,  # 1 MB
        file_count=10,
        has_metadata_files=True,
        metadata_files=["README.md"]
    )
    logger.info(f"  [OK] Dataset info created: {dataset_info.format}, {dataset_info.file_count} files")

    # 3. Create session context
    logger.info("\n[3/4] Creating session context in Redis...")
    start_time = time.time()

    session_context = SessionContext(
        session_id="debug-test-001",
        workflow_stage=WorkflowStage.INITIALIZED,
        dataset_info=dataset_info
    )

    await manager.create_session(session_context)

    elapsed = time.time() - start_time
    logger.info(f"  [OK] Session created in {elapsed:.2f}s")

    # 4. Retrieve session context
    logger.info("\n[4/4] Retrieving session context from Redis...")
    start_time = time.time()

    retrieved = await manager.get_session("debug-test-001")

    elapsed = time.time() - start_time
    logger.info(f"  [OK] Session retrieved in {elapsed:.2f}s")
    logger.info(f"  [OK] Session ID: {retrieved.session_id}")
    logger.info(f"  [OK] Workflow Stage: {retrieved.workflow_stage}")

    # 5. Update session context
    logger.info("\n[5/5] Updating session context...")
    start_time = time.time()

    updates = {"workflow_stage": WorkflowStage.COLLECTING_METADATA}
    await manager.update_session("debug-test-001", updates)

    elapsed = time.time() - start_time
    logger.info(f"  [OK] Session updated in {elapsed:.2f}s")

    # 6. Clean up
    logger.info("\n[6/6] Cleaning up...")
    await manager.delete_session("debug-test-001")
    await manager.disconnect()
    logger.info("  [OK] Cleaned up")

    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETED SUCCESSFULLY")
    logger.info("="*80)


if __name__ == "__main__":
    try:
        asyncio.run(test_session_context_performance())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nTest failed: {type(e).__name__}: {e}", exc_info=True)
        sys.exit(1)
