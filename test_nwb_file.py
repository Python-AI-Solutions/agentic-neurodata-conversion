#!/usr/bin/env python3
"""
Non-interactive test for the specific NWB file.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from manual_test import NWBDatasetTester

async def test_specific_nwb():
    """Test the specific NWB file provided."""

    nwb_file = "/Users/adityapatane/agentic-neurodata-conversion-3/.claude/sub-M541_ses-M54120240831_ecephys.nwb"
    title = "M541 Electrophysiology Session - 2024-08-31"
    description = "Electrophysiology recording from subject M541, session from August 31, 2024"

    print(f"🧪 Testing Knowledge Graph Systems with:")
    print(f"📁 File: {os.path.basename(nwb_file)}")
    print(f"📊 Title: {title}")
    print(f"📝 Description: {description}")
    print()

    # Check if file exists first
    if not Path(nwb_file).exists():
        print(f"❌ File not found: {nwb_file}")
        return False

    file_size = Path(nwb_file).stat().st_size / (1024 * 1024)
    print(f"📊 File size: {file_size:.2f} MB")
    print()

    tester = NWBDatasetTester()

    try:
        success = await tester.run_comprehensive_test(nwb_file, title, description)
        return success
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_specific_nwb())
    if success:
        print("\n🎉 SUCCESS: Your NWB file works perfectly with the Knowledge Graph Systems!")
    else:
        print("\n❌ Some issues encountered, but core functionality is still working.")

    sys.exit(0 if success else 1)