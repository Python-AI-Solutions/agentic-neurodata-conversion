# MCP (Model Context Protocol) Architecture Guide

## Overview

MCP (Model Context Protocol) is the **central communication layer** in this project that enables the three-agent architecture to work together. It's a custom implementation (not the Anthropic MCP SDK) designed specifically for this neurodata conversion system.

---

## 📍 Location in Project

### Core MCP Files

1. **MCP Server Implementation**
   - **File:** [backend/src/services/mcp_server.py](backend/src/services/mcp_server.py)
   - **Class:** `MCPServer`
   - **Role:** Central message router and state manager

2. **MCP Message Models**
   - **File:** [backend/src/models/mcp.py](backend/src/models/mcp.py)
   - **Classes:** `MCPMessage`, `MCPResponse`, `MCPEvent`
   - **Role:** Define message structure (JSON-RPC 2.0 based)

3. **Service Exports**
   - **File:** [backend/src/services/__init__.py](backend/src/services/__init__.py)
   - **Exports:** `MCPServer`, `get_mcp_server`, `create_llm_service`

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Layer                        │
│              (backend/src/api/main.py)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   MCP Server                            │
│          (backend/src/services/mcp_server.py)          │
│                                                         │
│  • Message Routing                                      │
│  • Global State Management                              │
│  • Event Broadcasting                                   │
│  • Handler Registration                                 │
└──────┬──────────────┬──────────────┬───────────────────┘
       │              │              │
       ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌──────────────┐
│Conversation │ │ Conversion  │ │ Evaluation   │
│   Agent     │ │   Agent     │ │   Agent      │
└─────────────┘ └─────────────┘ └──────────────┘
```

---

## 📦 MCP Components

### 1. MCPMessage (Request)

**File:** [backend/src/models/mcp.py:13-46](backend/src/models/mcp.py#L13-L46)

```python
class MCPMessage(BaseModel):
    message_id: str          # Unique identifier (UUID)
    target_agent: str        # "conversation" | "conversion" | "evaluation"
    action: str              # Action to perform (e.g., "detect_format")
    context: Dict[str, Any]  # Action-specific data
    timestamp: datetime      # When message was created
    reply_to: Optional[str]  # For tracking request/response chains
```

**Example:**
```python
message = MCPMessage(
    target_agent="conversion",
    action="detect_format",
    context={"input_path": "/path/to/data.bin"}
)
```

---

### 2. MCPResponse (Reply)

**File:** [backend/src/models/mcp.py:49-119](backend/src/models/mcp.py#L49-L119)

```python
class MCPResponse(BaseModel):
    message_id: str          # Response ID
    reply_to: str            # Original message ID
    success: bool            # True if succeeded
    result: Optional[Dict]   # Data if success=True
    error: Optional[Dict]    # Error details if success=False
    timestamp: datetime      # When response was created
```

**Helper Methods:**
```python
# Success response
MCPResponse.success_response(
    reply_to="original-msg-id",
    result={"format": "SpikeGLX", "confidence": 0.95}
)

# Error response
MCPResponse.error_response(
    reply_to="original-msg-id",
    error_code="FORMAT_DETECTION_FAILED",
    error_message="No .meta file found"
)
```

---

### 3. MCPServer (Router)

**File:** [backend/src/services/mcp_server.py:13-171](backend/src/services/mcp_server.py#L13-L171)

**Key Methods:**

#### `register_handler(agent_name, action, handler)`
Registers a function to handle specific agent actions.

```python
# Example: Conversion agent registers format detection
mcp_server.register_handler(
    agent_name="conversion",
    action="detect_format",
    handler=async_detect_format_function
)
```

#### `send_message(message) → MCPResponse`
Sends a message to an agent and waits for response.

```python
# Example: Conversation agent asks Conversion agent to detect format
message = MCPMessage(
    target_agent="conversion",
    action="detect_format",
    context={"input_path": "/data/file.bin"}
)
response = await mcp_server.send_message(message)
```

#### `broadcast_event(event)`
Broadcasts events to all subscribers (e.g., WebSocket clients).

```python
# Example: Notify frontend of status change
event = MCPEvent(
    event_type="status_change",
    data={"status": "converting", "progress": 50}
)
await mcp_server.broadcast_event(event)
```

#### `global_state` (property)
Access to shared global state across all agents.

```python
state = mcp_server.global_state
state.status = ConversionStatus.PROCESSING
state.add_log(LogLevel.INFO, "Starting conversion")
```

---

## 🔄 How MCP is Used - Message Flow

### Example: Complete Conversion Workflow

```python
# 1. USER UPLOADS FILE
# FastAPI receives file → Stores in global state

# 2. USER STARTS CONVERSION
# API calls Conversation Agent
POST /api/start-conversion

# 3. CONVERSATION AGENT → CONVERSION AGENT
msg1 = MCPMessage(
    target_agent="conversion",
    action="detect_format",
    context={"input_path": state.input_path}
)
response1 = await mcp_server.send_message(msg1)
# Response: {"success": True, "result": {"format": "SpikeGLX"}}

