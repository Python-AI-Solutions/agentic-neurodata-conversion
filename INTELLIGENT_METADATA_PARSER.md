# Intelligent Metadata Parser with User Confirmation

## Overview

The system now features an **Intelligent Metadata Parser** that accepts natural language input from users and automatically converts it to NWB/DANDI-compliant formats with a three-tier confidence-based confirmation system.

## Features

### 1. Natural Language Understanding
Users can provide metadata in plain English instead of strict formats:

**Before** (rigid format required):
```
experimenter: Smith, Jane
institution: Massachusetts Institute of Technology
age: P56D
```

**Now** (natural language accepted):
```
"I'm Dr. Jane Smith from MIT studying 8 week old mice"
```

### 2. Automatic Format Normalization

The parser automatically converts user input to NWB/DANDI standards:

| Input | Normalized Output | Format |
|-------|-------------------|--------|
| "Dr. Jane Smith" | "Smith, Jane" | LastName, FirstName |
| "MIT" | "Massachusetts Institute of Technology" | Full institution name |
| "8 weeks old" | "P56D" | ISO 8601 duration |
| "male mouse" | sex="M", species="Mus musculus" | Controlled vocabulary + scientific name |

### 3. Three-Tier Confidence System

The system uses AI to assess confidence and handle user responses intelligently:

#### **High Confidence (≥80%)**
```
User: "experimenter is Dr. Jane Smith"
System: ✓ Detected: experimenter = "Smith, Jane"
        Confidence: 95%

        Press Enter to accept, or type correction
User: [presses Enter]
System: ✓ Auto-applied experimenter = "Smith, Jane"
```

#### **Medium Confidence (50-79%)**
```
User: "subject is pretty old I think"
System: ⚠️ Detected: age = "P365D" (1 year)
        Confidence: 65%
        Note: Interpreting "pretty old" as 1 year based on typical research use

        Press Enter to accept, or type correction
User: [presses Enter]
System: ⚠️ Auto-applied age = "P365D" (medium confidence - best guess)
```

#### **Low Confidence (<50%)**
```
User: "young mouse"
System: ❓ Detected: age = "P21D" (3 weeks)
        Confidence: 35%
        Warning: Vague age description - guessing 3 weeks

        Press Enter to accept, or type correction
User: [presses Enter]
System: ❓ Auto-applied age = "P21D" (LOW CONFIDENCE - NEEDS REVIEW)
        This field will be flagged in the validation report
```

## Usage Scenarios

### Scenario 1: Piece-by-Piece Input with Confirmation

```
System: What is the experimenter's name?
User: "Dr. Jane Smith"

System: I understood:
        ✓ experimenter = "Smith, Jane"
        (from: "Dr. Jane Smith")

        What would you like to do?
        - Press Enter or say 'yes' to accept
        - Type the field name and new value to correct
        - Say 'edit' to review each field individually

User: [presses Enter]

System: ✓ Applied experimenter = "Smith, Jane"

        What institution are you from?
User: "MIT"

System: I understood:
        ✓ institution = "Massachusetts Institute of Technology"
        (from: "MIT")
        Confidence: 98%

        Press Enter to accept...
```

### Scenario 2: Batch Input (All at Once)

```
System: Please provide the missing metadata fields.
User: "I'm Dr. Jane Smith from MIT studying 8 week old male mice in visual cortex"

System: I understood the following from your input:

        ✓ experimenter = "Smith, Jane"
           (from: "Dr. Jane Smith")

        ✓ institution = "Massachusetts Institute of Technology"
           (from: "MIT")
           Confidence: 98%

        ✓ age = "P56D"
           (from: "8 week old")
           Confidence: 95%

        ✓ sex = "M"
           (from: "male")
           Confidence: 100%

        ⚠️ experiment_description = "Visual cortex recording in mouse"
           (from: "studying... visual cortex")
           Confidence: 65% - Inferred from context

        What would you like to do?
        - Press Enter or say 'yes' to accept all
        - Type the field name and new value to correct
        - Say 'edit' to review each field individually

User: "yes"

System: ✓ Applied all fields
        ⚠️ Note: 1 field flagged for review (experiment_description)
```

