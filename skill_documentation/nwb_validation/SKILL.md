---
name: nwb_validation
version: 0.1.0
description: Validates NWB files using NWB Inspector and provides intelligent correction recommendations
category: validation
author: Agentic Neurodata Conversion Team
tags:
  - validation
  - nwb
  - nwb-inspector
  - quality-assurance
  - dandi-compliance
  - issue-detection
dependencies:
  nwbinspector: ">=0.4.0"
  pynwb: ">=2.8.2"
  hdmf: ">=3.14.5"
  pydantic: ">=2.0.0"
input_format: "*.nwb files"
output_format: "ValidationResult with issues, summary, and corrections"
estimated_duration: "30 seconds - 2 minutes (depends on file size)"
implementation: backend/src/agents/evaluation_agent.py
---

# Skill: NWB Validation

## Purpose
Validate NWB (Neurodata Without Borders) files against the official specification and DANDI archive requirements using NWB Inspector. Provide detailed issue reports with intelligent prioritization and correction recommendations. This skill ensures converted files meet quality standards and are ready for sharing/archival.

## When to Use This Skill

### ✅ USE When:
- NWB conversion has completed
- User requests validation of existing NWB file
- Reconversion has completed (need to re-validate)
- Quality assessment is needed before DANDI upload
- Checking if file meets NWB specification requirements

### ❌ DON'T USE When:
- File is not in NWB format (`.nwb` extension)
- Conversion hasn't started yet
- User wants data conversion (not validation)
- Format detection is needed (use nwb_conversion skill)

## Core Responsibilities

### 1. NWB Inspector Integration
**Runs official NWB validation tool**:
- Checks compliance with NWB schema
- Validates required fields
- Detects specification violations
- Checks DANDI archive requirements
- Identifies best practice violations

**Issue Severities** (from NWB Inspector):
- **CRITICAL**: Spec violations, file unreadable
- **ERROR**: Required fields missing, serious problems
- **WARNING**: Best practices not followed, potential issues
- **INFO**: Suggestions for improvement

### 2. Intelligent Issue Analysis
**LLM-powered features** (when available):

**a) Issue Prioritization**:
- Ranks issues by importance
- Groups related issues
- Identifies which to fix first
- Separates critical from optional

**b) User-Friendly Explanations**:
- Translates technical issues to plain language
- Provides context ("why this matters")
- Gives specific examples
- Links to documentation

**c) Correction Recommendations**:
- Suggests specific fixes
- Categorizes: auto-fixable vs needs-user-input
- Provides example values
- Estimates effort required

### 3. Validation Status Determination
**Three possible outcomes**:

**PASSED** (Green):
- No critical, error, or warning issues
- File fully compliant with NWB spec
- Ready for DANDI upload
- Action: Mark complete, celebrate

**PASSED_WITH_ISSUES** (Yellow):
- File is valid but has warnings/info issues
- Usable but not perfect
- May not meet DANDI standards
- Action: Offer to fix or accept as-is

**FAILED** (Red):
- Has critical or error severity issues
- File may be unusable or incomplete
- Cannot upload to DANDI
- Action: Enter correction loop, must fix

### 4. Correction Context Generation
**Prepares data for correction loop**:
- Extracts fixable issues
- Categorizes auto-fix vs needs-input
- Generates suggested corrections
- Provides structured data for conversation agent

## MCP Message Handlers

### 1. `run_validation`
**Purpose**: Validate an NWB file and return results

**Input**:
```json
{
  "target_agent": "evaluation",
  "action": "run_validation",
  "context": {
    "nwb_path": "/tmp/outputs/session.nwb"
  }
}
```

**Workflow**:
1. Check if file exists and is readable
2. Run NWB Inspector on file
3. Parse Inspector output
4. Determine overall status (PASSED/PASSED_WITH_ISSUES/FAILED)
5. Use LLM to prioritize and explain issues (if available)
6. Generate correction recommendations (if needed)
7. Create validation report
8. Update GlobalState with results
9. Return structured response

