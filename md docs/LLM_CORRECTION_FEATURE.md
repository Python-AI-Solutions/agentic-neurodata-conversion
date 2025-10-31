# LLM-Powered Correction Analysis Feature

## Overview

The agentic neurodata conversion system now includes a fully functional **LLM-powered correction analysis** feature using Anthropic's Claude 3.5 Sonnet. This feature analyzes NWB validation errors and provides intelligent, actionable suggestions for fixing issues.

## How It Works

### 1. Automatic Validation

After every conversion to NWB format, the system automatically runs NWBInspector to validate the output file.

### 2. Error Detection

If validation fails (critical or error-level issues found), the system:
- Changes status to `awaiting_retry_approval`
- Shows a retry dialog in the web UI
- Waits for user decision

### 3. LLM Analysis (When User Approves Retry)

When the user clicks "🔄 Retry with Corrections":

1. **Context Gathering**: System collects:
   - Validation issues from NWBInspector
   - Input metadata
   - Conversion parameters
   - Previous correction attempts

2. **LLM Analysis**: Claude analyzes the issues and provides:
   - **Analysis**: Root cause explanation
   - **Suggestions**: Specific, actionable fixes for each issue
   - **Recommended Action**: `retry`, `manual_intervention`, or `accept_warnings`

3. **Logging**: All LLM insights are logged to the system logs (visible in web UI)

4. **Retry**: System attempts conversion again (currently without applying corrections automatically)

## Example LLM Analysis Output

```
Analysis: The validation issues primarily stem from missing or improperly
formatted metadata. While all issues are INFO level, they indicate incomplete
documentation that could affect data reusability. The main categories are:
missing subject information, empty institutional metadata, and improper
formatting of experimenter names.

Recommended Action: retry

Suggestions:
1. [info] Missing subject metadata
   Suggestion: Add required subject information including species, sex
   ('M'/'F'/'O'/'U'), and age in ISO 8601 format (e.g., 'P2Y' for 2 years)
   Actionable: True

2. [info] Empty institutional attributes
   Suggestion: Either remove the empty institution/lab attributes or populate
   them with valid values. If unknown, use None in PyNWB
   Actionable: True

3. [info] Experimenter name format
   Suggestion: Format experimenter name as 'LastName, FirstName'
   Actionable: True
```

## Architecture

### Components

1. **Evaluation Agent** (`backend/src/agents/evaluation_agent.py`)
   - `handle_run_validation()`: Runs NWBInspector
   - `handle_analyze_corrections()`: Calls LLM for analysis
   - `_analyze_with_llm()`: Interfaces with LLM service
   - `_build_correction_prompt()`: Constructs detailed prompt

2. **Conversation Agent** (`backend/src/agents/conversation_agent.py`)
   - `handle_retry_decision()`: Handles user retry approval
   - Calls evaluation agent's `analyze_corrections` method
   - Logs LLM insights to system logs

3. **LLM Service** (`backend/src/services/llm_service.py`)
   - `AnthropicLLMService`: Interfaces with Anthropic API
   - `generate_structured_output()`: Returns structured JSON responses

## User Interface Flow

```
[User uploads file]
     ↓
[Conversion happens]
     ↓
[Validation runs automatically]
     ↓
[Validation fails] → Status: "AWAITING_RETRY_APPROVAL"
     ↓
[UI shows retry dialog]:
  "⚠️ Validation Issues Found
   Would you like to retry with corrections?
   [🔄 Retry with Corrections] [❌ Cancel]"
     ↓
[User clicks Retry]
     ↓
[LLM analyzes validation issues]
     ↓
[Logs show LLM analysis and suggestions]
     ↓
[Conversion retries]
     ↓
[New validation runs]
```

## Testing

A standalone test script is provided: `test_llm_correction.py`

Run it:
```bash
pixi run python test_llm_correction.py
```

This script:
1. Creates an NWB file with validation issues
2. Runs NWBInspector validation
3. Calls LLM for correction analysis
4. Displays the LLM's suggestions

## Configuration

Required environment variable in `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

The API key is automatically loaded by `run_server.py` at startup.

## Current Limitations

### What's Implemented:
✅ LLM analysis of validation errors
✅ Intelligent, actionable suggestions
✅ Logging of LLM insights
✅ Retry workflow
✅ User interaction via web UI

### What's Not Yet Implemented:
❌ **Automatic application of corrections** - The LLM provides suggestions, but the system doesn't automatically modify conversion parameters based on those suggestions
❌ **Parameter correction mapping** - Need to implement logic to translate LLM suggestions into actual parameter changes
❌ **Iterative refinement** - System doesn't learn from previous attempts to adjust suggestions

## Future Enhancements

1. **Automatic Correction Application**: Parse LLM suggestions and automatically adjust conversion parameters (metadata, formatting options, etc.)

2. **Suggestion History**: Track which suggestions were helpful across sessions to improve future recommendations

3. **Custom Validation Rules**: Allow users to define custom validation criteria that LLM should prioritize

4. **Multi-Model Support**: Add support for other LLM providers (OpenAI, local models, etc.)

5. **Correction Templates**: Build library of common corrections for known data formats

## Code References

- Evaluation agent: [backend/src/agents/evaluation_agent.py:161-344](backend/src/agents/evaluation_agent.py#L161-L344)
- Conversation agent retry logic: [backend/src/agents/conversation_agent.py:348-437](backend/src/agents/conversation_agent.py#L348-L437)
- LLM service: [backend/src/services/llm_service.py](backend/src/services/llm_service.py)
- Frontend retry dialog: [frontend/public/index.html:231-241](frontend/public/index.html#L231-L241)
- Test script: [test_llm_correction.py](test_llm_correction.py)

## API Usage

The LLM correction analysis uses the Anthropic API with structured output:

```python
output_schema = {
    "type": "object",
    "properties": {
        "analysis": {"type": "string"},
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "issue": {"type": "string"},
                    "severity": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "actionable": {"type": "boolean"},
                },
            },
        },
        "recommended_action": {
            "type": "string",
            "enum": ["retry", "manual_intervention", "accept_warnings"],
        },
    },
}
```

Typical API cost per analysis: ~$0.01-0.05 depending on number of validation issues.
