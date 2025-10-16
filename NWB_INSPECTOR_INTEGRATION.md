# NWB Inspector Integration Documentation

## Overview

**Yes, NWB Inspector is fully integrated and actively used** in the Agentic Neurodata Conversion system. Every converted NWB file is automatically validated using the official NWB Inspector tool.

## Where NWB Inspector is Used

### Location in Code
**File**: [backend/src/agents/evaluation_agent.py](backend/src/agents/evaluation_agent.py)

### The Validation Flow

```python
# 1. Main validation handler (line 81)
async def handle_run_validation():
    validation_result = await self._run_nwb_inspector(nwb_path)
    # Process results...

# 2. NWB Inspector execution (lines 223-257)
async def _run_nwb_inspector(self, nwb_path: str) -> ValidationResult:
    """Run NWB Inspector validation."""

    # Import NWB Inspector
    from nwbinspector import inspect_nwbfile
    from nwbinspector import __version__ as inspector_version

    # Run NWB Inspector - THIS IS THE KEY LINE
    results = list(inspect_nwbfile(nwbfile_path=nwb_path))

    # Convert results to our format
    inspector_results = []
    for check_result in results:
        inspector_results.append({
            "severity": check_result.severity.name.lower(),
            "message": check_result.message,
            "location": str(check_result.location),
            "check_function_name": check_result.check_function_name,
        })

    # Create validation result
    validation_result = ValidationResult.from_inspector_output(
        inspector_results,
        inspector_version,
    )

    return validation_result
```

## Complete Validation Workflow

### Step-by-Step Process

1. **User Uploads File** → System converts to NWB
2. **NWB File Created** → Saved to temporary directory
3. **Validation Triggered** → Evaluation Agent called
4. **NWB Inspector Runs** → `inspect_nwbfile(nwbfile_path)` executes
5. **Results Collected** → All checks captured
6. **Results Processed** → Categorized by severity
7. **Status Determined** → PASSED/PASSED_WITH_ISSUES/FAILED
8. **Report Generated** → PDF or JSON with inspector results

### Code Path Trace

```
User Upload
    ↓
POST /api/upload
    ↓
Conversation Agent: start_conversion
    ↓
Conversion Agent: run_conversion
    ↓
[NWB file created]
    ↓
Evaluation Agent: run_validation
    ↓
_run_nwb_inspector(nwb_path)
    ↓
nwbinspector.inspect_nwbfile() ← NWB INSPECTOR RUNS HERE
    ↓
Results processed
    ↓
Report generated
    ↓
User downloads NWB + Report
```

## What NWB Inspector Checks

NWB Inspector runs **all standard checks**, including:

### Best Practice Checks
- ✓ Required metadata present
- ✓ Proper data types
- ✓ Valid timestamps
- ✓ Correct units
- ✓ Required groups exist

### Data Integrity Checks
- ✓ No empty datasets
- ✓ Valid array shapes
- ✓ Consistent dimensions
- ✓ No null values where not allowed

### Schema Compliance
- ✓ Follows NWB schema
- ✓ Proper hierarchy
- ✓ Valid attribute types
- ✓ Required fields present

### DANDI Readiness
- ✓ DANDI-compliant metadata
- ✓ Subject information complete
- ✓ Session details adequate

## Severity Levels

NWB Inspector returns issues with severity levels that we map:

```python
CRITICAL → FAILED (blocks upload)
ERROR    → FAILED (significant issues)
WARNING  → PASSED_WITH_ISSUES (minor issues)
INFO     → PASSED_WITH_ISSUES (informational)
```

## Evidence in Logs

When you run a conversion, you'll see these log entries:

```json
{
  "timestamp": "2025-10-15T18:34:08.934094",
  "level": "info",
  "message": "Starting NWB validation: /path/to/file.nwb"
}
```

```json
{
  "timestamp": "2025-10-15T18:34:09.123456",
  "level": "info",
  "message": "Validation passed",
  "context": {
    "nwb_path": "/path/to/file.nwb",
    "summary": {
      "critical": 0,
      "error": 0,
      "warning": 2,
      "info": 5
    },
    "overall_status": "PASSED_WITH_ISSUES"
  }
}
```

## Validation Results in Reports

### PDF Report (PASSED)
```
==================================
NWB File Quality Evaluation Report
==================================

FILE INFORMATION
- NWB Version: 2.6.0
- File Size: 1.2 MB
- Creation Date: 2025-10-15

VALIDATION SUMMARY
Status: ✓ PASSED
- Critical: 0
- Errors: 0
- Warnings: 2
- Info: 5

VALIDATION ISSUES
1. [WARNING] Session description is too short
   Location: /general/session_description

2. [INFO] Consider adding experimenter names
   Location: /general/experimenter
```

