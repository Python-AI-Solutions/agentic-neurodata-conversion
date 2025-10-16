# Conversational AI Implementation

## Overview

Implemented intelligent, LLM-driven conversational interface for NWB file conversion, similar to Claude.ai's natural interaction style.

## Problem Solved

**Before**: Rigid, predefined workflows with hardcoded retry approvals and specific user input fields.

**After**: Natural, adaptive conversation where the LLM:
- Analyzes validation results dynamically
- Determines what information is needed
- Asks specific, contextual questions
- Extracts metadata from natural language responses
- Decides when to proceed with fixes

## Key Components

### 1. `ConversationalHandler` (NEW)
**File**: `/backend/src/agents/conversational_handler.py`

**Purpose**: Enables LLM-driven intelligent conversations

**Key Methods**:

#### `analyze_validation_and_respond()`
- Analyzes NWB Inspector validation results using LLM
- Determines issue severity (low/medium/high)
- Identifies what information is missing
- Generates natural, helpful questions for the user
- Returns structured JSON with message and suggested fixes

**Example Flow**:
```python
# Input: Validation result with missing experimenter, institution
# Output:
{
    "message": "I see your NWB file is missing some recommended metadata. Could you provide:\n1. Experimenter name(s)\n2. Institution/lab affiliation\nThis helps others understand where the data came from.",
    "needs_user_input": true,
    "suggested_fixes": [
        {
            "field": "experimenter",
            "description": "Names of people who performed the experiment",
            "example": "['Jane Doe', 'John Smith']"
        },
        {
            "field": "institution",
            "description": "University or research institution",
            "example": "University of California, Berkeley"
        }
    ],
    "severity": "low"
}
```

#### `process_user_response()`
- Analyzes user's natural language response
- Extracts structured metadata (experimenter, institution, keywords, etc.)
- Determines if more information is needed
- Generates follow-up questions or confirms readiness to proceed

**Example Flow**:
```python
# User: "The experiment was done by Dr. Smith at MIT, studying vision in mice"
# Output:
{
    "extracted_metadata": {
        "experimenter": ["Dr. Smith"],
        "institution": "MIT",
        "keywords": ["vision", "mice"],
        "subject": {
            "species": "Mus musculus"
        }
    },
    "needs_more_info": false,
    "follow_up_message": "Great! I've extracted the metadata. I'll update your NWB file with this information and re-run validation.",
    "ready_to_proceed": true
}
```

### 2. `ConversationAgent` Updates

#### Added Conversational Mode
**File**: `/backend/src/agents/conversation_agent.py`

**New Features**:
- `_conversational_handler`: Instance of ConversationalHandler
- `_conversation_history`: Maintains conversation context
- LLM-driven validation analysis (replaces rigid retry approval)
- Natural metadata extraction from user responses

**Modified Workflow**:

```python
# OLD: Validation failed → awaiting_retry_approval status → rigid approve/reject
# NEW: Validation failed → LLM analyzes issues → conversational questions → extract metadata → retry

# Lines 248-290: Replace rigid retry logic with intelligent LLM analysis
if self._conversational_handler and state.can_retry():
    llm_analysis = await self._conversational_handler.analyze_validation_and_respond(
        validation_result=validation_result,
        nwb_file_path=output_path,
        state=state,
    )

    # Return conversational message instead of rigid status
    return MCPResponse.success_response(
        result={
            "status": "awaiting_user_input",
            "conversation_type": "validation_analysis",
            "message": llm_analysis.get("message"),  # Natural language!
            "needs_user_input": True,
            "suggested_fixes": llm_analysis.get("suggested_fixes", []),
        }
    )
```

#### New Method: `handle_conversational_response()`
**Lines 711-832**

Handles natural language responses from users:
1. Processes user message with LLM
2. Extracts structured metadata
3. Determines if ready to proceed or needs more info
4. Maintains conversation history for context

```python
# User sends: "The experimenter was John Doe at Stanford"
# System:
# 1. Adds to conversation history
# 2. Processes with LLM
# 3. Extracts: {"experimenter": ["John Doe"], "institution": "Stanford"}
# 4. If complete, triggers reconversion with updated metadata
# 5. If incomplete, asks follow-up questions
```

### 3. API Endpoint

**New Endpoint**: `POST /api/chat`
**File**: `/backend/src/api/main.py` (Lines 314-353)

**Purpose**: Accept conversational messages from UI

**Request**:
```json
POST /api/chat
{
    "message": "The experimenter was Dr. Smith from MIT"
}
```

**Response**:
```json
{
    "message": "Perfect! I've extracted the experimenter and institution. Is there anything else you'd like to add?",
    "status": "conversation_continues",
    "needs_more_info": false,
    "extracted_metadata": {
        "experimenter": ["Dr. Smith"],
        "institution": "MIT"
    }
}
```

## Workflow Comparison

### OLD Workflow (Rigid)
```
1. Upload file
2. Conversion runs
3. Validation fails
4. System: "Validation failed. Retry? [Approve/Reject]"
5. User clicks Approve
6. System tries again (maybe with LLM-generated fixes)
7. Still fails → repeat
```