**Output (PASSED)**:
```json
{
  "success": true,
  "result": {
    "overall_status": "PASSED",
    "validation_status": "PASSED",
    "is_valid": true,
    "summary": {
      "total_issues": 0,
      "critical": 0,
      "error": 0,
      "warning": 0,
      "info": 0
    },
    "issues": [],
    "message": "Validation passed! File is fully compliant with NWB specification."
  }
}
```

**Output (PASSED_WITH_ISSUES)**:
```json
{
  "success": true,
  "result": {
    "overall_status": "PASSED_WITH_ISSUES",
    "is_valid": true,
    "summary": {
      "total_issues": 3,
      "critical": 0,
      "error": 0,
      "warning": 2,
      "info": 1
    },
    "issues": [
      {
        "severity": "WARNING",
        "message": "session_start_time is recommended but missing",
        "location": "NWBFile.session_start_time",
        "check_function": "check_session_start_time"
      },
      {
        "severity": "WARNING",
        "message": "Subject.age uses non-standard format",
        "location": "Subject.age",
        "check_function": "check_age_format"
      },
      {
        "severity": "INFO",
        "message": "Consider adding keywords for discoverability",
        "location": "NWBFile.keywords",
        "check_function": "check_keywords"
      }
    ],
    "prioritized_issues": [
      {
        "issue": {...},
        "priority": "high",
        "explanation": "Session start time is required by DANDI...",
        "correction_suggestion": "Add session_start_time in ISO 8601 format: '2024-03-15T14:30:00'",
        "auto_fixable": false
      }
    ],
    "message": "Validation passed with 3 minor issues. You can fix them or proceed as-is."
  }
}
```

**Output (FAILED)**:
```json
{
  "success": true,
  "result": {
    "overall_status": "FAILED",
    "is_valid": false,
    "summary": {
      "total_issues": 5,
      "critical": 1,
      "error": 2,
      "warning": 2,
      "info": 0
    },
    "issues": [
      {
        "severity": "CRITICAL",
        "message": "NWBFile.session_description is required but missing",
        "location": "NWBFile.session_description",
        "check_function": "check_required_field"
      },
      {
        "severity": "ERROR",
        "message": "Subject.species must be in binomial nomenclature",
        "location": "Subject.species",
        "check_function": "check_species_format"
      },
      {...}
    ],
    "correction_context": {
      "auto_fixable_count": 1,
      "needs_user_input_count": 4,
      "suggested_corrections": {
        "species": {
          "current_value": "mouse",
          "suggested_value": "Mus musculus",
          "reasoning": "DANDI requires binomial nomenclature"
        }
      },
      "required_user_input": [
        {
          "field": "session_description",
          "prompt": "Please describe what was recorded in this session",
          "example": "Recording of V1 neurons during visual stimulation"
        }
      ]
    },
    "message": "Validation failed with 5 issues. I can help you fix them."
  }
}
```

### 2. `analyze_corrections`
**Purpose**: Generate correction recommendations for failed validation

**Input**:
```json
{
  "target_agent": "evaluation",
  "action": "analyze_corrections",
  "context": {
    "issues": [...],
    "current_metadata": {...}
  }
}
```

**Output**:
```json
{
  "success": true,
  "result": {
    "correction_context": {
      "auto_fixable_count": 2,
      "needs_user_input_count": 3,
      "auto_fixes": {
        "species": "Mus musculus",
        "age": "P90D"
      },
      "user_input_required": [
        {
          "field": "session_description",
          "prompt": "Describe what was recorded",
          "example": "Recording of V1 neurons",
          "why_needed": "Required by NWB spec"
        }
      ],
      "priority_order": ["session_description", "species", "age", ...],
      "estimated_fix_time": "5-10 minutes"
    }
  }
}
```

## Validation Workflow

### Step-by-Step Process

