# LLM Usage in the System 🤖

## Summary

**Yes, LLM is implemented and actively used** in the agentic neurodata conversion system.

**Implementation**: Anthropic Claude 3.5 Sonnet
**Architecture**: Provider-agnostic interface with dependency injection
**Status**: ✅ **Fully Functional**
**Optional**: Yes - system degrades gracefully without LLM

---

## Where LLM is Used

### 1. Evaluation Agent - Correction Analysis ⭐

**File**: [backend/src/agents/evaluation_agent.py](backend/src/agents/evaluation_agent.py)
**Method**: `handle_analyze_corrections()`
**Lines**: 176-303

**Purpose**: Analyze NWB validation failures and suggest corrections

**What the LLM does**:
1. Receives validation issues from NWB Inspector
2. Analyzes root causes
3. Suggests specific, actionable corrections
4. Recommends next action (retry/manual/accept)

**Code**:
```python
async def handle_analyze_corrections(
    self,
    message: MCPMessage,
    state: GlobalState,
) -> MCPResponse:
    """Analyze validation issues and suggest corrections (requires LLM)."""

    if not self._llm_service:
        # Graceful degradation
        return MCPResponse.error_response(
            reply_to=message.message_id,
            error_code="LLM_NOT_AVAILABLE",
            error_message="Correction analysis requires LLM service",
        )

    # Build correction context
    correction_context = CorrectionContext(
        validation_result=validation_result,
        input_metadata=input_metadata,
        conversion_parameters=conversion_parameters,
    )

    # Call LLM for analysis
    corrections = await self._analyze_with_llm(correction_context, state)
```

**LLM Prompt Structure**:
```
# NWB Validation Issues

## Summary
- Total issues: 15
- Critical: 2
- Errors: 5
- Warnings: 8

## Issues
- [CRITICAL] Missing required field: subject_id
- [ERROR] Invalid timestamps in acquisition/TimeSeries
- [WARNING] Non-standard electrode group name
...

## Task
Analyze these validation issues and provide:
1. A brief analysis of the root causes
2. Specific, actionable suggestions for each major issue
3. A recommended action (retry, manual_intervention, or accept_warnings)
```

**LLM Output** (Structured JSON):
```json
{
  "analysis": "The critical issues stem from missing required NWB metadata...",
  "suggestions": [
    {
      "issue": "Missing subject_id",
      "severity": "critical",
      "suggestion": "Add subject_id to metadata: {'subject': {'subject_id': 'mouse001'}}",
      "actionable": true
    },
    {
      "issue": "Invalid timestamps",
      "severity": "error",
      "suggestion": "Ensure timestamps are monotonically increasing...",
      "actionable": true
    }
  ],
  "recommended_action": "retry"
}
```

### 2. Conversation Agent - Retry Workflow ⭐

**File**: [backend/src/agents/conversation_agent.py](backend/src/agents/conversation_agent.py)
**Method**: `handle_retry_decision()`
**Lines**: 344-377

**Purpose**: When user approves retry, analyze corrections

**What the LLM does**:
1. User approves retry
2. System calls Evaluation Agent's `analyze_corrections`
3. LLM provides intelligent correction suggestions
4. User receives actionable guidance

**Code**:
```python
async def handle_retry_decision(
    self,
    message: MCPMessage,
    state: GlobalState,
) -> MCPResponse:
    """Handle user's retry approval/rejection."""

    if decision == "approve":
        state.increment_retry()

        # Analyze corrections with LLM if available
        if self._llm_service:
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "analyzing_corrections",
                    "message": "Analyzing validation issues for corrections",
                },
            )
```

---

## LLM Service Architecture

### Abstract Interface

**File**: [backend/src/services/llm_service.py](backend/src/services/llm_service.py)
**Class**: `LLMService` (ABC)

**Methods**:
```python
class LLMService(ABC):
    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text completion."""
        pass

    @abstractmethod
    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON output matching schema."""
        pass
```

### Anthropic Implementation