### NEW Workflow (Conversational)
```
1. Upload file
2. Conversion runs
3. Validation fails with missing metadata
4. LLM analyzes issues:
   System: "I see your NWB file is missing some important metadata:
           - Experimenter name
           - Institution
           - Subject information

           Could you provide these details? For example:
           'The experiment was done by Dr. Jane Doe at Stanford,
            studying neural activity in adult mice.'"

5. User responds naturally:
   "This was done by John Smith at MIT, we were studying vision in mice"

6. LLM extracts metadata:
   {
       "experimenter": ["John Smith"],
       "institution": "MIT",
       "keywords": ["vision"],
       "subject": {"species": "Mus musculus"}
   }

7. System: "Great! Let me update your file with this information..."
8. Reconverts with metadata
9. Validation passes ✓
```

## Benefits

### 1. **Natural Interaction**
- Users can type naturally instead of filling forms
- LLM understands context and extracts information intelligently
- Feels like talking to Claude.ai

### 2. **Adaptive Responses**
- Different messages for different validation issues
- Severity-based prioritization
- Educational explanations about why metadata matters

### 3. **Flexible Metadata Extraction**
- Handles various natural language formats
- Extracts multiple fields from single response
- Infers related information (e.g., "mice" → species: "Mus musculus")

### 4. **Context-Aware**
- Maintains conversation history
- Remembers what was already discussed
- Can clarify or expand on previous answers

### 5. **Error Recovery**
- If LLM fails, falls back to original rigid workflow
- Graceful degradation ensures system still works

## Technical Details

### LLM Prompts

#### Validation Analysis Prompt
```
You are an expert neuroscience data curator helping scientists convert data to NWB format.

Analyze NWB Inspector validation results and:
1. Explain issues in simple terms
2. Determine if they're critical or recommendations
3. Ask specific questions to gather needed information
4. Be conversational and educational

Return JSON with:
{
    "message": "Your conversational message",
    "needs_user_input": true/false,
    "suggested_fixes": [...],
    "severity": "low"|"medium"|"high"
}
```

#### Metadata Extraction Prompt
```
Extract metadata from user's natural language response.

Map to NWB fields:
- experimenter
- experiment_description
- institution
- keywords
- subject (subject_id, species, age)

Return JSON with:
{
    "extracted_metadata": {...},
    "needs_more_info": true/false,
    "follow_up_message": "...",
    "ready_to_proceed": true/false
}
```

### Integration Points

1. **Status Handling**: New status `awaiting_user_input` with `conversation_type: "validation_analysis"`
2. **WebSocket**: Can push conversational messages to UI in real-time
3. **Conversation History**: Stored in agent, provides context for follow-up questions
4. **Metadata Merging**: Extracted metadata merges with existing, preserves user-provided info

## Future Enhancements

1. **Multi-turn Clarifications**: Handle complex metadata requiring multiple exchanges
2. **Validation Education**: Explain NWB Inspector checks in detail when asked
3. **Best Practices Guidance**: Proactively suggest improvements
4. **File Format Help**: Answer questions about supported formats
5. **Troubleshooting**: Help debug conversion issues conversationally

## Testing

### Manual Test Flow
1. Upload NWB file with missing metadata
2. Wait for validation to complete
3. Observe LLM's conversational question about missing fields
4. Respond naturally: "Experimenter was Jane Doe at Stanford"
5. Verify metadata extraction
6. Confirm reconversion with updated metadata
7. Check validation passes

### Example Conversations

**Missing Experimenter**:
```
AI: I see your NWB file is missing experimenter information. Could you tell me who performed this experiment?

User: It was Dr. Jane Doe

AI: Great! I've added Dr. Jane Doe as the experimenter. Would you also like to add institution information?

User: Yes, she's at Stanford

AI: Perfect! Updating your file with experimenter: Dr. Jane Doe, institution: Stanford. Let me re-run the conversion...
```

**Missing Subject Info**:
```
AI: Your NWB file is missing subject information. Could you provide:
- Subject ID
- Species
- Age (if known)

User: The subject was a 3-month-old mouse, ID M001

AI: Thank you! I've extracted:
- Subject ID: M001
- Species: Mus musculus (mouse)
- Age: 3 months

Is this correct?

User: Yes

AI: Great! Updating and reconverting...
```

## Files Modified/Created

### Created
- `/backend/src/agents/conversational_handler.py` - Core LLM conversation logic

### Modified
- `/backend/src/agents/conversation_agent.py` - Integrated conversational mode
- `/backend/src/api/main.py` - Added `/api/chat` endpoint

### Next Steps for Frontend
- Update chat UI to detect `conversation_type: "validation_analysis"` responses
- Display LLM messages naturally in chat
- Send user responses to `/api/chat` endpoint
- Show extracted metadata for confirmation
- Handle conversation flow states

## Configuration

Requires `LLMService` to be configured with Anthropic API key. Falls back to rigid workflow if LLM unavailable.

```python
# In initialization
llm_service = LLMService(api_key=os.getenv("ANTHROPIC_API_KEY"))
conversation_agent = ConversationAgent(mcp_server, llm_service)
```