### Scenario 3: User Skips Confirmation (Auto-Apply)

```
System: I understood:
        ✓ experimenter = "Smith, Jane"
        ✓ institution = "Massachusetts Institute of Technology"

        Press Enter to accept...

User: [presses Enter - says nothing]

System: ✓ Auto-applied all fields using best interpretation
        Ready to proceed with conversion
```

### Scenario 4: User Requests Edit

```
System: I understood:
        ✓ experimenter = "Smith, Jane"

User: "no, it should be Smith, Jane M."

System: I understood:
        ✓ experimenter = "Smith, Jane M."

        Press Enter to accept...

User: "yes"

System: ✓ Applied experimenter = "Smith, Jane M."
```

## Architecture

### Components

1. **IntelligentMetadataParser** ([`backend/src/agents/intelligent_metadata_parser.py`](backend/src/agents/intelligent_metadata_parser.py))
   - `parse_natural_language_batch()` - Parse multiple fields from text
   - `parse_single_field()` - Parse one field at a time
   - `generate_confirmation_message()` - Create user-friendly confirmations
   - `apply_with_best_knowledge()` - Auto-apply based on confidence

2. **ConversationalHandler** ([`backend/src/agents/conversational_handler.py`](backend/src/agents/conversational_handler.py))
   - `parse_and_confirm_metadata()` - Orchestrate parsing + confirmation
   - `process_user_response()` - Enhanced to use intelligent parser

3. **NWBDANDISchema** ([`backend/src/agents/nwb_dandi_schema.py`](backend/src/agents/nwb_dandi_schema.py))
   - Schema definitions with normalization rules
   - Extraction patterns for LLM
   - Format requirements

### Data Flow

```
User Input (Natural Language)
        ↓
IntelligentMetadataParser.parse_natural_language_batch()
        ↓
LLM Analysis (Claude AI)
  - Extract fields
  - Normalize to NWB format
  - Calculate confidence scores
        ↓
ParsedField Objects
  - field_name: "experimenter"
  - raw_input: "Dr. Jane Smith"
  - parsed_value: "Smith, Jane"
  - confidence: 95
  - reasoning: "Clear name format"
        ↓
generate_confirmation_message()
  - Show original vs normalized
  - Display confidence levels
  - Provide instructions
        ↓
Wait for User Decision
        ↓
    ┌────┴────┬─────────┬───────────┐
    ▼         ▼         ▼           ▼
 Confirm    Edit     Skip       Reject
    │         │         │           │
    │         │         ▼           │
    │         │   apply_with_best_knowledge()
    │         │    - Check confidence
    │         │    - Log decision
    │         │    - Flag if low confidence
    │         │         │
    └─────────┴─────────┴───────────┘
              ↓
    Apply to state.metadata
              ↓
    Continue conversion
```

## Confidence Levels Explained

### How Confidence is Calculated

The LLM considers:
1. **Clarity**: How explicitly the field is stated
2. **Format Match**: How well it matches expected patterns
3. **Context**: How much inference is required
4. **Ambiguity**: Whether there are alternative interpretations

### Confidence Thresholds

| Range | Level | Action | Logging |
|-------|-------|--------|---------|
| 80-100% | HIGH | Auto-apply silently | ✓ INFO |
| 50-79% | MEDIUM | Auto-apply with note | ⚠️ WARNING |
| 0-49% | LOW | Auto-apply + flag for review | ❓ WARNING + needs_review flag |

### Low Confidence Handling

When confidence is <50%, the system:
1. ✅ **Still applies the value** (best guess)
2. ⚠️ **Logs a warning** in the conversion logs
3. 🏷️ **Flags the field** in `state.metadata_warnings`
4. 📝 **Includes in validation report** for user review before DANDI submission

