# NWB Conversion Workflow - State Machine Documentation

**Date:** 2025-10-20
**Version:** 2.0 (Post-Phase 2 Integration)
**Status:** Production

---

## Overview

This document describes the state machine that governs the NWB file conversion workflow, including all possible states, transitions, and the conditions that trigger them.

---

## Primary State Machine: ConversionStatus

### State Diagram

```
┌──────────┐
│   IDLE   │ ◄────────┐
└────┬─────┘           │
     │                 │ reset()
     │ upload file     │
     ▼                 │
┌─────────────┐        │
│  UPLOADING  │        │
└──────┬──────┘        │
       │               │
       │ upload complete│
       ▼               │
┌──────────────────┐   │
│ DETECTING_FORMAT │   │
└────────┬─────────┘   │
         │             │
         │ format detected
         ▼             │
    ┌────────┐         │
    │  IDLE  │         │
    └───┬────┘         │
        │              │
        │ start_conversion()
        │              │
        │ ┌─── metadata needed? ───┐
        │ │                        │
        ▼ ▼                        │
    ┌──────────────────────┐      │
    │ AWAITING_USER_INPUT  │◄─────┤
    │ (metadata)           │      │
    └──────────┬───────────┘      │
               │                  │
               │ user provides    │
               │                  │
               ▼                  │
       ┌─────────────┐            │
       │ CONVERTING  │            │
       └──────┬──────┘            │
              │                   │
              │ conversion complete│
              ▼                   │
       ┌─────────────┐            │
       │ VALIDATING  │            │
       └──────┬──────┘            │
              │                   │
              │                   │
         ┌────┴────┬──────────┬──┘
         │         │          │
    PASSED   PASSED_WITH  FAILED
         │    _ISSUES       │
         │         │        │
         ▼         ▼        ▼
    ┌──────────┐ ┌────────────────────┐ ┌─────────────────────────┐
    │COMPLETED │ │ AWAITING_USER_INPUT│ │ AWAITING_RETRY_APPROVAL │
    └────┬─────┘ │  (improve/accept)  │ └────────┬────────────────┘
         │       └──────────┬─────────┘          │
         │                  │                    │
         │          ┌───────┴────────┐           │
         │          │                │           │
         │       improve          accept         │
         │          │                │           │
         │          ▼                ▼           │
         │     ┌──────────┐    ┌──────────┐     │
         │     │CONVERTING│    │COMPLETED │     │
         │     └──────────┘    └──────────┘     │
         │                                       │
         │              ┌────────────────────────┤
         │              │                        │
         │           approve                  reject
         │              │                        │
         │              ▼                        ▼
         │         ┌──────────┐            ┌────────┐
         │         │CONVERTING│            │ FAILED │
         │         └──────────┘            └───┬────┘
         │                                     │
         └─────────────────────────────────────┘
                        reset()
```

### State Descriptions

| **State** | **Description** | **Can Accept Upload?** | **Can Start Conversion?** |
|-----------|----------------|----------------------|-------------------------|
| **IDLE** | Initial state, no file uploaded | ✅ Yes | ❌ No (no file) |
| **UPLOADING** | File upload in progress | ❌ No | ❌ No |
| **DETECTING_FORMAT** | Analyzing file format | ❌ No | ❌ No |
| **AWAITING_USER_INPUT** | Waiting for user response | ✅ Yes (can restart) | ❌ No |
| **CONVERTING** | Conversion in progress | ❌ No | ❌ No |
| **VALIDATING** | NWB Inspector validation | ❌ No | ❌ No |
| **AWAITING_RETRY_APPROVAL** | User must approve/reject retry | ✅ Yes (can restart) | ❌ No |
| **COMPLETED** | Conversion finished successfully | ✅ Yes (new conversion) | ✅ Yes (restart) |
| **FAILED** | Conversion failed permanently | ✅ Yes (new conversion) | ✅ Yes (restart) |

---

## Secondary State Machine: ConversationPhase

### Phase Diagram

