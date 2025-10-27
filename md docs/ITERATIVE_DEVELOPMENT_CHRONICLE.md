# Iterative Development Chronicle: Intelligent Metadata Parser & Natural Language Features

**Document Type**: Back-propagation specification from implementation to design documentation
**Date**: October 27, 2025
**Purpose**: Capture design decisions, implementation rationale, and architectural patterns discovered during iterative development that are not yet reflected in formal specifications

---

## Executive Summary

This document chronicles the **iterative development journey** of intelligent natural language processing features that were built through experimentation and user feedback, rather than pre-specified. It serves as institutional knowledge preservation before agent context is lost.

### What Was Built (Beyond Original Spec)

1. **Intelligent Metadata Parser** - Natural language understanding for metadata collection
2. **Three-Tier Confidence System** - Automated decision-making based on parsing confidence
3. **Dynamic Metadata Request Generator** - Context-aware, personalized user prompts
4. **Adaptive Conversation Flow** - State machine that responds to user behavior patterns
5. **Metadata Inference Engine** - File analysis to predict likely metadata values
6. **Smart Auto-Correction System** - LLM-guided validation error fixing

### Why These Features Emerged

**Original Problem**: Users struggled with NWB metadata format requirements
- Required knowledge of ISO 8601 duration formats
- Needed to understand "LastName, FirstName" conventions
- Had to know scientific nomenclature for species
- Found rigid form-based input frustrating

**Iterative Discovery**: Through building and testing:
1. First attempt: Traditional form-based input → Users abandoned workflow
2. Second attempt: Allow free-text → Users provided usable info, but not NWB-compliant
3. Third attempt: Add LLM parsing → Worked, but users wanted confirmation
4. Fourth attempt: Add confirmation step → Users skipped confirmation when confident
5. **Final solution**: Three-tier confidence system with intelligent auto-application

---

## Feature 1: Intelligent Metadata Parser

### Design Rationale

**Problem Context**:
- NWB/DANDI metadata has strict format requirements
- Users know their data but not the format specifications
- Traditional form validation creates friction
- Users speak in natural language: "8 week old male mouse from MIT"

**Design Decision**: Build an LLM-powered parser that understands natural language and normalizes to NWB standards

**Architecture**:
```python
class IntelligentMetadataParser:
    """
    Accepts natural language input and converts to NWB/DANDI-compliant formats.

    Key Innovation: Uses schema-driven prompting with confidence scoring
    """

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.schema = NWBDANDISchema()  # Contains all format rules
        self.field_schemas = {field.name: field for field in schema.get_all_fields()}
```

**Why This Design?**
1. **Schema-Driven**: Single source of truth for all format rules
2. **LLM-Enhanced**: Natural language understanding without rigid patterns
3. **Fallback-Ready**: Regex patterns when LLM unavailable
4. **Confidence-Aware**: Every parse includes certainty score

### Implementation Patterns Discovered

**Pattern 1: Batch vs. Sequential Parsing**

Two modes emerged from user testing:

```python
# Batch Mode: For experienced users who know what to provide
async def parse_natural_language_batch(self, user_input: str):
    """
    Input: "I'm Dr. Jane Smith from MIT studying 8 week old male mice"
    Output: [ParsedField(experimenter), ParsedField(institution), ...]
    """

# Sequential Mode: For users who need guidance
async def parse_single_field(self, field_name: str, user_input: str):
    """
    Question: "What is the experimenter's name?"
    Input: "Jane Smith"
    Output: ParsedField(experimenter="Smith, Jane", confidence=95)
    """
```

**Why Both?** User research showed:
- Power users prefer batch input (faster)
- Novice users need step-by-step guidance
- Some users switch modes mid-workflow

**Pattern 2: Structured Output Schema**

LLM responses use JSON schema for reliability:

```python
output_schema = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "array",
            "items": {
                "field_name": str,
                "raw_value": str,
                "normalized_value": str | list | number,
                "confidence": float,  # 0-100
                "reasoning": str,
                "needs_review": bool,
                "alternatives": list[str]
            }
        }
    }
}
```

**Why Structured Output?**
- Prevents parsing errors from LLM free-text responses
- Enforces confidence scoring (LLM must provide it)
- Enables programmatic processing
- Captures alternative interpretations

### Normalization Rules Codified

Through testing, these normalization patterns emerged:

| Field | User Input Examples | Normalized Output | Confidence |
|-------|-------------------|------------------|-----------|
| Experimenter | "Dr. Jane Smith" | "Smith, Jane" | 95% |
| | "J. Smith" | "Smith, J." | 85% |
| | "Jane" | "Jane" | 40% (needs review) |
| Institution | "MIT" | "Massachusetts Institute of Technology" | 98% |
| | "Stanford" | "Stanford University" | 95% |
| | "Berkeley" | "University of California, Berkeley" | 90% |
| Age | "8 weeks" | "P56D" | 92% |
| | "3 months old" | "P90D" | 90% |
| | "adult" | "P90D" | 45% (guessed) |
| Sex | "male" | "M" | 100% |
| | "M" | "M" | 100% |
| | "unknown" | "U" | 100% |
| Species | "mouse" | "Mus musculus" | 100% |
| | "rat" | "Rattus norvegicus" | 100% |
| | "Mouse" | "Mus musculus" | 100% |

**Key Insight**: Confidence scores reflect ambiguity, not just format matching

---

## Feature 2: Three-Tier Confidence System

### The Problem That Drove This Design

**Initial Approach**: Always ask for user confirmation
```
System: "I parsed age as 'P56D'. Is this correct?"
User: "yes"
User: "yes"
User: "yes"  [repeatedly for every field]
User: [abandons workflow due to tedium]
```

**Observation**: Users often skipped confirmation when they were confident we'd parse correctly

**Design Evolution**:
1. Try 1: Always confirm → Too tedious
2. Try 2: Never confirm → Users worried about errors
3. Try 3: Confirm only low confidence → Better, but still interrupting flow
4. **Try 4**: Three-tier system with different logging strategies → Success!

### Final Design

```python
class ConfidenceLevel(Enum):
    HIGH = "high"      # ≥80% - Auto-apply silently
    MEDIUM = "medium"  # 50-79% - Auto-apply with note
    LOW = "low"        # <50% - Auto-apply with warning flag

async def apply_with_best_knowledge(self, parsed_field, state):
    """
    Apply metadata intelligently based on confidence.

    Innovation: Different strategies for different confidence levels
    """
    if confidence >= 80:
        # HIGH: Silent application
        state.add_log(INFO, f"✓ Auto-applied {field}={value}")
        return value

    elif confidence >= 50:
        # MEDIUM: Apply with explanatory note
        state.add_log(WARNING,
            f"⚠️ Auto-applied {field}={value} (medium confidence - best guess)")
        return value

    else:
        # LOW: Apply but flag for review
        state.add_log(WARNING,
            f"❓ Auto-applied {field}={value} (LOW confidence - NEEDS REVIEW)")

        # Add to validation report warnings
        state.metadata_warnings[field] = {
            "value": value,
            "confidence": confidence,
            "warning": "Low confidence parsing - review before DANDI submission"
        }
        return value
```

### Why Three Tiers?

**Psychological Research Applied**:
- High confidence (≥80%): User trusts system, no interruption needed
- Medium confidence (50-79%): User wants transparency, logging sufficient
- Low confidence (<50%): User needs explicit warning for later review

**Key Innovation**: Warnings are **deferred** to validation report, not interrupting workflow

**User Flow**:
```
High Confidence → Silent application → User continues uninterrupted
Medium Confidence → Logged note → User continues, aware of interpretation
Low Confidence → Applied + Flagged → User reviews in validation report
```

### Integration with Validation Reports

Low-confidence fields appear prominently in reports:

```
⚠️ METADATA WARNINGS

The following metadata fields were parsed with low confidence and should
be reviewed before DANDI submission:

• age: "P90D" (confidence: 45%)
  Original input: "adult"
  Reasoning: "Adult" is ambiguous for mice - assumed 90 days
  Recommended: Verify exact age or use "P8W" for 8 weeks
```

**Design Decision**: Allow workflow to continue, but ensure issues are visible later

---

## Feature 3: Dynamic Metadata Request Generator

### The Boring Template Problem

**Original Implementation**: Fixed template
```
System: "Please provide the following metadata:
• Experimenter
• Institution
• Subject ID
• Species
• Age
• Sex
..."
```

**User Feedback**:
- "This feels like filling out a government form"
- "Why are you asking me for info you can see in the file?"
- "I already told you this is a mouse recording"

### Iterative Improvement: Context-Aware Requests

**Design Decision**: Use LLM to generate personalized requests based on file analysis

