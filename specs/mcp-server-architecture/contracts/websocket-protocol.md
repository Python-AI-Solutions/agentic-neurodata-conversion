# WebSocket Protocol Specification

**Version**: 1.0.0 **Date**: 2025-10-10 **Feature**: MCP Server Architecture -
WebSocket Transport

---

## Overview

This document defines the WebSocket message protocol for real-time bidirectional
communication between clients and the MCP orchestration server. The protocol
enables streaming progress updates, state change notifications, and interactive
communication during long-running conversion workflows.

### Protocol Characteristics

- **Message Format**: JSON Lines (newline-delimited JSON)
- **Connection URL**: `ws://[host]:[port]/api/v1/ws/conversions/{session_id}`
- **Framing**: Each message is a single-line JSON object terminated by `\n`
- **Encoding**: UTF-8
- **Heartbeat**: Server sends ping every 30 seconds, expects pong within 10
  seconds
- **Reconnection**: Client-side responsibility with exponential backoff (1s → 2s
  → 4s → ... → max 60s)

---

## Connection Lifecycle

### 1. Connection Establishment

```
Client → Server: WebSocket upgrade request
GET /api/v1/ws/conversions/{session_id} HTTP/1.1
Host: localhost:8000
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Authorization: Bearer <JWT_TOKEN>

Server → Client: WebSocket upgrade response
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

### 2. Authentication

WebSocket connections require a valid JWT token passed via `Authorization`
header or as a query parameter:

```
ws://localhost:8000/api/v1/ws/conversions/{session_id}?token=<JWT_TOKEN>
```

**Authentication Failure**:

```json
{
  "type": "error",
  "code": "unauthorized",
  "message": "Invalid or expired token"
}
```

Connection is closed with code `4001`.

### 3. Subscription

After connection, client must subscribe to session updates:

```json
{ "type": "subscribe", "session_id": "123e4567-e89b-12d3-a456-426614174000" }
```

**Server Response** (subscription confirmed):

```json
{
  "type": "subscribed",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "current_state": "converting",
  "progress_percentage": 45.5
}
```

### 4. Active Communication

Server sends updates as workflow progresses. Client can send commands and
queries.

### 5. Disconnection

**Graceful Close** (Client-initiated):

```json
{ "type": "unsubscribe", "session_id": "123e4567-e89b-12d3-a456-426614174000" }
```

**Server Response**:

```json
{ "type": "unsubscribed", "session_id": "123e4567-e89b-12d3-a456-426614174000" }
```

Connection closes with code `1000` (normal closure).

**Timeout Close** (Server-initiated): Connection closes with code `1001` (going
away) if client fails to respond to ping within 10 seconds.

**Error Close**: Connection closes with code `1011` (server error) on
unrecoverable errors.

---

## Message Types

### Client → Server Messages

#### 1. Subscribe

Subscribe to session progress updates.

```json
{
  "type": "subscribe",
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response**: `subscribed` message (see Server → Client)

---

#### 2. Unsubscribe

Unsubscribe from session updates (graceful disconnect).

```json
{
  "type": "unsubscribe",
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response**: `unsubscribed` message followed by connection close.

---

#### 3. Ping

Client-initiated keepalive (optional, server also sends pings).

```json
{
  "type": "ping",
  "timestamp": "2025-10-10T10:15:30Z"
}
```

**Response**: `pong` message with same timestamp.

---

#### 4. Query State

Request current session state (on-demand poll).

```json
{
  "type": "query_state",
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response**: `state_snapshot` message with current session state.

---

#### 5. Provide Input

Submit user input for suspended workflows (e.g., metadata questioner responses).

```json
{
  "type": "provide_input",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "input_data": {
    "experiment_description": "Multi-electrode array recording in motor cortex",
    "subject_species": "Mus musculus"
  }
}
```

**Response**: `input_received` acknowledgment, followed by workflow resumption.

---

### Server → Client Messages

#### 1. Subscribed

Confirmation of successful subscription.

```json
{
  "type": "subscribed",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "current_state": "converting",
  "progress_percentage": 45.5,
  "subscribed_at": "2025-10-10T10:15:30Z"
}
```

---

#### 2. Progress Update

Incremental progress notification during workflow execution.

```json
{
  "type": "progress_update",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-10-10T10:16:45Z",
  "current_step": "nwb_generation",
  "step_index": 3,
  "total_steps": 5,
  "progress_percentage": 62.5,
  "message": "Writing electrode metadata to NWB file",
  "details": {
    "files_processed": 12,
    "total_files": 20,
    "data_written_mb": 245.3
  }
}
```

**Fields**:

- `current_step`: Workflow step identifier (e.g., `format_detection`,
  `metadata_collection`, `nwb_generation`, `validation`)
- `step_index`: 0-based index of current step in workflow DAG
- `total_steps`: Total number of steps in workflow
- `progress_percentage`: Overall completion (0-100)
- `message`: Human-readable progress description
- `details`: Optional step-specific metrics

---

#### 3. Status Change

Workflow state transition notification.

```json
{
  "type": "status_change",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-10-10T10:18:00Z",
  "old_state": "converting",
  "new_state": "validating",
  "progress_percentage": 75.0,
  "reason": "Conversion completed, starting validation"
}
```

**State Values**: `analyzing`, `collecting_metadata`, `converting`,
`validating`, `completed`, `failed`, `cancelled`, `suspended`

---

#### 4. Error

Error notification with recovery guidance.

```json
{
  "type": "error",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-10-10T10:19:30Z",
  "error_type": "agent_timeout",
  "severity": "high",
  "message": "Conversion agent failed to respond within 300 seconds",
  "details": {
    "agent_type": "conversion",
    "timeout_seconds": 300,
    "retry_attempt": 1,
    "max_retries": 3
  },
  "recovery_suggestions": [
    "Workflow will automatically retry (attempt 1 of 3)",
    "Check agent health status",
    "Consider increasing timeout in workflow configuration"
  ],
  "recoverable": true
}
```

**Severity Levels**: `critical`, `high`, `medium`, `low`, `info`

---

#### 5. Completed

Workflow completion notification with final results.

```json
{
  "type": "completed",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-10-10T10:25:45Z",
  "final_state": "completed",
  "progress_percentage": 100.0,
  "duration_seconds": 345.2,
  "results": {
    "output_file": "/output/experiment_001.nwb",
    "file_size_mb": 512.7,
    "validation_status": "PASS",
    "quality_score": 87.5,
    "dandi_readiness_score": 92.0,
    "critical_issues": 0,
    "warnings": 3
  }
}
```

---

#### 6. Input Required

Workflow suspended, awaiting user input (e.g., metadata questioner prompts).

```json
{
  "type": "input_required",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-10-10T10:12:00Z",
  "suspended_at_step": "metadata_collection",
  "prompt": {
    "question_id": "q_001",
    "question": "What is the experiment description?",
    "field_name": "experiment_description",
    "field_type": "string",
    "required": true,
    "validation": {
      "min_length": 10,
      "max_length": 500
    },
    "help_text": "Provide a brief description of the experimental protocol"
  },
  "timeout_seconds": 3600
}
```

**Client Response**: Send `provide_input` message with answer.

---

#### 7. Pong

Heartbeat response to client or server ping.

```json
{
  "type": "pong",
  "timestamp": "2025-10-10T10:15:30Z"
}
```

---

#### 8. State Snapshot

On-demand state snapshot in response to `query_state`.

```json
{
  "type": "state_snapshot",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-10-10T10:17:00Z",
  "state": "converting",
  "current_step": "nwb_generation",
  "progress_percentage": 58.3,
  "created_at": "2025-10-10T10:10:00Z",
  "updated_at": "2025-10-10T10:17:00Z",
  "checkpoints": [
    {
      "version": 1,
      "state": "analyzing",
      "created_at": "2025-10-10T10:11:30Z"
    },
    {
      "version": 2,
      "state": "converting",
      "created_at": "2025-10-10T10:14:15Z"
    }
  ]
}
```

---

#### 9. Unsubscribed

Confirmation of unsubscription (precedes connection close).

```json
{
  "type": "unsubscribed",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-10-10T10:30:00Z"
}
```

---

## Heartbeat Protocol

### Server → Client Ping

Server sends ping every 30 seconds to detect broken connections:

```json
{
  "type": "ping",
  "timestamp": "2025-10-10T10:20:00Z"
}
```

### Client → Server Pong

Client must respond within 10 seconds:

```json
{
  "type": "pong",
  "timestamp": "2025-10-10T10:20:00Z"
}
```

**Failure**: If client fails to respond to 2 consecutive pings, server closes
connection with code `1001`.

---

## Error Handling

### Invalid Message Format

**Client sends malformed JSON**:

```json
{type: subscribe, session_id: 123}  // Missing quotes
```

**Server Response**:

```json
{
  "type": "error",
  "code": "invalid_message_format",
  "message": "Message is not valid JSON",
  "details": {
    "parse_error": "Expecting property name enclosed in double quotes"
  }
}
```

Connection remains open.

---

### Unknown Message Type

**Client sends unsupported type**:

```json
{ "type": "unknown_action", "data": "..." }
```

**Server Response**:

```json
{
  "type": "error",
  "code": "unknown_message_type",
  "message": "Message type 'unknown_action' is not supported",
  "supported_types": [
    "subscribe",
    "unsubscribe",
    "ping",
    "query_state",
    "provide_input"
  ]
}
```

---

### Session Not Found

**Client subscribes to non-existent session**:

```json
{ "type": "subscribe", "session_id": "999e9999-e89b-12d3-a456-426614174999" }
```

**Server Response**:

```json
{
  "type": "error",
  "code": "session_not_found",
  "message": "Session 999e9999-e89b-12d3-a456-426614174999 does not exist"
}
```

Connection closes with code `4004` (not found).

---

## Reconnection Strategy

### Client-Side Reconnection Logic

1. **Detect Disconnection**: Monitor WebSocket `onclose` and `onerror` events
2. **Exponential Backoff**:
   - Initial delay: 1 second
   - Double delay after each failed attempt: 1s → 2s → 4s → 8s → 16s → 32s → 60s
     (max)
3. **Jitter**: Add random jitter (±25%) to prevent thundering herd
4. **Max Attempts**: Retry indefinitely while session is active, stop on
   terminal states (`completed`, `failed`, `cancelled`)
5. **Resume Subscription**: After reconnection, immediately send `subscribe`
   message
6. **State Sync**: Server sends `subscribed` with current state, client updates
   UI

### Example Reconnection Sequence

```
1. Connection lost (network issue)
2. Wait 1 second → reconnect attempt 1 → FAILED
3. Wait 2 seconds → reconnect attempt 2 → FAILED
4. Wait 4 seconds → reconnect attempt 3 → SUCCESS
5. Send subscribe message
6. Receive subscribed with current state
7. Resume receiving updates
```

---

## Backpressure Handling

### Server-Side Backpressure

If client send buffer is full (slow consumer):

- **Behavior**: Server drops intermediate `progress_update` messages
- **Preservation**: Always send `status_change`, `error`, `completed`,
  `input_required` (critical messages)
- **Rationale**: Prefer latest state over complete history for progress updates

### Client-Side Backpressure

If client is overwhelmed with messages:

- **Client Action**: Batch UI updates (e.g., update progress bar at most once
  per 500ms)
- **Server Rate Limiting**: Progress updates sent at most once per second per
  session

---

## Security Considerations

1. **Authentication**: JWT token required in header or query parameter
2. **Authorization**: Token must have access to requested `session_id`
3. **Input Validation**: All client messages validated against JSON schema
4. **Rate Limiting**: Max 10 messages per second per connection
5. **Connection Limits**: Max 100 concurrent WebSocket connections per user
6. **Message Size**: Max 1MB per message

---

## Example Client Implementation (JavaScript)

```javascript
class ConversionWebSocketClient {
  constructor(sessionId, token) {
    this.sessionId = sessionId;
    this.token = token;
    this.reconnectDelay = 1000; // Start at 1 second
    this.maxReconnectDelay = 60000; // Cap at 60 seconds
    this.connect();
  }

  connect() {
    const url = `ws://localhost:8000/api/v1/ws/conversions/${this.sessionId}?token=${this.token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("Connected");
      this.reconnectDelay = 1000; // Reset backoff
      this.subscribe();
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    this.ws.onclose = (event) => {
      console.log(`Disconnected: ${event.code} ${event.reason}`);
      if (event.code !== 1000) {
        // Not normal closure
        this.scheduleReconnect();
      }
    };

    // Heartbeat
    setInterval(() => {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: "ping", timestamp: new Date().toISOString() });
      }
    }, 30000);
  }

  subscribe() {
    this.send({ type: "subscribe", session_id: this.sessionId });
  }

  send(message) {
    this.ws.send(JSON.stringify(message) + "\n");
  }

  handleMessage(message) {
    switch (message.type) {
      case "subscribed":
        console.log("Subscribed to session:", message.session_id);
        break;
      case "progress_update":
        console.log(
          `Progress: ${message.progress_percentage}% - ${message.message}`,
        );
        break;
      case "status_change":
        console.log(
          `State changed: ${message.old_state} → ${message.new_state}`,
        );
        break;
      case "completed":
        console.log("Workflow completed:", message.results);
        break;
      case "error":
        console.error("Error:", message.message);
        break;
      case "pong":
        // Heartbeat response
        break;
      default:
        console.warn("Unknown message type:", message.type);
    }
  }

  scheduleReconnect() {
    setTimeout(() => {
      console.log(`Reconnecting in ${this.reconnectDelay}ms...`);
      this.connect();
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay,
      );
    }, this.reconnectDelay);
  }

  close() {
    this.send({ type: "unsubscribe", session_id: this.sessionId });
    this.ws.close(1000, "Client closing");
  }
}

