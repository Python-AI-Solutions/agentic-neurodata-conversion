# Design Patterns & Best Practices: Lessons from Implementation

**Document Type**: Design patterns catalog from real implementation
**Date**: October 27, 2025
**Purpose**: Codify reusable patterns discovered during development for future projects

---

## Overview

This document catalogs the **design patterns, architectural decisions, and best practices** that emerged from building the Agentic Neurodata Conversion system. These patterns are generalizable to other AI-powered, conversation-driven applications.

---

## Pattern 1: Schema-Driven AI Prompting

### Context
When using LLMs for structured data extraction or normalization, embedding format rules directly in prompts leads to inconsistency and maintenance burden.

### Problem
- Format rules scattered across multiple prompt templates
- Changes to format requirements require updating many prompts
- No single source of truth for data specifications
- LLM outputs vary in format compliance

### Solution: Centralized Schema with Dynamic Prompt Generation

**Implementation**:
```python
# 1. Define schema once
class NWBDANDISchema:
    """Single source of truth for all metadata format rules."""

    def get_field_schema(self, field_name: str) -> MetadataFieldSchema:
        """Returns complete specification for field."""
        return MetadataFieldSchema(
            name="age",
            description="Subject age at experiment time",
            format="ISO 8601 duration",
            example="P56D",
            normalization_rules={
                "8 weeks": "P56D",
                "adult": "P90D"
            },
            validation_regex=r"^P\d+[DWMY]$"
        )

# 2. Generate prompts from schema
def build_prompt_from_schema(field_schema: MetadataFieldSchema) -> str:
    """Dynamically construct prompt using schema."""
    return f"""Parse this field: {field_schema.name}

Description: {field_schema.description}
Expected format: {field_schema.format}
Example: {field_schema.example}

Normalization rules:
{chr(10).join(f"  '{k}' → '{v}'" for k, v in field_schema.normalization_rules.items())}

Validation: Must match regex {field_schema.validation_regex}
"""

# 3. Use across all LLM calls
async def parse_field_with_llm(field_name: str, user_input: str):
    schema = nwb_schema.get_field_schema(field_name)
    prompt = build_prompt_from_schema(schema)
    return await llm_service.generate(prompt + f"\n\nInput: {user_input}")
```

### Benefits
- ✅ Change schema once, all prompts update automatically
- ✅ Guaranteed consistency across all AI interactions
- ✅ Schema serves as documentation, validation, and prompt source
- ✅ Easy to extend (add field → instant LLM support)

### When to Apply
- Structured data extraction from natural language
- Data normalization/transformation tasks
- Any domain with formal data specifications
- Multi-step workflows requiring consistent format rules

### Related Patterns
- **Configuration as Code**: Schema is versioned with code
- **Single Source of Truth**: One definition, many uses
- **Template Method**: Prompt generation algorithm, schema provides data

---

## Pattern 2: Confidence-Tiered Automation

### Context
AI systems make predictions with varying certainty. Treating all predictions equally creates poor UX (either too cautious or too risky).

### Problem
Binary automation decisions create friction:
- Always confirm → Tedious for users
- Never confirm → Users distrust system
- Ask for confirmation threshold → Hard to choose right value

### Solution: Three-Tier Strategy Based on Confidence

**Implementation**:
```python
class ConfidenceLevel(Enum):
    HIGH = "high"      # ≥80% confidence
    MEDIUM = "medium"  # 50-79% confidence
    LOW = "low"        # <50% confidence

async def apply_with_confidence_strategy(
    parsed_field: ParsedField,
    state: GlobalState
):
    """Different actions based on confidence tier."""

    if parsed_field.confidence >= 80:
        # HIGH: Silent automation
        state.add_log(INFO, f"✓ Applied {field}={value}")
        return value

    elif parsed_field.confidence >= 50:
        # MEDIUM: Automated with transparency
        state.add_log(WARNING,
            f"⚠️ Applied {field}={value} (medium confidence - best guess)")
        return value

    else:
        # LOW: Automated but flagged for review
        state.add_log(WARNING,
            f"❓ Applied {field}={value} (LOW confidence - NEEDS REVIEW)")

        # Defer review to validation report
        state.warnings[field] = {
            "value": value,
            "confidence": parsed_field.confidence,
            "action_required": "Review before final submission"
        }
        return value
```