**Class**: `AnthropicLLMService`
**Model**: Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`)

**Features**:
- API key authentication
- Error handling with custom exceptions
- Structured output via prompt engineering
- Configurable temperature and max tokens

**Example Usage**:
```python
llm_service = AnthropicLLMService(api_key="sk-ant-...")

# Text completion
response = await llm_service.generate_completion(
    prompt="Analyze this NWB validation error...",
    system_prompt="You are an NWB expert.",
    temperature=0.7,
)

# Structured output
corrections = await llm_service.generate_structured_output(
    prompt="Analyze these issues...",
    output_schema={
        "type": "object",
        "properties": {
            "analysis": {"type": "string"},
            "suggestions": {"type": "array"},
            "recommended_action": {"type": "string"}
        }
    },
)
```

### Mock Implementation (Testing)

**Class**: `MockLLMService`

**Purpose**: Testing without API calls

**Features**:
- Returns predefined responses
- No API key required
- Configurable responses per prompt

**Example**:
```python
mock_llm = MockLLMService()
mock_llm.set_response(
    "Analyze validation issues",
    '{"analysis": "Mock analysis", "suggestions": []}'
)
```

---

## How to Enable LLM

### 1. Set API Key

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

### 2. Start the Server

```bash
pixi run dev
```

The server automatically detects the API key and enables LLM features:

**File**: [backend/src/api/main.py](backend/src/api/main.py#L58-L66)
```python
def get_or_create_mcp_server() -> MCPServer:
    """Get or create the MCP server with all agents registered."""
    # ...

    # Initialize LLM service if API key is available
    llm_service = None
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        llm_service = create_llm_service(
            provider="anthropic",
            api_key=api_key,
        )

    # Register agents with LLM service
    register_evaluation_agent(_mcp_server, llm_service=llm_service)
    register_conversation_agent(_mcp_server, llm_service=llm_service)
```

### 3. Verify LLM is Active

Check the logs when validation fails - you'll see:

```
[INFO] Starting correction analysis with LLM
[INFO] Correction analysis completed
```

---

## Graceful Degradation (No LLM)

### What Happens Without API Key?

The system **still works** but with reduced intelligence:

**With LLM** ✅:
```
Validation Failed
↓
LLM analyzes issues
↓
User sees intelligent suggestions:
  "Add subject_id to metadata: {'subject': {'subject_id': 'mouse001'}}"
  "Ensure timestamps are monotonically increasing"
↓
User can make informed corrections
```

**Without LLM** ⚠️:
```
Validation Failed
↓
User sees raw NWB Inspector output:
  "Missing required field: subject_id"
  "Invalid timestamps"
↓
User must figure out corrections manually
```

### Code for Graceful Degradation

**Evaluation Agent**:
```python
if not self._llm_service:
    state.add_log(
        LogLevel.ERROR,
        "LLM service not available for correction analysis",
    )
    return MCPResponse.error_response(
        reply_to=message.message_id,
        error_code="LLM_NOT_AVAILABLE",
        error_message="Correction analysis requires LLM service",
    )
```

**Conversation Agent**:
```python
if self._llm_service:
    # Use LLM for correction analysis
    return MCPResponse.success_response(
        result={"status": "analyzing_corrections"}
    )
else:
    # Ask user for manual corrections
    state.update_status(ConversionStatus.AWAITING_USER_INPUT)
    return MCPResponse.success_response(
        result={"status": "awaiting_corrections"}
    )
```

---

## LLM Configuration Options

### Change Model

Edit [backend/src/api/main.py](backend/src/api/main.py):
```python
llm_service = create_llm_service(
    provider="anthropic",
    api_key=api_key,
    model="claude-3-opus-20240229",  # Use Opus instead of Sonnet
)
```

### Adjust Temperature

Edit [backend/src/agents/evaluation_agent.py](backend/src/agents/evaluation_agent.py):
```python
result = await self._llm_service.generate_structured_output(
    prompt=prompt,
    output_schema=output_schema,
    system_prompt="You are an NWB expert.",
    temperature=0.3,  # Lower = more focused, Higher = more creative
)
```

### Add New Provider (e.g., OpenAI)

1. **Create new class** in `llm_service.py`:
```python
class OpenAILLMService(LLMService):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    async def generate_completion(self, prompt: str, **kwargs) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content
```

2. **Update factory**:
```python
def create_llm_service(provider: str, **kwargs) -> LLMService:
    if provider == "anthropic":
        return AnthropicLLMService(**kwargs)
    elif provider == "openai":
        return OpenAILLMService(**kwargs)
    elif provider == "mock":
        return MockLLMService(**kwargs)