// Usage
const client = new ConversionWebSocketClient(
  "123e4567-e89b-12d3-a456-426614174000",
  "JWT_TOKEN",
);
```

---

## WebSocket Close Codes

| Code | Name              | Description                      |
| ---- | ----------------- | -------------------------------- |
| 1000 | Normal Closure    | Graceful close after unsubscribe |
| 1001 | Going Away        | Server shutdown or timeout       |
| 1011 | Server Error      | Unrecoverable server error       |
| 4001 | Unauthorized      | Invalid or expired token         |
| 4004 | Not Found         | Session does not exist           |
| 4429 | Too Many Requests | Rate limit exceeded              |

---

## Testing Recommendations

### Contract Tests

1. **Message Schema Validation**: Validate all message types against JSON
   schemas
2. **Reconnection Logic**: Test exponential backoff and state sync after
   reconnect
3. **Heartbeat Handling**: Verify ping/pong and timeout behavior
4. **Error Scenarios**: Test malformed messages, auth failures, session not
   found

### Integration Tests

1. **Full Workflow**: Subscribe → receive updates → completion
2. **Interrupted Workflow**: Disconnect mid-workflow → reconnect → resume
   updates
3. **Interactive Input**: Receive `input_required` → send `provide_input` →
   workflow resumes
4. **Multi-Client**: Multiple clients subscribed to same session receive
   identical updates

---

**Status**: Contract Complete **Next**: Implement WebSocket adapter in
`src/adapters/http/websocket_adapter.py`
