"""
Evaluation Agent implementation.

Responsible for:
- NWB file validation using NWB Inspector
- Quality assessment
- Correction analysis (using LLM if available)
"""
import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from models import (
    ConversionStatus,
    CorrectionContext,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationResult,
    ValidationStatus,
    ValidationOutcome,
)
from services import LLMService
from services.report_service import ReportService
from services.prompt_service import PromptService

# Import intelligent evaluation modules
from agents.intelligent_validation_analyzer import IntelligentValidationAnalyzer
from agents.smart_issue_resolution import SmartIssueResolution
from agents.validation_history_learning import ValidationHistoryLearner


class EvaluationAgent:
    """
    Evaluation agent for validation and quality assessment.

    This agent validates NWB files and performs quality checks.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the evaluation agent.

        Args:
            llm_service: Optional LLM service for correction analysis
        """
        self._llm_service = llm_service
        self._report_service = ReportService()
        self._prompt_service = PromptService()

        # Initialize intelligent evaluation modules
        self._validation_analyzer = (
            IntelligentValidationAnalyzer(llm_service) if llm_service else None
        )
        self._issue_resolution = (
            SmartIssueResolution(llm_service) if llm_service else None
        )
        self._history_learner = (
            ValidationHistoryLearner(llm_service) if llm_service else None
        )

    async def handle_run_validation(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Run NWB Inspector validation on an NWB file.

        Args:
            message: MCP message with context containing 'nwb_path'
            state: Global state

        Returns:
            MCPResponse with validation results
        """
        nwb_path = message.context.get("nwb_path")

        if not nwb_path:
            state.add_log(
                LogLevel.ERROR,
                "Missing nwb_path in validation request",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_NWB_PATH",
                error_message="nwb_path is required for validation",
            )

        # ValidationStatus is for final outcomes, not intermediate states
        # ConversionStatus.VALIDATING is used for the running state
        state.add_log(
            LogLevel.INFO,
            f"Starting NWB validation: {nwb_path}",
            {"nwb_path": nwb_path},
        )

        try:
            validation_result = await self._run_nwb_inspector(nwb_path)

            # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Use ValidationOutcome enum
            # Determine overall status for reporting
            if validation_result.is_valid:
                # No critical or error issues
                if len(validation_result.issues) == 0:
                    overall_status = ValidationOutcome.PASSED
                elif validation_result.summary.get("warning", 0) > 0 or validation_result.summary.get("info", 0) > 0:
                    overall_status = ValidationOutcome.PASSED_WITH_ISSUES
                else:
                    overall_status = ValidationOutcome.PASSED
            else:
                # Has critical or error issues
                overall_status = ValidationOutcome.FAILED

            # Bug #2 fix: Store overall_status in state (Story 7.2)
            state.overall_status = overall_status

            # Update state based on validation result
            # Bug #6 fix: Set validation_status to passed_improved if this is a successful improvement
            if validation_result.is_valid and overall_status == ValidationOutcome.PASSED:
                # Check if this is after a correction attempt (Story 8.8 line 957)
                if state.correction_attempt > 0:
                    state.update_validation_status(ValidationStatus.PASSED_IMPROVED)
                else:
                    state.update_validation_status(ValidationStatus.PASSED)

                state.add_log(
                    LogLevel.INFO,
                    f"Validation {overall_status.value.lower()}",
                    {
                        "nwb_path": nwb_path,
                        "summary": validation_result.summary,
                        "overall_status": overall_status.value,
                        "validation_status": state.validation_status.value if state.validation_status else None,
                    },
                )
            elif validation_result.is_valid and overall_status == ValidationOutcome.PASSED_WITH_ISSUES:
                # Don't set final validation_status yet - wait for user decision
                state.add_log(
                    LogLevel.INFO,
                    f"Validation {overall_status.value.lower()} (awaiting user decision)",
                    {"nwb_path": nwb_path, "summary": validation_result.summary, "overall_status": overall_status.value},
                )
            else:
                # FAILED status - don't set validation_status yet, wait for user decision
                state.add_log(
                    LogLevel.WARNING,
                    "Validation failed (awaiting user decision)",
                    {
                        "nwb_path": nwb_path,
                        "summary": validation_result.summary,
                        "issue_count": len(validation_result.issues),
                        "overall_status": overall_status.value,
                    },
                )

            # Create enriched validation result with overall_status
            validation_result_dict = validation_result.model_dump()
            # Serialize enum to string value for JSON response
            validation_result_dict["overall_status"] = overall_status.value

            # Fix issue counts mapping for report generation
            # Map lowercase severity keys to uppercase for report compatibility
            if validation_result.summary:
                validation_result_dict["issue_counts"] = {
                    "CRITICAL": validation_result.summary.get("critical", 0),
                    "ERROR": validation_result.summary.get("error", 0),
                    "WARNING": validation_result.summary.get("warning", 0),
                    "INFO": validation_result.summary.get("info", 0),
                    "BEST_PRACTICE": validation_result.summary.get("best_practice", 0),
                }

            # Use LLM to prioritize and explain issues if available
            if self._llm_service and validation_result.issues:
                try:
                    prioritized_issues = await self._prioritize_and_explain_issues(
                        issues=validation_result.issues,
                        state=state,
                    )
                    validation_result_dict["prioritized_issues"] = prioritized_issues
                    state.add_log(
                        LogLevel.INFO,
                        f"Prioritized {len(prioritized_issues)} validation issues",
                        {"dandi_blocking_count": len([i for i in prioritized_issues if i.get("priority") == "dandi_blocking"])},
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Issue prioritization failed: {e}",
                    )

            # 🎯 PRIORITY 3: Quality Scoring System
            if self._llm_service:
                try:
                    quality_score = await self._assess_nwb_quality(
                        nwb_path=nwb_path,
                        validation_result=validation_result,
                        state=state,
                    )
                    validation_result_dict["quality_score"] = quality_score
                    state.add_log(
                        LogLevel.INFO,
                        f"NWB Quality Score: {quality_score.get('score', 0)}/100 (Grade: {quality_score.get('grade', 'N/A')})",
                        {"quality_details": quality_score},
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Quality scoring failed: {e}",
                    )

            # 🎯 NEW: Intelligent Validation Analysis
            if self._validation_analyzer and validation_result.issues:
                try:
                    file_context = {
                        "nwb_path": nwb_path,
                        "file_size_mb": Path(nwb_path).stat().st_size / (1024 * 1024) if Path(nwb_path).exists() else 0,
                        "nwb_version": validation_result_dict.get("file_info", {}).get("nwb_version", "unknown"),
                    }

                    deep_analysis = await self._validation_analyzer.analyze_validation_results(
                        validation_result=validation_result,
                        file_context=file_context,
                        state=state,
                    )
                    validation_result_dict["deep_analysis"] = deep_analysis

                    state.add_log(
                        LogLevel.INFO,
                        f"Deep validation analysis: {len(deep_analysis.get('root_causes', []))} root causes, "
                        f"{len(deep_analysis.get('quick_wins', []))} quick wins",
                        {"analysis_summary": deep_analysis.get("analysis_summary", "")},
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Deep validation analysis failed: {e}",
                    )

            # 🎯 NEW: Smart Resolution Plan
            if self._issue_resolution and validation_result.issues:
                try:
                    file_context = {
                        "nwb_path": nwb_path,
                        "file_size_mb": Path(nwb_path).stat().st_size / (1024 * 1024) if Path(nwb_path).exists() else 0,
                        "nwb_version": validation_result_dict.get("file_info", {}).get("nwb_version", "unknown"),
                    }

                    resolution_plan = await self._issue_resolution.generate_resolution_plan(
                        issues=validation_result.issues,
                        file_context=file_context,
                        existing_metadata=state.metadata,
                        state=state,
                    )
                    validation_result_dict["resolution_plan"] = resolution_plan

                    state.add_log(
                        LogLevel.INFO,
                        f"Generated resolution plan with {len(resolution_plan.get('workflows', []))} workflows",
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Resolution plan generation failed: {e}",
                    )

            # 🎯 NEW: Record to validation history for learning
            if self._history_learner:
                try:
                    file_context = {
                        "format": state.metadata.get("format", "unknown"),
                        "file_size_mb": Path(nwb_path).stat().st_size / (1024 * 1024) if Path(nwb_path).exists() else 0,
                        "nwb_version": validation_result_dict.get("file_info", {}).get("nwb_version", "unknown"),
                    }

                    await self._history_learner.record_validation_session(
                        validation_result=validation_result,
                        file_context=file_context,
                        resolution_actions=None,  # Will be populated if user applies fixes
                        state=state,
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.DEBUG,
                        f"History recording failed: {e}",
                    )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "validation_result": validation_result_dict,
                },
            )

        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"nwb_path": nwb_path, "exception": str(e)},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="VALIDATION_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    def _extract_file_info(self, nwb_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive file information from NWB file for reports.

        Args:
            nwb_path: Path to NWB file

        Returns:
            Dictionary with complete file metadata including experimenter,
            institution, subject info, etc.
        """
        from datetime import datetime
        import h5py

        # Initialize with all possible NWB metadata fields
        file_info = {
            # File-level metadata
            'nwb_version': 'Unknown',
            'file_size_bytes': 0,
            'creation_date': 'Unknown',
            'identifier': 'Unknown',
            'session_description': 'N/A',
            'session_start_time': 'N/A',
            'session_id': 'N/A',

            # General metadata (experimenter, institution, lab)
            'experimenter': [],
            'institution': 'N/A',
            'lab': 'N/A',
            'experiment_description': 'N/A',

            # Subject metadata
            'subject_id': 'N/A',
            'species': 'N/A',
            'sex': 'N/A',
            'age': 'N/A',
            'date_of_birth': 'N/A',
            'description': 'N/A',
            'genotype': 'N/A',
            'strain': 'N/A',

            # Provenance tracking - record source of each metadata field
            '_provenance': {},
            '_source_files': {},
        }

        def decode_value(value):
            """Helper to decode bytes to string."""
            if isinstance(value, bytes):
                return value.decode('utf-8')
            elif isinstance(value, str):
                return value
            else:
                return str(value)

        try:
            nwb_file_path = Path(nwb_path)

            # Get file size and creation date
            if nwb_file_path.exists():
                file_info['file_size_bytes'] = nwb_file_path.stat().st_size
                file_info['creation_date'] = datetime.fromtimestamp(
                    nwb_file_path.stat().st_ctime
                ).strftime('%Y-%m-%d %H:%M:%S')

            # Try to read NWB metadata using h5py
            try:
                with h5py.File(nwb_path, 'r') as f:
                    print(f"DEBUG: Reading NWB file with h5py: {nwb_path}")
                    print(f"DEBUG: Root level groups: {list(f.keys())}")
                    print(f"DEBUG: Root level attrs: {list(f.attrs.keys())}")

                    # Helper to set top-level attrs with provenance
                    def set_attr_with_provenance(attr_name, field_name=None):
                        """Extract and set a root-level attribute with provenance tracking."""
                        if field_name is None:
                            field_name = attr_name
                        if attr_name in f.attrs:
                            value = decode_value(f.attrs[attr_name])
                            file_info[field_name] = value
                            file_info['_provenance'][field_name] = 'file-extracted'
                            file_info['_source_files'][field_name] = nwb_path

                    # Extract top-level attributes
                    set_attr_with_provenance('nwb_version')
                    set_attr_with_provenance('identifier')
                    set_attr_with_provenance('session_description')
                    set_attr_with_provenance('session_start_time')

                    # Extract general metadata
                    if 'general' in f:
                        general = f['general']
                        print(f"DEBUG: Found /general group")
                        print(f"DEBUG: /general attrs: {list(general.attrs.keys())}")
                        print(f"DEBUG: /general subgroups: {list(general.keys())}")

                        # CRITICAL FIX: Check both attributes AND datasets
                        # NeuroConv writes metadata as datasets, not attributes!
                        def get_value(group, key):
                            """Get value from either attribute or dataset."""
                            if key in group.attrs:
                                return group.attrs[key]
                            elif key in group:
                                # It's a dataset - read the value
                                return group[key][()]
                            return None

                        def set_with_provenance(field_name, value, provenance='file-extracted', source_file=None):
                            """Set a field value and track its provenance."""
                            file_info[field_name] = value
                            file_info['_provenance'][field_name] = provenance
                            if source_file:
                                file_info['_source_files'][field_name] = source_file

                        # Experimenter (can be string or array)
                        exp_value = get_value(general, 'experimenter')
                        if exp_value is not None:
                            exp_value = exp_value
                            if isinstance(exp_value, bytes):
                                set_with_provenance('experimenter', [exp_value.decode('utf-8')], 'file-extracted', nwb_path)
                            elif isinstance(exp_value, str):
                                set_with_provenance('experimenter', [exp_value], 'file-extracted', nwb_path)
                            elif isinstance(exp_value, (list, tuple)):
                                set_with_provenance('experimenter', [
                                    e.decode('utf-8') if isinstance(e, bytes) else str(e)
                                    for e in exp_value
                                ], 'file-extracted', nwb_path)
                            else:
                                # Handle numpy arrays or other iterable types
                                try:
                                    set_with_provenance('experimenter', [decode_value(e) for e in exp_value], 'file-extracted', nwb_path)
                                except TypeError:
                                    set_with_provenance('experimenter', [decode_value(exp_value)], 'file-extracted', nwb_path)

                        # Institution
                        inst_value = get_value(general, 'institution')
                        if inst_value is not None:
                            set_with_provenance('institution', decode_value(inst_value), 'file-extracted', nwb_path)

                        # Lab
                        lab_value = get_value(general, 'lab')
                        if lab_value is not None:
                            set_with_provenance('lab', decode_value(lab_value), 'file-extracted', nwb_path)

                        # Experiment description
                        exp_desc_value = get_value(general, 'experiment_description')
                        if exp_desc_value is not None:
                            set_with_provenance('experiment_description', decode_value(exp_desc_value), 'file-extracted', nwb_path)

                        # Session ID
                        session_id_value = get_value(general, 'session_id')
                        if session_id_value is not None:
                            set_with_provenance('session_id', decode_value(session_id_value), 'file-extracted', nwb_path)

                        # Extract subject metadata
                        if 'subject' in general:
                            subject_group = general['subject']

                            # Check both attrs and datasets for subject fields
                            subj_id_value = get_value(subject_group, 'subject_id')
                            if subj_id_value is not None:
                                set_with_provenance('subject_id', decode_value(subj_id_value), 'file-extracted', nwb_path)

                            species_value = get_value(subject_group, 'species')
                            if species_value is not None:
                                set_with_provenance('species', decode_value(species_value), 'file-extracted', nwb_path)

                            sex_value = get_value(subject_group, 'sex')
                            if sex_value is not None:
                                set_with_provenance('sex', decode_value(sex_value), 'file-extracted', nwb_path)

                            age_value = get_value(subject_group, 'age')
                            if age_value is not None:
                                set_with_provenance('age', decode_value(age_value), 'file-extracted', nwb_path)

                            dob_value = get_value(subject_group, 'date_of_birth')
                            if dob_value is not None:
                                set_with_provenance('date_of_birth', decode_value(dob_value), 'file-extracted', nwb_path)

                            desc_value = get_value(subject_group, 'description')
                            if desc_value is not None:
                                set_with_provenance('description', decode_value(desc_value), 'file-extracted', nwb_path)

                            geno_value = get_value(subject_group, 'genotype')
                            if geno_value is not None:
                                set_with_provenance('genotype', decode_value(geno_value), 'file-extracted', nwb_path)

                            strain_value = get_value(subject_group, 'strain')
                            if strain_value is not None:
                                set_with_provenance('strain', decode_value(strain_value), 'file-extracted', nwb_path)

            except Exception as e:
                # If h5py fails, try PyNWB
                print(f"h5py extraction failed: {e}, trying PyNWB...")
                try:
                    from pynwb import NWBHDF5IO
                    with NWBHDF5IO(nwb_path, 'r') as io:
                        nwbfile = io.read()

                        # File-level attributes
                        file_info['nwb_version'] = str(getattr(nwbfile, 'nwb_version', 'Unknown'))
                        file_info['identifier'] = str(getattr(nwbfile, 'identifier', 'Unknown'))
                        file_info['session_description'] = str(getattr(nwbfile, 'session_description', 'N/A'))
                        file_info['session_start_time'] = str(getattr(nwbfile, 'session_start_time', 'N/A'))
                        file_info['session_id'] = str(getattr(nwbfile, 'session_id', 'N/A'))

                        # General metadata
                        experimenter = getattr(nwbfile, 'experimenter', None)
                        if experimenter:
                            file_info['experimenter'] = list(experimenter) if hasattr(experimenter, '__iter__') and not isinstance(experimenter, str) else [str(experimenter)]

                        file_info['institution'] = str(getattr(nwbfile, 'institution', 'N/A'))
                        file_info['lab'] = str(getattr(nwbfile, 'lab', 'N/A'))
                        file_info['experiment_description'] = str(getattr(nwbfile, 'experiment_description', 'N/A'))

                        # Subject metadata
                        if nwbfile.subject:
                            file_info['subject_id'] = str(getattr(nwbfile.subject, 'subject_id', 'N/A'))
                            file_info['species'] = str(getattr(nwbfile.subject, 'species', 'N/A'))
                            file_info['sex'] = str(getattr(nwbfile.subject, 'sex', 'N/A'))
                            file_info['age'] = str(getattr(nwbfile.subject, 'age', 'N/A'))
                            file_info['date_of_birth'] = str(getattr(nwbfile.subject, 'date_of_birth', 'N/A'))
                            file_info['description'] = str(getattr(nwbfile.subject, 'description', 'N/A'))
                            file_info['genotype'] = str(getattr(nwbfile.subject, 'genotype', 'N/A'))
                            file_info['strain'] = str(getattr(nwbfile.subject, 'strain', 'N/A'))
                        else:
                            print(f"WARNING: NWB file has no subject object!")

                        print(f"PyNWB extraction succeeded: experimenter={file_info['experimenter']}, institution={file_info['institution']}, subject_id={file_info['subject_id']}")

                except Exception as pynwb_error:
                    print(f"CRITICAL: Could not extract file info with PyNWB either: {pynwb_error}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"Error extracting file info: {e}")

        return file_info

    async def _prioritize_and_explain_issues(
        self,
        issues: List[Any],
        state: GlobalState,
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to prioritize validation issues and explain their importance.

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
        import json

        # Format issues for LLM
        issues_text = []
        for idx, issue in enumerate(issues[:20], 1):  # Limit to first 20 for token efficiency
            issue_dict = issue.model_dump() if hasattr(issue, 'model_dump') else issue
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
                    original = issues[idx].model_dump() if hasattr(issues[idx], 'model_dump') else issues[idx]
                    result.append({
                        **original,  # Keep all original fields
                        "priority": prioritized_issue.get("priority"),
                        "explanation": prioritized_issue.get("explanation"),
                        "why_it_matters": prioritized_issue.get("why_it_matters"),
                        "fix_action": prioritized_issue.get("fix_action"),
                        "user_fixable": prioritized_issue.get("user_fixable", False),
                        "dandi_requirement": prioritized_issue.get("dandi_requirement", False),
                    })

            return result

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"LLM prioritization failed: {e}",
            )
            # Fallback: return original issues without prioritization
            return [issue.model_dump() if hasattr(issue, 'model_dump') else issue for issue in issues]

    async def _assess_nwb_quality(
        self,
        nwb_path: str,
        validation_result: ValidationResult,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        🎯 PRIORITY 3: Quality Scoring System
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
            state: Global state

        Returns:
            Quality assessment with score, grade, and improvement suggestions
        """
        import json
        from pathlib import Path

        # Extract file information
        file_info = self._extract_file_info(nwb_path)

        # Summarize validation issues
        issue_summary = {
            "total_issues": len(validation_result.issues),
            "by_severity": validation_result.summary,
            "is_valid": validation_result.is_valid,
        }

        # Get sample issues for context
        sample_issues = []
        for issue in validation_result.issues[:10]:  # First 10 issues
            issue_dict = issue.model_dump() if hasattr(issue, 'model_dump') else issue
            sample_issues.append(
                f"[{issue_dict.get('severity', 'UNKNOWN')}] {issue_dict.get('message', 'No message')}"
            )

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

            return quality_assessment

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

    async def _run_nwb_inspector(self, nwb_path: str) -> ValidationResult:
        """
        Run NWB Inspector validation.

        Args:
            nwb_path: Path to NWB file

        Returns:
            ValidationResult object

        Raises:
            Exception: If validation cannot be run
        """
        from nwbinspector import inspect_nwbfile
        from nwbinspector import __version__ as inspector_version

        # Run NWB Inspector
        results = list(inspect_nwbfile(nwbfile_path=nwb_path))

        # Convert to our format
        inspector_results = []
        for check_result in results:
            inspector_results.append({
                "severity": check_result.severity.name.lower(),
                "message": check_result.message,
                "location": str(check_result.location) if hasattr(check_result, "location") else None,
                "check_function_name": check_result.check_function_name,
            })

        validation_result = ValidationResult.from_inspector_output(
            inspector_results,
            inspector_version,
        )

        return validation_result

    async def handle_analyze_corrections(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Analyze validation issues and suggest corrections (requires LLM).

        Args:
            message: MCP message with context containing validation results
            state: Global state

        Returns:
            MCPResponse with correction suggestions or error
        """
        if not self._llm_service:
            state.add_log(
                LogLevel.ERROR,
                "LLM service not available for correction analysis",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="LLM_NOT_AVAILABLE",
                error_message="Correction analysis requires LLM service",
            )

        validation_result_data = message.context.get("validation_result")
        input_metadata = message.context.get("input_metadata", {})
        conversion_parameters = message.context.get("conversion_parameters", {})

        if not validation_result_data:
            state.add_log(
                LogLevel.ERROR,
                "Missing validation_result in correction analysis request",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_VALIDATION_RESULT",
                error_message="validation_result is required",
            )

        state.add_log(
            LogLevel.INFO,
            "Starting correction analysis with LLM",
            {"attempt": state.correction_attempt},
        )

        try:
            # Parse validation result
            validation_result = ValidationResult(**validation_result_data)

            # Create correction context
            correction_context = CorrectionContext(
                validation_result=validation_result,
                input_metadata=input_metadata,
                conversion_parameters=conversion_parameters,
            )

            # Analyze with LLM
            corrections = await self._analyze_with_llm(correction_context, state)

            state.add_log(
                LogLevel.INFO,
                "Correction analysis completed",
                {"corrections_count": len(corrections.get("suggestions", []))},
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "corrections": corrections,
                },
            )

        except Exception as e:
            error_msg = f"Correction analysis failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"exception": str(e)},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="ANALYSIS_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    async def _analyze_with_llm(
        self,
        correction_context: CorrectionContext,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze validation issues and suggest corrections.

        Args:
            correction_context: Context for correction analysis
            state: Global state

        Returns:
            Dictionary with correction suggestions
        """
        # Build prompt
        prompt = self._build_correction_prompt(correction_context)

        # Define output schema
        output_schema = {
            "type": "object",
            "properties": {
                "analysis": {"type": "string"},
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "severity": {"type": "string"},
                            "suggestion": {"type": "string"},
                            "actionable": {"type": "boolean"},
                        },
                    },
                },
                "recommended_action": {
                    "type": "string",
                    "enum": ["retry", "manual_intervention", "accept_warnings"],
                },
            },
        }

        # Call LLM
        result = await self._llm_service.generate_structured_output(
            prompt=prompt,
            output_schema=output_schema,
            system_prompt="You are an expert in NWB (Neurodata Without Borders) file format and validation. Analyze validation issues and suggest corrections.",
        )

        return result

    def _build_correction_prompt(self, context: CorrectionContext) -> str:
        """
        Build LLM prompt for correction analysis.

        Args:
            context: Correction context

        Returns:
            Prompt string
        """
        issues_text = "\n".join([
            f"- [{issue.severity.value.upper()}] {issue.message}"
            + (f" (at {issue.location})" if issue.location else "")
            for issue in context.validation_result.issues[:20]  # Limit to 20 issues
        ])

        if len(context.validation_result.issues) > 20:
            issues_text += f"\n... and {len(context.validation_result.issues) - 20} more issues"

        prompt = f"""# NWB Validation Issues

## Summary
- Total issues: {len(context.validation_result.issues)}
- Critical: {context.validation_result.summary.get('critical', 0)}
- Errors: {context.validation_result.summary.get('error', 0)}
- Warnings: {context.validation_result.summary.get('warning', 0)}

## Issues
{issues_text}

## Conversion Parameters
{context.conversion_parameters}

## Previous Attempts
{len(context.previous_attempts)} previous correction attempts

## Task
Analyze these validation issues and provide:
1. A brief analysis of the root causes
2. Specific, actionable suggestions for each major issue
3. A recommended action (retry, manual_intervention, or accept_warnings)

Focus on the most critical issues first."""

        return prompt

    async def handle_generate_report(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Generate evaluation report (PDF for PASSED, JSON for FAILED).

        Args:
            message: MCP message with validation_result and optional llm_analysis
            state: Global state

        Returns:
            MCPResponse with report path

        Implements Stories 9.5 and 9.6: Report Generation
        """
        validation_result_data = message.context.get("validation_result")
        llm_analysis = message.context.get("llm_analysis")
        nwb_path = message.context.get("nwb_path")
        final_accepted = message.context.get("final_accepted", False)  # BUG #4 FIX

        if not validation_result_data:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_VALIDATION_RESULT",
                error_message="validation_result is required for report generation",
            )

        try:
            # Determine report type based on validation status
            overall_status = validation_result_data.get('overall_status', 'UNKNOWN')

            # BUG #4 FIX: If user accepted PASSED_WITH_ISSUES, treat as PASSED for final report generation
            if final_accepted and overall_status == 'PASSED_WITH_ISSUES':
                overall_status = 'PASSED'
                state.add_log(
                    LogLevel.INFO,
                    "Generating final reports for PASSED_WITH_ISSUES after user acceptance (treating as PASSED)",
                    {"original_status": "PASSED_WITH_ISSUES", "final_status": "PASSED"},
                )

            if nwb_path:
                nwb_path_obj = Path(nwb_path)
                report_base = nwb_path_obj.stem
            else:
                report_base = "evaluation_report"

            # BUG #4 FIX: Only generate final reports for clean PASSED
            # For PASSED_WITH_ISSUES, wait for user decision before generating final reports
            if overall_status == 'PASSED':
                # Generate both PDF and text reports (clean pass)
                output_dir = Path(state.output_path).parent if state.output_path else Path("outputs")
                pdf_report_path = output_dir / f"{report_base}_evaluation_report.pdf"
                text_report_path = output_dir / f"{report_base}_inspection_report.txt"

                # CRITICAL FIX: Always extract file info directly from NWB file
                # This ensures we get the actual metadata that was written during conversion
                if nwb_path:
                    state.add_log(
                        LogLevel.INFO,
                        f"Extracting metadata from NWB file for report: {nwb_path}",
                    )
                    file_info = self._extract_file_info(nwb_path)

                    # Add provenance information for each metadata field
                    # Track source: user-provided, file-extracted, ai-inferred, or default
                    file_info_with_provenance = self._add_metadata_provenance(
                        file_info=file_info,
                        state=state,
                    )

                    validation_result_data['file_info'] = file_info_with_provenance
                    state.add_log(
                        LogLevel.DEBUG,
                        f"Extracted file metadata: experimenter={file_info.get('experimenter')}, "
                        f"institution={file_info.get('institution')}, "
                        f"subject_id={file_info.get('subject_id')}",
                    )

                # If LLM service available and no analysis provided, generate it
                if self._llm_service and not llm_analysis:
                    llm_analysis = await self._generate_quality_assessment(validation_result_data)

                # Build workflow trace for transparency and reproducibility
                workflow_trace = self._build_workflow_trace(state)

                # Generate HTML report (interactive with embedded CSS/JS)
                html_report_path = output_dir / f"{report_base}_evaluation_report.html"
                self._report_service.generate_html_report(
                    html_report_path,
                    validation_result_data,
                    llm_analysis,
                    workflow_trace
                )

                # Generate PDF report (detailed with LLM analysis and workflow trace)
                self._report_service.generate_pdf_report(
                    pdf_report_path,
                    validation_result_data,
                    llm_analysis,
                    workflow_trace
                )

                # Generate text report (NWB Inspector style with LLM analysis and workflow trace)
                self._report_service.generate_text_report(
                    text_report_path,
                    validation_result_data,
                    llm_analysis,
                    workflow_trace
                )

                state.add_log(
                    LogLevel.INFO,
                    f"Generated evaluation reports: HTML, PDF, and text",
                    {
                        "html_report": str(html_report_path),
                        "pdf_report": str(pdf_report_path),
                        "text_report": str(text_report_path),
                        "status": overall_status
                    },
                )

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "report_path": str(html_report_path),  # Primary report (HTML for interactivity)
                        "html_report_path": str(html_report_path),
                        "pdf_report_path": str(pdf_report_path),
                        "text_report_path": str(text_report_path),
                        "report_type": "html_pdf_and_text",
                    },
                )

            elif overall_status == 'PASSED_WITH_ISSUES':
                # BUG #4 FIX: For PASSED_WITH_ISSUES, don't generate final reports yet
                # Wait for user decision (improve or accept) before generating final reports
                # Generate a temporary JSON summary for user to review
                output_dir = Path(state.output_path).parent if state.output_path else Path("outputs")
                preview_report_path = output_dir / f"{report_base}_preview.json"

                # CRITICAL FIX: Always extract file info directly from NWB file
                # This ensures we get the actual metadata that was written during conversion
                if nwb_path:
                    state.add_log(
                        LogLevel.INFO,
                        f"Extracting metadata from NWB file for preview report: {nwb_path}",
                    )
                    file_info = self._extract_file_info(nwb_path)

                    # Add provenance information for transparency
                    file_info_with_provenance = self._add_metadata_provenance(
                        file_info=file_info,
                        state=state,
                    )

                    validation_result_data['file_info'] = file_info_with_provenance

                # Build workflow trace
                workflow_trace = self._build_workflow_trace(state)

                # Generate preview JSON report (not final)
                self._report_service.generate_json_report(
                    preview_report_path,
                    validation_result_data,
                    llm_analysis,
                    workflow_trace
                )

                state.add_log(
                    LogLevel.INFO,
                    f"Generated preview report for PASSED_WITH_ISSUES (final reports deferred until user accepts)",
                    {"preview_report": str(preview_report_path), "status": overall_status},
                )

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "report_path": str(preview_report_path),
                        "report_type": "preview_json",
                        "awaiting_user_decision": True,  # Flag to indicate final reports not yet generated
                    },
                )

            elif overall_status == 'PASSED_WITH_ISSUES':
                # BUG #4 FIX: For PASSED_WITH_ISSUES, don't generate final reports yet
                # Wait for user decision (improve or accept) before generating final reports
                # Generate a temporary JSON summary for user to review
                output_dir = Path(state.output_path).parent if state.output_path else Path("outputs")
                preview_report_path = output_dir / f"{report_base}_preview.json"

                # Build workflow trace
                workflow_trace = self._build_workflow_trace(state)

                # Generate preview JSON report (not final)
                self._report_service.generate_json_report(
                    preview_report_path,
                    validation_result_data,
                    llm_analysis,
                    workflow_trace
                )

                state.add_log(
                    LogLevel.INFO,
                    f"Generated preview report for PASSED_WITH_ISSUES (final reports deferred until user accepts)",
                    {"preview_report": str(preview_report_path), "status": overall_status},
                )

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "report_path": str(preview_report_path),
                        "report_type": "preview_json",
                        "awaiting_user_decision": True,  # Flag to indicate final reports not yet generated
                    },
                )

            else:  # FAILED
                # Generate JSON report
                output_dir = Path(state.output_path).parent if state.output_path else Path("outputs")
                report_path = output_dir / f"{report_base}_correction_context.json"

                # CRITICAL FIX: Always extract file info directly from NWB file
                # Even for FAILED files, we want to show what metadata IS present
                if nwb_path:
                    state.add_log(
                        LogLevel.INFO,
                        f"Extracting metadata from NWB file for correction report: {nwb_path}",
                    )
                    file_info = self._extract_file_info(nwb_path)

                    # Add provenance information even for failed conversions
                    file_info_with_provenance = self._add_metadata_provenance(
                        file_info=file_info,
                        state=state,
                    )

                    validation_result_data['file_info'] = file_info_with_provenance

                # If LLM service available and no analysis provided, generate it
                if self._llm_service and not llm_analysis:
                    llm_analysis = await self._generate_correction_guidance(validation_result_data)

                # Build workflow trace for transparency and reproducibility
                workflow_trace = self._build_workflow_trace(state)

                self._report_service.generate_json_report(
                    report_path,
                    validation_result_data,
                    llm_analysis,
                    workflow_trace
                )

                state.add_log(
                    LogLevel.INFO,
                    f"Generated JSON correction report: {report_path}",
                    {"report_path": str(report_path), "status": overall_status},
                )

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "report_path": str(report_path),
                        "report_type": "json",
                    },
                )

        except Exception as e:
            error_msg = f"Report generation failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"exception": str(e)},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="REPORT_GENERATION_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    def _build_workflow_trace(self, state: GlobalState) -> Dict[str, Any]:
        """
        Build a comprehensive workflow trace from the state for transparency and reproducibility.

        Args:
            state: The global state containing logs and workflow information

        Returns:
            Dictionary containing complete workflow trace
        """
        from datetime import datetime, timedelta

        # Calculate duration
        start_time = None
        end_time = datetime.now()
        if state.logs:
            start_time = state.logs[0].timestamp
            duration_seconds = (end_time - start_time).total_seconds()
            duration = f"{duration_seconds:.2f} seconds"
        else:
            duration = "N/A"

        # Build summary
        summary = {
            'start_time': start_time.isoformat() if start_time else 'N/A',
            'end_time': end_time.isoformat(),
            'duration': duration,
            'input_format': state.metadata.get('detected_format', 'Unknown'),
        }

        # Technologies used
        technologies = [
            "NWB (Neurodata Without Borders) 2.0+ Standard",
            "NeuroConv - Unified conversion framework",
            "NWB Inspector - Validation tool",
            "SpikeInterface - Electrophysiology data processing",
            "PyNWB - Python NWB API",
            "HDF5 - Hierarchical data format",
            "Claude AI (Anthropic) - Metadata assistance and quality assessment",
            "FastAPI - Backend API framework",
            "Python 3.14 - Programming language",
        ]

        # Build workflow steps from logs
        steps = []
        step_mapping = {
            'detecting_format': {
                'name': 'Format Detection',
                'description': 'Automatically detected the input data format using intelligent pattern matching',
            },
            'awaiting_user_input': {
                'name': 'Metadata Collection',
                'description': 'Collected required NWB metadata from user with AI-assisted suggestions',
            },
            'converting': {
                'name': 'Data Conversion',
                'description': 'Converted electrophysiology data to NWB format using NeuroConv',
            },
            'validating': {
                'name': 'Validation',
                'description': 'Validated NWB file against standards using NWB Inspector',
            },
            'completed': {
                'name': 'Completion',
                'description': 'Conversion and validation completed successfully',
            },
        }

        # Extract steps from logs
        seen_statuses = set()
        for log in state.logs:
            if log.level == LogLevel.INFO and 'Status changed to' in log.message:
                status = log.context.get('status', '')
                if status and status not in seen_statuses:
                    seen_statuses.add(status)
                    step_info = step_mapping.get(status, {
                        'name': status.replace('_', ' ').title(),
                        'description': f'Pipeline stage: {status}',
                    })
                    steps.append({
                        'name': step_info['name'],
                        'status': 'completed',
                        'description': step_info['description'],
                        'timestamp': log.timestamp.isoformat(),
                    })

        # Data provenance
        provenance = {
            'original_file': state.input_path or 'N/A',
            'conversion_method': 'NeuroConv with AI-assisted metadata collection',
            'metadata_sources': [
                'User-provided metadata',
                'File header extraction',
                'AI-assisted inference',
            ],
            'agent_versions': 'Multi-agent system: ConversationAgent, ConversionAgent, EvaluationAgent',
        }

        # User interactions
        user_interactions = []
        for log in state.logs:
            if 'chat' in log.message.lower() or 'user' in log.message.lower():
                user_interactions.append({
                    'timestamp': log.timestamp.isoformat(),
                    'action': log.message,
                })

        # Include metadata_provenance from state for HTML report
        # This preserves original provenance (AI-parsed, user-specified, etc.)
        # without storing it in the NWB file (which would violate DANDI compliance)
        metadata_provenance_dict = {}
        if state.metadata_provenance:
            for field_name, prov_info in state.metadata_provenance.items():
                metadata_provenance_dict[field_name] = {
                    'provenance': prov_info.provenance.value,
                    'confidence': prov_info.confidence,
                    'source': prov_info.source,
                    'timestamp': prov_info.timestamp.isoformat(),
                }

        return {
            'summary': summary,
            'technologies': technologies,
            'steps': steps,
            'provenance': provenance,
            'user_interactions': user_interactions if user_interactions else None,
            'metadata_provenance': metadata_provenance_dict,
        }

    def _add_metadata_provenance(
        self,
        file_info: Dict[str, Any],
        state: GlobalState
    ) -> Dict[str, Any]:
        """
        Add provenance information to metadata fields for transparency and reproducibility.

        Tracks the source of each metadata value with 6 provenance types:
        - user-specified: User directly provided value
        - file-extracted: Automatically extracted from file headers (includes source filename)
        - ai-parsed: AI parsed from unstructured text with high confidence
        - ai-inferred: AI inferred from available context
        - schema-default: NWB schema default value
        - system-default: System fallback value (N/A or Unknown)

        Args:
            file_info: Dictionary of metadata extracted from NWB file
            state: Global state containing metadata provenance tracking

        Returns:
            Dictionary with provenance information added for each field
        """
        # Get provenance tracking from state metadata (if available)
        metadata_provenance = state.metadata.get('_provenance', {})

        # Get source file information from state
        source_files = state.metadata.get('_source_files', {})
        primary_source_file = state.metadata.get('primary_data_file', '')

        # Create a copy with provenance information
        file_info_with_prov = dict(file_info)

        # Define which fields to track provenance for
        tracked_fields = [
            'experimenter', 'institution', 'lab', 'session_description',
            'experiment_description', 'session_id', 'subject_id', 'species',
            'sex', 'age', 'description', 'genotype', 'strain', 'date_of_birth',
            'weight', 'keywords', 'pharmacology', 'protocol',
            'surgery', 'virus', 'stimulus_notes', 'data_collection'
        ]

        # Add provenance dict if not exists
        if '_provenance' not in file_info_with_prov:
            file_info_with_prov['_provenance'] = {}

        if '_source_files' not in file_info_with_prov:
            file_info_with_prov['_source_files'] = {}

        for field in tracked_fields:
            value = file_info.get(field)
            provenance_info = {}

            # Determine provenance source using complete 6-tag system
            if field in metadata_provenance:
                # Use tracked provenance from metadata collection
                prov_type = metadata_provenance[field]

                # Map old provenance types to new system
                if prov_type == 'user-provided':
                    provenance_info['type'] = 'user-specified'
                elif prov_type == 'ai-parsed':
                    provenance_info['type'] = 'ai-parsed'
                elif prov_type == 'ai-inferred':
                    provenance_info['type'] = 'ai-inferred'
                elif prov_type == 'file-extracted':
                    provenance_info['type'] = 'file-extracted'
                    # Add source filename if available
                    if field in source_files:
                        provenance_info['source_file'] = source_files[field]
                    elif primary_source_file:
                        provenance_info['source_file'] = os.path.basename(primary_source_file)
                elif prov_type == 'default':
                    # Distinguish between schema defaults and system defaults
                    if value in ['N/A', 'Unknown', 'Not specified', '']:
                        provenance_info['type'] = 'system-default'
                    else:
                        provenance_info['type'] = 'schema-default'
                else:
                    provenance_info['type'] = prov_type

            elif value and value not in ['N/A', 'Unknown', 'Not specified', [], '', None]:
                # Has a real value but no tracking
                # Check if it matches NWB schema defaults
                nwb_defaults = {
                    'species': 'Mus musculus',
                    'genotype': 'Wild-type',
                    'strain': 'C57BL/6J'
                }

                if field in nwb_defaults and value == nwb_defaults[field]:
                    provenance_info['type'] = 'schema-default'
                else:
                    # Assume file-extracted with primary source file
                    provenance_info['type'] = 'file-extracted'
                    if primary_source_file:
                        provenance_info['source_file'] = os.path.basename(primary_source_file)
            else:
                # System default value
                provenance_info['type'] = 'system-default'

            # Store provenance information
            file_info_with_prov['_provenance'][field] = provenance_info['type']

            # Store source file information if available
            if 'source_file' in provenance_info:
                file_info_with_prov['_source_files'][field] = provenance_info['source_file']

        state.add_log(
            LogLevel.DEBUG,
            f"Added metadata provenance for {len(file_info_with_prov['_provenance'])} fields with 6-tag system",
        )

        return file_info_with_prov

    async def _generate_quality_assessment(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate LLM-powered quality assessment for PASSED/PASSED_WITH_ISSUES files.

        Implements Story 9.3: LLM Report Generation
        """
        if not self._llm_service:
            return None

        # Create prompt using template
        prompt_data = self._prompt_service.create_llm_prompt(
            'evaluation_passed',
            {
                'file_info': validation_result.get('file_info', {}),
                'overall_status': validation_result.get('overall_status', 'UNKNOWN'),
                'issues': validation_result.get('issues', []),
                'issue_counts': validation_result.get('issue_counts', {}),
            }
        )

        # Call LLM with structured output
        result = await self._llm_service.generate_structured_output(
            prompt=prompt_data['prompt'],
            output_schema=prompt_data['output_schema'],
            system_prompt=prompt_data['system_role'],
        )

        return result

    async def _generate_correction_guidance(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate LLM-powered correction guidance for FAILED files.

        Implements Story 9.4: LLM Correction Analysis
        """
        if not self._llm_service:
            return None

        # Create prompt using template
        prompt_data = self._prompt_service.create_llm_prompt(
            'evaluation_failed',
            {
                'nwb_file_path': validation_result.get('nwb_file_path', 'unknown'),
                'issues': validation_result.get('issues', []),
                'issue_counts': validation_result.get('issue_counts', {}),
                'input_metadata': {},  # Could be passed from context
                'conversion_parameters': {},  # Could be passed from context
            }
        )

        # Call LLM with structured output
        result = await self._llm_service.generate_structured_output(
            prompt=prompt_data['prompt'],
            output_schema=prompt_data['output_schema'],
            system_prompt=prompt_data['system_role'],
        )

        return result


def register_evaluation_agent(
    mcp_server,
    llm_service: Optional[LLMService] = None,
) -> EvaluationAgent:
    """
    Register Evaluation Agent handlers with MCP server.

    Args:
        mcp_server: MCP server instance
        llm_service: Optional LLM service for correction analysis

    Returns:
        EvaluationAgent instance
    """
    agent = EvaluationAgent(llm_service=llm_service)

    mcp_server.register_handler(
        "evaluation",
        "run_validation",
        agent.handle_run_validation,
    )

    mcp_server.register_handler(
        "evaluation",
        "analyze_corrections",
        agent.handle_analyze_corrections,
    )

    mcp_server.register_handler(
        "evaluation",
        "generate_report",
        agent.handle_generate_report,
    )

    return agent