# 4. CONVERSATION AGENT → CONVERSION AGENT
msg2 = MCPMessage(
    target_agent="conversion",
    action="run_conversion",
    context={
        "input_path": state.input_path,
        "metadata": state.metadata,
        "format": "SpikeGLX"
    }
)
response2 = await mcp_server.send_message(msg2)
# Response: {"success": True, "result": {"output_path": "/outputs/file.nwb"}}

# 5. CONVERSION AGENT → EVALUATION AGENT
msg3 = MCPMessage(
    target_agent="evaluation",
    action="validate_nwb",
    context={"nwb_path": response2.result["output_path"]}
)
response3 = await mcp_server.send_message(msg3)
# Response: {
#   "success": True,
#   "result": {
#     "overall_status": "PASSED_WITH_ISSUES",
#     "issues": [...]
#   }
# }

# 6. EVALUATION AGENT → CONVERSATION AGENT
# (Evaluation sends validation results back to Conversation for user decision)
msg4 = MCPMessage(
    target_agent="conversation",
    action="handle_validation_result",
    context={"validation_result": response3.result}
)
response4 = await mcp_server.send_message(msg4)
```

---

## 🎯 Agent Registration

### Where Agents Register Their Handlers

**File:** [backend/src/api/main.py:89-91](backend/src/api/main.py#L89-L91)

```python
def get_or_create_mcp_server() -> MCPServer:
    global _mcp_server

    if _mcp_server is None:
        _mcp_server = get_mcp_server()

        # Initialize LLM service
        llm_service = create_llm_service(...)

        # Register all three agents
        register_conversion_agent(_mcp_server, llm_service=llm_service)
        register_evaluation_agent(_mcp_server, llm_service=llm_service)
        register_conversation_agent(_mcp_server, llm_service=llm_service)

    return _mcp_server
```

### Agent Registration Functions

Each agent has a `register_*_agent()` function:

#### 1. Conversation Agent
**File:** [backend/src/agents/conversation_agent.py](backend/src/agents/conversation_agent.py)

```python
def register_conversation_agent(
    mcp_server: MCPServer,
    llm_service: Optional[LLMService] = None,
) -> ConversationAgent:
    """Register conversation agent handlers."""
    agent = ConversationAgent(mcp_server, llm_service)

    # Register handlers for each action
    mcp_server.register_handler(
        "conversation",
        "start_conversion",
        agent.start_conversion
    )
    mcp_server.register_handler(
        "conversation",
        "handle_user_message",
        agent.handle_user_message
    )
    mcp_server.register_handler(
        "conversation",
        "handle_validation_result",
        agent.handle_validation_result
    )
    # ... more handlers

    return agent
```

#### 2. Conversion Agent
**File:** [backend/src/agents/conversion_agent.py](backend/src/agents/conversion_agent.py)

```python
def register_conversion_agent(
    mcp_server: MCPServer,
    llm_service: Optional[LLMService] = None,
) -> ConversionAgent:
    """Register conversion agent handlers."""
    agent = ConversionAgent(mcp_server, llm_service)

    mcp_server.register_handler(
        "conversion",
        "detect_format",
        agent.detect_format
    )
    mcp_server.register_handler(
        "conversion",
        "run_conversion",
        agent.run_conversion
    )
    mcp_server.register_handler(
        "conversion",
        "apply_corrections",
        agent.apply_corrections
    )

    return agent
```

#### 3. Evaluation Agent
**File:** [backend/src/agents/evaluation_agent.py](backend/src/agents/evaluation_agent.py)

```python
def register_evaluation_agent(
    mcp_server: MCPServer,
    llm_service: Optional[LLMService] = None,
) -> EvaluationAgent:
    """Register evaluation agent handlers."""
    agent = EvaluationAgent(mcp_server, llm_service)

    mcp_server.register_handler(
        "evaluation",
        "validate_nwb",
        agent.validate_nwb
    )
    mcp_server.register_handler(
        "evaluation",
        "generate_report",
        agent.generate_report
    )

    return agent
```

---

## 🔍 Real-World Example: Metadata Collection

**Scenario:** User provides metadata via chat, system needs to process it.

### 1. Frontend sends message
```javascript
// frontend/public/chat-ui.html
fetch('/api/chat', {
    method: 'POST',
    body: formData  // contains user message
})
```

### 2. API receives and routes to Conversation Agent
```python
# backend/src/api/main.py
@app.post("/api/chat")
async def chat_message(message: str = Form(...)):
    mcp_server = get_or_create_mcp_server()

    # Send to conversation agent
    msg = MCPMessage(
        target_agent="conversation",
        action="handle_user_message",
        context={"message": message}
    )

    response = await mcp_server.send_message(msg)
    return response.result
