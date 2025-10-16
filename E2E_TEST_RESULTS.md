# End-to-End Workflow Test Results
## Frontend Perspective - Three-Agent Architecture

**Test Date:** 2025-10-20
**Test Type:** Complete workflow from user upload → validation
**Status:** ❌ CRITICAL BUG IDENTIFIED - Agent 1 → Agent 2 Handoff Failing

---

## Executive Summary

The E2E test revealed a **CRITICAL workflow blocker**: After metadata extraction, the system never triggers the Conversation Agent → Conversion Agent handoff, leaving users stuck in `awaiting_user_input` status indefinitely.

### Test Flow

```
✓ Step 1: File Upload         - PASSED
✓ Step 2: Start Conversion     - PASSED
✓ Step 3: Metadata Request     - PASSED (conversation_type: required_metadata)
✓ Step 4: Metadata Extraction  - PASSED (8 fields extracted)
⏳ Step 5: User Confirmation   - SENT ("I'm ready to proceed")
❌ Step 6: Agent Handoff       - FAILED (status stuck at awaiting_user_input)
❌ Step 7: Conversion          - NEVER REACHED
❌ Step 8: Validation          - NEVER REACHED
```

---

## Detailed Test Results

### Step 1: File Upload ✓
**Action:** User uploads `Noise4Sam_g0_t0.imec0.ap.bin` (SpikeGLX format)
**Expected:** File accepted, path stored
**Actual:** ✓ File uploaded successfully
**Verification:**
```json
{
  "status": "upload_acknowledged",
  "input_path": "/var/folders/.../Noise4Sam_g0_t0.imec0.ap.bin",
  "uploaded_files": ["Noise4Sam_g0_t0.imec0.ap.bin"]
}
```

### Step 2: Start Conversion ✓
**Action:** User clicks "Start Conversion" button
**Expected:** Conversation Agent activates metadata collection
**Actual:** ✓ Workflow started, metadata request triggered
**Verification:**
```json
{
  "status": "awaiting_user_input",
  "conversation_type": "required_metadata"
}
```

###Step 3: Metadata Extraction ✓
**Action:** User provides metadata via chat:
> "Dr Jane Smith from MIT, male mouse age P60 ID mouse001, visual cortex recording"

**Expected:** LLM extracts structured metadata
**Actual:** ✓ Successfully extracted 8 metadata fields
**Extracted Metadata:**
```json
{
  "experimenter": ["Smith, Jane"],
  "institution": "Massachusetts Institute of Technology",
  "subject_id": "mouse001",
  "species": "Mus musculus",
  "sex": "M",
  "age": "P60D",
  "experiment_description": "Visual cortex recording",
  "keywords": ["electrophysiology", "visual cortex", "mouse"]
}
```
**Response:** `needs_more_info: True` (expected - waiting for user confirmation)

### Step 4: User Confirmation ⚠️
**Action:** User sends explicit confirmation:
> "Yes, I'm ready to start the conversion now. Please proceed."

**Expected:**
- LLM sets `ready_to_proceed: true`
- Metadata persisted to state
- Status changes to `converting`
- Conversion Agent receives handoff message

**Actual:** ❌ **CHAT RESPONSE COMPLETELY EMPTY**
```json
{
  "ready_to_proceed": "NOT SET",
  "message": "",
  "status": "N/A",
  "needs_more_info": "N/A"
}
```

**State After 60+ seconds:**
```json
{
  "status": "awaiting_user_input",
  "conversation_type": "required_metadata",
  "metadata": {},  // ← EMPTY! Extracted metadata NOT persisted
  "user_provided_metadata": {},
  "auto_extracted_metadata": {}
}
```

### Step 5: Agent Handoff ❌ FAILED
**Expected:** Conversation Agent → Conversion Agent handoff within 10-30 seconds
**Actual:** System stuck in `awaiting_user_input` for 200+ seconds
**Monitoring Log:**
```
[5s]   Status: awaiting_user_input
[10s]  Status: awaiting_user_input
[15s]  Status: awaiting_user_input
...
[200s] Status: awaiting_user_input  ← STUCK
```

### Final State - What User Sees
```json
{
  "status": "awaiting_user_input",
  "conversation_phase": null,
  "overall_status": null,
  "correction_attempt": 0,
  "can_retry": true,
  "validation_result": null
}
```

**Frontend UI State:**
- ✓ AGENT 1 (Conversation) appears active
- ❌ AGENT 2 (Conversion) never activates
- ❌ AGENT 3 (Evaluation) never reached
- ⚠️ User sees "waiting" state indefinitely

---

## Root Cause Analysis

### Primary Issue: LLM Call Failing Silently

**Evidence:**
1. Chat API returns completely empty response (no message, no status, no fields)
2. Metadata extracted in first chat but NOT persisted to state
3. Second chat (confirmation) produces zero output
4. No error messages visible to user or in API responses

**Possible Causes:**