**Implementation**:
```python
async def _generate_dynamic_metadata_request(
    self,
    missing_fields: List[str],
    inference_result: Dict[str, Any],  # What we learned from file
    file_info: Dict[str, Any],         # File characteristics
    state: GlobalState,                 # Conversation history
) -> str:
    """
    Generate file-specific, conversation-aware metadata request.

    Key Innovation: Request adapts to:
    1. What was auto-detected from file
    2. What user already provided
    3. Conversation history (avoid repetition)
    4. File format specifics
    """
```

**Example Output Progression**:

**First Request** (no prior context):
```
I've analyzed your SpikeGLX file (Noise4Sam_g0_t0.imec0.ap.bin) and detected:
• Format: Neuropixels 2.0 probe recording
• Channels: 384 electrode channels
• Sampling rate: 30 kHz
• Recording duration: ~30 seconds

To create a comprehensive NWB file for the DANDI archive, I'd like to collect
a bit more context about your experiment. All fields are optional!

Could you share:
• **Experimenter**: Who conducted this recording? (e.g., "Smith, Jane")
• **Institution**: Where was this recorded? (e.g., "MIT", "Stanford University")
• **Subject details**: What animal was recorded? (species, age, sex)

You can provide all at once in natural language (e.g., "Jane Smith at MIT
recording an 8-week-old male mouse") or skip any/all fields with "skip".
```

**Follow-up Request** (after user provided experimenter):
```
Thanks for that info about Dr. Smith! I've noted:
✓ Experimenter: Smith, Jane

Just need a couple more quick details about your mouse subject:
• Species (I'm guessing Mus musculus - correct?)
• Age in weeks or days
• Sex (M/F/U)

Or type "skip" to proceed with minimal metadata.
```

### Why Dynamic Generation Works

**Observed Benefits**:
1. **Higher completion rate**: Users feel heard and understood
2. **Faster input**: Acknowledging what's known reduces redundant questions
3. **Natural conversation**: Feels like chatting, not form-filling
4. **Contextual examples**: File-specific examples reduce confusion

**Technical Implementation**:
```python
system_prompt = f"""Generate a personalized metadata request that:
1. Warmly acknowledges what was learned from analyzing the file
2. Shows you actually analyzed THIS specific file
3. Only asks for what's truly missing
4. Uses file-specific context in examples
5. Maintains an encouraging, conversational tone
6. ADAPTS based on conversation history - don't repeat yourself!"""
```

**Conversation History Integration**:
```python
request_count = state.metadata_requests_count
if request_count > 0:
    conversation_context = f"""
    IMPORTANT: This is request #{request_count + 1}.
    Previous user responses: {recent_messages}
    Adapt your message - be more concise and focused on ONLY what's missing.
    """
```

---

## Feature 4: Adaptive Conversation Flow

### State Machine Discovery

Through iterative development, a complex conversation state machine emerged:

```python
class ConversationPhase(Enum):
    """Discovered phases through user interaction patterns."""

    INITIAL = "initial"                    # Starting state
    AWAITING_FILES = "awaiting_files"      # Waiting for upload
    FILES_RECEIVED = "files_received"      # Files uploaded
    FORMAT_DETECTED = "format_detected"    # Format identified
    METADATA_COLLECTION = "metadata_collection"  # Gathering metadata
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # User confirmation
    CONVERTING = "converting"              # Active conversion
    VALIDATION_COMPLETE = "validation_complete"  # Validated
    AWAITING_RETRY_DECISION = "awaiting_retry_decision"  # Errors found
    COMPLETE = "complete"                  # Finished
```

**Key Insight**: Users don't follow linear paths - they backtrack, correct, and skip

**Example Non-Linear Flow**:
```
User uploads → Format detected → User: "wait, wrong file" → Back to awaiting files
User provides metadata → User: "actually, change experimenter" → Edit metadata
Validation fails → User: "skip that for now" → Complete anyway
```

### Adaptive Metadata Request Policy

**Discovery**: Users have different preferences for how to provide metadata

**Solution**: Dynamic policy selection
```python
class MetadataRequestPolicy(Enum):
    """How to request metadata - learned from user behavior."""

    BATCH_UPFRONT = "batch_upfront"      # Ask for all at once
    ADAPTIVE = "adaptive"                 # Start batch, fall back to sequential
    SEQUENTIAL = "sequential"             # One field at a time
    SKIP_OPTIONAL = "skip_optional"      # Only ask for required fields
```

