import asyncio
from dataclasses import dataclass, field
import json
import os
from typing import Any, Optional
import uuid

from openai import OpenAI  # pip install openai
import yaml


# --- Simulated MCP SDK Classes ---
class MCPRequest:
    def __init__(self, method: str, params: dict, request_id: str = None):
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
                return json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": f"Unknown method {method}",
                    }
                )

            result = await self.methods[method](params)
            return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})

        except Exception as e:
            return json.dumps(
                {"jsonrpc": "2.0", "id": message.get("id", None), "error": str(e)}
            )


# --- Data Models ---
@dataclass
class ConversationSession:
    session_id: str
    user_id: str
    dataset_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    ai_suggestions: list[dict] = field(default_factory=list)


# --- Conversation Agent ---
class ConversationAgentMCP:
    def __init__(
        self,
        generation_agent_host: str = "localhost",
        generation_agent_port: int = 8002,
    ):
        self.server = MCPServer(name="conversation_agent", version="1.2.0")
        self.sessions: dict[str, ConversationSession] = {}

        # Register MCP methods
        self.server.register_method("conversation/initiate", self.start_conversation)
        self.server.register_method("conversation/metadata", self.submit_metadata)
        self.server.register_method("conversation/validate", self.validate_metadata)
        self.server.register_method("conversation/handoff", self.handoff_to_generation)
        self.server.register_method("conversation/context", self.load_context)

        # Generation agent config
        self.generation_agent_host = generation_agent_host
        self.generation_agent_port = generation_agent_port

        # Context path (schemas, prior examples, etc.)
        self.context_path = os.getenv("CONTEXT_PATH", "./context")
        self.context_store: dict[str, Any] = {}
        self._load_context_files()

        # LLM setup
        self.llm_provider = os.getenv("LLM_PROVIDER", "none")  # must be "openai"
        self.openai_api_key = os.getenv("OPENAI_API_KEY", None)
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_client = None
        if self.llm_provider == "openai" and self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)

    def _load_context_files(self):
        """Load all YAML/JSON files from context path"""
        if not os.path.isdir(self.context_path):
            return
        for file in os.listdir(self.context_path):
            full_path = os.path.join(self.context_path, file)
            try:
                if file.endswith((".yaml", ".yml")):
                    with open(full_path) as f:
                        self.context_store[file] = yaml.safe_load(f)
                elif file.endswith(".json"):
                    with open(full_path) as f:
                        self.context_store[file] = json.load(f)
            except Exception as e:
                print(f"Failed to load context {file}: {e}")

    async def start_conversation(self, params: dict):
        session_id = str(uuid.uuid4())
        session = ConversationSession(session_id=session_id, user_id=params["user_id"])
        self.sessions[session_id] = session
        return {"session_id": session_id, "status": "started"}

    async def submit_metadata(self, params: dict):
        session_id = params["session_id"]
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Invalid session_id")

        session.dataset_path = params.get("dataset_path")
        session.metadata.update(params.get("metadata", {}))
        session.missing_fields = params.get("missing_fields", [])
        return {"status": "metadata received", "session_id": session_id}

    async def validate_metadata(self, params: dict):
        session_id = params["session_id"]
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Invalid session_id")

        if "subject_id" not in session.metadata:
            session.missing_fields.append("subject_id")

        # If OpenAI enabled, call it
        if self.openai_client and session.missing_fields:
            ai_suggestions = await self._ask_openai(
                session.metadata, session.missing_fields
            )
            session.ai_suggestions.extend(ai_suggestions)

        return {
            "session_id": session_id,
            "valid": len(session.missing_fields) == 0,
            "missing_fields": session.missing_fields,
            "ai_suggestions": session.ai_suggestions,
        }

    async def handoff_to_generation(self, params: dict):
        """Pass session data to Generation Agent"""
        session_id = params["session_id"]
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Invalid session_id")

        request_payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "conversion/execute",
            "params": {
                "session_id": session_id,
                "input_path": session.dataset_path,
                "output_path": f"/data/output/{session_id}.nwb",
                "conversion_config": {},
                "metadata": session.metadata,
                "provenance": {},
            },
        }

        reader, writer = await asyncio.open_connection(
            self.generation_agent_host, self.generation_agent_port
        )
        writer.write((json.dumps(request_payload) + "\n").encode())
        await writer.drain()

        raw_response = await reader.readline()
        writer.close()
        await writer.wait_closed()

        return json.loads(raw_response.decode())

    async def load_context(self, params: dict):
        """Return loaded context files or a specific one"""
        file_name = params.get("file_name")
        if file_name:
            return self.context_store.get(file_name, {})
        return self.context_store

    async def _ask_openai(
        self, metadata: dict, missing_fields: list[str]
    ) -> list[dict]:
        """Call OpenAI with metadata + context to fill missing fields"""
        context_str = json.dumps(self.context_store, indent=2)

        prompt = f"""
        You are assisting in filling missing NWB metadata fields.
        Current metadata: {json.dumps(metadata, indent=2)}
        Missing fields: {missing_fields}
        Reference schemas and examples: {context_str}

        For each missing field, suggest a plausible value.
        Return only a JSON list of objects with keys: field, suggestion.
        """

        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a neuroscience metadata assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        try:
            suggestions = json.loads(response.choices[0].message.content)
            return suggestions
        except Exception:
            return [{"field": f, "suggestion": "Unknown"} for f in missing_fields]


# --- Example MCP Agent Runner ---
async def run_server(agent: ConversationAgentMCP):
    print("Conversation Agent MCP server running... (stdin/stdout mode)")
    while True:
        raw_input = await asyncio.to_thread(input)  # simulate message bus
        if not raw_input:
            continue
        response = await agent.server.handle(raw_input)
        print(response)


if __name__ == "__main__":
    agent = ConversationAgentMCP()
    asyncio.run(run_server(agent))
