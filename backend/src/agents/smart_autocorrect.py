"""
Smart Auto-Correction System with LLM.

This module intelligently fixes validation issues automatically
by understanding the context and applying domain knowledge.
"""
from typing import Any, Dict, List, Optional
import json

from models import GlobalState, LogLevel
from services import LLMService


class SmartAutoCorrectionSystem:
    """
    Intelligent auto-correction of validation issues.

    Features:
    - Context-aware correction strategies
    - Domain knowledge application
    - Safe vs. risky correction classification
    - Explanation of corrections
    - Confidence-based decision making
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize smart auto-correction system.

        Args:
            llm_service: LLM service for intelligent corrections
        """
        self.llm_service = llm_service
        self.correction_history = []

    async def analyze_and_correct(
        self,
        validation_issues: List[Dict[str, Any]],
        current_metadata: Dict[str, Any],
        file_context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Analyze validation issues and generate smart corrections.

        Args:
            validation_issues: List of validation issues
            current_metadata: Current metadata state
            file_context: Context about the file
            state: Global conversion state

        Returns:
            Dict with:
            - safe_corrections: Auto-applicable fixes
            - risky_corrections: Need user approval
            - cannot_auto_fix: Require user input
            - correction_plan: Step-by-step plan
            - estimated_success: Probability of success
        """
        if not self.llm_service:
            return self._basic_auto_corrections(validation_issues, current_metadata)

        try:
            result = await self._llm_smart_corrections(
                validation_issues=validation_issues,
                current_metadata=current_metadata,
                file_context=file_context,
                state=state,
            )

            state.add_log(
                LogLevel.INFO,
                f"Smart auto-correction analysis complete",
                {
                    "safe_fixes": len(result.get("safe_corrections", {})),
                    "risky_fixes": len(result.get("risky_corrections", {})),
                    "needs_user": len(result.get("cannot_auto_fix", [])),
                }
            )

            return result

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Smart auto-correction failed, using basic: {e}",
            )
            return self._basic_auto_corrections(validation_issues, current_metadata)

    async def _llm_smart_corrections(
        self,
        validation_issues: List[Dict[str, Any]],
        current_metadata: Dict[str, Any],
        file_context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """Use LLM to generate intelligent corrections."""
        system_prompt = """You are an expert NWB data fixer with deep knowledge of:
- NWB schema requirements and best practices
- DANDI archive submission standards
- Common validation issues and their solutions
- Neuroscience metadata conventions
- Safe vs. risky data modifications

Your job is to analyze validation issues and provide smart correction strategies.

**Classification Rules**:

**SAFE Corrections** (can apply automatically):
- Formatting issues (e.g., converting strings to lists)
- Removing empty/null fields
- Expanding abbreviations to full names
- Adding missing required fields with reasonable defaults
- Fixing data types (string → number, etc.)

**RISKY Corrections** (need user approval):
- Modifying existing scientific data
- Changing timestamps or session info
- Altering subject metadata
- Removing warnings (may lose information)

**CANNOT Auto-Fix** (need user input):
- Missing critical information (experimenter name, institution)
- Ambiguous data (which value is correct?)
- Domain-specific knowledge required

Be conservative: when in doubt, classify as RISKY or CANNOT."""

        # Format issues for LLM
        issues_summary = []
        for i, issue in enumerate(validation_issues, 1):
            issues_summary.append({
                "issue_id": i,
                "message": issue.get("message", "Unknown issue"),
                "severity": issue.get("severity", "INFO"),
                "location": issue.get("location", "unknown"),
                "importance": issue.get("importance", "medium"),
            })

        user_prompt = f"""Analyze these NWB validation issues and provide smart corrections.

**Current Metadata**:
```json
{json.dumps(current_metadata, indent=2)}
```

**File Context**:
```json
{json.dumps(file_context, indent=2)}
```

**Validation Issues** ({len(issues_summary)} total):
```json
{json.dumps(issues_summary, indent=2)}
```

**Your Task**:

For EACH issue, determine:

1. **Can it be auto-fixed?**
   - SAFE: Apply automatically, zero risk
   - RISKY: Could work but needs user approval
   - NO: Requires user input

2. **If SAFE or RISKY, provide**:
   - Field to modify
   - Current value (if any)
   - Proposed new value
   - Correction action (add/modify/remove)
   - Reasoning
   - Confidence score (0-100)

3. **If NO, provide**:
   - What information is needed
   - Why it can't be auto-fixed
   - Example of valid input

**Output Format**:
Classify ALL issues into safe_corrections, risky_corrections, or cannot_auto_fix.
Provide a correction_plan with step-by-step instructions.
Estimate overall success probability."""

        output_schema = {
            "type": "object",
            "properties": {
                "safe_corrections": {
                    "type": "object",
                    "description": "Auto-applicable fixes (field → new value)",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "current_value": {"type": ["string", "null", "number", "array", "boolean"]},
                            "new_value": {"type": ["string", "null", "number", "array", "boolean"]},
                            "action": {"type": "string", "enum": ["add", "modify", "remove", "format"]},
                            "reasoning": {"type": "string"},
                            "confidence": {"type": "number"}
                        }
                    }
                },
                "risky_corrections": {
                    "type": "object",
                    "description": "Fixes needing user approval",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "current_value": {"type": ["string", "null", "number", "array", "boolean"]},
                            "proposed_value": {"type": ["string", "null", "number", "array", "boolean"]},
                            "action": {"type": "string"},
                            "risk_reason": {"type": "string"},
                            "confidence": {"type": "number"}
                        }
                    }
                },
                "cannot_auto_fix": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "required_info": {"type": "string"},
                            "why_manual": {"type": "string"},
                            "example_input": {"type": "string"}
                        }
                    }
                },
                "correction_plan": {
                    "type": "string",
                    "description": "Step-by-step correction plan"
                },
                "estimated_success": {
                    "type": "number",
                    "description": "Estimated success probability 0-100"
                }
            },
            "required": ["safe_corrections", "risky_corrections", "cannot_auto_fix", "correction_plan"]
        }

        response = await self.llm_service.generate_structured_output(
            prompt=user_prompt,
            output_schema=output_schema,
            system_prompt=system_prompt,
        )

        return response

    def _basic_auto_corrections(
        self,
        validation_issues: List[Dict[str, Any]],
        current_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fallback basic auto-corrections without LLM."""
        safe_corrections = {}
        cannot_auto_fix = []

        for issue in validation_issues:
            message = issue.get("message", "").lower()

            # Simple heuristic rules
            if "empty" in message and "institution" in message:
                # Can remove empty institution
                safe_corrections["institution"] = {
                    "current_value": current_metadata.get("institution"),
                    "new_value": None,
                    "action": "remove",
                    "reasoning": "Remove empty institution field",
                    "confidence": 80,
                }
            elif "experimenter" in message or "institution" in message:
                # Needs user input
                cannot_auto_fix.append({
                    "issue": message,
                    "required_info": "User must provide this information",
                    "why_manual": "Critical DANDI-required field",
                    "example_input": "Dr. Jane Smith",
                })

        return {
            "safe_corrections": safe_corrections,
            "risky_corrections": {},
            "cannot_auto_fix": cannot_auto_fix,
            "correction_plan": "Apply safe corrections first, then request user input for remaining issues",
            "estimated_success": 50,
        }

    async def apply_safe_corrections(
        self,
        safe_corrections: Dict[str, Any],
        current_metadata: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Apply safe corrections to metadata.

        Args:
            safe_corrections: Dictionary of safe corrections to apply
            current_metadata: Current metadata state
            state: Global state for logging

        Returns:
            Updated metadata
        """
        updated_metadata = current_metadata.copy()
        applied_corrections = []

        for field, correction in safe_corrections.items():
            action = correction.get("action")
            new_value = correction.get("new_value")
            confidence = correction.get("confidence", 0)

            if confidence < 70:
                state.add_log(
                    LogLevel.WARNING,
                    f"Skipping low-confidence correction for {field} ({confidence}%)",
                )
                continue

            if action == "add" or action == "modify":
                updated_metadata[field] = new_value
                applied_corrections.append(f"Set {field} to {new_value}")
            elif action == "remove":
                if field in updated_metadata:
                    del updated_metadata[field]
                    applied_corrections.append(f"Removed {field}")
            elif action == "format":
                # Apply formatting transformation
                updated_metadata[field] = new_value
                applied_corrections.append(f"Reformatted {field}")

        state.add_log(
            LogLevel.INFO,
            f"Applied {len(applied_corrections)} safe auto-corrections",
            {"corrections": applied_corrections}
        )

        return updated_metadata

    def get_correction_summary(
        self,
        safe_count: int,
        risky_count: int,
        manual_count: int,
    ) -> str:
        """Generate user-friendly summary of corrections."""
        summary_parts = []

        if safe_count > 0:
            summary_parts.append(f"✅ {safe_count} issues can be fixed automatically")

        if risky_count > 0:
            summary_parts.append(f"⚠️ {risky_count} fixes need your approval")

        if manual_count > 0:
            summary_parts.append(f"📝 {manual_count} issues require your input")

        return " | ".join(summary_parts) if summary_parts else "No corrections needed"
