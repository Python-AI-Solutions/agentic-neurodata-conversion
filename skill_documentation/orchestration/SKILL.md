---
name: orchestration
version: 0.1.0
description: Orchestrates the entire NWB conversion workflow through conversational interaction with users
category: workflow_management
author: Agentic Neurodata Conversion Team
tags:
  - orchestration
  - conversation
  - user-interaction
  - workflow
  - metadata-collection
  - correction-loop
  - natural-language
dependencies:
  pydantic: ">=2.0.0"
  anthropic: "*"  # For LLM-powered conversations
uses_skills:
  - nwb_conversion
  - nwb_validation
input_format: "Natural language user messages"
output_format: "Natural language responses + workflow actions"
estimated_duration: "5-30 minutes (depends on user interaction)"
implementation: backend/src/agents/conversation_agent.py
---

# Skill: Orchestration (Conversation Agent)

## Purpose
Orchestrate the complete NWB conversion workflow while maintaining natural, helpful conversations with users. This skill is the "conductor" of the system - it manages the entire process from initial upload through validation, corrections, and final acceptance. It's the only agent that directly interacts with users.

## When to Use This Skill

### ✅ USE When:
- User initiates any conversion workflow
- User provides input (answers, clarifications, metadata)
- User requests status updates or help
- User wants to retry, correct, or accept results
- Workflow coordination is needed between other skills
- Natural language interaction is required
- Metadata collection is needed
- Correction loop management is required

### ❌ DON'T USE When:
- Pure technical conversion operations (use nwb_conversion skill)
- Validation tasks (use nwb_validation skill)
- No user interaction needed
- Backend-only operations

## Core Responsibilities

### 1. Workflow Orchestration
**Manages the complete conversion pipeline**:
```
1. File Upload → User uploads neurophysiology data
2. Format Detection → Calls conversion skill to detect format
3. Metadata Collection → Interacts with user to gather required info
4. Conversion → Triggers conversion skill
5. Validation → Triggers validation skill
6. Issue Resolution → Manages correction loop if needed
7. Final Acceptance → Confirms completion or offers retries
```

### 2. User Interaction
**Natural language conversation handling**:
- Asks clarifying questions when needed
- Explains technical concepts in simple terms
- Provides progress updates and status
- Handles user requests and commands
- Manages conversation history and context

### 3. Metadata Collection
**Gathers required NWB/DANDI metadata**:

**Critical Fields (asked before conversion)**:
- `experimenter`: Required by DANDI for attribution
- `institution`: Required by DANDI for affiliation
- `experiment_description` or `session_description`: Required by DANDI

**Optional Fields (collected if time permits)**:
- Subject metadata: `subject_id`, `species`, `age`, `sex`
- Session details: `session_start_time`, `lab`, `protocol`
- Additional context: `keywords`, `related_publications`