**1. File Check** (1-2 seconds)
```
- Verify file exists
- Check .nwb extension
- Verify file is readable
- Check file size (warn if >5GB, slow validation)
```

**2. NWB Inspector Execution** (30 sec - 2 min)
```
- Run: nwbinspector inspect {nwb_path}
- Capture JSON output
- Parse validation results
- Extract issues with severities
```

**3. Issue Categorization** (1-2 seconds)
```
- Count by severity: critical, error, warning, info
- Determine overall status:
  - PASSED: 0 critical/error/warning
  - PASSED_WITH_ISSUES: 0 critical/error, >0 warning/info
  - FAILED: >0 critical/error
```

**4. LLM Enhancement** (2-5 seconds, if available)
```
- Prioritize issues by importance
- Generate user-friendly explanations
- Suggest specific corrections
- Identify auto-fixable issues
```

**5. State Update** (instant)
```
- Set state.validation_status
- Set state.overall_status
- Store state.validation_report
- Update state.previous_issues (for no-progress detection)
```

**6. Return Results** (instant)
```
- Package all data into MCPResponse
- Include correction context if failed
- Provide actionable message
```

## Issue Analysis

### Auto-Fixable Issues

**Type 1: Format Standardization**
```
Issue: "species is 'mouse', should be binomial nomenclature"
Auto-Fix: species = "Mus musculus"
Reasoning: Common name → scientific name mapping
```

**Type 2: Format Conversion**
```
Issue: "age is '90 days', should be ISO 8601 duration"
Auto-Fix: age = "P90D"
Reasoning: Parse duration and convert to ISO 8601
```

**Type 3: Default Values**
```
Issue: "sex is missing"
Auto-Fix: sex = "U" (Unknown)
Reasoning: Use standard unknown value when not provided
```

### Needs User Input

**Type 1: Required Descriptive Fields**
```
Issue: "session_description is required but missing"
Cannot Auto-Fix: Requires domain knowledge
Ask User: "Please describe what was recorded in this session"
Example: "Recording of V1 neurons during visual stimulation"
```

**Type 2: Experiment-Specific Values**
```
Issue: "session_start_time is missing"
Cannot Auto-Fix: Only user knows when experiment occurred
Ask User: "When did this recording session start?"
Example: "2024-03-15T14:30:00-05:00"
```

**Type 3: Ambiguous Corrections**
```
Issue: "experimenter format is unclear"
Current: "Smith"
Cannot Auto-Fix: Could be "Dr. Smith", "J. Smith", "Jane Smith"
Ask User: "What's the full name of the experimenter?"
```

## LLM-Enhanced Features

### Feature 1: Issue Prioritization

**Input**: List of 10 issues (mixed severities)

**LLM Prompt**:
```
You are an NWB validation expert. Prioritize these issues by:
1. Severity (critical > error > warning > info)
2. DANDI requirements (required > recommended)
3. Fix difficulty (quick > complex)
4. Impact on usability (high > low)

Return ranked list with reasoning.
```

**Output**:
```json
[
  {
    "issue": "session_description missing",
    "priority": "critical",
    "rank": 1,
    "reasoning": "Required by NWB spec, blocks DANDI upload, easy to fix"
  },
  {
    "issue": "species format incorrect",
    "priority": "high",
    "rank": 2,
    "reasoning": "DANDI requirement, auto-fixable"
  },
  ...
]
```

### Feature 2: User-Friendly Explanations

**Technical Issue**:
```
"check_subject_species failed: species 'mouse' does not match binomial nomenclature pattern"
```

**LLM Translation**:
```
"The species needs to be in scientific format (like 'Mus musculus' instead of 'mouse').
This is required by DANDI so other researchers can precisely identify the organism.

Quick fix: I can change 'mouse' to 'Mus musculus' for you."
```

### Feature 3: Correction Suggestions

**LLM Prompt**:
```
Given this validation issue and current metadata, suggest a specific correction:

Issue: Subject.age uses non-standard format
Current value: "90 days"
Expected format: ISO 8601 duration (e.g., "P90D")

What should the corrected value be?
```