#### 1. LLM Service Timeout/Failure
```python
# In conversation_agent.py lines 2416-2426
if response.get("ready_to_proceed", False):
    extracted_metadata = response.get("extracted_metadata", {})
    if extracted_metadata:
        state.user_provided_metadata.update(extracted_metadata)
        state.metadata = combined_metadata
```

**Problem:** If LLM call fails/times out:
- `response` is empty dict
- `ready_to_proceed` is never True
- Metadata never persisted
- No error surfaced to user

#### 2. Missing Error Handling
```python
# Current code in main.py /api/chat endpoint
async def chat_message(message: str = Form(...)):
    chat_msg = MCPMessage(...)
    response = await mcp_server.send_message(chat_msg)
    return response  # ← If response is {}, user gets nothing
```

**Missing:**
- Try/except around LLM calls
- Timeout handling
- Fallback error messages
- Logging of failures

#### 3. State Persistence Gap
Even when metadata IS extracted (first chat), it's only returned in API response but NOT persisted because:
```python
# Only persists if ready_to_proceed=True AND extracted_metadata non-empty
if response.get("ready_to_proceed", False):
    if extracted_metadata:  # ← This prevents incremental metadata collection
        state.user_provided_metadata.update(extracted_metadata)
```

---

## Three-Agent Communication Breakdown

### Expected Flow:
```
User Upload
    ↓
[AGENT 1: Conversation] - Metadata Collection
    ├─ Request metadata
    ├─ Extract metadata from user input
    ├─ Set ready_to_proceed=true
    └─ Send MCPMessage(target="conversion", action="start_conversion")
         ↓
[AGENT 2: Conversion] - File Processing
    ├─ Detect format
    ├─ Convert to NWB
    └─ Send MCPMessage(target="evaluation", action="validate_nwb")
         ↓
[AGENT 3: Evaluation] - Validation
    ├─ Run NWB Inspector
    ├─ Analyze issues
    └─ Return validation result to user
```

### Actual Flow (Current Bug):
```
User Upload
    ↓
[AGENT 1: Conversation]
    ├─ Request metadata ✓
    ├─ Extract metadata ✓ (but not persisted)
    ├─ User confirms ready ✓
    ├─ LLM call fails silently ❌
    ├─ ready_to_proceed never set ❌
    └─ STUCK IN LOOP ❌
```

**Handoff Never Happens** → Agents 2 & 3 never activate

---

## User Experience Impact

### What User Sees:
1. ✓ File uploads successfully
2. ✓ System asks for metadata
3. ✓ User provides metadata, sees it extracted
4. ✓ User says "I'm ready"
5. ⏳ **Nothing happens** - UI shows "waiting" indefinitely
6. ❌ No error message
7. ❌ No progress indication
8. ❌ No way to proceed

### Confusion Points:
- "Did my message send?"
- "Is the system processing?"
- "Should I wait longer?"
- "Did I say the wrong thing?"
- **User has NO feedback that something went wrong**

---

## Required Fixes

### 1. CRITICAL: Add LLM Error Handling (PRIORITY 1)

**File:** `backend/src/api/main.py`
**Location:** `/api/chat` endpoint (around line 709)

```python
@app.post("/api/chat")
async def chat_message(message: str = Form(...)):
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # Edge Case Fix #1: LLM processing guard
    if state.llm_processing:
        return {
            "message": "I'm still processing your previous message. Please wait...",
            "status": "busy",
            "needs_more_info": False,
        }

    async with state._llm_lock:
        state.llm_processing = True
        try:
            chat_msg = MCPMessage(
                target_agent="conversation",
                action="conversational_response",
                context={"message": message},
            )

            # ADD TIMEOUT AND ERROR HANDLING
            response = await asyncio.wait_for(
                mcp_server.send_message(chat_msg),
                timeout=120.0  # 2 minute timeout
            )

            # VALIDATE RESPONSE
            if not response or not isinstance(response, dict):
                raise ValueError("Empty or invalid LLM response")

            # CHECK FOR ERROR IN RESPONSE
            if response.get("error"):
                raise RuntimeError(f"LLM error: {response['error']}")

            return response

        except asyncio.TimeoutError:
            state.add_log(LogLevel.ERROR, "LLM call timed out", {"message": message})
            return {
                "message": "I'm sorry, that request took too long to process. Please try rephrasing your message or contact support if this persists.",
                "status": "error",
                "error": "timeout",
                "needs_more_info": True,
            }
        except Exception as e:
            state.add_log(LogLevel.ERROR, f"Chat error: {str(e)}", {"message": message})
            return {
                "message": f"I encountered an error processing your message: {str(e)}. Please try again.",
                "status": "error",
                "error": str(e),
                "needs_more_info": True,
            }
        finally:
            state.llm_processing = False
```

### 2. CRITICAL: Incremental Metadata Persistence (PRIORITY 2)

**File:** `backend/src/agents/conversation_agent.py`
**Location:** `_handle_conversational_response` method (around line 2416)

