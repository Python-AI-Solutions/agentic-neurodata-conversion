"""
Intelligent Error Recovery and Handling.

This module uses LLM to intelligently handle errors and suggest recovery actions.
Instead of generic error messages, it provides context-aware guidance.
"""
from typing import Any, Dict, List, Optional
import json

from models import GlobalState, LogLevel
from services import LLMService


class IntelligentErrorRecovery:
    """
    LLM-powered error analysis and recovery suggestions.

    Features:
    - Analyzes errors in context
    - Suggests specific recovery actions
    - Learns from error patterns
    - Provides user-friendly explanations
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the error recovery system.

        Args:
            llm_service: Optional LLM service for intelligent analysis
        """
        self.llm_service = llm_service
        self.error_history = []

    async def analyze_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Analyze an error and provide intelligent recovery suggestions.

        Args:
            error: The exception that occurred
            context: Context about what was happening
            state: Global conversion state

        Returns:
            Dict with:
            - user_message: User-friendly explanation
            - technical_details: Technical error info
            - recovery_actions: List of suggested actions
            - severity: Error severity (low/medium/high/critical)
            - is_recoverable: Whether this can be recovered
        """
        # Record error for pattern analysis
        self.error_history.append({
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": state.updated_at.isoformat(),
        })

        if not self.llm_service:
            # Fallback to basic error handling
            return self._basic_error_analysis(error, context)

        try:
            system_prompt = """You are an expert at analyzing errors in scientific data conversion workflows.

Your job is to:
1. Analyze the error in context
2. Explain what went wrong in simple terms
3. Determine if it's recoverable
4. Suggest specific, actionable recovery steps
5. Assess severity

**Severity Levels:**
- **critical**: System cannot continue, data may be corrupted
- **high**: Conversion cannot proceed without user action
- **medium**: Issue exists but workarounds available
- **low**: Minor issue, system can handle automatically

**Recovery Action Types:**
- **user_action**: User needs to do something (provide info, fix file, etc.)
- **system_retry**: System can retry automatically
- **manual_fix**: Requires manual intervention
- **skip**: Can skip this step
- **abort**: Must stop and restart

Be helpful, specific, and actionable."""

            # Build error context
            recent_logs = [log.message for log in state.logs[-10:]]
            error_context = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "operation": context.get("operation", "unknown"),
                "file_path": context.get("file_path"),
                "format": context.get("format"),
                "status": state.status.value,
                "recent_activity": recent_logs[-5:],
            }

            user_prompt = f"""An error occurred during NWB data conversion. Analyze it and provide guidance.

**Error Details:**
```
Type: {error_context['error_type']}
Message: {error_context['error_message']}
```

**Operation Context:**
- What was happening: {error_context['operation']}
- File: {error_context.get('file_path', 'unknown')}
- Format: {error_context.get('format', 'unknown')}
- Current status: {error_context['status']}

**Recent Activity:**
{chr(10).join(f"- {log}" for log in error_context['recent_activity'])}

**Previous Errors (if any):**
{self._get_error_patterns()}

Analyze this error and provide:
1. User-friendly explanation (non-technical)
2. What likely caused it
3. Specific recovery actions
4. Severity assessment
5. Whether it's recoverable

Be specific and actionable."""

            output_schema = {
                "type": "object",
                "properties": {
                    "user_message": {
                        "type": "string",
                        "description": "Clear, user-friendly explanation of what went wrong"
                    },
                    "likely_cause": {
                        "type": "string",
                        "description": "What probably caused this error"
                    },
                    "recovery_actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "description": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": ["user_action", "system_retry", "manual_fix", "skip", "abort"]
                                }
                            }
                        },
                        "description": "Ordered list of recovery actions to try"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Error severity level"
                    },
                    "is_recoverable": {
                        "type": "boolean",
                        "description": "Whether this error can be recovered from"
                    },
                    "technical_details": {
                        "type": "string",
                        "description": "Technical details for debugging (optional)"
                    }
                },
                "required": ["user_message", "likely_cause", "recovery_actions", "severity", "is_recoverable"]
            }

            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                f"Intelligent error analysis complete: {response.get('severity')} severity, recoverable={response.get('is_recoverable')}",
                {
                    "error_type": type(error).__name__,
                    "recovery_actions_count": len(response.get("recovery_actions", [])),
                }
            )

            return response

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"LLM error analysis failed, using fallback: {e}",
            )
            return self._basic_error_analysis(error, context)

    def _basic_error_analysis(
        self,
        error: Exception,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fallback error analysis without LLM."""
        error_type = type(error).__name__
        error_msg = str(error)

        # Basic severity assessment
        if "FileNotFound" in error_type or "Permission" in error_type:
            severity = "high"
        elif "Validation" in error_type:
            severity = "medium"
        else:
            severity = "medium"

        return {
            "user_message": f"An error occurred: {error_msg}",
            "likely_cause": f"{error_type} during {context.get('operation', 'conversion')}",
            "recovery_actions": [
                {
                    "action": "Check the error details and try again",
                    "description": "Review the error message and attempt the operation again",
                    "type": "user_action"
                }
            ],
            "severity": severity,
            "is_recoverable": True,
            "technical_details": f"{error_type}: {error_msg}",
        }

    def _get_error_patterns(self) -> str:
        """Analyze recent error history for patterns."""
        if not self.error_history:
            return "No previous errors"

        # Get last 5 errors
        recent = self.error_history[-5:]

        # Count error types
        error_types = {}
        for err in recent:
            err_type = err["error_type"]
            error_types[err_type] = error_types.get(err_type, 0) + 1

        summary = f"Recent errors: {len(recent)} total\n"
        for err_type, count in error_types.items():
            summary += f"- {err_type}: {count} occurrences\n"

        return summary

    async def suggest_proactive_fix(
        self,
        state: GlobalState,
    ) -> Optional[Dict[str, Any]]:
        """
        Proactively suggest fixes based on error patterns.

        If we see the same error multiple times, suggest a proactive fix.

        Args:
            state: Global conversion state

        Returns:
            Suggestion dict or None if no patterns detected
        """
        if len(self.error_history) < 3:
            return None

        # Check for repeated errors
        recent_errors = self.error_history[-5:]
        error_types = [e["error_type"] for e in recent_errors]

        # If same error appears 3+ times, suggest proactive fix
        for err_type in set(error_types):
            if error_types.count(err_type) >= 3:
                state.add_log(
                    LogLevel.WARNING,
                    f"Detected repeated error pattern: {err_type}",
                    {"occurrences": error_types.count(err_type)}
                )

                return {
                    "pattern_detected": err_type,
                    "occurrences": error_types.count(err_type),
                    "suggestion": "This error has occurred multiple times. Consider checking the input file format or configuration.",
                }

        return None