**LLM Response**:
```json
{
  "corrected_value": "P90D",
  "reasoning": "Converted '90 days' to ISO 8601 duration format",
  "confidence": 0.95,
  "auto_fixable": true
}
```

## ValidationResult Structure

```python
class ValidationResult(BaseModel):
    is_valid: bool
    # True if no CRITICAL/ERROR, False otherwise

    overall_status: str
    # "PASSED" | "PASSED_WITH_ISSUES" | "FAILED"

    summary: Dict[str, int]
    # {"total_issues": 5, "critical": 1, "error": 2, "warning": 1, "info": 1}

    issues: List[Issue]
    # Full list of issues from NWB Inspector

    prioritized_issues: Optional[List[PrioritizedIssue]]
    # LLM-enhanced issues with explanations (if LLM available)

    correction_context: Optional[CorrectionContext]
    # Auto-fixes and user input requirements (if FAILED)

class Issue(BaseModel):
    severity: str  # CRITICAL | ERROR | WARNING | INFO
    message: str  # Technical description
    location: str  # NWBFile.session_description
    check_function: str  # check_required_field

class PrioritizedIssue(BaseModel):
    issue: Issue
    priority: str  # critical | high | medium | low
    rank: int  # 1, 2, 3, ...
    explanation: str  # User-friendly description
    correction_suggestion: str  # Specific fix
    auto_fixable: bool  # Can system fix it?
    estimated_effort: str  # "30 seconds", "2 minutes"

class CorrectionContext(BaseModel):
    auto_fixable_count: int
    needs_user_input_count: int
    auto_fixes: Dict[str, Any]  # field → corrected_value
    user_input_required: List[UserInputRequest]
    priority_order: List[str]  # Ordered list of fields to fix
    estimated_fix_time: str
```

## Integration with Other Skills

### Called By:
- **Orchestration Skill**: After conversion completes
- **Orchestration Skill**: After reconversion (correction loop)
- **API Endpoints**: Direct validation requests

