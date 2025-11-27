"""Issue analysis module for evaluation agent.

Handles:
- LLM-powered validation issue prioritization
- DANDI archive requirement analysis
- Quality scoring and grading (0-100 scale)
- Best practices assessment
"""

import logging
from typing import TYPE_CHECKING, Any

from agentic_neurodata_conversion.models import GlobalState, LogLevel, ValidationResult

if TYPE_CHECKING:
    from agentic_neurodata_conversion.services import LLMService

logger = logging.getLogger(__name__)


class IssueAnalyzer:
    """Handles intelligent validation issue analysis using LLM.

    Features:
    - Prioritizes issues by DANDI blocking status
    - Assesses overall NWB file quality (0-100 score)
    - Provides user-friendly explanations
    - Suggests specific fix actions
    """

    def __init__(self, llm_service: "LLMService | None" = None):
        """Initialize issue analyzer.

        Args:
            llm_service: Optional LLM service for intelligent analysis
        """
        self._llm_service = llm_service

    async def prioritize_and_explain_issues(
        self,
        issues: list[Any],
        state: GlobalState,
    ) -> list[dict[str, Any]]:
        """Use LLM to prioritize validation issues and explain their importance.

        Categorizes issues into:
        - DANDI-blocking: Critical for DANDI archive submission
        - Best practices: Important but not blocking
        - Nice-to-have: Optional improvements

        Args:
            issues: List of validation issues from NWB Inspector
            state: Global state

        Returns:
            List of prioritized issues with explanations and action items
        """
        if not self._llm_service:
            logger.warning("LLM service not available, returning unprioritized issues")
            return [issue.model_dump() if hasattr(issue, "model_dump") else issue for issue in issues]

        # Format issues for LLM
        issues_text = []
        for idx, issue in enumerate(issues[:20], 1):  # Limit to first 20 for token efficiency
            issue_dict = issue.model_dump() if hasattr(issue, "model_dump") else issue
            issues_text.append(
                f"{idx}. [{issue_dict.get('severity', 'UNKNOWN')}] "
                f"{issue_dict.get('message', 'No message')}\n"
                f"   Check: {issue_dict.get('check_function_name', 'Unknown')}"
            )

        system_prompt = """You are an expert NWB data curator with deep knowledge of DANDI archive requirements.

Your job is to analyze NWB Inspector validation issues and categorize them by priority:

1. **dandi_blocking**: Issues that WILL prevent submission to DANDI archive
   - Missing required metadata (subject_id, session_description, etc.)
   - File format violations
   - Data integrity problems

2. **best_practices**: Important issues that should be fixed but won't block DANDI
   - Missing optional but recommended metadata (experimenter, institution)
   - Inconsistent naming conventions
   - Suboptimal data organization

3. **nice_to_have**: Optional improvements that enhance data quality
   - Additional keywords
   - Extended descriptions
   - Extra documentation

For each issue, provide:
- Priority category
- Plain English explanation of what's wrong
- Why it matters
- Specific action to fix it
- Whether it's fixable by user"""

        user_prompt = f"""Analyze these NWB validation issues and prioritize them:

{chr(10).join(issues_text)}

For each issue, determine:
1. Priority: dandi_blocking, best_practices, or nice_to_have
2. User-friendly explanation
3. Why this matters for data sharing
4. Specific fix action
5. Whether user can fix it

Focus on DANDI archive requirements."""

        output_schema = {
            "type": "object",
            "properties": {
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "original_message": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["dandi_blocking", "best_practices", "nice_to_have"],
                            },
                            "explanation": {"type": "string"},
                            "why_it_matters": {"type": "string"},
                            "fix_action": {"type": "string"},
                            "user_fixable": {"type": "boolean"},
                            "dandi_requirement": {"type": "boolean"},
                        },
                        "required": ["original_message", "priority", "explanation", "fix_action", "user_fixable"],
                    },
                },
            },
            "required": ["issues"],
        }

        try:
            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            prioritized = response.get("issues", [])

            # Merge with original issue data
            result = []
            for idx, prioritized_issue in enumerate(prioritized):
                if idx < len(issues):
                    original = issues[idx].model_dump() if hasattr(issues[idx], "model_dump") else issues[idx]
                    result.append(
                        {
                            **original,  # Keep all original fields
                            "priority": prioritized_issue.get("priority"),
                            "explanation": prioritized_issue.get("explanation"),
                            "why_it_matters": prioritized_issue.get("why_it_matters"),
                            "fix_action": prioritized_issue.get("fix_action"),
                            "user_fixable": prioritized_issue.get("user_fixable", False),
                            "dandi_requirement": prioritized_issue.get("dandi_requirement", False),
                        }
                    )

            return result

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"LLM prioritization failed: {e}",
            )
            # Fallback: return original issues without prioritization
            return [issue.model_dump() if hasattr(issue, "model_dump") else issue for issue in issues]

    async def assess_nwb_quality(
        self,
        nwb_path: str,
        validation_result: ValidationResult,
        file_info: dict[str, Any],
        state: GlobalState,
    ) -> dict[str, Any]:
        """🎯 PRIORITY 3: Quality Scoring System.

        Use LLM to assess overall NWB file quality on a 0-100 scale.

        Evaluates:
        - Metadata completeness
        - DANDI readiness
        - Data organization
        - Documentation quality
        - Best practices adherence

        Args:
            nwb_path: Path to NWB file
            validation_result: Validation results from NWB Inspector
            file_info: Extracted file information
            state: Global state

        Returns:
            Quality assessment with score, grade, and improvement suggestions
        """
        import json

        if not self._llm_service:
            logger.warning("LLM service not available, using fallback quality scoring")
            # Fallback: basic scoring based on validation results
            fallback_score = 100 - (len(validation_result.issues) * 5)  # Deduct 5 points per issue
            fallback_score = max(0, min(100, fallback_score))

            return {
                "score": fallback_score,
                "grade": "C" if fallback_score >= 70 else "D" if fallback_score >= 60 else "F",
                "dandi_readiness_percent": 80 if validation_result.is_valid else 40,
                "strengths": ["File validated successfully"] if validation_result.is_valid else [],
                "improvement_suggestions": ["Fix validation issues"],
                "effort_to_a_grade": "medium",
                "summary": f"Basic quality assessment: {fallback_score}/100",
            }

        # Summarize validation issues
        issue_summary = {
            "total_issues": len(validation_result.issues),
            "by_severity": validation_result.summary,
            "is_valid": validation_result.is_valid,
        }

        # Get sample issues for context
        sample_issues = []
        for issue in validation_result.issues[:10]:  # First 10 issues
            # Convert ValidationIssue to dict for string formatting
            if hasattr(issue, "model_dump"):
                issue_dict: dict[str, Any] = issue.model_dump()
            else:
                issue_dict = issue  # type: ignore[assignment]
            sample_issues.append(f"[{issue_dict.get('severity', 'UNKNOWN')}] {issue_dict.get('message', 'No message')}")

        system_prompt = """You are an expert NWB data quality assessor and DANDI archive curator.

Your job is to evaluate NWB files on a 0-100 quality scale based on:

**Scoring Criteria:**
- **90-100 (A)**: Exceptional - DANDI-ready, complete metadata, follows all best practices
- **80-89 (B)**: Good - Minor improvements needed, mostly DANDI-ready
- **70-79 (C)**: Acceptable - Some important issues, fixable with moderate effort
- **60-69 (D)**: Below standard - Multiple significant issues, requires substantial work
- **0-59 (F)**: Poor - Critical issues, not suitable for sharing without major fixes

**Evaluation Factors:**
1. DANDI Archive Readiness (40 points)
   - Required metadata present
   - No blocking validation errors
   - File format compliance

2. Metadata Completeness (25 points)
   - Session description, subject info
   - Experimenter, institution, lab
   - Timestamps and identifiers

3. Data Organization (20 points)
   - Proper NWB hierarchy
   - Clear data relationships
   - Appropriate data types

4. Documentation Quality (10 points)
   - Descriptive names and descriptions
   - Protocol documentation
   - Citation information

5. Best Practices (5 points)
   - Follows NWB conventions
   - Efficient data storage
   - Reproducible metadata"""

        user_prompt = f"""Assess this NWB file's overall quality:

**File Information:**
{json.dumps(file_info, indent=2, default=str)}

**Validation Summary:**
{json.dumps(issue_summary, indent=2)}

**Sample Issues:**
{chr(10).join(sample_issues) if sample_issues else "No issues found"}

Provide:
1. Overall quality score (0-100)
2. Letter grade (A/B/C/D/F)
3. DANDI readiness percentage (0-100)
4. Strengths (what's done well)
5. Top 3 improvement suggestions
6. Estimated effort to reach grade A (low/medium/high)"""

        output_schema = {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "description": "Overall quality score (0-100)",
                    "minimum": 0,
                    "maximum": 100,
                },
                "grade": {
                    "type": "string",
                    "enum": ["A", "B", "C", "D", "F"],
                    "description": "Letter grade",
                },
                "dandi_readiness_percent": {
                    "type": "number",
                    "description": "DANDI submission readiness (0-100)",
                    "minimum": 0,
                    "maximum": 100,
                },
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of strengths",
                },
                "improvement_suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Top 3 improvement suggestions",
                },
                "effort_to_a_grade": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Effort needed to reach grade A",
                },
                "summary": {
                    "type": "string",
                    "description": "Brief 2-3 sentence quality summary",
                },
            },
            "required": [
                "score",
                "grade",
                "dandi_readiness_percent",
                "strengths",
                "improvement_suggestions",
                "effort_to_a_grade",
                "summary",
            ],
        }

        try:
            quality_assessment = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            return dict(quality_assessment)  # Cast Any to dict

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Quality scoring failed: {e}",
            )
            # Fallback: basic scoring based on validation results
            fallback_score = 100 - (len(validation_result.issues) * 5)  # Deduct 5 points per issue
            fallback_score = max(0, min(100, fallback_score))

            return {
                "score": fallback_score,
                "grade": "C" if fallback_score >= 70 else "D" if fallback_score >= 60 else "F",
                "dandi_readiness_percent": 80 if validation_result.is_valid else 40,
                "strengths": ["File validated successfully"] if validation_result.is_valid else [],
                "improvement_suggestions": ["Fix validation issues"],
                "effort_to_a_grade": "medium",
                "summary": f"Basic quality assessment: {fallback_score}/100",
            }