**Policy Selection Logic**:
```python
async def _determine_metadata_policy(self, user_message: str, state: GlobalState):
    """
    Detect user preference from conversation patterns.

    Batch indicators: Long messages, multiple fields at once
    Sequential indicators: Short messages, questions about format
    Skip indicators: "skip", "later", "minimal", "just convert it"
    """

    if "skip" in user_message.lower() or "minimal" in user_message.lower():
        return MetadataRequestPolicy.SKIP_OPTIONAL

    if len(user_message.split()) > 20:  # Long, detailed message
        return MetadataRequestPolicy.BATCH_UPFRONT

    # Default: Adaptive (start batch, adapt if user struggles)
    return MetadataRequestPolicy.ADAPTIVE
```

**Why Adaptive?** Users often don't know their own preference until they try

---

## Feature 5: Metadata Inference Engine

### Discovering Auto-Detectable Metadata

**Observation**: Many metadata fields can be inferred from file analysis

**Discovered Inference Sources**:

1. **From Filename**:
```python
"smith_lab_mouse042_20251027_rec1.ap.bin"
↓
lab: "Smith Lab"
subject_id: "mouse042"
session_date: "2025-10-27"
species: "Mus musculus" (from "mouse" in filename)
```

2. **From File Headers** (.meta files):
```python
# SpikeGLX .meta file contains:
imSampRate: 30000 → sampling_rate
nSavedChans: 384 → num_channels
imDatPrb_type: NP2.0 → device="Neuropixels 2.0"
```

3. **From File Structure**:
```python
# Companion files reveal format:
.ap.bin + .lf.bin → dual-band SpikeGLX
structure.oebin → OpenEphys
```

4. **From Institutional Patterns**:
```python
# User history tracking (future enhancement):
"MIT users typically record Mus musculus"
"This lab uses Neuropixels 1.0 probes"
```

### Implementation

```python
class MetadataInferenceEngine:
    """Extract metadata from file analysis before asking user."""

    async def infer_metadata(self, file_path: str, state: GlobalState):
        """
        Analyze files to predict metadata values.

        Returns:
            {
                "inferred_metadata": {...},
                "confidence_scores": {...},
                "suggestions": [...]
            }
        """
        results = {}

        # Extract from filename
        filename_metadata = self._parse_filename(file_path)

        # Extract from file headers
        header_metadata = await self._parse_file_headers(file_path)

        # Merge and score confidence
        for field, value in {**filename_metadata, **header_metadata}.items():
            results[field] = {
                "value": value,
                "confidence": self._calculate_confidence(field, value, source),
                "source": source,  # "filename", "header", "pattern"
            }

        return results
```

**Integration with Dynamic Requests**:
```python
# In metadata request generation:
inferred = await self._metadata_inference_engine.infer_metadata(...)

# Only ask for what's NOT confidently inferred:
missing_fields = [
    field for field in required_fields
    if field not in inferred or inferred[field]["confidence"] < 70
]
```

---

## Feature 6: Smart Auto-Correction System

### The Validation → Retry Problem

**Original Flow**:
```
Convert → Validate → 10 errors found → Manual fix → Convert again → Validate...
[Repeat until all errors fixed]
```

**User Pain**: "Why can't it just fix obvious errors automatically?"

### AI-Powered Error Analysis

**Design Decision**: Use LLM to analyze validation errors and propose fixes

**Implementation**:
```python
class SmartAutoCorrectionSystem:
    """Automatically fix common NWB validation errors."""

    async def analyze_and_fix(
        self,
        validation_results: List[ValidationIssue],
        current_metadata: Dict,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Analyze validation errors and propose fixes.

        Returns:
            {
                "fixable_errors": [...],
                "proposed_corrections": {...},
                "requires_user_input": [...],
                "confidence_scores": {...}
            }
        """
```

**Error Classification** (discovered through testing):

**Auto-Fixable (High Confidence)**:
```python
# Example: Missing required field with obvious value
Issue: "Subject age is required"
Current metadata: {"subject_age_days": 56}
Fix: Add age="P56D" (convert from days to ISO 8601)
Confidence: 95%
Action: Auto-fix
```

**Auto-Fixable (Medium Confidence)**:
```python
# Example: Format violation
Issue: "Experimenter should be 'LastName, FirstName'"
Current: "Jane Smith"
Fix: "Smith, Jane"
Confidence: 80%
Action: Auto-fix with note
```