```
┌──────────┐
│   IDLE   │
└────┬─────┘
     │
     │ metadata needed
     ▼
┌──────────────────────┐
│ METADATA_COLLECTION  │
│  (required_metadata) │
└──────────┬───────────┘
           │
           │ user provides / declines
           ▼
      ┌─────────┐
      │  IDLE   │
      └────┬────┘
           │
           │ validation complete
           │
      ┌────┴─────────┬──────────────┐
      │              │              │
   PASSED    PASSED_WITH_ISSUES  FAILED
      │              │              │
      ▼              ▼              ▼
 ┌─────────┐  ┌───────────────────────┐  ┌──────────────────────┐
 │  IDLE   │  │ IMPROVEMENT_DECISION  │  │ VALIDATION_ANALYSIS  │
 └─────────┘  │ (improve/accept)      │  │ (analyze & retry)    │
              └───────────┬───────────┘  └──────────┬───────────┘
                          │                         │
                   ┌──────┴────────┐                │
                   │               │                │
                improve         accept              │
                   │               │                │
                   ▼               ▼                ▼
              ┌─────────┐     ┌─────────┐     ┌─────────┐
              │  IDLE   │     │  IDLE   │     │  IDLE   │
              └─────────┘     └─────────┘     └─────────┘
```

### Phase Descriptions

| **Phase** | **ConversionStatus** | **User Action Required** | **Next Phase** |
|-----------|---------------------|------------------------|---------------|
| **IDLE** | Any | None | - |
| **METADATA_COLLECTION** | AWAITING_USER_INPUT | Provide or decline metadata | IDLE |
| **VALIDATION_ANALYSIS** | AWAITING_USER_INPUT | Answer LLM questions about issues | IDLE |
| **IMPROVEMENT_DECISION** | AWAITING_USER_INPUT | Choose "improve" or "accept" | IDLE |

---

## Tertiary State Machine: MetadataRequestPolicy

### Policy State Diagram

```
┌──────────────┐
│  NOT_ASKED   │
└──────┬───────┘
       │
       │ system requests metadata
       ▼
┌─────────────┐
│ ASKED_ONCE  │
└──────┬──────┘
       │
       │
  ┌────┴────┬───────────┐
  │         │           │
user     user       user skips
provides  declines   entirely
  │         │           │
  ▼         ▼           ▼
┌──────────────┐ ┌─────────────────┐ ┌────────────────────┐
│USER_PROVIDED │ │ USER_DECLINED   │ │ PROCEEDING_MINIMAL │
└──────────────┘ └─────────────────┘ └────────────────────┘
       │                 │                      │
       │                 │                      │
       └─────────────────┴──────────────────────┘
                         │
                         │ conversion complete / reset
                         ▼
                  ┌──────────────┐
                  │  NOT_ASKED   │
                  └──────────────┘
```

### Policy Descriptions

| **Policy** | **Meaning** | **Will Request Again?** | **Backward Compat** |
|------------|------------|------------------------|-------------------|
| **NOT_ASKED** | Metadata not yet requested | ✅ Yes | `metadata_requests_count == 0` |
| **ASKED_ONCE** | Requested, awaiting response | ❌ No | `metadata_requests_count == 1` |
| **USER_PROVIDED** | User provided metadata | ❌ No | `metadata_requests_count >= 1` |
| **USER_DECLINED** | User declined to provide | ❌ No | `user_wants_minimal == True` |
| **PROCEEDING_MINIMAL** | Proceeding without metadata | ❌ No | `user_wants_minimal == True` |

---

## Validation Outcome State Machine

### ValidationOutcome Enum

```
     ┌──── NWB Inspector ────┐
     │                       │
     ▼                       ▼
 No Issues            Has Issues
     │                       │
     ▼                       ▼
┌──────────┐    ┌─────────────┬──────────┐
│  PASSED  │    │  CRITICAL   │ WARNING  │
└──────────┘    │  / ERROR    │ / INFO   │
                └──────┬──────┴────┬─────┘
                       │           │
                       ▼           ▼
                  ┌────────┐  ┌─────────────────────┐
                  │ FAILED │  │ PASSED_WITH_ISSUES  │
                  └────────┘  └─────────────────────┘
```

### Outcome Descriptions

| **Outcome** | **Validation Status** | **User Action** | **System Action** |
|-------------|---------------------|----------------|------------------|
| **PASSED** | No issues found | None - download ready | Set status=COMPLETED |
| **PASSED_WITH_ISSUES** | Warnings/best practices | Choose improve/accept | Set status=AWAITING_USER_INPUT |
| **FAILED** | Critical errors | Approve/reject retry | Set status=AWAITING_RETRY_APPROVAL |

---

## Complete Workflow Example

### Scenario 1: Happy Path (No Issues)