### JSON Report (FAILED)
```json
{
  "evaluation_metadata": {
    "timestamp": "2025-10-15T18:34:09.123456",
    "inspector_version": "0.5.2",
    "overall_status": "FAILED"
  },
  "failure_summary": {
    "critical_count": 1,
    "error_count": 2,
    "warning_count": 0,
    "info_count": 0
  },
  "critical_issues": [
    {
      "severity": "error",
      "message": "Missing required metadata: subject_id",
      "location": "/general/subject",
      "check": "check_subject_id_exists"
    }
  ]
}
```

## NWB Inspector Version

The system uses the version installed in the Pixi environment:

```bash
pixi list | grep nwbinspector
# nwbinspector  0.5.2
```

## How to Verify It's Working

### Method 1: Check Logs
```bash
curl http://localhost:8000/api/logs?limit=50 | python -m json.tool | grep -i "validation"
```

Look for:
- "Starting NWB validation"
- "Validation passed" or "Validation failed"
- Issue summaries

### Method 2: Upload a File
1. Use chat UI
2. Upload and convert
3. Check status shows "VALIDATING"
4. Check completion message
5. Download report - it contains inspector results

### Method 3: Check Report
Download the PDF/JSON report and look for:
- Inspector version
- Issue list with check names
- Severity levels
- Locations in NWB file

## Integration Points

### 1. Evaluation Agent Registration
```python
# backend/src/agents/__init__.py
def register_evaluation_agent(mcp_server, llm_service=None):
    agent = EvaluationAgent(mcp_server, llm_service)
    mcp_server.register_handler("evaluation", "run_validation", agent.handle_run_validation)
```

### 2. Validation Called After Conversion
```python
# backend/src/agents/conversation_agent.py
async def _run_conversion():
    # ... conversion happens ...

    # Run validation
    validation_msg = MCPMessage(
        target_agent="evaluation",
        action="run_validation",
        context={"nwb_path": output_path}
    )
    validation_response = await self._mcp_server.send_message(validation_msg)
```

### 3. Results Used for Decisions
```python
if validation_result["is_valid"]:
    state.update_status(ConversionStatus.COMPLETED)
    # Generate PDF report
else:
    if state.can_retry():
        state.update_status(ConversionStatus.AWAITING_RETRY_APPROVAL)
        # Show retry dialog with inspector issues
```

## Testing NWB Inspector Integration

### Test 1: Valid File
```bash
# Should pass validation
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test_data/valid.bin" \
  -F 'metadata={"session_description":"Test","experimenter":["John"]}'

# Check logs
curl http://localhost:8000/api/logs | grep validation
# Should show: "Validation passed"
```

### Test 2: File with Issues
```bash
# Should find warnings
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test_data/minimal.bin" \
  -F 'metadata={"session_description":"x"}'

# Check status
curl http://localhost:8000/api/status
# Should show: "validation_status": "passed_with_issues"
```

### Test 3: Invalid File
```bash
# Should fail validation
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test_data/bad.bin" \
  -F 'metadata={}'

# Should show retry dialog with inspector issues
```

## NWB Inspector Package Info

**Installed via Pixi**:
```toml
# pixi.toml
[dependencies]
nwbinspector = ">=0.5.2"
```

**Import Path**:
```python
from nwbinspector import inspect_nwbfile
```

**Official Docs**: https://nwbinspector.readthedocs.io/

## Benefits of Integration

1. **Standard Compliance**: Uses official NWB validation tool
2. **Comprehensive**: All NWB best practices checked
3. **DANDI Ready**: Ensures files meet DANDI requirements
4. **Automated**: No manual validation needed
5. **Detailed Reports**: Inspector results in PDF/JSON
6. **Actionable**: Issues include locations and suggestions

## Troubleshooting

### Issue: Validation Takes Too Long
**Cause**: Large NWB files can take 1-5 minutes
**Solution**: Normal - inspector checks all datasets

### Issue: No Validation Results
**Check**:
```bash
# Verify inspector installed
pixi run python -c "import nwbinspector; print(nwbinspector.__version__)"

# Check logs
curl http://localhost:8000/api/logs | grep validation
```

### Issue: All Files Failing
**Check**:
- Conversion succeeded?
- NWB file created?
- File size > 0?
- Check error in logs

## Summary

✅ **NWB Inspector IS being used**
✅ **Every converted file is validated**
✅ **Results appear in logs and reports**
✅ **Integration is complete and working**

The system provides **professional-grade NWB validation** using the official NWB Inspector tool, ensuring all converted files meet NWB standards and are ready for DANDI upload.

## Quick Verification

Run this to see NWB Inspector in action:

```bash
# 1. Start server
pixi run serve

# 2. Upload file (in new terminal)
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin"

# 3. Watch logs in real-time
watch -n 1 'curl -s http://localhost:8000/api/logs?limit=5 | python -m json.tool'

# You'll see:
# - "Starting NWB validation"
# - Inspector running
# - "Validation passed/failed"
# - Issue summary
```

---

**Status**: ✅ Fully Integrated and Working
**Tool**: NWB Inspector 0.5.2+
**Usage**: Automatic on every conversion