```

3. **Use it**:
```python
llm_service = create_llm_service(
    provider="openai",
    api_key="sk-...",
    model="gpt-4-turbo-preview",
)
```

---

## Testing LLM Integration

### Unit Tests

**File**: [backend/tests/integration/test_conversion_workflow.py](backend/tests/integration/test_conversion_workflow.py)

**Test with Mock LLM**:
```python
@pytest.fixture
def mcp_server_with_agents():
    """Create MCP server with all agents registered."""
    server = MCPServer()

    # Use mock LLM service for testing
    mock_llm = MockLLMService()

    register_conversion_agent(server)
    register_evaluation_agent(server, llm_service=mock_llm)
    register_conversation_agent(server, llm_service=mock_llm)

    return server
```

### Manual Testing

**With Real LLM**:
```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Start server
pixi run dev

# Upload a file that will fail validation
curl -X POST http://localhost:8000/api/upload \
  -F "file=@invalid_data.bin"

# Check status - will show retry approval needed
curl http://localhost:8000/api/status

# Approve retry - triggers LLM analysis
curl -X POST http://localhost:8000/api/retry-approval \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve"}'

# Check logs for LLM activity
curl http://localhost:8000/api/logs | grep "correction analysis"
```

---

## LLM Costs & Usage

### Estimated Costs (Anthropic Claude 3.5 Sonnet)

**Input**: $3.00 per million tokens
**Output**: $15.00 per million tokens

**Per Correction Analysis**:
- Input: ~500 tokens (validation issues + context)
- Output: ~300 tokens (analysis + suggestions)
- Cost: ~$0.006 per analysis (less than 1 cent)

**For 1000 conversions** with ~30% failure rate:
- Analyses: 300
- Total cost: ~$1.80

Very affordable for typical use cases.

### Token Tracking

The `AnthropicLLMService` can be extended to track tokens:

```python
class AnthropicLLMService(LLMService):
    def __init__(self, api_key: str, model: str):
        # ...
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def generate_completion(self, prompt: str, **kwargs) -> str:
        response = self._client.messages.create(...)

        # Track usage
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens

        return response.content[0].text
```

---

## Summary

### ✅ LLM is Fully Implemented

**Used For**:
1. ⭐ **Correction Analysis** (Evaluation Agent)
   - Analyzes NWB validation failures
   - Suggests actionable corrections
   - Recommends retry strategy

2. ⭐ **Workflow Intelligence** (Conversation Agent)
   - Coordinates correction loop
   - Provides user guidance

**Provider**: Anthropic Claude 3.5 Sonnet
**Architecture**: Provider-agnostic with dependency injection
**Status**: Production-ready
**Optional**: Yes - graceful degradation
**Cost**: ~$0.006 per analysis

### 🔧 How to Use

```bash
# 1. Get API key from Anthropic
# Visit: https://console.anthropic.com/

# 2. Set environment variable
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Start server (auto-detects LLM)
pixi run dev

# 4. Use the system normally
# LLM will automatically enhance correction suggestions
```

### 📊 In the MVP

- ✅ LLM service abstraction
- ✅ Anthropic Claude integration
- ✅ Mock service for testing
- ✅ Graceful degradation
- ✅ Structured output generation
- ✅ Error handling
- ✅ Provider-agnostic design

**LLM is a core, working feature of the system** 🎉

---

**See Also**:
- [llm_service.py](backend/src/services/llm_service.py) - LLM service implementation
- [evaluation_agent.py](backend/src/agents/evaluation_agent.py#L176) - Correction analysis
- [conversation_agent.py](backend/src/agents/conversation_agent.py#L344) - Retry workflow
- [main.py](backend/src/api/main.py#L58) - LLM initialization