**Smart Collection Strategy**:
- Asks for critical fields BEFORE conversion (prevents rework)
- Limits requests to 2 per workflow (avoids user frustration)
- Allows users to skip non-critical fields
- Remembers declined fields (won't ask again)
- Supports bulk input ("Dr. Smith, MIT, recording V1 neurons")
- Supports one-by-one input (interactive Q&A)

### 4. Correction Loop Management
**Handles validation failures and retries**:

**When Validation Fails**:
1. Analyze issues from validation report
2. Categorize: auto-fixable vs needs-user-input
3. Apply automatic fixes where possible
4. Ask user for clarifications where needed
5. Trigger reconversion with corrections
6. Re-validate and repeat if necessary

**Features**:
- **Unlimited retries**: No cap on correction attempts
- **No-progress detection**: Detects when stuck in loop
- **Accept-as-is option**: User can proceed despite issues
- **Version tracking**: Keeps previous conversion attempts
- **Smart suggestions**: LLM suggests fixes

### 5. Status Management
**Tracks conversion state through all phases**:

**Status Flow**:
```
IDLE
  ↓
DETECTING_FORMAT
  ↓
AWAITING_USER_INPUT (if ambiguous format or missing metadata)
  ↓
CONVERTING
  ↓
VALIDATING
  ↓
(If validation fails)
  ├→ AWAITING_USER_INPUT (needs clarification)
  └→ CONVERTING (auto-retry with fixes)
  ↓
COMPLETED (passed) or PASSED_WITH_ISSUES or FAILED
```

## MCP Message Handlers

This skill responds to multiple MCP actions:

### 1. `start_conversion`
**Purpose**: Initiate the conversion workflow

**Input**:
```json
{
  "target_agent": "conversation",
  "action": "start_conversion",
  "context": {
    "input_path": "/tmp/uploads/recording.bin",
    "metadata": {
      "experimenter": "Dr. Smith",
      "institution": "MIT"
    }
  }
}
```

**Workflow**:
1. Store input_path and metadata in state
2. Call conversion skill: `detect_format`
3. If ambiguous → Ask user to select format
4. Check for missing critical metadata
5. If missing → Ask user for metadata
6. Proceed to conversion

**Output (Needs Format)**:
```json
{
  "success": true,
  "result": {
    "status": "awaiting_format_selection",
    "supported_formats": ["SpikeGLX", "OpenEphys", ...],
    "message": "Please select the data format"
  }
}
```

**Output (Needs Metadata)**:
```json
{
  "success": true,
  "result": {
    "status": "awaiting_user_input",
    "conversation_type": "required_metadata",
    "message": "I need experimenter, institution, and experiment description...",
    "required_fields": ["experimenter", "institution", "experiment_description"],
    "phase": "pre_conversion"
  }
}
```

### 2. `handle_user_input`
**Purpose**: Process user responses during workflow

**Input**:
```json
{
  "target_agent": "conversation",
  "action": "handle_user_input",
  "context": {
    "user_message": "Dr. Jane Smith, MIT, recording mouse V1 neurons",
    "conversation_context": "required_metadata"
  }
}
```

**What It Does**:
- Parses user message using LLM (if available)
- Extracts structured metadata from natural language
- Updates state with new information
- Decides next step (continue workflow, ask follow-up, etc.)

**Output**:
```json
{
  "success": true,
  "result": {
    "extracted_metadata": {
      "experimenter": "Dr. Jane Smith",
      "institution": "MIT",
      "experiment_description": "recording mouse V1 neurons"
    },
    "next_action": "proceed_to_conversion",
    "message": "Got it! Proceeding with conversion..."
  }
}
```

### 3. `handle_validation_result`
**Purpose**: Process validation outcomes and manage correction loop

**Input**:
```json
{
  "target_agent": "conversation",
  "action": "handle_validation_result",
  "context": {
    "validation_status": "FAILED",
    "issues": [
      {
        "severity": "ERROR",
        "message": "session_start_time is missing",
        "location": "NWBFile.session_start_time"
      }
    ]
  }
}
```

**Decision Logic**:
```
IF validation = PASSED:
  → Return success, workflow complete

IF validation = PASSED_WITH_ISSUES:
  → Ask user if they want to fix or accept as-is
  → If accept: Mark complete
  → If fix: Enter correction loop

IF validation = FAILED:
  → Analyze issues
  → Categorize: auto-fixable vs needs-user-input
  → Apply auto-fixes
  → Ask user for missing info
  → Trigger reconversion
```

**Output (Auto-fix)**:
```json
{
  "success": true,
  "result": {
    "status": "auto_correcting",
    "auto_fixes": {
      "session_start_time": "2024-03-15T14:30:00"
    },
    "message": "I found the issue and fixed it. Reconverting now..."
  }
}
```

**Output (Needs User Input)**:
```json
{
  "success": true,
  "result": {
    "status": "awaiting_user_input",
    "conversation_type": "correction_needed",
    "issues": [...],
    "message": "The validation found 3 issues. Can you provide the session start time?",
    "required_fields": ["session_start_time"]
  }
}
```

### 4. `handle_correction`
**Purpose**: Apply corrections and retry conversion

**Input**:
```json
{
  "target_agent": "conversation",
  "action": "handle_correction",
  "context": {
    "user_corrections": {
      "session_start_time": "2024-03-15T14:30:00"
    }
  }
}
```

**Workflow**:
1. Merge user corrections with existing metadata
2. Call conversion skill: `apply_corrections`
3. Wait for reconversion to complete
4. Call validation skill to re-validate
5. Return to correction loop if still failing
6. Detect no-progress and offer escape

**Output**:
```json
{
  "success": true,
  "result": {
    "status": "reconverting",
    "attempt": 2,
    "message": "Applying your corrections and reconverting..."
  }
}
```

### 5. `accept_as_is`
**Purpose**: User accepts file despite validation issues

**Input**:
```json
{
  "target_agent": "conversation",
  "action": "accept_as_is",
  "context": {}
}
```

**What It Does**:
- Sets validation_status to PASSED_WITH_ISSUES
- Marks workflow as complete
- Preserves issues list for user's records
- Logs user's decision

**Output**:
```json
{
  "success": true,
  "result": {
    "status": "completed_with_issues",
    "message": "File accepted as-is. Note that it may not meet DANDI standards.",
    "output_path": "/tmp/outputs/session.nwb"
  }
}
```

## Conversational Features

### LLM-Powered Conversation (When Available)

**1. Natural Language Parsing**
- Extracts metadata from freeform user input
- Example: "Dr. Smith, MIT, V1 recording" → structured metadata
- Handles variations: "Smith et al.", "Massachusetts Institute of Technology", etc.

**2. Context-Aware Responses**
- Remembers conversation history
- References previous messages
- Maintains conversational flow

**3. Intelligent Clarifications**
- Asks targeted follow-up questions
- Suggests corrections based on common mistakes
- Provides examples and guidance

**4. Progress Narration**
- Explains what's happening in real-time
- Translates technical operations to plain English
- Manages user expectations

### Fallback (No LLM)
- Uses structured prompts and keyword matching
- Asks explicit questions with clear formats
- Provides templates for user responses
- Still functional, just less conversational

## Workflow Scenarios

### Scenario 1: Happy Path (No Issues)
```
1. User uploads file
2. Agent detects format automatically (SpikeGLX)
3. Agent asks for critical metadata (experimenter, institution, description)
4. User provides metadata in one message
5. Agent triggers conversion
6. Conversion completes successfully
7. Agent triggers validation
8. Validation passes with no issues
9. Agent reports success with download link
```

**Duration**: 5-10 minutes

### Scenario 2: Ambiguous Format
```
1. User uploads file
2. Agent cannot detect format automatically
3. Agent asks user to select format
4. User selects "OpenEphys"
5. Agent proceeds with metadata collection
6. ... (continues as Scenario 1)
```

**Duration**: 6-12 minutes

### Scenario 3: Missing Metadata
```
1. User uploads file with minimal metadata
2. Agent detects format
3. Agent asks for 3 critical fields
4. User provides partial info
5. Agent asks for remaining fields
6. User provides rest or skips
7. Agent proceeds with conversion
8. ... (continues as Scenario 1)
```

**Duration**: 8-15 minutes

### Scenario 4: Validation Fails (Correction Loop)
```
1-8. (Same as Scenario 1 through validation)
9. Validation fails with 2 errors
10. Agent categorizes: 1 auto-fixable, 1 needs user input
11. Agent applies auto-fix
12. Agent asks user for missing info
13. User provides info
14. Agent reconverts with corrections (attempt 2)
15. Agent re-validates
16. Validation passes
17. Agent reports success
```

**Duration**: 15-25 minutes

### Scenario 5: Stuck in Loop (No Progress)
```
1-14. (Same as Scenario 4 through attempt 2)
15. Validation still fails with same errors
16. Agent detects no progress (same errors, attempt 3)
17. Agent offers 3 options:
    a) Try different approach
    b) Accept as-is (despite issues)
    c) Abort and seek expert help
18. User selects option b (accept as-is)
19. Agent marks file as PASSED_WITH_ISSUES
20. Agent reports completion with warnings
```

**Duration**: 20-30 minutes

### Scenario 6: User Aborts
```
1-9. (Any point in workflow)
10. User says "cancel" or "abort"
11. Agent confirms cancellation
12. Agent cleans up temporary files
13. Agent resets state to IDLE
14. Agent reports cancellation
```

**Duration**: Variable

## State Management

### GlobalState Fields Used:

**Read/Write**:
- `input_path`: Source data path
- `output_path`: NWB file path
- `metadata`: User-provided metadata (flat structure)
- `current_phase`: Workflow status
- `validation_status`: Validation outcome
- `correction_attempt`: Retry counter
- `logs`: Detailed activity log

**Write Only**:
- `progress`: Current progress %
- `user_declined_fields`: Fields user chose to skip
- `metadata_requests_count`: Times we asked for metadata
- `user_wants_minimal`: User preference flag
- `previous_issues`: Issues from last attempt (for no-progress detection)
- `conversation_history`: Message history (for LLM context)

### Conversation History Management
**Important**: Conversation history is now stored in `GlobalState.conversation_history` to prevent memory leaks. Previous attempts stored history in agent instance, causing unlimited growth.

**Structure**:
```python
conversation_history: List[Dict[str, str]] = [
    {"role": "user", "content": "I want to convert my data"},
    {"role": "assistant", "content": "Great! I'll help you..."},
    ...
]
```

**Cleanup**: History is cleared when workflow completes or user aborts.

## Decision Logic

### Metadata Collection Decision
```python
def should_ask_for_metadata(state: GlobalState) -> bool:
    # Don't ask if user wants minimal conversion
    if state.user_wants_minimal:
        return False

    # Don't ask if we've already asked twice
    if state.metadata_requests_count >= 2:
        return False

    # Check for missing critical fields
    critical_fields = ["experimenter", "institution", "experiment_description"]
    missing = [f for f in critical_fields if not state.metadata.get(f)]

    # Filter out fields user declined
    missing = [f for f in missing if f not in state.user_declined_fields]

    return len(missing) > 0
```

### Correction Strategy Decision
```python
def determine_correction_strategy(issues: List[Issue]) -> str:
    auto_fixable_count = count_auto_fixable(issues)
    needs_user_count = count_needs_user_input(issues)

    if needs_user_count == 0:
        return "auto_fix_and_retry"
    elif auto_fixable_count > 0:
        return "mixed"  # Fix some, ask for rest
    else:
        return "ask_user_for_all"
```

### No-Progress Detection
```python
def detect_no_progress(state: GlobalState) -> bool:
    # Check if we've tried 3+ times
    if state.correction_attempt < 3:
        return False

    # Check if issues are identical to previous attempt
    current_issues = state.validation_report.issues
    previous_issues = state.previous_issues

    return issues_are_identical(current_issues, previous_issues)
```

## Integration with Other Skills

### Calls These Skills:
- **nwb_conversion**: Format detection, conversion, reconversion
- **nwb_validation**: Validation of converted files

### Used By:
- **API Layer**: FastAPI endpoints call this skill for all user requests
- **WebSocket Handler**: Real-time updates during workflow

### Coordination Pattern:
```
User Request
    ↓
API Endpoint
    ↓
Orchestration Skill (this)
    ├→ nwb_conversion skill
    ├→ nwb_validation skill
    └→ Response to user
```

## Error Handling

### User-Friendly Error Messages
**Technical Error**:
```
ValueError: session_start_time must be ISO 8601 format
```

**User-Friendly Message** (LLM-generated):
```
The session start time format wasn't recognized. Please use ISO 8601 format
like '2024-03-15T14:30:00-05:00' (date, time, and timezone).
```

### Graceful Degradation
- If LLM unavailable: Falls back to structured prompts
- If conversion fails: Offers detailed error info + retry
- If validation fails repeatedly: Offers escape options
- If user provides invalid input: Asks for clarification with examples

### Escape Hatches
1. **Accept as-is**: Proceed despite validation issues
2. **Skip metadata**: Convert with minimal info
3. **Abort workflow**: Clean up and start over
4. **Request help**: Provide debug info for expert review

## Performance Characteristics

| Scenario | Duration | User Interaction |
|----------|----------|------------------|
| Happy path | 5-10 min | Minimal (2-3 messages) |
| Ambiguous format | 6-12 min | 1 extra clarification |
| Missing metadata | 8-15 min | 2-3 metadata questions |
| Correction loop | 15-25 min | 3-5 corrections |
| Stuck loop escape | 20-30 min | Multiple retries + decision |

**Notes**:
- LLM calls add 1-2 seconds per interaction
- Conversion time dominates (2-10 min per GB)
- User response time is variable (30 sec - 5 min)

## Common User Patterns

### Pattern 1: Power User
```
User: "Convert recording.bin, SpikeGLX, Dr. Smith, MIT, V1 recording, mouse001, Mus musculus, P90D, M"
```
**Agent Response**: Extracts all info, proceeds immediately

### Pattern 2: Minimal User
```
User: "Just convert it, skip all the questions"
```
**Agent Response**: Sets user_wants_minimal=True, converts with minimal metadata

### Pattern 3: Interactive User
```
User: "I want to convert my data"
Agent: "What format is it?"
User: "SpikeGLX"
Agent: "I need experimenter, institution, and description"
User: "Ask me one by one"
Agent: "What's the experimenter name?"
User: "Dr. Smith"
... (continues)
```

### Pattern 4: Frustrated User
```
User: "This keeps failing!"
Agent: (Detects no-progress)
Agent: "I notice we're stuck. Would you like to accept the file as-is?"
User: "Yes, just finish it"
Agent: (Accepts with issues)
```

## Testing Checklist

- [ ] Workflow starts correctly with valid input
- [ ] Ambiguous format triggers user selection
- [ ] Missing metadata triggers collection
- [ ] Metadata extraction from natural language works
- [ ] Conversion success path completes
- [ ] Validation failure triggers correction loop
- [ ] Auto-fixes apply correctly
- [ ] User corrections merge with existing metadata
- [ ] No-progress detection activates at attempt 3
- [ ] Accept-as-is option works
- [ ] Abort workflow cleans up correctly
- [ ] LLM fallback works when unavailable
- [ ] Conversation history doesn't leak memory
- [ ] All MCP handlers respond correctly

## Security Considerations

### Input Validation
- Sanitize all user messages before processing
- Validate file paths (no directory traversal)
- Limit conversation history size (prevent memory exhaustion)
- Validate metadata values (no code injection)

### Rate Limiting
- Limit LLM calls per session (cost control)
- Limit correction attempts per workflow (prevent infinite loops)
- Limit metadata requests (avoid user frustration)

### Data Privacy
- Don't log sensitive user metadata
- Clear conversation history after workflow
- Don't send user data to external LLMs without consent

## Version History

### v0.1.0 (2025-10-17)
- Initial skill documentation
- Complete workflow orchestration
- Natural language conversation support
- Metadata collection (pre-conversion)
- Unlimited correction loop with no-progress detection
- Accept-as-is option for stuck workflows
- LLM-powered parsing and responses
- Memory-safe conversation history management

### Planned Features (v0.2.0):
- Multi-session support (concurrent users)
- Conversation templates (customize interaction style)
- Batch processing orchestration
- Progress snapshots (resume interrupted workflows)
- User preference profiles (remember settings)

## References

- [Implementation Code](backend/src/agents/conversation_agent.py)
- [Conversational Handler](backend/src/agents/conversational_handler.py)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [GlobalState Schema](backend/src/models/state.py)

---

**Last Updated**: 2025-10-17
**Maintainer**: Agentic Neurodata Conversion Team
**License**: MIT
**Support**: GitHub Issues