```
1. User uploads file
   State: IDLE → UPLOADING → DETECTING_FORMAT → IDLE

2. System checks metadata
   - Missing required fields
   - MetadataPolicy: NOT_ASKED → ASKED_ONCE
   - ConversationPhase: IDLE → METADATA_COLLECTION
   - State: IDLE → AWAITING_USER_INPUT

3. User provides metadata
   - MetadataPolicy: ASKED_ONCE → USER_PROVIDED
   - ConversationPhase: METADATA_COLLECTION → IDLE
   - State: AWAITING_USER_INPUT → CONVERTING

4. Conversion completes
   State: CONVERTING → VALIDATING

5. Validation passes
   - ValidationOutcome: PASSED
   - State: VALIDATING → COMPLETED

✅ File ready for download
```

### Scenario 2: Validation Issues (User Improves)

```
1-4. [Same as Scenario 1]

5. Validation finds warnings
   - ValidationOutcome: PASSED_WITH_ISSUES
   - ConversationPhase: IDLE → IMPROVEMENT_DECISION
   - State: VALIDATING → AWAITING_USER_INPUT

6. User chooses "improve"
   - ConversationPhase: IMPROVEMENT_DECISION → IDLE
   - State: AWAITING_USER_INPUT → CONVERTING
   - correction_attempt: 0 → 1

7. Re-validation passes
   - ValidationOutcome: PASSED
   - State: VALIDATING → COMPLETED

✅ File ready for download (improved version)
```

### Scenario 3: Validation Failure (Retry Approved)

```
1-4. [Same as Scenario 1]

5. Validation fails
   - ValidationOutcome: FAILED
   - ConversationPhase: IDLE → VALIDATION_ANALYSIS
   - State: VALIDATING → AWAITING_RETRY_APPROVAL

6. User approves retry
   - correction_attempt: 0 → 1
   - can_retry: True (attempt 1/5)
   - State: AWAITING_RETRY_APPROVAL → CONVERTING

7. Re-conversion and validation
   State: CONVERTING → VALIDATING

8. [Repeat 5-7 up to MAX_RETRY_ATTEMPTS=5]

9a. Success after retry N < 5
    - ValidationOutcome: PASSED
    - State: VALIDATING → COMPLETED
    ✅ File ready for download

9b. Still failing after 5 attempts
    - can_retry: False
    - State: VALIDATING → FAILED
    ❌ Conversion terminated
```

### Scenario 4: User Declines Metadata

```
1. User uploads file
   State: IDLE → UPLOADING → DETECTING_FORMAT → IDLE

2. System checks metadata
   - Missing required fields
   - MetadataPolicy: NOT_ASKED → ASKED_ONCE
   - ConversationPhase: IDLE → METADATA_COLLECTION
   - State: IDLE → AWAITING_USER_INPUT

3. User declines ("skip all")
   - MetadataPolicy: ASKED_ONCE → USER_DECLINED
   - user_wants_minimal: False → True
   - ConversationPhase: METADATA_COLLECTION → IDLE
   - State: AWAITING_USER_INPUT → CONVERTING

4. Conversion with minimal metadata
   State: CONVERTING → VALIDATING

5. Validation (likely warnings due to missing metadata)
   - ValidationOutcome: PASSED_WITH_ISSUES
   - ConversationPhase: IDLE → IMPROVEMENT_DECISION
   - State: VALIDATING → AWAITING_USER_INPUT

6. User chooses "accept"
   - ConversationPhase: IMPROVEMENT_DECISION → IDLE
   - State: AWAITING_USER_INPUT → COMPLETED

✅ File ready for download (with warnings)
```

---

## State Transition Guards

### WorkflowStateManager Methods

These methods enforce state transition rules:

#### `can_accept_upload(state: GlobalState) -> bool`

**Returns True when:**
- Status is IDLE, COMPLETED, FAILED, or AWAITING_USER_INPUT

**Returns False when:**
- Status is UPLOADING, DETECTING_FORMAT, CONVERTING, or VALIDATING

**Purpose:** Prevents concurrent uploads during active processing

---

#### `can_start_conversion(state: GlobalState) -> bool`

**Returns True when:**
- input_path is set
- Status is NOT in {DETECTING_FORMAT, CONVERTING, VALIDATING}

**Returns False when:**
- No input_path
- Already converting/validating

**Purpose:** Ensures file is uploaded before conversion starts

---

#### `should_request_metadata(state: GlobalState) -> bool`