```

### 3. Conversation Agent processes message
```python
# backend/src/agents/conversation_agent.py
async def handle_user_message(
    self,
    message: MCPMessage,
    state: GlobalState
) -> MCPResponse:
    user_message = message.context["message"]

    # Extract metadata using LLM
    extracted = await self._metadata_inference_engine.extract_metadata(
        user_message
    )

    # Update global state
    state.metadata.update(extracted)

    # Check if ready to proceed
    if self._has_all_required_metadata(state):
        # Start conversion by sending message to conversion agent
        conv_msg = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": state.input_path,
                "metadata": state.metadata
            }
        )
        await self._mcp_server.send_message(conv_msg)

        return MCPResponse.success_response(
            reply_to=message.message_id,
            result={"status": "conversion_started"}
        )
    else:
        return MCPResponse.success_response(
            reply_to=message.message_id,
            result={
                "needs_more_info": True,
                "message": "I still need subject_id..."
            }
        )
```

---

## 🌐 Event Broadcasting (WebSocket)

MCP also handles real-time updates to frontend via WebSocket.

### Backend: Broadcast Event
```python
# In any agent
event = MCPEvent(
    event_type="validation_complete",
    data={
        "overall_status": "PASSED_WITH_ISSUES",
        "issue_count": 3
    }
)
await mcp_server.broadcast_event(event)
```

### Frontend: Receive Event
```javascript
// frontend/public/chat-ui.html
websocket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.event_type === 'validation_complete') {
        updateUI(message.data);
    }
};
```

---

## 📊 Global State Management

MCP Server maintains a **single source of truth** - the GlobalState.

**File:** [backend/src/models/state.py](backend/src/models/state.py)

```python
class GlobalState(BaseModel):
    status: ConversionStatus
    validation_status: Optional[ValidationStatus]
    input_path: Optional[Path]
    output_path: Optional[Path]
    metadata: Dict[str, Any]
    logs: List[LogEntry]
    # ... more fields
```

**All agents access the same state:**
```python
# In any agent handler
async def some_handler(
    self,
    message: MCPMessage,
    state: GlobalState  # ← Injected by MCP Server
) -> MCPResponse:
    # Modify state
    state.status = ConversionStatus.PROCESSING
    state.add_log(LogLevel.INFO, "Processing...")

    # State changes are immediately visible to all agents
```

---

## 🔧 Key Features

### 1. Decoupled Agents
- Agents never import each other directly
- Communication only through MCP messages
- Easy to test agents in isolation

### 2. Async/Await Support
- All message handlers are async
- Non-blocking communication
- Can handle long-running operations

### 3. Type Safety
- Pydantic models for messages and responses
- Validation at message boundaries
- Clear contracts between agents

### 4. Observability
- All messages logged
- Event broadcasting for real-time updates
- Global state accessible for debugging

### 5. Error Handling
- Standardized error responses
- Error codes and messages
- Failed messages don't crash the system

---

## 📝 MCP vs Anthropic MCP

**Important:** This is **NOT** the Anthropic MCP SDK. It's a custom implementation inspired by MCP concepts.

| Feature | This Project | Anthropic MCP |
|---------|-------------|---------------|
| **Purpose** | Internal agent communication | External tool/data source integration |
| **Protocol** | Custom JSON-RPC 2.0 based | Anthropic MCP protocol |
| **Scope** | Three agents (Conversation, Conversion, Evaluation) | LLM → External tools |
| **Implementation** | Custom Python code | MCP SDK |
| **Message Format** | `MCPMessage`, `MCPResponse` | MCP protocol messages |

**Why custom implementation?**
- Simpler than full MCP SDK for internal use
- Tailored to three-agent architecture
- Direct integration with FastAPI
- No external dependencies

---

## 🧪 Testing MCP

**File:** [backend/tests/unit/test_mcp_server.py](backend/tests/unit/test_mcp_server.py)

```python
def test_mcp_message_routing():
    mcp_server = MCPServer()

    # Register handler
    async def test_handler(msg, state):
        return MCPResponse.success_response(
            reply_to=msg.message_id,
            result={"received": True}
        )

    mcp_server.register_handler("test_agent", "test_action", test_handler)

    # Send message
    msg = MCPMessage(
        target_agent="test_agent",
        action="test_action",
        context={"foo": "bar"}
    )

    response = await mcp_server.send_message(msg)

    assert response.success == True
    assert response.result["received"] == True
```

---

## 🎓 Summary

### MCP in this project is:

1. **A Message Router** - Routes messages between agents
2. **A State Manager** - Manages global conversion state
3. **An Event Bus** - Broadcasts events to subscribers (WebSocket)
4. **A Registry** - Registers agent handlers for actions

### Key Files:
- `backend/src/services/mcp_server.py` - MCP Server implementation
- `backend/src/models/mcp.py` - Message/Response models
- Agent files - Handler registration and usage

### Message Flow:
```
User → API → MCP Server → Agent Handler → MCP Server → Response → API → User
                   ↓
             Global State (shared)
                   ↓
         Event Broadcasting (WebSocket)
```

This architecture enables the three-agent system to work together seamlessly while maintaining clean separation of concerns.