### Calls:
- **None**: This is a leaf skill (doesn't call other skills)

### Provides Data To:
- **Orchestration Skill**: Validation results, correction context
- **Report Service**: Detailed validation reports
- **GlobalState**: Updates validation_status and validation_report

## State Management

### GlobalState Fields Used:

**Write**:
- `validation_status`: RUNNING → PASSED / PASSED_IMPROVED / (none for FAILED)
- `overall_status`: "PASSED" / "PASSED_WITH_ISSUES" / "FAILED"
- `validation_report`: Full ValidationResult object
- `previous_issues`: Copy of issues (for no-progress detection)
- `logs`: Detailed activity log

**Read**:
- `correction_attempt`: To determine if this is PASSED_IMPROVED
- `output_path`: NWB file to validate

### Validation Status vs Overall Status

**Important Distinction**:

- **validation_status** (ValidationStatus enum):
  - State machine status: RUNNING, PASSED, PASSED_IMPROVED
  - Used internally to track workflow
  - Only set when validation completes successfully
  - NOT set for FAILED (leaves in RUNNING, awaits correction)

- **overall_status** (string):
  - Outcome category: "PASSED", "PASSED_WITH_ISSUES", "FAILED"
  - Used for user-facing messages and decision-making
  - Always set after validation runs
  - Determines next workflow step

**Example**:
```python
# After validation runs:
if no_issues:
    state.overall_status = "PASSED"
    if correction_attempt > 0:
        state.validation_status = ValidationStatus.PASSED_IMPROVED
    else:
        state.validation_status = ValidationStatus.PASSED

elif has_warnings_only:
    state.overall_status = "PASSED_WITH_ISSUES"
    # Don't set validation_status yet (await user decision)

else:  # has errors/critical
    state.overall_status = "FAILED"
    # Don't set validation_status yet (await correction)
```

## Performance Characteristics

| File Size | Validation Time | Issues Detected (typical) |
|-----------|----------------|--------------------------|
| 100 MB    | 30-45 seconds  | 0-5                      |
| 1 GB      | 1-2 minutes    | 0-10                     |
| 10 GB     | 5-10 minutes   | 0-15                     |
| 50 GB     | 20-40 minutes  | 0-20                     |

**Notes**:
- NWB Inspector is I/O bound (reads entire file)
- LLM analysis adds 2-5 seconds (negligible)
- Large files (>10GB) may timeout if validation limit not increased
- Issue count independent of file size (depends on metadata quality)

## Common Validation Issues

### Issue 1: Missing Required Fields
**Example**:
```
CRITICAL: NWBFile.session_description is required but missing
```
**Fix**: Provide session description
**User Action**: "Describe what was recorded"

### Issue 2: Species Format
**Example**:
```
ERROR: Subject.species 'mouse' does not match binomial nomenclature
```
**Fix**: species = "Mus musculus" (auto-fixable)
**User Action**: None (system fixes)

### Issue 3: Age Format
**Example**:
```
WARNING: Subject.age '90 days' should use ISO 8601 duration
```
**Fix**: age = "P90D" (auto-fixable)
**User Action**: None (system fixes)

### Issue 4: Session Start Time
**Example**:
```
WARNING: session_start_time is recommended but missing
```
**Fix**: Needs user input
**User Action**: "When did the experiment start?"

### Issue 5: Sex Value
**Example**:
```
INFO: Subject.sex is missing
```
**Fix**: sex = "U" for Unknown (auto-fixable)
**User Action**: None or provide if known

## Testing Checklist

- [ ] Validates files with no issues (PASSED)
- [ ] Validates files with warnings only (PASSED_WITH_ISSUES)
- [ ] Validates files with errors (FAILED)
- [ ] Handles missing file gracefully
- [ ] Handles corrupt/unreadable files
- [ ] LLM prioritization works when available
- [ ] LLM explanations are helpful
- [ ] Auto-fix suggestions are correct
- [ ] Correction context generated properly
- [ ] State.validation_status set correctly
- [ ] State.overall_status set correctly
- [ ] PASSED_IMPROVED set after successful retry
- [ ] previous_issues stored for no-progress detection
- [ ] Validation report complete and accurate

## Security Considerations

### File Access:
- **Read**: NWB files in `/tmp/outputs/`
- **No Write**: Validation is read-only, never modifies files
- **No Network**: NWB Inspector runs locally

### Data Privacy:
- Validation results may contain file metadata
- Don't log sensitive experiment details
- Sanitize file paths in public logs

### Resource Limits:
- Set timeout for large files (default: 10 minutes)
- Limit memory usage (NWB Inspector can be memory-intensive)
- Monitor CPU during validation

## Version History

### v0.1.0 (2025-10-17)
- Initial skill documentation
- NWB Inspector integration
- LLM-powered issue prioritization and explanation
- Correction recommendation generation
- Three-tier status system (PASSED/PASSED_WITH_ISSUES/FAILED)
- Auto-fix vs needs-input categorization
- PASSED_IMPROVED status for successful corrections

### Planned Features (v0.2.0):
- Custom validation rules (beyond NWB Inspector)
- Validation caching (skip re-validation if file unchanged)
- Incremental validation (only check what changed)
- Validation quality score (0-100)
- Best practice recommendations (beyond spec compliance)

## References

- [NWB Inspector Documentation](https://nwbinspector.readthedocs.io/)
- [NWB Specification](https://nwb-schema.readthedocs.io/)
- [DANDI Validation Requirements](https://www.dandiarchive.org/handbook/13_upload/)
- [Implementation Code](backend/src/agents/evaluation_agent.py)
- [Report Service](backend/src/services/report_service.py)

---

**Last Updated**: 2025-10-17
**Maintainer**: Agentic Neurodata Conversion Team
**License**: MIT
**Support**: GitHub Issues
