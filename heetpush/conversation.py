import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# --- Simulated MCP SDK Classes ---
class MCPRequest:
    def __init__(self, method: str, params: Dict, request_id: str = None):
        self.method = method
        self.params = params
        self.id = request_id or str(uuid.uuid4())


class MCPResponse:
    def __init__(self, result: Any = None, error: str = None, request_id: str = None):
        self.result = result
        self.error = error
        self.id = request_id


class MCPServer:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.methods = {}

    def register_method(self, name: str, func):
        self.methods[name] = func

    async def handle(self, raw_message: str) -> str:
        """Handle incoming JSON-RPC requests"""
        try:
            message = json.loads(raw_message)
            method = message["method"]
            params = message.get("params", {})
            request_id = message.get("id")

            if method not in self.methods:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": f"Unknown method {method}"
                })

            result = await self.methods[method](params)
            return json.dumps({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            })

        except Exception as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": message.get("id", None),
                "error": str(e)
            })


# --- Data Models ---
@dataclass
class ConversationSession:
    session_id: str
    user_id: str
    dataset_path: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)
    ai_suggestions: List[Dict] = field(default_factory=list)


# --- Conversation Agent ---
class ConversationAgentMCP:
    def __init__(self):
        self.server = MCPServer(name="conversation_agent", version="1.0.0")
        self.sessions: Dict[str, ConversationSession] = {}

        # Register MCP methods
        self.server.register_method("conversation/initiate", self.start_conversation)
        self.server.register_method("conversation/metadata", self.submit_metadata)
        self.server.register_method("conversation/validate", self.validate_metadata)

    async def start_conversation(self, params: Dict):
        session_id = str(uuid.uuid4())
        session = ConversationSession(session_id=session_id, user_id=params["user_id"])
        self.sessions[session_id] = session
        return {"session_id": session_id, "status": "started"}

    async def submit_metadata(self, params: Dict):
        session_id = params["session_id"]
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Invalid session_id")

        session.dataset_path = params.get("dataset_path")
        session.metadata.update(params.get("metadata", {}))
        session.missing_fields = params.get("missing_fields", [])
        return {"status": "metadata received", "session_id": session_id}

    async def validate_metadata(self, params: Dict):
        session_id = params["session_id"]
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Invalid session_id")

        if "subject_id" not in session.metadata:
            session.missing_fields.append("subject_id")

        return {
            "session_id": session_id,
            "valid": len(session.missing_fields) == 0,
            "missing_fields": session.missing_fields,
            "ai_suggestions": session.ai_suggestions,
        }


# --- Example MCP Agent Runner ---
async def run_server(agent: ConversationAgentMCP):
    print("Conversation Agent MCP server running... (listening on stdin/stdout)")
    loop = asyncio.get_running_loop()

    # For demo purposes, read stdin line by line
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, asyncio.StreamReader())

    while True:
        raw_input = await asyncio.to_thread(input)  # blocking input()
        if not raw_input:
            continue
        response = await agent.server.handle(raw_input)
        print(response)


if __name__ == "__main__":
    agent = ConversationAgentMCP()
    asyncio.run(run_server(agent))