**Returns True when:**
- Has missing required DANDI fields
- metadata_policy == NOT_ASKED
- NOT in active metadata conversation

**Returns False when:**
- All required fields present
- metadata_policy != NOT_ASKED
- Already in conversation

**Purpose:** Requests metadata exactly once per session

---

#### `is_in_active_conversation(state: GlobalState) -> bool`

**Returns True when:**
- Status == AWAITING_USER_INPUT
- AND (conversation_history not empty OR conversation_phase == METADATA_COLLECTION)

**Returns False when:**
- Any other status
- No conversation history

**Purpose:** Detects if user is currently engaged in conversation

---

## Retry Limit Enforcement

### MAX_RETRY_ATTEMPTS = 5

```python
class GlobalState:
    correction_attempt: int = Field(default=0, ge=0, le=5)

    @property
    def can_retry(self) -> bool:
        return self.correction_attempt < MAX_RETRY_ATTEMPTS

    @property
    def retry_attempts_remaining(self) -> int:
        return max(0, MAX_RETRY_ATTEMPTS - self.correction_attempt)
```

**Purpose:** Prevents infinite retry loops by limiting to 5 attempts

**Behavior:**
- After 5 failed attempts, `can_retry` returns `False`
- System transitions to FAILED state
- User must upload new file to retry

---

## Race Condition Prevention

### Atomic State Updates

```python
async def set_validation_result(
    self,
    overall_status: ValidationOutcome,
    requires_user_decision: bool = False,
    conversation_phase: Optional[ConversationPhase] = None
) -> None:
    """Atomically update validation result and related state."""
    async with self._status_lock:
        self.overall_status = overall_status
        if requires_user_decision:
            self.status = ConversionStatus.AWAITING_USER_INPUT
            self.conversation_phase = conversation_phase or ConversationPhase.IMPROVEMENT_DECISION
        else:
            self.status = ConversionStatus.COMPLETED
            self.conversation_phase = ConversationPhase.IDLE
```

**Purpose:** Ensures frontend always sees consistent state

**Benefits:**
- No partial updates visible to frontend
- Thread-safe state transitions
- Prevents race conditions during validation

---

## State Reset Behavior

### `reset()` Method

Resets state to initial conditions:

```python
def reset(self) -> None:
    self.status = ConversionStatus.IDLE
    self.validation_status = None
    self.overall_status = None
    self.input_path = None
    self.output_path = None
    self.metadata = {}
    self.inference_result = {}
    self.user_provided_metadata = {}
    self.auto_extracted_metadata = {}
    self.conversation_history = []
    self.conversation_phase = ConversationPhase.IDLE
    self.conversation_type = None
    self.metadata_policy = MetadataRequestPolicy.NOT_ASKED
    self.metadata_requests_count = 0
    self.user_wants_minimal = False
    self.correction_attempt = 0
    # ... more resets
```

**When Called:**
- User uploads new file (resets previous session)
- Explicit reset request

**Purpose:** Clean slate for new conversion session

---

## Backward Compatibility

### Deprecated Fields (Phase 2)

These fields are maintained for backward compatibility but new code should use enums:

| **Old Field** | **New Field** | **Sync Method** |
|--------------|--------------|----------------|
| `conversation_type: str` | `conversation_phase: ConversationPhase` | Manually set both |
| `user_wants_minimal: bool` | `metadata_policy: MetadataRequestPolicy` | Property getter |
| `metadata_requests_count: int` | `metadata_policy: MetadataRequestPolicy` | Updated on transitions |
| `overall_status: str` | `overall_status: ValidationOutcome` | Enum with string value |

---

## Testing

Comprehensive unit tests verify all state transitions:

- **30 tests** covering all WorkflowStateManager methods
- **Integration tests** for full workflow scenarios
- **Edge case tests** for race conditions and retry limits
- **Backward compatibility tests** for deprecated fields

See: [backend/tests/test_workflow_state_manager.py](backend/tests/test_workflow_state_manager.py)

---

## Conclusion

The state machine provides:

✅ **Clear state transitions** with well-defined rules
✅ **Type-safe enums** preventing invalid states
✅ **Centralized logic** via WorkflowStateManager
✅ **Retry limit** enforcement (MAX=5)
✅ **Race condition prevention** with atomic updates
✅ **Backward compatibility** with deprecated fields
✅ **Comprehensive testing** (30 unit tests passing)

**System Status:** Production-ready with robust state management ✅
