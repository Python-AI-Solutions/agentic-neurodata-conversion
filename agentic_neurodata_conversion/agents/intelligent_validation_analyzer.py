"""Intelligent Validation Result Analyzer.

Deep analysis of NWB validation results to understand relationships between issues,
identify root causes, and provide actionable insights beyond simple issue listing.

Features:
- Cross-issue relationship detection (one issue causing multiple symptoms)
- Root cause analysis using LLM reasoning
- Impact assessment (which issues are most critical to fix first)
- Pattern recognition across validation sessions
- Smart grouping of related issues
"""

import json
import logging
from typing import Any

from agentic_neurodata_conversion.models import GlobalState, LogLevel, ValidationResult
from agentic_neurodata_conversion.services import LLMService

logger = logging.getLogger(__name__)


class IntelligentValidationAnalyzer:
    """Analyzes validation results with deep reasoning to uncover insights.

    Goes beyond simple issue listing to provide:
    - Root cause identification
    - Issue dependency mapping
    - Fix priority ordering
    - Impact prediction
    """

    def __init__(self, llm_service: LLMService | None = None):
        """Initialize the validation analyzer.

        Args:
            llm_service: Optional LLM service for intelligent analysis
        """
        self.llm_service = llm_service

    async def analyze_validation_results(
        self,
        validation_result: ValidationResult,
        file_context: dict[str, Any],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Deep analysis of validation results.

        Args:
            validation_result: Validation results from NWB Inspector
            file_context: Context about the NWB file
            state: Global state

        Returns:
            Comprehensive analysis with:
            - root_causes: Identified root causes
            - issue_groups: Related issues grouped together
            - fix_order: Recommended fix order
            - impact_analysis: Impact of each issue
            - quick_wins: Easy fixes that improve quality significantly
        """
        try:
            if not self.llm_service:
                return self._basic_analysis(validation_result, state)

            # Step 1: Group related issues
            issue_groups = await self._group_related_issues(validation_result.issues, state)

            # Step 2: Identify root causes
            root_causes = await self._identify_root_causes(validation_result.issues, issue_groups, file_context, state)

            # Step 3: Determine fix order
            fix_order = await self._determine_fix_order(root_causes, issue_groups, state)

            # Step 4: Assess impact
            impact_analysis = await self._assess_issue_impact(validation_result.issues, root_causes, state)

            # Step 5: Identify quick wins
            quick_wins = self._identify_quick_wins(validation_result.issues, impact_analysis)

            analysis_result = {
                "root_causes": root_causes,
                "issue_groups": issue_groups,
                "fix_order": fix_order,
                "impact_analysis": impact_analysis,
                "quick_wins": quick_wins,
                "analysis_summary": self._generate_summary(root_causes, quick_wins, len(validation_result.issues)),
            }

            state.add_log(
                LogLevel.INFO,
                "Intelligent validation analysis completed",
                {
                    "root_causes_found": len(root_causes),
                    "issue_groups": len(issue_groups),
                    "quick_wins": len(quick_wins),
                },
            )

            return analysis_result

        except Exception as e:
            logger.exception(f"Validation analysis failed: {e}")
            state.add_log(LogLevel.WARNING, f"Validation analysis failed: {e}")
            return self._basic_analysis(validation_result, state)

    def _basic_analysis(
        self,
        validation_result: ValidationResult,
        state: GlobalState,
    ) -> dict[str, Any]:
        """Basic analysis when LLM is not available.

        Uses heuristics and pattern matching.
        """
        # Simple grouping by severity
        issue_groups: dict[str, list[Any]] = {}
        for issue in validation_result.issues:
            severity = issue.severity.value if hasattr(issue, "severity") else "unknown"
            if severity not in issue_groups:
                issue_groups[severity] = []
            issue_groups[severity].append(issue.model_dump() if hasattr(issue, "model_dump") else issue)

        return {
            "root_causes": [],
            "issue_groups": [
                {"name": severity, "issues": issues, "count": len(issues)} for severity, issues in issue_groups.items()
            ],
            "fix_order": ["Fix critical issues first", "Then address errors", "Finally warnings"],
            "impact_analysis": {},
            "quick_wins": [],
            "analysis_summary": f"Found {len(validation_result.issues)} validation issues. No detailed analysis available (LLM required).",
        }

    async def _group_related_issues(
        self,
        issues: list[Any],
        state: GlobalState,
    ) -> list[dict[str, Any]]:
        """Group related issues together using LLM understanding.

        For example:
        - All issues related to missing subject metadata
        - All issues related to timestamp problems
        - All issues related to data type mismatches
        """
        system_prompt = """You are an expert NWB validation analyst.

Your task is to analyze validation issues and group related ones together.

**Grouping Principles**:
1. **Common Root Cause**: Issues that stem from the same underlying problem
2. **Same Location**: Issues affecting the same NWB object or field
3. **Dependency Chain**: Issues where one causes others
4. **Related Metadata**: Issues about related metadata fields

**Example Groups**:
- "Subject Metadata Issues" - subject_id missing, species missing, age missing
- "Timestamp Problems" - session_start_time invalid, timestamps_reference_time missing
- "Device Configuration" - device name missing, device description invalid

For each group, provide:
- Clear group name
- Why these issues are related
- How fixing one might help others"""

        # Format issues for analysis
        issues_text = []
        for idx, issue in enumerate(issues[:30], 1):  # Limit to 30 for efficiency
            issue_dict = issue.model_dump() if hasattr(issue, "model_dump") else issue
            issues_text.append(
                f"{idx}. [{issue_dict.get('severity', 'UNKNOWN')}] "
                f"{issue_dict.get('message', 'No message')}\n"
                f"   Location: {issue_dict.get('location', 'Unknown')}\n"
                f"   Check: {issue_dict.get('check_function_name', 'Unknown')}"
            )

        user_prompt = f"""Analyze these {len(issues)} validation issues and group related ones:

{chr(10).join(issues_text)}

Group these issues by:
1. Common root causes
2. Related metadata or data
3. Same location in NWB file
4. Dependency relationships

Provide clear group names and explanations."""

        output_schema = {
            "type": "object",
            "properties": {
                "groups": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "group_name": {"type": "string"},
                            "issue_indices": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "1-based indices of issues in this group",
                            },
                            "relationship": {"type": "string", "description": "How these issues are related"},
                            "common_root_cause": {
                                "type": "string",
                                "description": "The underlying cause linking these issues",
                            },
                        },
                        "required": ["group_name", "issue_indices", "relationship"],
                    },
                },
            },
            "required": ["groups"],
        }

        try:
            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            # Build groups with actual issue data
            groups = []
            for group in response.get("groups", []):
                group_issues = []
                for idx in group.get("issue_indices", []):
                    # Convert 1-based to 0-based index
                    actual_idx = idx - 1
                    if 0 <= actual_idx < len(issues):
                        issue = issues[actual_idx]
                        group_issues.append(issue.model_dump() if hasattr(issue, "model_dump") else issue)

                if group_issues:  # Only include groups with valid issues
                    groups.append(
                        {
                            "group_name": group.get("group_name"),
                            "relationship": group.get("relationship"),
                            "common_root_cause": group.get("common_root_cause", ""),
                            "issues": group_issues,
                            "count": len(group_issues),
                        }
                    )

            return groups

        except Exception as e:
            logger.exception(f"Issue grouping failed: {e}")
            state.add_log(LogLevel.WARNING, f"Issue grouping failed: {e}")
            return []

    async def _identify_root_causes(
        self,
        issues: list[Any],
        issue_groups: list[dict[str, Any]],
        file_context: dict[str, Any],
        state: GlobalState,
    ) -> list[dict[str, Any]]:
        """Identify root causes that explain multiple validation issues.

        Uses LLM reasoning to detect patterns like:
        - "Missing metadata template during conversion"
        - "Incorrect timestamp format in source data"
        - "Incomplete subject information in input"
        """
        system_prompt = """You are an expert NWB data diagnostician.

Analyze validation issues to identify **root causes** - the underlying problems that explain multiple symptoms.

**Root Cause Examples**:

**Symptom**: subject_id missing, species missing, age missing
**Root Cause**: "Subject metadata was not provided during conversion"

**Symptom**: Multiple "timestamps out of order" errors across different data streams
**Root Cause**: "Source data has inconsistent timestamp references"

**Symptom**: Device name invalid, electrode metadata incomplete
**Root Cause**: "Recording device configuration was not properly mapped"

For each root cause:
- Identify the fundamental problem
- List which issues it explains
- Estimate how many issues would be fixed by addressing this root cause
- Provide specific remediation steps"""

        # Prepare context
        issues_summary = []
        for idx, issue in enumerate(issues[:20], 1):
            issue_dict = issue.model_dump() if hasattr(issue, "model_dump") else issue
            issues_summary.append(f"{idx}. [{issue_dict.get('severity')}] {issue_dict.get('message')}")

        groups_summary = []
        for group in issue_groups[:10]:
            groups_summary.append(
                f"- {group['group_name']}: {group['count']} issues ({group.get('relationship', 'Related')})"
            )

        user_prompt = f"""Identify root causes for these validation issues:

**Issues** ({len(issues)} total):
{chr(10).join(issues_summary)}

**Issue Groups**:
{chr(10).join(groups_summary) if groups_summary else "No groups identified"}

**File Context**:
{json.dumps(file_context, indent=2, default=str)[:500]}

Identify 3-5 root causes that explain most issues. Focus on actionable, fixable problems."""

        output_schema = {
            "type": "object",
            "properties": {
                "root_causes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "cause": {"type": "string", "description": "Clear description of root cause"},
                            "explained_issues": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Which issue types this explains",
                            },
                            "impact_score": {
                                "type": "number",
                                "description": "How many issues would be fixed (0-100)",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "remediation": {"type": "string", "description": "How to fix this root cause"},
                            "difficulty": {
                                "type": "string",
                                "enum": ["easy", "medium", "hard"],
                                "description": "Difficulty to fix",
                            },
                        },
                        "required": ["cause", "explained_issues", "impact_score", "remediation", "difficulty"],
                    },
                },
            },
            "required": ["root_causes"],
        }

        try:
            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            root_causes = response.get("root_causes", [])

            # Sort by impact score (highest first)
            root_causes.sort(key=lambda x: x.get("impact_score", 0), reverse=True)

            return list(root_causes)  # Cast Any to list

        except Exception as e:
            logger.exception(f"Root cause identification failed: {e}")
            state.add_log(LogLevel.WARNING, f"Root cause identification failed: {e}")
            return []

    async def _determine_fix_order(
        self,
        root_causes: list[dict[str, Any]],
        issue_groups: list[dict[str, Any]],
        state: GlobalState,
    ) -> list[dict[str, Any]]:
        """Determine optimal order to fix issues for maximum impact.

        Considers:
        - Dependencies (fix A before B)
        - Impact (fixes that resolve many issues)
        - Difficulty (easy wins first when impact is similar)
        """
        system_prompt = """You are an expert at prioritizing technical debt and issue resolution.

Given root causes and issue groups, create an optimal fix order that:
1. Maximizes early impact (fixes that resolve many issues)
2. Respects dependencies (fix foundational issues first)
3. Balances difficulty (prefer easier fixes when impact is similar)
4. Groups related work together

**Example Fix Order**:
1. "Add missing subject metadata" - Easy, fixes 5 issues, no dependencies
2. "Fix timestamp reference format" - Medium, fixes 8 issues, must be done before data validation
3. "Complete device configuration" - Hard, fixes 3 issues, depends on #1 and #2

Provide a clear, actionable sequence."""

        user_prompt = f"""Create optimal fix order for these root causes:

**Root Causes**:
{json.dumps(root_causes, indent=2, default=str)}

**Issue Groups**:
{json.dumps([{k: v for k, v in g.items() if k != "issues"} for g in issue_groups], indent=2, default=str)}

Provide step-by-step fix order with rationale."""

        output_schema = {
            "type": "object",
            "properties": {
                "fix_steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_number": {"type": "number"},
                            "action": {"type": "string"},
                            "rationale": {"type": "string"},
                            "expected_impact": {"type": "string"},
                            "estimated_effort": {
                                "type": "string",
                                "enum": ["5 min", "15 min", "30 min", "1 hour", "2+ hours"],
                            },
                            "dependencies": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "Step numbers that must be completed first",
                            },
                        },
                        "required": ["step_number", "action", "rationale", "expected_impact", "estimated_effort"],
                    },
                },
            },
            "required": ["fix_steps"],
        }

        try:
            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            return list(response.get("fix_steps", []))  # Cast Any to list

        except Exception as e:
            logger.exception(f"Fix order determination failed: {e}")
            state.add_log(LogLevel.WARNING, f"Fix order determination failed: {e}")
            return []

    async def _assess_issue_impact(
        self,
        issues: list[Any],
        root_causes: list[dict[str, Any]],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Assess the impact of each issue.

        - DANDI submission readiness
        - Data usability
        - Scientific validity
        - Community standards compliance.
        """
        # Count issues by type
        dandi_blocking = 0
        usability_impact = 0
        best_practices = 0

        for issue in issues:
            issue_dict = issue.model_dump() if hasattr(issue, "model_dump") else issue
            severity = issue_dict.get("severity", "").lower()
            message = issue_dict.get("message", "").lower()

            # Heuristics for DANDI blocking
            if any(keyword in message for keyword in ["required", "missing", "subject_id", "session_description"]):
                dandi_blocking += 1
            elif severity in ["critical", "error"]:
                usability_impact += 1
            else:
                best_practices += 1

        total = len(issues)

        return {
            "total_issues": total,
            "dandi_blocking": dandi_blocking,
            "dandi_blocking_percent": round((dandi_blocking / max(total, 1)) * 100, 1),
            "usability_impact": usability_impact,
            "best_practices": best_practices,
            "critical_path": root_causes[0] if root_causes else None,
            "readiness_score": max(0, 100 - (dandi_blocking * 20) - (usability_impact * 5)),
        }

    def _identify_quick_wins(
        self,
        issues: list[Any],
        impact_analysis: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Identify "quick win" issues - easy to fix with significant impact.

        These are prioritized for user action.
        """
        quick_wins = []

        for issue in issues[:10]:  # First 10 issues
            issue_dict = issue.model_dump() if hasattr(issue, "model_dump") else issue
            message = issue_dict.get("message", "").lower()

            # Heuristics for quick wins
            is_quick_win = False
            win_type = ""

            if "missing" in message and any(field in message for field in ["experimenter", "institution", "lab"]):
                is_quick_win = True
                win_type = "Add simple metadata field"
            elif "keywords" in message:
                is_quick_win = True
                win_type = "Add keywords for discoverability"
            elif "description" in message and "missing" not in message:
                is_quick_win = True
                win_type = "Improve existing description"

            if is_quick_win:
                quick_wins.append(
                    {
                        "issue": issue_dict.get("message"),
                        "type": win_type,
                        "estimated_time": "< 5 minutes",
                        "impact": "Improves metadata completeness",
                    }
                )

        return quick_wins

    def _generate_summary(
        self,
        root_causes: list[dict[str, Any]],
        quick_wins: list[dict[str, Any]],
        total_issues: int,
    ) -> str:
        """Generate human-readable analysis summary."""
        summary_parts = [
            f"Found {total_issues} validation issues.",
        ]

        if root_causes:
            summary_parts.append(
                f"Identified {len(root_causes)} root causes. "
                f"Top cause: '{root_causes[0].get('cause', 'Unknown')}' "
                f"(fixes ~{root_causes[0].get('impact_score', 0)}% of issues)."
            )

        if quick_wins:
            summary_parts.append(f"Found {len(quick_wins)} quick wins that can be fixed in < 5 minutes each.")

        return " ".join(summary_parts)
