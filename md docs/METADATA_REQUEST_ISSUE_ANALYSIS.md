# Metadata Request Issue: Fixed Template vs. File-Based Questions

## Issue Description

**User Report**: "even when i changed the input bin file it asked for same information. is that question fixed? shouldn't it be dependent on llm analysis of input file?"

**Actual Behavior**: The system asks the same 3 DANDI metadata questions for EVERY file, regardless of:
- What file is uploaded
- What metadata is already in the file
- What the file format is
- What the LLM inference engine discovered

**Expected Behavior**: The metadata request should be DYNAMIC:
- Analyze the uploaded file first
- Check what metadata already exists
- Only ask for what's MISSING
- Tailor questions to the specific file and format

## Root Cause Analysis

### What Currently Happens

#### Step 1: File Analysis (WORKING)
File: `backend/src/agents/conversation_agent.py`, lines 135-186

```python
# Step 1.5: Intelligent Metadata Inference from File
if self._metadata_inference_engine:
    inference_result = await self._metadata_inference_engine.infer_metadata(
        input_path=input_path,
        state=state,
    )

    inferred_metadata = inference_result.get("inferred_metadata", {})
    confidence_scores = inference_result.get("confidence_scores", {})

    # Pre-fill metadata with high-confidence inferences (>= 80% confidence)
    high_confidence_inferences = {
        key: value
        for key, value in inferred_metadata.items()
        if confidence_scores.get(key, 0) >= 80
    }

    # Update state with inferred metadata
    state.metadata.update(metadata)
```

**This works**: The system successfully analyzes files and extracts metadata.

From `backend/src/agents/metadata_inference.py`, the inference engine:
- Extracts technical metadata (sampling rate, channels, duration) - lines 116-150
- Applies heuristic rules (species from filename, brain regions) - lines 204-263
- Uses LLM to infer experiment type, description, keywords - lines 265-371
- Provides confidence scores for each inference

#### Step 2: Fixed Template (PROBLEM)
File: `backend/src/agents/conversation_agent.py`, lines 187-281

```python
# Step 1.6: Check for DANDI-required metadata BEFORE conversion
if self._conversational_handler:
    # Check if we have the 3 essential DANDI fields
    required_fields = {
        "experimenter": metadata.get("experimenter"),
        "institution": metadata.get("institution"),
        "experiment_description": metadata.get("experiment_description") or metadata.get("session_description"),
    }

    # Filter out fields the user already declined
    missing_fields = [
        field for field, value in required_fields.items()
        if not value and field not in state.user_declined_fields
    ]

    if missing_fields and state.metadata_requests_count < 1 and not state.user_wants_minimal:
        # Generate FIXED message asking for required metadata
        message_text = f"""🔴 **Critical Information Needed**

To create a DANDI-compatible NWB file, I need 3 essential fields:

• **Experimenter Name(s)**: Required by DANDI for attribution and reproducibility
Example: ["Dr. Jane Smith", "Dr. John Doe"]

• **Experiment Description**: Required by DANDI to help others understand your data
Example: Recording of neural activity in mouse V1 during visual stimulation

• **Institution**: Required by DANDI for institutional affiliation
Example: University of California, Berkeley

**How would you like to proceed?**
• Provide all at once (e.g., "Dr. Smith, MIT, recording neural activity")
• Answer one by one (say "ask one by one")
• Skip for now (file won't be DANDI-compatible)"""
```

**The Problem**:
1. The template is HARDCODED and never changes
2. It asks for the same 3 fields regardless of what was inferred
3. It doesn't reference file-specific context (e.g., "I detected this is a SpikeGLX recording from a Neuropixels probe...")
4. It doesn't acknowledge what WAS successfully inferred (e.g., "I found that this is from a mouse V1 recording, but I still need...")

### Why This Happens

The code has two separate phases:
1. **Inference Phase**: Analyzes file and infers metadata → Pre-fills `state.metadata`
2. **Request Phase**: Checks which REQUIRED fields are missing → Shows FIXED template

The REQUEST phase only checks IF fields are missing, not:
- WHY they're missing (inference failed vs. never in file)
- WHAT context was learned from the file
- WHAT the user should know about their specific file

## Impact

### User Experience Issues

1. **Repetitive**: Same questions for every file, feels robotic
2. **Ignores Context**: Doesn't acknowledge what was learned from file analysis
3. **No Personalization**: Generic template doesn't reference file-specific details
4. **Cognitive Disconnect**: User uploaded a file → system analyzed it → but questions don't reflect that analysis

### Example Scenarios

#### Scenario 1: SpikeGLX Recording
**File**: `Noise4Sam_g0_t0.imec0.ap.bin`

**What System Knows** (from inference):
- Format: SpikeGLX
- Probe: Neuropixels
- Data stream: Action potentials (AP)
- Sampling rate: 30000 Hz
- Species: Possibly mouse (inferred from filename pattern)

**What System Asks** (current):
> 🔴 **Critical Information Needed**
>
> To create a DANDI-compatible NWB file, I need 3 essential fields...

**What System SHOULD Ask**:
> 🔍 **File Analysis Complete**
>
> I've analyzed your SpikeGLX recording (`Noise4Sam_g0_t0.imec0.ap.bin`):
> - Neuropixels probe recording at 30kHz
> - Action potential (AP) data stream
> - Possibly from mouse (based on filename)
>
> To create a DANDI-compatible file, I need a few more details:
>
> • **Experimenter**: Who conducted this recording?
> • **Institution**: Where was this recorded?
> • **Experiment Description**: What was the purpose? (e.g., "Neural activity in V1 during visual stimulation")