**User Experience**:
```
High Confidence (95%):
  System: [Silently applies, user continues uninterrupted]

Medium Confidence (70%):
  System: [Applies with note in logs, user can review if curious]
  Log: "⚠️ Applied age=P90D (medium confidence - best guess)"

Low Confidence (40%):
  System: [Applies but adds prominent warning to final report]
  Report: "⚠️ REVIEW REQUIRED: age was guessed as P90D with low confidence"
```

### Benefits
- ✅ Maintains workflow momentum (no interrupting confirmations)
- ✅ Builds user trust (transparency about uncertainty)
- ✅ Enables batch review (warnings collected in report)
- ✅ Adapts to AI capabilities (adjust thresholds as AI improves)

### Threshold Selection Guide

**High Threshold (≥80%)**:
- Should be wrong <5% of time
- Cost of error is low (easy to fix later)
- User can review in batch

**Medium Threshold (50-79%)**:
- Wrong ~15-30% of time
- User should be aware but not blocked
- Visible in logs, not blocking workflow

**Low Threshold (<50%)**:
- Wrong >50% of time
- Must be flagged prominently
- Requires user review before critical action (e.g., submission)

### When to Apply
- Any ML/AI prediction task
- Form auto-fill features
- Automated data validation
- Intelligent defaults in UIs

### Calibration Strategy
```python
class ConfidenceCalibrator:
    """Track actual accuracy vs. predicted confidence."""

    def record_outcome(self, confidence: float, was_correct: bool):
        """Record actual correctness for calibration."""
        self.history.append((confidence, was_correct))

    def get_calibrated_thresholds(self):
        """Compute thresholds based on actual performance."""
        # Find confidence values where error rate crosses 5%, 30%
        high_threshold = self._find_threshold(error_rate=0.05)
        low_threshold = self._find_threshold(error_rate=0.50)
        return high_threshold, low_threshold
```

---

## Pattern 3: Graceful LLM Degradation

### Context
LLM APIs are external dependencies that can fail, have rate limits, or be unavailable.

### Problem
- Hard dependency on LLM → System fails when LLM unavailable
- No API key → Application unusable
- Rate limited → Users blocked
- Cost concerns → Can't always use expensive LLM

### Solution: Layered Fallback Strategy

**Architecture**:
```
Attempt 1: LLM-Powered (Best Quality)
   ↓ (on failure)
Attempt 2: Rule-Based Heuristics (Good Quality)
   ↓ (on failure)
Attempt 3: Simple Pattern Matching (Basic Quality)
```

**Implementation**:
```python
class IntelligentMetadataParser:
    def __init__(self, llm_service: Optional[LLMService] = None):
        """LLM service is optional!"""
        self.llm_service = llm_service

    async def parse_natural_language(self, user_input: str):
        """Parse with best available method."""

        if not self.llm_service:
            logger.info("LLM unavailable, using fallback parser")
            return self._fallback_parse(user_input)

        try:
            # Try LLM first
            return await self._llm_parse(user_input)

        except anthropic.RateLimitError:
            logger.warning("Rate limited, falling back to rules")
            return self._rule_based_parse(user_input)

        except anthropic.APIError as e:
            logger.error(f"LLM API error: {e}, using fallback")
            return self._fallback_parse(user_input)

    async def _llm_parse(self, text: str):
        """Best quality: Natural language understanding."""
        # Full LLM processing with confidence scoring
        ...

    def _rule_based_parse(self, text: str):
        """Good quality: Heuristics and domain knowledge."""
        # Apply normalization rules from schema
        # Use regex patterns for common formats
        # Return lower confidence scores
        ...

    def _fallback_parse(self, text: str):
        """Basic quality: Simple pattern matching."""
        # key:value pattern extraction
        # Direct mapping from normalization rules
        # Return minimal confidence
        ...
```