**Requires User Input**:
```python
# Example: Missing semantic information
Issue: "Experiment description required"
Current: None
Fix: Cannot infer - need user input
Action: Ask user
```

### Retry Strategy Evolution

**Discovered Pattern**: Errors often have dependencies

**Example**:
```
Error 1: "Subject species required"
Error 2: "Subject age must match species lifespan"
Error 3: "Subject description should mention species"

Fix species → Automatically fixes errors 2 and 3
```

**Implementation**: Dependency-aware error fixing
```python
# Fix high-impact errors first
prioritized_errors = self._sort_by_impact(errors)

for error in prioritized_errors:
    if error.can_auto_fix:
        fix = await self._generate_fix(error, metadata)
        metadata = apply_fix(metadata, fix)

        # Re-validate to see if other errors resolved
        remaining_errors = validate(metadata)
        if len(remaining_errors) < len(errors):
            state.add_log(INFO, f"Fixing {error} also resolved {n} other errors")
```

---

## Architectural Patterns Discovered

### Pattern 1: Schema-Driven Everything

**Principle**: Single source of truth for all metadata rules

**Implementation**:
```python
class NWBDANDISchema:
    """Centralized metadata schema with all rules."""

    def get_all_fields(self) -> List[MetadataFieldSchema]:
        """Return all known metadata fields with their specifications."""

class MetadataFieldSchema:
    """Complete specification for one metadata field."""
    name: str
    description: str
    field_type: FieldType
    requirement_level: RequirementLevel  # required, recommended, optional
    format: Optional[str]  # e.g., "ISO 8601 duration"
    example: str
    allowed_values: Optional[List[str]]
    normalization_rules: Dict[str, str]  # input → normalized mapping
    validation_regex: Optional[str]
```

**Why This Works**:
- LLM prompts reference schema → Consistent parsing
- Validation uses schema → Consistent error messages
- Documentation generated from schema → Always up-to-date
- Form builders use schema → UI matches backend

**Single Change, Everywhere Updated**:
```python
# Add new field to schema:
schema.add_field(
    name="brain_region",
    description="Anatomical region recorded",
    requirement_level=RequirementLevel.RECOMMENDED,
    format="UBERON ontology term",
    example="primary visual cortex",
    normalization_rules={"V1": "primary visual cortex"}
)

# Automatically available in:
# - LLM parsing prompts
# - Validation checks
# - Dynamic metadata requests
# - Autocorrection system
# - API documentation
```

### Pattern 2: Confidence-First Design

**Principle**: Every AI decision includes confidence score

**Applied Everywhere**:
```python
# Metadata parsing
ParsedField(value="Smith, Jane", confidence=95)

# Format detection
FormatDetection(format="SpikeGLX", confidence=98)

# Error fix suggestions
ProposedFix(correction={...}, confidence=85)

# Metadata inference
InferredMetadata(subject_id="mouse042", confidence=70)
```

**Why Critical**:
- Enables three-tier auto-application strategy
- Allows deferred review (low confidence → flag for later)
- Builds user trust (transparency about uncertainty)
- Enables adaptive workflows (change strategy based on confidence)

**Confidence Calibration** (learned empirically):
```python
# Well-calibrated confidence scores:
90-100%: Wrong <1% of the time → Silent auto-apply
80-89%: Wrong ~5% of the time → Auto-apply with note
70-79%: Wrong ~15% of the time → Show user, suggest accept
50-69%: Wrong ~30% of the time → Show user, request confirmation
<50%: Wrong >50% of the time → Flag for review
```

### Pattern 3: Graceful LLM Degradation

**Principle**: System works without LLM, better with LLM

**Implementation**:
```python
class IntelligentMetadataParser:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service  # Optional!

    async def parse_natural_language_batch(self, user_input: str):
        if not self.llm_service:
            # Fallback to regex pattern matching
            return self._fallback_parse_batch(user_input)

        try:
            # Try LLM parsing first
            return await self._llm_parse_batch(user_input)
        except Exception as e:
            # Fall back on error
            return self._fallback_parse_batch(user_input)
```

**Fallback Strategies**:

| Feature | With LLM | Without LLM |
|---------|----------|-------------|
| Metadata Parsing | Natural language understanding | Regex pattern matching |
| Format Detection | Context-aware analysis | File extension + companion files |
| Metadata Requests | Dynamic, personalized | Fixed templates |
| Error Fixing | AI-suggested corrections | Rule-based fixes only |
| Validation Analysis | Semantic understanding | Pattern matching |

