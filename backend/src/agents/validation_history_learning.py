"""Validation History Learning System.

Learns from past validation sessions to:
- Recognize recurring issues
- Suggest preventive measures
- Detect patterns across conversions
- Provide proactive recommendations
- Build knowledge base of common problems

Features:
- Pattern detection across validation sessions
- Issue recurrence tracking
- Success factor analysis
- Preventive recommendations
- Knowledge base accumulation
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from models import GlobalState, LogLevel, ValidationResult
from services import LLMService

logger = logging.getLogger(__name__)


class ValidationHistoryLearner:
    """Learns from validation history to provide intelligent insights and predictions.

    Tracks:
    - Common validation issues across files
    - Successful resolution patterns
    - Format-specific problems
    - User-specific patterns
    """

    def __init__(self, llm_service: LLMService | None = None, history_path: str | None = None):
        """Initialize the history learner.

        Args:
            llm_service: Optional LLM service for intelligent analysis
            history_path: Path to store validation history
        """
        self.llm_service = llm_service
        self.history_path = Path(history_path) if history_path else Path("outputs/validation_history")
        self.history_path.mkdir(parents=True, exist_ok=True)

    async def record_validation_session(
        self,
        validation_result: ValidationResult,
        file_context: dict[str, Any],
        resolution_actions: list[dict[str, Any]] | None,
        state: GlobalState,
    ) -> None:
        """Record a validation session for learning.

        Args:
            validation_result: Validation results
            file_context: Context about the file validated
            resolution_actions: Actions taken to resolve issues (if any)
            state: Global state
        """
        try:
            session_record = {
                "timestamp": datetime.now().isoformat(),
                "file_info": {
                    "format": file_context.get("format", "unknown"),
                    "size_mb": file_context.get("file_size_mb", 0),
                    "nwb_version": file_context.get("nwb_version", "unknown"),
                },
                "validation": {
                    "is_valid": validation_result.is_valid,
                    "total_issues": len(validation_result.issues),
                    "summary": validation_result.summary,
                },
                "issues": [
                    {
                        "severity": issue.severity.value if hasattr(issue, "severity") else "unknown",
                        "message": issue.message if hasattr(issue, "message") else str(issue),
                        "check_function": issue.check_function_name if hasattr(issue, "check_function_name") else None,
                    }
                    for issue in validation_result.issues[:50]  # Store first 50
                ],
                "resolution_actions": resolution_actions or [],
            }

            # Save to history
            session_file = self.history_path / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(session_file, "w") as f:
                json.dump(session_record, f, indent=2)

            state.add_log(LogLevel.DEBUG, "Recorded validation session to history", {"session_file": str(session_file)})

        except Exception as e:
            logger.warning(f"Failed to record validation session: {e}")

    async def analyze_patterns(
        self,
        state: GlobalState,
    ) -> dict[str, Any]:
        """Analyze patterns across all validation history.

        Returns:
            Analysis with:
            - common_issues: Most frequently occurring issues
            - format_specific_issues: Issues by file format
            - success_patterns: What correlates with successful validation
            - preventive_recommendations: Proactive suggestions
        """
        try:
            # Load all session records
            sessions = self._load_history()

            if len(sessions) < 2:
                return {
                    "common_issues": [],
                    "format_specific_issues": {},
                    "success_patterns": [],
                    "preventive_recommendations": [],
                    "note": "Insufficient history data (need at least 2 sessions)",
                }

            # Analyze patterns
            common_issues = self._identify_common_issues(sessions)
            format_issues = self._analyze_format_specific_issues(sessions)
            success_patterns = self._analyze_success_patterns(sessions)

            # Use LLM for intelligent insights if available
            if self.llm_service:
                insights = await self._llm_pattern_analysis(common_issues, format_issues, success_patterns, state)
            else:
                insights = {"preventive_recommendations": self._basic_recommendations(common_issues)}

            return {
                "common_issues": common_issues,
                "format_specific_issues": format_issues,
                "success_patterns": success_patterns,
                "preventive_recommendations": insights.get("preventive_recommendations", []),
                "total_sessions": len(sessions),
                "analysis_date": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.exception(f"Pattern analysis failed: {e}")
            state.add_log(LogLevel.WARNING, f"Pattern analysis failed: {e}")
            return {
                "common_issues": [],
                "format_specific_issues": {},
                "success_patterns": [],
                "preventive_recommendations": [],
                "error": str(e),
            }

    def _load_history(self) -> list[dict[str, Any]]:
        """Load all validation history records."""
        sessions = []

        for session_file in sorted(self.history_path.glob("session_*.json")):
            try:
                with open(session_file) as f:
                    session = json.load(f)
                    sessions.append(session)
            except Exception as e:
                logger.warning(f"Failed to load session file {session_file}: {e}")

        return sessions

    def _identify_common_issues(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify most common validation issues across sessions."""
        issue_counts: defaultdict[str, int] = defaultdict(int)
        issue_severities: defaultdict[str, list[str]] = defaultdict(list)

        for session in sessions:
            for issue in session.get("issues", []):
                # Normalize message to detect similar issues
                normalized_msg = self._normalize_issue_message(issue.get("message", ""))
                issue_counts[normalized_msg] += 1
                issue_severities[normalized_msg].append(issue.get("severity", "unknown"))

        # Sort by frequency
        common_issues = []
        for message, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            common_issues.append(
                {
                    "issue_pattern": message,
                    "occurrence_count": count,
                    "percentage": round((count / len(sessions)) * 100, 1),
                    "typical_severity": max(set(issue_severities[message]), key=issue_severities[message].count),
                }
            )

        return common_issues

    def _normalize_issue_message(self, message: str) -> str:
        """Normalize issue message to detect similar issues.

        Examples:
        - "Missing field 'experimenter'" → "Missing field"
        - "Invalid timestamp '2024-01-01'" → "Invalid timestamp"
        """
        import re

        # Remove specific values in quotes
        normalized = re.sub(r"'[^']*'", "'...'", message)

        # Remove file paths
        normalized = re.sub(r"/[^\s]+", "/...", normalized)

        # Remove numbers
        normalized = re.sub(r"\d+", "N", normalized)

        return normalized

    def _analyze_format_specific_issues(self, sessions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Analyze issues specific to each file format."""
        format_issues: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))

        for session in sessions:
            file_format = session.get("file_info", {}).get("format", "unknown")

            for issue in session.get("issues", []):
                normalized_msg = self._normalize_issue_message(issue.get("message", ""))
                format_issues[file_format][normalized_msg] += 1

        # Convert to list format
        result = {}
        for fmt, issues in format_issues.items():
            result[fmt] = [
                {
                    "issue_pattern": msg,
                    "count": count,
                }
                for msg, count in sorted(issues.items(), key=lambda x: x[1], reverse=True)[:5]
            ]

        return result

    def _analyze_success_patterns(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify patterns that correlate with successful validation."""
        patterns = []

        # Pattern 1: File size correlation
        valid_sizes = [
            s.get("file_info", {}).get("size_mb", 0) for s in sessions if s.get("validation", {}).get("is_valid", False)
        ]

        if valid_sizes:
            avg_valid_size = sum(valid_sizes) / len(valid_sizes)
            patterns.append(
                {
                    "pattern": "File size",
                    "observation": f"Successfully validated files average {avg_valid_size:.1f} MB",
                    "sample_size": len(valid_sizes),
                }
            )

        # Pattern 2: Format success rates
        format_success: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "valid": 0})
        for session in sessions:
            fmt = session.get("file_info", {}).get("format", "unknown")
            format_success[fmt]["total"] += 1
            if session.get("validation", {}).get("is_valid", False):
                format_success[fmt]["valid"] += 1

        for fmt, stats in format_success.items():
            if stats["total"] >= 2:  # At least 2 samples
                success_rate = (stats["valid"] / stats["total"]) * 100
                patterns.append(
                    {
                        "pattern": f"Format: {fmt}",
                        "observation": f"{success_rate:.0f}% success rate ({stats['valid']}/{stats['total']})",
                        "sample_size": stats["total"],
                    }
                )

        return patterns

    def _basic_recommendations(self, common_issues: list[dict[str, Any]]) -> list[str]:
        """Generate basic preventive recommendations."""
        recommendations = []

        for issue in common_issues[:3]:  # Top 3 issues
            if "missing" in issue["issue_pattern"].lower():
                recommendations.append(
                    f"Always verify {issue['issue_pattern'].lower()} before conversion "
                    f"(occurs in {issue['percentage']}% of conversions)"
                )
            elif "invalid" in issue["issue_pattern"].lower():
                recommendations.append(
                    f"Validate {issue['issue_pattern'].lower()} format before conversion "
                    f"(common issue: {issue['percentage']}% occurrence)"
                )

        return recommendations

    async def _llm_pattern_analysis(
        self,
        common_issues: list[dict[str, Any]],
        format_issues: dict[str, list[dict[str, Any]]],
        success_patterns: list[dict[str, Any]],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to generate intelligent insights from patterns."""
        system_prompt = """You are an expert data scientist analyzing NWB validation patterns.

Your job is to analyze validation history and provide **actionable preventive recommendations**.

Focus on:
1. **Root Causes**: What underlying factors lead to validation issues?
2. **Prevention**: How can users avoid these issues proactively?
3. **Best Practices**: What correlates with successful validation?
4. **Format-Specific Guidance**: What should users know about specific formats?

Provide specific, actionable recommendations that help users succeed on first try."""

        user_prompt = f"""Analyze these validation patterns and provide preventive recommendations:

**Most Common Issues** (across all validations):
{json.dumps(common_issues, indent=2)}

**Format-Specific Issues**:
{json.dumps(format_issues, indent=2)}

**Success Patterns**:
{json.dumps(success_patterns, indent=2)}

Generate 5-7 specific preventive recommendations to help users avoid common issues."""

        output_schema = {
            "type": "object",
            "properties": {
                "preventive_recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "recommendation": {"type": "string"},
                            "rationale": {"type": "string"},
                            "applies_to": {
                                "type": "string",
                                "description": "When this applies (e.g., 'All formats', 'SpikeGLX only')",
                            },
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                        },
                        "required": ["recommendation", "rationale", "applies_to", "priority"],
                    },
                },
                "key_insights": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key insights from the analysis",
                },
            },
            "required": ["preventive_recommendations", "key_insights"],
        }

        try:
            analysis = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            return dict(analysis)  # Cast Any to dict

        except Exception as e:
            logger.exception(f"LLM pattern analysis failed: {e}")
            state.add_log(LogLevel.WARNING, f"LLM pattern analysis failed: {e}")
            return {
                "preventive_recommendations": self._basic_recommendations(common_issues),
                "key_insights": [],
            }

    async def predict_issues(
        self,
        file_context: dict[str, Any],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Predict likely validation issues based on file characteristics and history.

        Args:
            file_context: Context about the file to be validated
            state: Global state

        Returns:
            Predictions with:
            - likely_issues: Issues that are likely to occur
            - confidence: Confidence scores
            - preventive_actions: What to do proactively
        """
        try:
            sessions = self._load_history()

            if len(sessions) < 3:
                return {"likely_issues": [], "preventive_actions": [], "note": "Insufficient history for predictions"}

            # Find similar files in history
            similar_sessions = self._find_similar_sessions(file_context, sessions)

            if not similar_sessions:
                return {
                    "likely_issues": [],
                    "preventive_actions": ["No similar files in validation history"],
                }

            # Extract common issues from similar files
            likely_issues = self._extract_common_issues_from_similar(similar_sessions)

            # Use LLM for intelligent predictions if available
            if self.llm_service:
                predictions = await self._llm_issue_prediction(file_context, similar_sessions, likely_issues, state)
            else:
                predictions = {
                    "likely_issues": likely_issues,
                    "preventive_actions": [f"Check for: {issue['pattern']}" for issue in likely_issues[:3]],
                }

            return predictions

        except Exception as e:
            logger.exception(f"Issue prediction failed: {e}")
            return {
                "likely_issues": [],
                "preventive_actions": [],
                "error": str(e),
            }

    def _find_similar_sessions(
        self, file_context: dict[str, Any], sessions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Find validation sessions for similar files."""
        target_format = file_context.get("format", "").lower()
        target_size = file_context.get("file_size_mb", 0)

        similar = []

        for session in sessions:
            session_format = session.get("file_info", {}).get("format", "").lower()
            session_size = session.get("file_info", {}).get("size_mb", 0)

            # Match by format
            if target_format and target_format in session_format:
                similar.append(session)
            # Or by similar size (within 50%)
            elif target_size > 0 and session_size > 0:
                size_ratio = session_size / target_size
                if 0.5 <= size_ratio <= 2.0:
                    similar.append(session)

        return similar

    def _extract_common_issues_from_similar(self, similar_sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract common issues from similar validation sessions."""
        issue_counts: defaultdict[str, int] = defaultdict(int)

        for session in similar_sessions:
            seen_in_session = set()
            for issue in session.get("issues", []):
                normalized = self._normalize_issue_message(issue.get("message", ""))
                if normalized not in seen_in_session:  # Count once per session
                    issue_counts[normalized] += 1
                    seen_in_session.add(normalized)

        # Calculate likelihood
        total_sessions = len(similar_sessions)
        likely_issues = []

        for issue_pattern, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            likelihood = (count / total_sessions) * 100
            likely_issues.append(
                {
                    "pattern": issue_pattern,
                    "likelihood_percent": round(likelihood, 1),
                    "occurred_in": f"{count}/{total_sessions} similar files",
                }
            )

        return likely_issues

    async def _llm_issue_prediction(
        self,
        file_context: dict[str, Any],
        similar_sessions: list[dict[str, Any]],
        likely_issues: list[dict[str, Any]],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to generate intelligent issue predictions."""
        system_prompt = """You are an expert at predicting NWB validation issues.

Based on file characteristics and validation history of similar files,
predict likely issues and provide proactive recommendations.

Be specific and actionable."""

        user_prompt = f"""Predict validation issues for this file:

**File Context**:
{json.dumps(file_context, indent=2, default=str)}

**Similar Files Validated**:
{len(similar_sessions)} similar files in history

**Common Issues in Similar Files**:
{json.dumps(likely_issues, indent=2)}

Provide:
1. Top 3-5 likely validation issues
2. Confidence for each prediction
3. Specific preventive actions to avoid these issues"""

        output_schema = {
            "type": "object",
            "properties": {
                "predictions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "predicted_issue": {"type": "string"},
                            "confidence_percent": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "reasoning": {"type": "string"},
                            "preventive_action": {"type": "string"},
                        },
                        "required": ["predicted_issue", "confidence_percent", "reasoning", "preventive_action"],
                    },
                },
            },
            "required": ["predictions"],
        }

        try:
            result = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            return {
                "likely_issues": result.get("predictions", []),
                "preventive_actions": [p.get("preventive_action") for p in result.get("predictions", [])],
            }

        except Exception as e:
            logger.exception(f"LLM issue prediction failed: {e}")
            return {
                "likely_issues": likely_issues,
                "preventive_actions": [],
            }