Example:
```python
state.metadata_warnings = {
    "age": {
        "value": "P21D",
        "confidence": 35,
        "original_input": "young mouse",
        "warning": "Low confidence parsing - please review before DANDI submission",
        "alternatives": ["P14D", "P28D"]
    }
}
```

## NWB/DANDI Format Compliance

### Supported Normalizations

#### Experimenter Names
```
"Dr. Jane Smith"     → "Smith, Jane"
"Jane Smith"         → "Smith, Jane"
"J. Smith"           → "Smith, J."
"Smith, Jane M."     → "Smith, Jane M."  (already correct)
```

#### Institutions
```
"MIT"                → "Massachusetts Institute of Technology"
"Stanford"           → "Stanford University"
"UCB"                → "University of California, Berkeley"
"Harvard"            → "Harvard University"
"Janelia"            → "Janelia Research Campus"
```

#### Age (ISO 8601 Duration)
```
"8 weeks old"        → "P56D"  (8 weeks = 56 days)
"3 months"           → "P90D"
"1 year old"         → "P365D"
"P90D"               → "P90D"  (already correct)
```

#### Sex (Controlled Vocabulary)
```
"male"               → "M"
"female"             → "F"
"unknown"            → "U"
"M"                  → "M"  (already correct)
```

#### Species (Scientific Names)
```
"mouse"              → "Mus musculus"
"rat"                → "Rattus norvegicus"
"human"              → "Homo sapiens"
"Mus musculus"       → "Mus musculus"  (already correct)
```

## Error Handling

### Fallback Behavior

If the LLM-based parser fails:
1. **First fallback**: Pattern-based regex matching
2. **Second fallback**: Original LLM extraction method
3. **Final fallback**: Ask user for structured input

### Validation

After parsing, the system:
1. Validates against NWB schema
2. Checks DANDI requirements
3. Highlights any non-compliant fields
4. Provides correction suggestions

## Benefits

### For Users
- ✅ **Natural input**: No need to memorize format specifications
- ✅ **Faster workflow**: Provide all info at once or step-by-step
- ✅ **Confidence transparency**: See how certain the system is
- ✅ **Safety net**: Low-confidence fields flagged for review
- ✅ **Flexibility**: Confirm, edit, or skip as needed

### For Data Quality
- ✅ **Format compliance**: Auto-normalized to NWB/DANDI standards
- ✅ **Consistency**: Same normalization rules every time
- ✅ **Traceability**: Full logs of parsing decisions
- ✅ **Review flagging**: Low-confidence fields highlighted
- ✅ **DANDI-ready**: Proper formats for archive submission

## Testing

### Example Test Cases

**Test 1: High Confidence Batch**
```python
input = "I'm Dr. Jane Smith from MIT studying 8 week old mice"
expected = {
    "experimenter": "Smith, Jane",  # confidence: 95%
    "institution": "Massachusetts Institute of Technology",  # confidence: 98%
    "age": "P56D",  # confidence: 92%
}
```

**Test 2: Low Confidence with Skip**
```python
input = "pretty old mouse"
expected = {
    "age": "P365D",  # confidence: 40%
    "warnings": {"age": "Low confidence - needs review"}
}
```

**Test 3: Edit Workflow**
```python
input_1 = "experimenter is Dr. Jane Smith"
parsed = "Smith, Jane"
user_response = "no, it should be Smith, Jane M."
expected = "Smith, Jane M."
```

## Future Enhancements

1. **Learning from corrections**: Track user edits to improve parsing
2. **Institution database**: Expand abbreviation mappings
3. **Context awareness**: Use file metadata to infer values
4. **Validation integration**: Pre-validate before user confirmation
5. **Batch edit mode**: Allow editing multiple fields at once

## Conclusion

The Intelligent Metadata Parser significantly improves user experience by:
- Accepting natural language input
- Providing smart format normalization
- Offering transparent confidence scoring
- Enabling flexible confirmation workflows
- Ensuring DANDI compliance

Users can now focus on their science instead of format specifications! 🧠✨