#### Scenario 2: File with Metadata Already Present
**File**: `recording_smith_mit_2024.nwb` (hypothetical example with embedded metadata)

**What System Knows**:
- Experimenter: Dr. Smith (extracted from filename or file metadata)
- Institution: MIT (extracted from filename)

**What System Asks** (current):
> 🔴 **Critical Information Needed**
>
> [Same fixed template asking for ALL 3 fields]

**What System SHOULD Ask**:
> ✅ **Metadata Detected**
>
> I found some information in your file:
> - Experimenter: Dr. Smith ✓
> - Institution: MIT ✓
>
> I just need one more detail:
> • **Experiment Description**: What was the purpose of this recording?

## Solution Design

### Option 1: Dynamic Template Generation (Recommended)

**Approach**: Use LLM to generate custom questions based on inference results

**Changes Required**:

1. **New Function**: `_generate_dynamic_metadata_request()`

```python
async def _generate_dynamic_metadata_request(
    self,
    missing_fields: List[str],
    inference_result: Dict[str, Any],
    file_info: Dict[str, Any],
    state: GlobalState,
) -> str:
    """
    Generate dynamic metadata request based on file analysis.

    Args:
        missing_fields: List of required fields that are missing
        inference_result: Results from metadata inference engine
        file_info: Basic file information (name, format, size)
        state: Global state

    Returns:
        Customized message asking for missing metadata
    """
    system_prompt = """You are a friendly NWB conversion assistant.

Generate a personalized metadata request that:
1. Acknowledges what was learned from file analysis
2. Shows you analyzed the specific file
3. Only asks for what's actually missing
4. Uses file-specific context in examples
5. Keeps a warm, conversational tone"""

    inferred_metadata = inference_result.get("inferred_metadata", {})
    confidence_scores = inference_result.get("confidence_scores", {})

    user_prompt = f"""Generate a metadata request message.

**File Information:**
- Name: {file_info['name']}
- Format: {file_info['format']}
- Size: {file_info['size_mb']} MB

**What We Inferred:**
{json.dumps(inferred_metadata, indent=2)}

**Confidence Scores:**
{json.dumps(confidence_scores, indent=2)}

**Still Missing (need to ask user):**
{missing_fields}

Create a friendly message that:
1. Summarizes what you learned from the file
2. Asks ONLY for the missing fields
3. Uses file-specific context
4. Provides relevant examples based on the file type"""

    # Use LLM to generate custom message
    response = await self._llm_service.generate_structured_output(
        prompt=user_prompt,
        output_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "suggested_defaults": {"type": "object"}
            }
        },
        system_prompt=system_prompt,
    )

    return response.get("message")
```

2. **Update Request Logic** (lines 187-281):

Replace the fixed template with:

```python
if missing_fields and state.metadata_requests_count < 1:
    # Generate DYNAMIC message based on file analysis
    message_text = await self._generate_dynamic_metadata_request(
        missing_fields=missing_fields,
        inference_result=state.metadata.get("_inference_result", {}),
        file_info={
            "name": Path(input_path).name,
            "format": format_name,
            "size_mb": Path(input_path).stat().st_size / (1024 * 1024),
        },
        state=state,
    )
```

### Option 2: Template Variables (Simpler but Less Flexible)

**Approach**: Use a template with variables filled from inference results

**Example**:

```python
# Build context from inference
inferred_summary = []
if inference_result.get("inferred_metadata"):
    if inference_result["inferred_metadata"].get("species"):
        inferred_summary.append(f"Species: {inference_result['inferred_metadata']['species']}")
    if inference_result["inferred_metadata"].get("brain_region"):
        inferred_summary.append(f"Brain region: {inference_result['inferred_metadata']['brain_region']}")

message_text = f"""🔍 **File Analysis Complete**

I've analyzed your {format_name} file: `{Path(input_path).name}`

**What I found:**
{chr(10).join(f"• {item}" for item in inferred_summary) if inferred_summary else "• Basic file structure validated"}

**What I still need:**
{chr(10).join(f"• **{field.replace('_', ' ').title()}**: [helpful description]" for field in missing_fields)}

Please provide the missing information, or say "skip" to proceed with minimal metadata."""
```

## Recommendation

**Implement Option 1 (Dynamic Template Generation)** because:

1. **Fully Adaptive**: Questions change based on what's in each file
2. **Better UX**: Users see that the system actually analyzed their file
3. **Context-Aware**: Examples and language match the file type
4. **Professional**: Feels like talking to an AI assistant, not filling a form

**Benefits**:
- Each file gets personalized questions
- Users feel the system "understood" their file
- Reduces cognitive disconnect between upload → analysis → questions
- More engaging and less repetitive experience

**Estimated Effort**:
- Add new function: 2-3 hours
- Update request logic: 1 hour
- Testing with different file types: 2 hours
- **Total**: ~5-6 hours

## Testing Plan

After implementing, test with:

1. **Same file twice**: Verify questions are identical (deterministic)
2. **Different file formats**: Verify questions adapt (SpikeGLX vs OpenEphys)
3. **Files with partial metadata**: Verify only missing fields are requested
4. **Files with no metadata**: Verify all fields are requested with context
5. **Sequential uploads**: Verify each file gets its own custom request

## Files to Modify

1. `backend/src/agents/conversation_agent.py`
   - Add `_generate_dynamic_metadata_request()` function
   - Update lines 187-281 to use dynamic generation

2. `backend/tests/integration/test_conversion_workflow.py`
   - Add test for dynamic metadata request generation
   - Verify different files get different questions

## Related Issues

- User reported: "even when i changed the input bin file it asked for same information"
- This is the LAST major issue identified in the current session
- Fixing this will complete the UX improvements for metadata collection
