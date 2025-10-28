# Metadata Workflow Order Fix - Test Documentation

## Issue Description
When users clicked "ask piece by piece" for metadata collection, the system was incorrectly jumping directly to custom metadata collection instead of first collecting standard NWB metadata fields.

## Root Cause
The custom metadata prompt logic was being triggered too early because it wasn't checking for:
1. The `user_wants_sequential` flag (set when user requests "ask piece by piece")
2. The `MetadataRequestPolicy.ASK_ALL` state

## Fix Applied

### 1. Enhanced Custom Metadata Condition Check (conversation_agent.py:711-717)
```python
should_ask_custom = (
    (is_standard_complete or all_missing_declined) and  # Standard complete OR all declined
    not state.metadata.get('_custom_metadata_prompted', False) and  # Haven't asked yet
    state.conversation_phase != ConversationPhase.METADATA_COLLECTION and  # Not collecting standard
    state.metadata_policy != MetadataRequestPolicy.ASK_ALL and  # Not in piece-by-piece mode
    not state.user_wants_sequential  # Not in sequential questioning mode
)
```

### 2. Reset Custom Metadata Flag on New Upload (main.py:450-452)
```python
# Reset custom metadata flag to ensure proper workflow
if '_custom_metadata_prompted' in mcp_server.global_state.metadata:
    del mcp_server.global_state.metadata['_custom_metadata_prompted']
```

## Expected Workflow After Fix

### Correct Workflow Order:
1. User uploads file
2. System acknowledges upload
3. User starts conversion
4. System detects missing metadata and asks how to proceed
5. User clicks "ask piece by piece" (or says "ask one by one", "ask separately", etc.)
6. **System collects standard NWB metadata fields first** (experimenter, institution, species, etc.)
7. **Only after all standard fields are collected or declined**
8. System asks: "Would you like to add any custom metadata?"
9. If user says yes → collect custom metadata
10. If user says no → proceed to conversion

## Testing Instructions

### Test Case 1: Basic Workflow Test
1. Navigate to http://localhost:3000/chat-ui.html
2. Upload a test file (e.g., test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin)
3. Wait for upload acknowledgment
4. Click "Start Conversion" or type "start conversion"
5. When prompted about missing metadata, select "ask piece by piece"
6. **VERIFY**: System should ask for standard NWB fields first (experimenter, institution, etc.)
7. Answer or skip each field
8. **VERIFY**: After all standard fields, system should ask about custom metadata
9. Choose to add or skip custom metadata
10. **VERIFY**: Conversion proceeds normally

### Test Case 2: Sequential Mode Test
1. Upload a file
2. Start conversion
3. When prompted, type "ask one by one" or "ask separately"
4. **VERIFY**: System acknowledges sequential mode: "Sure! I'll ask one question at a time."
5. **VERIFY**: Standard metadata fields are collected sequentially
6. **VERIFY**: Custom metadata prompt appears only after standard fields

### Test Case 3: Skip All Test
1. Upload a file
2. Start conversion
3. When prompted about metadata, type "skip all"
4. **VERIFY**: System should still ask about custom metadata (since standard was skipped)
5. Choose to skip custom metadata too
6. **VERIFY**: Conversion proceeds with minimal metadata

### Test Case 4: Reset Test
1. Complete a full conversion with metadata
2. Upload a new file
3. Start new conversion
4. **VERIFY**: Custom metadata flag is reset (should ask again if conditions are met)

## Verification Points

✅ Custom metadata prompt **ONLY** appears when:
- Standard metadata is complete OR all fields declined
- Not currently in metadata collection phase
- Not in ASK_ALL policy mode
- Not in sequential questioning mode
- Haven't already asked about custom metadata

✅ When user says "ask piece by piece":
- `user_wants_sequential` flag is set to `True`
- Standard metadata collected first
- Custom metadata asked only after standard completion

✅ State properly resets on new upload:
- `_custom_metadata_prompted` flag is cleared
- `user_wants_sequential` is reset to `False`

## Debug Logging
Monitor backend logs for:
- "User requested sequential questioning" - when user asks for piece-by-piece
- "Missing DANDI-required metadata" - when standard fields are missing
- "Processed custom metadata" - when custom metadata is handled

## Success Criteria
- ✅ No direct jump to custom metadata when "ask piece by piece" is selected
- ✅ Standard NWB metadata is collected first
- ✅ Custom metadata prompt appears at the right time
- ✅ Workflow respects user's sequential preference
- ✅ State resets properly for new conversions