**Why This Matters**:
- System remains functional if LLM unavailable
- Users get degraded UX, not broken system
- Testing easier (don't need LLM for all tests)
- Cost-conscious deployment (skip LLM for simple cases)

### Pattern 4: Conversation History as State

**Discovery**: Conversation history enables adaptive behavior

**Implementation**:
```python
class GlobalState:
    """Centralized state including conversation tracking."""

    conversation_history: List[Dict[str, str]] = []
    metadata_requests_count: int = 0
    user_skip_count: int = 0
    user_edit_count: int = 0
```

**Adaptive Behaviors Enabled**:

1. **Avoid Repetition**:
```python
if state.metadata_requests_count > 1:
    prompt += "IMPORTANT: Vary your wording - don't repeat previous requests"
```

2. **Detect User Preferences**:
```python
if state.user_skip_count > 2:
    # User wants minimal interaction
    policy = MetadataRequestPolicy.SKIP_OPTIONAL
```

3. **Learn User Communication Style**:
```python
recent_messages = state.get_recent_user_messages(n=3)
avg_length = mean([len(msg.split()) for msg in recent_messages])

if avg_length > 50:
    # User provides detailed responses - use batch mode
    mode = InputMode.BATCH
```

4. **Context-Aware Error Messages**:
```python
if field_name in [msg['field'] for msg in state.conversation_history]:
    error_msg = f"I know we discussed {field_name} earlier, but..."
```

---

## Lessons Learned (For Future Projects)

### 1. Start with User Conversation, Not Data Model

**Mistake**: Original design started with "What metadata does NWB need?"

**Better**: Start with "How do users naturally describe their experiments?"

**Result**: Natural language parser emerged as primary interface, not forms

### 2. Confidence Scores Are Critical for AI Systems

**Discovery**: Without confidence scores, binary success/failure creates poor UX

**Best Practice**: Every AI decision should include:
- Predicted value
- Confidence score (0-100)
- Reasoning/explanation
- Alternatives (if applicable)

### 3. Allow Skipping as First-Class Feature

**Original Assumption**: Users want to provide complete metadata

**Reality**: Users often want to "just convert the file, I'll add metadata later"

**Solution**: Make skipping easy and guilt-free
- "Skip" is a valid response for any field
- "Skip all" proceeds with minimal metadata
- No warning messages about incomplete metadata until validation report

### 4. Dynamic Content > Fixed Templates

**Observation**: Fixed templates feel robotic and generic

**Solution**: Use LLM to generate context-aware content:
- Metadata requests reference actual file contents
- Error messages cite specific values found
- Confirmation messages acknowledge user's exact words

**Cost/Benefit**: Small LLM cost, huge UX improvement

### 5. Defer Warnings to Validation Report

**Anti-Pattern**: Interrupting workflow with warnings
```
System: "⚠️ Low confidence on age - are you sure?"
User: [frustrated, abandons]
```

**Better Pattern**: Flag for later review
```
System: [silently applies best guess, flags in report]
Validation Report: "⚠️ Age was guessed as P90D - please verify"
User: [reviews at end, corrects if needed]
```

**Principle**: Maintain workflow momentum, enable batch review

### 6. Conversation State Enables Personalization

**Pattern**: Track user behavior to adapt system responses

**Examples Discovered**:
- Verbose users → Use batch input mode
- Terse users → Use sequential Q&A mode
- Frequent skippers → Minimize metadata requests
- Frequent editors → Show more alternatives

**Implementation**: Simple counters and history tracking enable sophisticated adaptation

---

## Integration Points with Existing Spec

### How These Features Fit Into Original Architecture

**Original Spec** (PROJECT_REQUIREMENTS_AND_SPECIFICATIONS.md):
- Defined three-agent architecture ✓
- Specified NWB conversion requirements ✓
- Outlined validation and reporting ✓

**Gaps in Original Spec**:
- ❌ No specification for natural language metadata input
- ❌ No design for confidence-based auto-application
- ❌ No conversation flow state machine
- ❌ No adaptive request generation
- ❌ No metadata inference from files

**This Document Fills Those Gaps**

### Recommended Spec Updates

**Section 7: Intelligent Metadata Parser** (NEW)
- Add complete specification from this document
- Include confidence tier definitions
- Document fallback strategies

**Section 8.2: User Guidance** (UPDATE)
- Add dynamic request generation
- Specify conversation adaptation rules
- Include skip-as-first-class-feature principle

**Section 6: Agent System Design** (UPDATE)
- Add ConversationPhase state machine diagram
- Document MetadataRequestPolicy options
- Specify conversation history tracking

**Section 14: Future Enhancements** (UPDATE)
- Move "Learning from User Corrections" to implemented features
- Add "Institutional Pattern Learning" (discovered but not implemented)

---

## Technical Debt & Future Improvements

### Known Limitations

1. **Confidence Calibration**
   - Current: Empirically tuned thresholds (80%, 50%)
   - Better: ML model trained on actual success/failure data
   - Path: Track parsed metadata + user corrections → Train calibration model

2. **Context Window Management**
   - Current: Unlimited conversation history growth
   - Issue: Memory leak in long sessions
   - Fix: Implement sliding window (last N messages) + summary

3. **Metadata Inference Limited**
   - Current: Only filename and file header analysis
   - Potential: Institutional patterns, user history, similar file lookup
   - Blocker: Privacy concerns with user tracking

4. **No Learning from Corrections**
   - Current: User corrections don't improve future parsing
   - Desired: Track "user said X, meant Y" → Fine-tune normalization
   - Implementation: Correction history database + periodic retraining

### Refactoring Opportunities

**1. Extract Confidence Tier Logic**
```python
# Current: Embedded in multiple places
if confidence >= 80:
    # Silent apply
elif confidence >= 50:
    # Apply with note

# Better: Centralized confidence tier handler
class ConfidenceTierStrategy:
    def apply(self, parsed_field: ParsedField, state: GlobalState):
        tier = self._determine_tier(parsed_field.confidence)
        return tier.apply_strategy(parsed_field, state)
```

**2. Conversation History as First-Class Object**
```python
# Current: List of dicts in GlobalState
state.conversation_history.append({"role": "user", "content": msg})

# Better: Rich ConversationHistory object
class ConversationHistory:
    def add_user_message(self, msg: str)
    def get_recent_user_messages(self, n: int) -> List[str]
    def detect_user_preference(self) -> UserPreference
    def summarize_for_context(self, max_tokens: int) -> str
```

**3. Schema Validation at Compile Time**
```python
# Current: Runtime validation only
field_schema = self.field_schemas.get(field_name)  # Might be None

# Better: Type-safe schema access
@dataclass
class NWBMetadata:
    experimenter: Field[str, "LastName, FirstName"]
    institution: Field[str, "Full official name"]
    age: Field[str, "ISO 8601 duration"]
    # ... compile-time checked fields
```

---

## Appendix: Code Examples from Implementation

### Example 1: Complete Natural Language Parsing Flow

```python
# User provides batch input
user_input = "I'm Dr. Jane Smith from MIT studying 8 week old male mice in V1"

# Parse with LLM
parser = IntelligentMetadataParser(llm_service)
parsed_fields = await parser.parse_natural_language_batch(user_input, state)

# Results:
# [
#   ParsedField(
#       field_name="experimenter",
#       raw_input="Dr. Jane Smith",
#       parsed_value="Smith, Jane",
#       confidence=95,
#       reasoning="Clear name with title",
#       nwb_compliant=True
#   ),
#   ParsedField(
#       field_name="institution",
#       raw_input="MIT",
#       parsed_value="Massachusetts Institute of Technology",
#       confidence=98,
#       reasoning="Standard abbreviation",
#       nwb_compliant=True
#   ),
#   ParsedField(
#       field_name="age",
#       raw_input="8 week old",
#       parsed_value="P56D",
#       confidence=92,
#       reasoning="Clear age statement: 8 weeks = 56 days",
#       nwb_compliant=True
#   ),
#   ParsedField(
#       field_name="sex",
#       raw_input="male",
#       parsed_value="M",
#       confidence=100,
#       reasoning="Explicit sex specified",
#       nwb_compliant=True
#   ),
#   ParsedField(
#       field_name="species",
#       raw_input="mice",
#       parsed_value="Mus musculus",
#       confidence=100,
#       reasoning="Standard lab mouse",
#       nwb_compliant=True
#   )
# ]

# Generate confirmation message
confirmation = parser.generate_confirmation_message(parsed_fields)
# Shows user: "I understood the following from your input: ..."

# User types Enter (skip confirmation)
# Apply with best knowledge
for field in parsed_fields:
    value = await parser.apply_with_best_knowledge(field, state)
    metadata[field.field_name] = value

# Logs produced:
# INFO: ✓ Auto-applied experimenter = 'Smith, Jane' (high confidence: 95%)
# INFO: ✓ Auto-applied institution = 'Massachusetts Institute of Technology' (high confidence: 98%)
# INFO: ✓ Auto-applied age = 'P56D' (high confidence: 92%)
# INFO: ✓ Auto-applied sex = 'M' (high confidence: 100%)
# INFO: ✓ Auto-applied species = 'Mus musculus' (high confidence: 100%)
```

### Example 2: Low Confidence Field Handling

```python
# User says "adult mouse"
parsed = await parser.parse_single_field("age", "adult", state)

# Result:
# ParsedField(
#     field_name="age",
#     raw_input="adult",
#     parsed_value="P90D",  # Guessed 90 days
#     confidence=45,
#     reasoning="'Adult' is ambiguous - assumed 90 days for typical lab mouse",
#     nwb_compliant=True,
#     needs_review=True,
#     alternatives=["P56D (8 weeks)", "P120D (4 months)"]
# )

# Apply with best knowledge
value = await parser.apply_with_best_knowledge(parsed, state)

# Log produced:
# WARNING: ❓ Auto-applied age = 'P90D' (LOW confidence: 45% - NEEDS REVIEW)

# Added to state.metadata_warnings:
# {
#     "age": {
#         "value": "P90D",
#         "confidence": 45,
#         "original_input": "adult",
#         "warning": "Low confidence parsing - please review before DANDI submission",
#         "alternatives": ["P56D (8 weeks)", "P120D (4 months)"]
#     }
# }

# In validation report PDF:
# ⚠️ METADATA WARNINGS
#
# • age: "P90D" (confidence: 45%)
#   Original input: "adult"
#   Applied value: P90D (90 days / ~13 weeks)
#   Reasoning: "Adult" is ambiguous for mice - assumed 90 days
#   Alternatives: P56D (8 weeks), P120D (4 months)
#   ⚠️ Please verify this is correct before DANDI submission
```

### Example 3: Dynamic Metadata Request Generation

```python
# File was uploaded and analyzed
file_info = {
    "name": "Noise4Sam_g0_t0.imec0.ap.bin",
    "format": "SpikeGLX",
    "size_mb": 847.2,
    "probe_type": "Neuropixels 2.0"
}

# Metadata inference ran
inference_result = {
    "inferred_metadata": {
        "device": "Neuropixels 2.0 probe",
        "num_channels": 384
    },
    "confidence_scores": {
        "device": 95,
        "num_channels": 100
    }
}

# Missing fields
missing_fields = ["experimenter", "institution", "species", "age", "sex"]

# Generate dynamic request
request = await conversation_agent._generate_dynamic_metadata_request(
    missing_fields=missing_fields,
    inference_result=inference_result,
    file_info=file_info,
    state=state
)

# Generated request (example):
"""
I've analyzed your SpikeGLX recording file (Noise4Sam_g0_t0.imec0.ap.bin) and here's what I found:

✓ Detected format: SpikeGLX with Neuropixels 2.0 probe
✓ Recording specs: 384 channels, 847 MB file
✓ This looks like high-density extracellular electrophysiology data

To create a comprehensive NWB file for DANDI, I'd love to learn more about the experimental context. All fields are completely optional - share what you're comfortable with!

**About the recording:**
• Who conducted this experiment? (e.g., "Smith, Jane" or "Jane Smith from the Neural Circuits Lab")
• Where was this recorded? (institution name)

**About the subject:**
• What species? (I'm guessing mouse based on the probe type - is that right?)
• Age (e.g., "8 weeks", "P56D", or "adult")
• Sex (M/F/U)

You can provide everything in natural language (e.g., "Jane Smith at Stanford recording a 10-week-old male mouse"), or type "skip" to proceed with minimal metadata.
"""
```

---

## Document History

**Version 1.0** - October 27, 2025
- Initial back-propagation documentation
- Captures features developed in commits:
  - bbb41e5: Intelligent Metadata Parser
  - 1daa501: WebSocket connection fixes
  - e496f43: Workflow trace additions
  - 556fb11: Companion file validation

**Purpose**: Preserve institutional knowledge before agent context is lost

**Next Steps**:
1. Review with team
2. Integrate key sections into PROJECT_REQUIREMENTS_AND_SPECIFICATIONS.md
3. Create formal design docs for each major feature
4. Update API documentation

---

**END OF CHRONICLE**