```python
# CURRENT (BROKEN):
if response.get("ready_to_proceed", False):
    extracted_metadata = response.get("extracted_metadata", {})
    if extracted_metadata:  # ← Only saves if ready AND has metadata
        state.user_provided_metadata.update(extracted_metadata)

# FIX - Save metadata incrementally:
extracted_metadata = response.get("extracted_metadata", {})

# ALWAYS persist extracted metadata, even if not ready to proceed
if extracted_metadata:
    state.user_provided_metadata.update(extracted_metadata)
    combined_metadata = {**state.auto_extracted_metadata, **state.user_provided_metadata}
    state.metadata = combined_metadata
    state.add_log(
        LogLevel.INFO,
        "Metadata extracted and persisted",
        {"fields": list(extracted_metadata.keys())}
    )

# THEN check if ready to proceed
if response.get("ready_to_proceed", False):
    state.add_log(LogLevel.INFO, "User ready to proceed with conversion")
    # Trigger conversion...
```

### 3. Add User-Facing Error Messages (PRIORITY 3)

**File:** `backend/src/agents/conversational_handler.py`
**Location:** LLM call sites

```python
async def process_conversational_response(self, ...):
    try:
        llm_response = await self._llm_service.generate_response(...)

        # Validate LLM response has required fields
        if not llm_response.get("message"):
            logger.error("LLM returned empty message")
            return {
                "message": "I'm having trouble formulating a response. Could you please rephrase that?",
                "needs_more_info": True,
                "ready_to_proceed": False,
            }

        return llm_response

    except Exception as e:
        logger.error(f"LLM error: {str(e)}")
        return {
            "message": "I encountered a technical issue. Please try again in a moment.",
            "error": str(e),
            "needs_more_info": True,
            "ready_to_proceed": False,
        }
```

### 4. Add Workflow State Logging (PRIORITY 4)

Add detailed logging to track agent handoffs:

```python
# In conversation_agent.py
state.add_log(LogLevel.INFO, "Triggering Agent 1 → Agent 2 handoff", {
    "metadata_fields": len(state.metadata),
    "input_path": state.input_path,
})

# In conversion_agent.py
state.add_log(LogLevel.INFO, "Agent 2 received conversion request", {
    "from_agent": "conversation",
    "file_format": detected_format,
})

# In evaluation_agent.py
state.add_log(LogLevel.INFO, "Agent 3 starting validation", {
    "nwb_file": nwb_path,
})
```

---

## Testing Recommendations

### 1. Unit Tests for Error Cases
```python
@pytest.mark.asyncio
async def test_chat_handles_llm_timeout():
    """Test chat endpoint gracefully handles LLM timeouts."""
    # Mock LLM to timeout
    with patch('llm_service.generate_response', side_effect=asyncio.TimeoutError):
        response = await client.post("/api/chat", data={"message": "test"})
        assert response["status"] == "error"
        assert "too long" in response["message"].lower()

@pytest.mark.asyncio
async def test_chat_handles_empty_llm_response():
    """Test chat endpoint validates LLM responses."""
    with patch('llm_service.generate_response', return_value={}):
        response = await client.post("/api/chat", data={"message": "test"})
        assert response["status"] == "error"
        assert response["message"]  # Has user-facing error message
```

### 2. Integration Test for Full Workflow
```bash
# Test complete Agent 1 → 2 → 3 flow
./tests/test_three_agent_handoff.sh
```

### 3. Manual Testing Checklist
- [ ] Upload file
- [ ] Provide metadata
- [ ] Confirm ready
- [ ] Verify status changes to `converting` within 30s
- [ ] Verify conversion completes
- [ ] Verify validation runs
- [ ] Test with LLM API disabled (error handling)
- [ ] Test with invalid metadata
- [ ] Test with incomplete metadata

---

## Immediate Next Steps

1. **Apply Fix #1** (LLM error handling) - 15 minutes
2. **Apply Fix #2** (incremental metadata persistence) - 10 minutes
3. **Test manually** - Upload → metadata → confirm → verify handoff - 5 minutes
4. **If working:** Run full E2E test - 10 minutes
5. **Document** any remaining issues

**Total Time Estimate:** 40 minutes to production-ready workflow

---

## Success Criteria

The workflow will be considered FIXED when:

1. ✅ User provides metadata → metadata persists to state immediately
2. ✅ User confirms ready → status changes to `converting` within 30 seconds
3. ✅ Conversion Agent processes file → status changes to `validating`
4. ✅ Evaluation Agent validates NWB → validation_result populated
5. ✅ If ANY step fails → user sees clear error message
6. ✅ E2E test completes all 9 steps without manual intervention

---

## Conclusion

**Current Status:** System is **NOT production-ready** due to critical Agent 1 → Agent 2 handoff failure.

**Impact:** **100% of users** attempting conversions will be stuck after metadata collection.

**Severity:** **P0 - Blocker**

**Fix Complexity:** **Medium** (40 minutes, 4 code changes, well-understood root cause)

**Recommendation:** **Apply fixes immediately** before any user testing.

The good news: The three-agent architecture is sound, metadata extraction works, and the fixes are straightforward error handling improvements rather than architectural changes.
