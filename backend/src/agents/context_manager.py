"""
Intelligent Conversation Context Management.

Manages conversation history with smart summarization to prevent
context overflow while preserving critical information.
"""
from typing import Any, Dict, List, Optional
import json

from models import GlobalState, LogLevel
from services import LLMService


class ConversationContextManager:
    """
    Manages conversation context with intelligent summarization.

    Key features:
    - Rolling window with recent messages kept verbatim
    - LLM-powered summarization of older messages
    - Preservation of critical information (metadata, decisions)
    - Configurable context limits
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        max_messages: int = 50,
        keep_recent: int = 10,
        summarize_threshold: int = 15,
    ):
        """
        Initialize context manager.

        Args:
            llm_service: LLM service for summarization
            max_messages: Maximum messages to keep (hard limit)
            keep_recent: Number of recent messages to keep verbatim
            summarize_threshold: Trigger summarization when exceeds this
        """
        self.llm_service = llm_service
        self.max_messages = max_messages
        self.keep_recent = keep_recent
        self.summarize_threshold = summarize_threshold

    async def manage_context(
        self,
        conversation_history: List[Dict[str, Any]],
        state: GlobalState,
    ) -> List[Dict[str, Any]]:
        """
        Manage conversation context intelligently.

        Args:
            conversation_history: Current conversation history
            state: Global state for logging

        Returns:
            Optimized conversation history
        """
        # If under threshold, no action needed
        if len(conversation_history) <= self.summarize_threshold:
            return conversation_history

        # If no LLM, use simple truncation
        if not self.llm_service:
            return self._simple_truncation(conversation_history, state)

        # Use LLM-powered summarization
        try:
            return await self._smart_summarization(conversation_history, state)
        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Context summarization failed, using simple truncation: {e}"
            )
            return self._simple_truncation(conversation_history, state)

    def _simple_truncation(
        self,
        conversation_history: List[Dict[str, Any]],
        state: GlobalState,
    ) -> List[Dict[str, Any]]:
        """
        Simple truncation fallback (no LLM needed).

        Keeps most recent messages and critical system messages.
        """
        state.add_log(
            LogLevel.DEBUG,
            f"Using simple truncation (no LLM)",
            {"original_length": len(conversation_history)}
        )

        # Keep last N messages
        recent = conversation_history[-self.keep_recent:]

        # Extract critical info from older messages
        older = conversation_history[:-self.keep_recent]
        critical_info = self._extract_critical_info(older)

        # Create summary message
        summary_msg = {
            "role": "system",
            "content": f"[Conversation summary]: {critical_info}",
            "timestamp": "system_generated"
        }

        return [summary_msg] + recent

    def _extract_critical_info(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Extract critical information from messages (keyword-based).
        """
        critical_parts = []

        for msg in messages:
            content = msg.get("content", "").lower()

            # Extract metadata mentions
            if any(keyword in content for keyword in ["experimenter", "institution", "experiment"]):
                critical_parts.append(f"User mentioned: {msg.get('content', '')[:100]}")

            # Extract decisions
            if any(keyword in content for keyword in ["skip", "retry", "cancel", "proceed"]):
                critical_parts.append(f"Decision: {msg.get('content', '')[:100]}")

        return " | ".join(critical_parts) if critical_parts else "Previous conversation context"

    async def _smart_summarization(
        self,
        conversation_history: List[Dict[str, Any]],
        state: GlobalState,
    ) -> List[Dict[str, Any]]:
        """
        LLM-powered smart summarization.

        Preserves critical information while reducing token count.
        """
        # Keep last N messages verbatim
        recent_messages = conversation_history[-self.keep_recent:]
        older_messages = conversation_history[:-self.keep_recent]

        state.add_log(
            LogLevel.DEBUG,
            f"Summarizing conversation context",
            {
                "total_messages": len(conversation_history),
                "recent_kept": len(recent_messages),
                "older_to_summarize": len(older_messages)
            }
        )

        # Format older messages for summarization
        formatted_conversation = self._format_messages_for_summary(older_messages)

        # LLM summarization prompt
        system_prompt = """You are an expert conversation summarizer for neuroscience data conversion.

Your goal: Create a concise summary that preserves ALL critical information while reducing verbosity.

Focus on:
1. Metadata provided by user (experimenter names, institutions, dates, descriptions)
2. User decisions (skip, retry, accept, decline)
3. Files mentioned or uploaded
4. Errors or issues discussed
5. Current conversion state

Omit:
- Pleasantries and acknowledgments
- Repeated questions
- System status messages

Format: Structured bullet points, max 250 words."""

        user_prompt = f"""Summarize this conversation history:

{formatted_conversation}

Create a structured summary highlighting:
- Key metadata provided
- User decisions made
- Files and formats discussed
- Issues encountered
- Current state

Be concise but preserve ALL critical details."""

        try:
            # Get summary from LLM
            summary = await self.llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for factual summarization
                max_tokens=400,
            )

            # Create summary message
            summary_msg = {
                "role": "system",
                "content": f"[Previous conversation summary]:\n\n{summary}",
                "timestamp": "llm_generated",
                "metadata": {
                    "summarized_messages": len(older_messages),
                    "summary_tokens_approx": len(summary.split())
                }
            }

            state.add_log(
                LogLevel.INFO,
                f"Conversation context summarized successfully",
                {
                    "original_messages": len(conversation_history),
                    "new_messages": len([summary_msg] + recent_messages),
                    "compression_ratio": f"{len(older_messages)}/{len([summary_msg] + recent_messages)}"
                }
            )

            return [summary_msg] + recent_messages

        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"LLM summarization failed: {e}"
            )
            raise

    def _format_messages_for_summary(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Format messages for LLM summarization.
        """
        formatted_lines = []

        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            # Format each message
            formatted_lines.append(f"[{i}] {role.upper()}: {content[:200]}")

            # Add context if available
            if "context" in msg:
                context = msg["context"]
                if "field" in context:
                    formatted_lines.append(f"    Context: Asking for field '{context['field']}'")

        return "\n".join(formatted_lines)

    def should_summarize(self, conversation_history: List[Dict[str, Any]]) -> bool:
        """
        Determine if summarization is needed.
        """
        return len(conversation_history) > self.summarize_threshold

    def estimate_tokens(self, conversation_history: List[Dict[str, Any]]) -> int:
        """
        Rough estimate of token count.

        Uses simple word count * 1.3 approximation.
        """
        total_chars = sum(len(str(msg.get("content", ""))) for msg in conversation_history)
        estimated_words = total_chars / 5  # Rough chars-to-words
        estimated_tokens = int(estimated_words * 1.3)  # Words-to-tokens approximation
        return estimated_tokens