**Quality Degradation Gracefully**:
```python
# With LLM
Input: "8 week old mouse"
Output: ParsedField(
    field="age",
    value="P56D",
    confidence=92,
    reasoning="8 weeks = 56 days in ISO 8601 format"
)

# With rules
Input: "8 weeks"  # Must be more structured
Output: ParsedField(
    field="age",
    value="P56D",
    confidence=75,
    reasoning="Pattern matched '8 weeks' → P56D"
)

# With fallback
Input: "age: P56D"  # Must be exact format
Output: ParsedField(
    field="age",
    value="P56D",
    confidence=60,
    reasoning="Direct key:value extraction"
)
```

### Benefits
- ✅ System remains functional without LLM
- ✅ Graceful quality degradation, not total failure
- ✅ Cost optimization (use LLM only when needed)
- ✅ Easier testing (don't need LLM for all tests)

### When to Apply
- Any feature using LLM or external AI service
- Production systems requiring high availability
- Cost-sensitive applications
- Systems with offline/low-connectivity requirements

### Cost Optimization Strategy
```python
def should_use_llm(input_complexity: str) -> bool:
    """Decide if LLM worth cost for this input."""

    # Simple, structured input → Use rules
    if re.match(r"^\w+:\s*\w+$", input_complexity):
        return False

    # Complex natural language → Use LLM
    if len(input_complexity.split()) > 10:
        return True

    # Medium complexity → Use rules first, LLM if fails
    return "medium"
```

---

## Pattern 4: Conversation-Aware State Management

### Context
Conversational UIs benefit from remembering user interaction patterns to personalize responses.

### Problem
- Repeating same questions annoys users
- No adaptation to user communication style
- Can't learn user preferences within session
- Lose context in multi-turn conversations

### Solution: Rich Conversation History with Behavioral Tracking

**State Structure**:
```python
@dataclass
class GlobalState:
    """State includes conversation history and behavioral metrics."""

    # Conversation transcript
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    # Behavioral metrics
    metadata_requests_count: int = 0      # How many times asked
    user_skip_count: int = 0              # How often user skips
    user_edit_count: int = 0              # How often user corrects
    avg_message_length: float = 0.0       # User verbosity

    # Preferences learned
    preferred_input_mode: Optional[str] = None  # "batch" or "sequential"
    wants_minimal_interaction: bool = False

    def add_conversation_message(self, role: str, content: str):
        """Track message and update behavioral metrics."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Update metrics
        if role == "user":
            self._update_user_metrics(content)

    def _update_user_metrics(self, message: str):
        """Learn from user message patterns."""

        # Update average message length
        msg_len = len(message.split())
        total_user_msgs = len([m for m in self.conversation_history if m["role"] == "user"])
        self.avg_message_length = (
            (self.avg_message_length * (total_user_msgs - 1) + msg_len) / total_user_msgs
        )

        # Detect skip intent
        if any(word in message.lower() for word in ["skip", "later", "minimal"]):
            self.user_skip_count += 1

        # Infer input mode preference
        if msg_len > 20 and "," in message:
            self.preferred_input_mode = "batch"
        elif msg_len < 5:
            self.preferred_input_mode = "sequential"
```

**Adaptive Behavior**:
```python
async def generate_metadata_request(state: GlobalState):
    """Adapt request based on conversation history."""

    # Check if we've asked before
    if state.metadata_requests_count > 1:
        # Be more concise on follow-ups
        prompt_modifier = "IMPORTANT: Be brief - this is a follow-up request."
    else:
        prompt_modifier = ""

    # Adapt to user verbosity
    if state.avg_message_length > 30:
        # User likes detail - ask for batch input
        request_style = "batch"
    elif state.avg_message_length < 10:
        # User is terse - ask one field at a time
        request_style = "sequential"
    else:
        request_style = "adaptive"

    # Detect skip preference
    if state.user_skip_count > 2:
        state.wants_minimal_interaction = True
        # Only ask for truly required fields

    # Generate personalized request
    return await llm.generate_request(
        style=request_style,
        modifier=prompt_modifier,
        minimal=state.wants_minimal_interaction
    )
```

**Example Adaptation**:
```
Turn 1:
System: "I've analyzed your file... could you share experimenter,
         institution, and subject details?"
User: "Jane Smith"  [Short response]

[System learns: User prefers sequential]

Turn 2:
System: "Thanks! And the institution where this was recorded?"
User: "MIT"

[Adapts to terse responses]

vs.

Turn 1:
System: "I've analyzed your file... could you share experimenter,
         institution, and subject details?"
User: "I'm Dr. Jane Smith from the MIT Neuroscience Department
       studying visual processing in 8-week-old male C57BL/6 mice"
       [Long, detailed response]

[System learns: User prefers batch, provides detail]

Turn 2:
System: "Perfect! I got most of that. Just need session description
         and any keywords for your study."
User: [Continues with detailed batch input]
```

### Benefits
- ✅ Personalized user experience
- ✅ Reduces user frustration (no repetition)
- ✅ Adapts to different user types (novice vs. expert)
- ✅ Improves efficiency (learns optimal interaction style)

### When to Apply
- Multi-turn conversational interfaces
- Adaptive forms or wizards
- User onboarding flows
- Any system with repeated user interactions

### Privacy Consideration
```python
class ConversationHistory:
    """Conversation history with privacy controls."""

    MAX_HISTORY_SIZE = 50  # Limit memory
    EXPIRY_HOURS = 24      # Auto-delete after session

    def add_message(self, role: str, content: str):
        # Add message
        self.messages.append(...)

        # Prune old messages
        if len(self.messages) > self.MAX_HISTORY_SIZE:
            self.messages = self.messages[-self.MAX_HISTORY_SIZE:]

    def anonymize_for_logging(self):
        """Remove PII before logging."""
        # Hash user messages
        # Keep system messages
        # Preserve behavioral metrics
```

---

## Pattern 5: Deferred Validation with Batch Review

### Context
Real-time validation that blocks user workflow creates friction, but users need to know about issues.

### Problem
- Interrupt user for every validation error → Frustrating
- Don't show errors → Users surprised at end
- Can't proceed until all errors fixed → Workflow stuck
- Multiple validation passes → Slow

### Solution: Allow Workflow Continuation, Flag for Later Review

**Architecture**:
```python
class ValidationStrategy:
    """Separate blocking vs. non-blocking validation."""

    BLOCKING_ERRORS = [
        "CRITICAL_FORMAT_ERROR",
        "FILE_CORRUPTION",
        "MISSING_REQUIRED_DEPENDENCY"
    ]

    async def validate_with_continuation(
        self,
        data: Any,
        state: GlobalState
    ) -> ValidationResult:
        """Validate but allow continuation on non-critical issues."""

        issues = await self._run_all_checks(data)

        # Separate blocking vs. non-blocking
        blocking = [iss for iss in issues if iss.severity == "CRITICAL"]
        warnings = [iss for iss in issues if iss.severity in ["WARNING", "INFO"]]

        if blocking:
            # Must fix to continue
            state.validation_status = ValidationStatus.FAILED
            return ValidationResult(
                can_continue=False,
                message="Critical errors must be fixed",
                issues=blocking
            )

        else:
            # Non-blocking: Add to warnings, allow continuation
            state.validation_status = ValidationStatus.PASSED_WITH_WARNINGS
            state.deferred_warnings.extend(warnings)

            return ValidationResult(
                can_continue=True,
                message=f"✓ Validation passed with {len(warnings)} warnings (review later)",
                issues=warnings
            )
```

**Deferred Warning Display**:
```python
# During workflow: Silent or minimal logging
state.add_log(INFO, f"⚠️ {len(warnings)} warnings flagged for review")

# In final report: Prominent display
async def generate_validation_report(state: GlobalState):
    """Show all deferred warnings in final report."""

    report = f"""
VALIDATION REPORT
═════════════════

⚠️ WARNINGS REQUIRING REVIEW ({len(state.deferred_warnings)})

{chr(10).join(format_warning(w) for w in state.deferred_warnings)}

These issues won't prevent NWB file usage but should be addressed
for DANDI submission.

[Review] [Fix All] [Accept Anyway]
"""

    return report
```

**Progressive Validation**:
```python
async def validate_progressively(data: Any, state: GlobalState):
    """Run validation in stages, continue if possible."""

    # Stage 1: Quick checks (1-2 seconds)
    quick_issues = await quick_validate(data)
    if has_critical(quick_issues):
        return early_stop(quick_issues)

    # Allow user to continue while deep validation runs
    state.validation_status = ValidationStatus.IN_PROGRESS

    # Stage 2: Deep validation (30+ seconds) - async
    asyncio.create_task(deep_validate(data, state))

    return ValidationResult(
        can_continue=True,
        message="Quick validation passed, deep validation running in background..."
    )
```

### Benefits
- ✅ Maintains workflow momentum
- ✅ User not blocked by minor issues
- ✅ Batch review is faster than one-by-one
- ✅ User can prioritize critical issues first

### When to Apply
- Long forms with many validation rules
- Multi-step workflows
- File processing pipelines
- Data quality checking systems

### Warning Prioritization
```python
class WarningPriority(Enum):
    BLOCKING = "blocking"          # Must fix to continue
    HIGH = "high"                  # Should fix before final submit
    MEDIUM = "medium"              # Nice to fix
    LOW = "low"                    # Optional improvement

def prioritize_warnings(warnings: List[Warning]) -> List[Warning]:
    """Sort warnings by priority and impact."""

    priority_scores = {
        WarningPriority.BLOCKING: 1000,
        WarningPriority.HIGH: 100,
        WarningPriority.MEDIUM: 10,
        WarningPriority.LOW: 1
    }

    return sorted(
        warnings,
        key=lambda w: (
            priority_scores[w.priority],
            w.affects_dandi_submission,  # Boolean
            len(w.affected_fields)        # Impact scope
        ),
        reverse=True
    )
```

---

## Pattern 6: Dynamic Prompt Generation from Context

### Context
Static prompt templates feel generic and robotic. Users respond better to personalized, contextual messages.

### Problem
- Fixed templates: "Please provide experimenter name"
- Feels like government form-filling
- Doesn't acknowledge what system already knows
- Repetitive (same template for every user/file)

### Solution: LLM-Generated Prompts Using File and Conversation Context

**Implementation**:
```python
async def generate_contextual_request(
    missing_fields: List[str],
    file_info: Dict[str, Any],
    inference_results: Dict[str, Any],
    conversation_history: List[Dict],
    state: GlobalState
) -> str:
    """Generate personalized request based on complete context."""

    # Build context summary
    context_prompt = f"""Generate a personalized metadata request for this specific scenario.

FILE CONTEXT:
- Name: {file_info['filename']}
- Format: {file_info['detected_format']}
- Size: {file_info['size_mb']:.1f} MB
- Detected features: {file_info['features']}

WHAT I LEARNED FROM FILE ANALYSIS:
{json.dumps(inference_results['inferred_metadata'], indent=2)}

WHAT I STILL NEED:
{json.dumps(missing_fields, indent=2)}

CONVERSATION HISTORY:
{json.dumps(conversation_history[-3:], indent=2) if conversation_history else 'First interaction'}

INSTRUCTIONS:
1. Start by acknowledging specific file details you discovered
2. Explain why you need the missing information (DANDI compliance, discoverability)
3. Ask for missing fields with file-relevant examples
4. Make it conversational, not robotic
5. IMPORTANT: If this is a follow-up, be concise and acknowledge previous conversation
"""

    output_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "tone": {"type": "string"}
        }
    }

    result = await llm_service.generate_structured_output(
        prompt=context_prompt,
        output_schema=output_schema,
        system_prompt="You are a friendly NWB conversion assistant."
    )

    return result["message"]
```

**Example Output**:

**Static Template** (boring):
```
Please provide the following metadata:
• Experimenter
• Institution
• Subject ID
• Species
• Age
• Sex
```

**Dynamic Context-Aware** (engaging):
```
I've analyzed your SpikeGLX recording (Noise4Sam_g0_t0.imec0.ap.bin) and found:
✓ Format: Neuropixels 2.0 probe with 384 channels
✓ Recording: ~30 seconds at 30kHz sampling
✓ File size: 847 MB

To create a comprehensive NWB file for DANDI, I'd like to learn more about
your experiment. All fields are optional!

Could you share:
• Who conducted this recording? (e.g., "Smith, Jane")
• Which institution? (I'm guessing MIT based on your file path - correct?)
• Subject details: species, age, sex

You can provide everything in one message or skip individual fields.
```

**Follow-up** (acknowledges conversation):
```
Thanks for that info about Dr. Smith at MIT!

Just need a few quick details about your subject:
• Species (I'm guessing Mus musculus?)
• Age (in weeks or days)
• Sex

Type "skip" if you'd like to proceed with minimal metadata.
```

### Benefits
- ✅ Feels conversational, not transactional
- ✅ Shows system "understands" the specific file
- ✅ Reduces redundant questions
- ✅ Adapts to conversation flow

### When to Apply
- Chatbots and conversational UIs
- Form-filling assistants
- Customer support automation
- Onboarding flows

### Cost Consideration
```python
# Cache generated requests for similar contexts
@lru_cache(maxsize=100)
def get_cached_request(file_type: str, missing_fields_hash: str) -> Optional[str]:
    """Cache requests for similar file types and field combinations."""
    # If another user uploads similar file with same missing fields,
    # reuse generated request (with file-specific details swapped)
    ...

# Use cached template, swap file-specific details
if cached := get_cached_request(file_type, fields_hash):
    return cached.format(
        filename=file_info['filename'],
        format=file_info['format'],
        size=file_info['size_mb']
    )
else:
    # Generate new request with LLM
    return await generate_with_llm(...)
```

---

## Pattern 7: Workflow Trace for Reproducibility

### Context
Scientific and production systems require audit trails showing how outputs were generated.

### Problem
- Can't reproduce results
- No visibility into processing steps
- Hard to debug issues
- Compliance requirements unmet

### Solution: Comprehensive Workflow Trace in All Outputs

**Trace Structure**:
```python
@dataclass
class WorkflowTrace:
    """Complete record of processing workflow."""

    # Input provenance
    input_info: Dict[str, Any]  # Source file details
    input_format: str
    input_checksum: str

    # Processing steps
    steps: List[ProcessingStep]  # Ordered list of operations

    # Technologies used
    technologies: Dict[str, str]  # Tool → Version

    # Parameters
    parameters: Dict[str, Any]  # All configuration

    # Outputs
    outputs: List[str]  # Paths to generated files
    output_checksum: str

    # Metadata
    execution_time: datetime
    duration_seconds: float
    executed_by: str

async def build_workflow_trace(state: GlobalState) -> WorkflowTrace:
    """Build complete workflow trace from state."""

    return WorkflowTrace(
        input_info={
            "file_path": state.input_path,
            "file_size_bytes": Path(state.input_path).stat().st_size,
            "upload_time": state.upload_time.isoformat()
        },
        input_format=state.detected_format,
        input_checksum=calculate_sha256(state.input_path),

        steps=[
            ProcessingStep(
                step_number=1,
                description=f"Detected {state.detected_format} format",
                method="AI-powered analysis with rule-based fallback",
                duration_seconds=state.format_detection_duration
            ),
            ProcessingStep(
                step_number=2,
                description="Extracted metadata from file headers",
                method="Binary file parsing",
                duration_seconds=state.metadata_extraction_duration
            ),
            # ... all processing steps
        ],

        technologies={
            "neuroconv": neuroconv.__version__,
            "pynwb": pynwb.__version__,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}"
        },

        parameters={
            "compression": "gzip",
            "compression_level": 4,
            "chunk_shape": "auto"
        },

        outputs=[
            state.output_path,
            state.pdf_report_path,
            state.json_report_path
        ],
        output_checksum=calculate_sha256(state.output_path),

        execution_time=datetime.now(),
        duration_seconds=(datetime.now() - state.start_time).total_seconds(),
        executed_by="Agentic Neurodata Conversion v1.0"
    )
```

**Include in All Outputs**:
```python
# JSON Report
{
    "report_metadata": {...},
    "validation_results": {...},
    "workflow_trace": workflow_trace.to_dict(),  # Full trace
    ...
}

# PDF Report
"""
WORKFLOW TRACE
══════════════

Input Format: SpikeGLX
Processing Duration: 23.4 seconds

Technologies Used:
  • NeuroConv v0.6.3
  • PyNWB v2.8.2
  • Python 3.13.0

Processing Steps:
  1. Detected SpikeGLX format (AI + rules, 2.1s)
  2. Extracted metadata from .meta file (0.3s)
  3. Created SpikeGLXRecordingInterface (0.1s)
  4. Converted raw data to ElectricalSeries (18.2s)
  5. Validated with NWBInspector (2.7s)

Data Provenance:
  Original: /uploads/recording.bin (SHA256: a3f2...)
  Output: /outputs/recording.nwb (SHA256: b7e4...)
"""

# NWB File Metadata (embedded)
nwbfile.add_acquisition(
    ElectricalSeries(
        name="acquisition",
        data=recording_data,
        # ... other fields
    )
)

# Add processing history
processing_module = nwbfile.create_processing_module(
    name="provenance",
    description="Data processing provenance"
)

processing_module.add_data_interface(
    ProcessingHistory(
        description=json.dumps(workflow_trace.to_dict())
    )
)
```

### Benefits
- ✅ Scientific reproducibility
- ✅ Debugging capability (know exactly what happened)
- ✅ Compliance with data standards
- ✅ Builds user trust (transparency)

### When to Apply
- Scientific data processing
- Production ML pipelines
- Regulated industries (healthcare, finance)
- Any system requiring audit trails

### Minimal Trace for Simple Cases
```python
# Even minimal outputs should have basic trace
minimal_trace = {
    "tool": "Agentic NWB Converter v1.0",
    "input": input_path,
    "output": output_path,
    "timestamp": datetime.now().isoformat(),
    "version": "1.0.0"
}
```

---

## Best Practices Summary

### AI/LLM Integration

1. **Always provide fallback strategies** (Pattern 3: Graceful Degradation)
   - Don't hard-depend on LLM availability
   - Quality degrades, not functionality

2. **Use structured output schemas** (All patterns)
   - Define expected JSON schema
   - Validate LLM responses
   - Easier to handle programmatically

3. **Include confidence scores** (Pattern 2: Confidence-Tiered Automation)
   - Every AI decision should have confidence
   - Use for tiered automation strategies

4. **Schema-driven prompts** (Pattern 1: Schema-Driven Prompting)
   - Single source of truth
   - Dynamic prompt generation
   - Consistency guaranteed

### User Experience

5. **Adapt to user behavior** (Pattern 4: Conversation-Aware State)
   - Track user interaction patterns
   - Personalize responses
   - Learn preferences within session

6. **Don't interrupt workflow** (Pattern 5: Deferred Validation)
   - Defer non-blocking warnings
   - Batch review > one-by-one confirmation
   - Maintain momentum

7. **Context-aware communication** (Pattern 6: Dynamic Prompts)
   - Reference specific user/file context
   - Acknowledge previous conversation
   - Avoid robotic templates

### Architecture

8. **Centralize domain knowledge** (Pattern 1: Schema Registry)
   - One schema used everywhere
   - Validation, parsing, docs from same source
   - Easy to extend

9. **State machine for workflows** (Pattern 4)
   - Valid state transitions enforced
   - Clear phases
   - Easy debugging

10. **Comprehensive logging** (Pattern 7: Workflow Trace)
    - Every decision logged
    - Complete audit trail
    - Scientific reproducibility

### Development

11. **Test without LLM** (Pattern 3)
    - Mock LLM for unit tests
    - Fallback paths enable testing
    - Faster test execution

12. **Async for I/O** (All patterns)
    - Non-blocking LLM calls
    - Concurrent operations
    - Better performance

13. **Confidence calibration** (Pattern 2)
    - Track actual accuracy
    - Adjust thresholds empirically
    - Continuous improvement

---

## Anti-Patterns to Avoid

### ❌ LLM Over-Reliance
```python
# BAD: No fallback
async def parse_metadata(input: str):
    return await llm.parse(input)  # Fails if LLM down

# GOOD: Fallback strategy
async def parse_metadata(input: str):
    if llm_available:
        try:
            return await llm.parse(input)
        except LLMError:
            return rule_based_parse(input)
    else:
        return rule_based_parse(input)
```

### ❌ Binary Confidence Decisions
```python
# BAD: Hard threshold
if confidence > 70:
    auto_apply()
else:
    ask_user()  # Interrupts workflow

# GOOD: Tiered strategy
if confidence >= 80:
    auto_apply_silent()
elif confidence >= 50:
    auto_apply_with_note()
else:
    auto_apply_with_warning()  # Never interrupt
```

### ❌ Blocking Validation
```python
# BAD: Block user on every issue
for issue in validation_issues:
    user_response = await ask_user_to_fix(issue)
    # User stuck in loop

# GOOD: Deferred review
blocking = [iss for iss in issues if iss.severity == "CRITICAL"]
if blocking:
    must_fix(blocking)
else:
    flag_for_later_review(issues)
    continue_workflow()
```

### ❌ Static Templates
```python
# BAD: Same message for everyone
message = "Please provide experimenter name"

# GOOD: Contextual generation
message = await generate_contextual_request(
    missing_fields=["experimenter"],
    file_context=file_info,
    conversation_history=history
)
# Result: "I noticed you're recording at MIT - who's the lead experimenter?"
```

### ❌ Scattered Validation Rules
```python
# BAD: Rules in multiple places
if field == "age":
    validate_age(value)  # Logic here
# ... elsewhere
prompt = "Age should be ISO 8601"  # Duplicate rule
# ... elsewhere
schema = {"age": {"format": "duration"}}  # Another place

# GOOD: Single source of truth
age_schema = schema_registry.get("age")
validate(value, age_schema)
build_prompt(age_schema)
parse_with_llm(value, age_schema)
```

---

## Pattern Selection Guide

**Choose Schema-Driven Prompting when:**
- Domain has formal specifications
- Multiple AI tasks need same rules
- Format rules change frequently

**Choose Confidence-Tiered Automation when:**
- AI makes predictions with varying certainty
- Want to minimize user interruptions
- Errors are low-stakes (can be fixed later)

**Choose Graceful Degradation when:**
- Using external APIs (LLM, 3rd party)
- Need high availability
- Cost-conscious deployment

**Choose Conversation-Aware State when:**
- Multi-turn interactions
- Want to personalize UX
- Users have different interaction preferences

**Choose Deferred Validation when:**
- Many non-critical validation rules
- Workflow has multiple steps
- Batch review is more efficient

**Choose Dynamic Prompts when:**
- Conversational UI
- Have rich context (file analysis, user history)
- Want to feel less robotic

**Choose Workflow Trace when:**
- Scientific computing
- Compliance requirements
- Need reproducibility

---

## Conclusion

These patterns emerged from real-world development challenges and user feedback. They represent **proven solutions** to common problems in AI-powered conversational systems.

### Key Takeaways

1. **AI should enhance, not replace** rule-based logic (graceful degradation)
2. **Confidence scores enable smart automation** (tiered strategies)
3. **User experience beats perfect accuracy** (don't interrupt workflow)
4. **Context makes interactions feel intelligent** (dynamic prompts)
5. **Single source of truth prevents drift** (schema-driven design)

### Applying These Patterns

These patterns are **generalizable** beyond NWB conversion:
- E-commerce product data normalization
- Medical form filling assistants
- Legal document drafting tools
- Any conversational data collection system

**Start with**: Schema-Driven Prompting + Confidence-Tiered Automation
**Add as needed**: Other patterns based on requirements

---

**END OF DOCUMENT**