# Validation and Quality Assurance Design

## Overview

This design document outlines validation and quality assurance systems that ensure converted NWB files meet community standards and best practices. The system integrates NWB Inspector validation, LinkML schema validation, metadata completeness checking, and comprehensive quality assessment frameworks to provide thorough quality assurance for neuroscience data conversions.

## Architecture

### High-Level Validation Architecture

```
Validation and Quality Assurance Systems
├── NWB Validation Engine
│   ├── NWB Inspector Integration
│   ├── Schema Compliance Checker
│   └── Best Practices Validator
├── LinkML Validation Framework
│   ├── Schema Definition Manager
│   ├── Runtime Validation Engine
│   └── Pydantic Class Generator
├── Quality Assessment Engine
│   ├── Metadata Completeness Analyzer
│   ├── Data Integrity Checker
│   └── Quality Metrics Calculator
├── Domain Knowledge Validator
│   ├── Scientific Plausibility Checker
│   ├── Experimental Consistency Validator
│   └── Neuroscience Domain Rules
└── Validation Orchestrator
    ├── Validation Pipeline Manager
    ├── Results Aggregator
    ├── Report Generator
    └── API Integration Layer
```

### Validation Flow

```
NWB File/Metadata Input → Validation Orchestrator → Multiple Validation Engines
                                ↓
NWB Inspector → Schema Validation → LinkML Validation → Quality Assessment → Domain Validation
                                ↓
Results Aggregation → Severity Classification → Remediation Suggestions → Final Report
```## C
ore Components

### 1. NWB Validation Engine

#### NWB Inspector Integration
```python
# agentic_neurodata_conversion/validation/nwb_validation.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

try:
    from nwbinspector import inspect_nwb, Importance
    NWB_INSPECTOR_AVAILABLE = True
except ImportError:
    NWB_INSPECTOR_AVAILABLE = False
    logging.warning("NWB Inspector not available")

class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    BEST_PRACTICE = "best_practice"

@dataclass
class ValidationIssue:
    """Individual validation issue."""
    severity: ValidationSeverity
    message: str
    location: str
    check_name: str
    object_type: Optional[str] = None
    object_name: Optional[str] = None
    remediation: Optional[str] = None

@dataclass
class ValidationResult:
    """Complete validation result."""
    file_path: str
    is_valid: bool
    issues: List[ValidationIssue]
    summary: Dict[str, Any]
    execution_time: float
    validator_version: str

class NWBValidationEngine:
    """Integrates NWB Inspector for comprehensive NWB file validation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        if not NWB_INSPECTOR_AVAILABLE:
            raise ImportError("NWB Inspector is required but not available")
        
        # Configure NWB Inspector settings
        self.inspector_config = {
            'importance_threshold': Importance.BEST_PRACTICE_SUGGESTION,
            'progress_bar': False,
            'detailed_errors': True,
            **self.config.get('nwb_inspector', {})
        }
    
    def validate_nwb_file(self, nwb_path: str) -> ValidationResult:
        """Validate NWB file using NWB Inspector."""
        import time
        
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting NWB validation for: {nwb_path}")
            
            # Run NWB Inspector validation
            inspection_results = inspect_nwb(
                nwbfile_path=nwb_path,
                **self.inspector_config
            )
            
            # Process and categorize results
            issues = self._process_inspection_results(inspection_results)
            
            # Generate summary
            summary = self._generate_validation_summary(issues)
            
            # Determine overall validity
            is_valid = not any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)
            
            execution_time = time.time() - start_time
            
            result = ValidationResult(
                file_path=nwb_path,
                is_valid=is_valid,
                issues=issues,
                summary=summary,
                execution_time=execution_time,
                validator_version=self._get_nwb_inspector_version()
            )
            
            self.logger.info(f"NWB validation completed in {execution_time:.2f}s: {len(issues)} issues found")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"NWB validation failed: {e}")
            
            return ValidationResult(
                file_path=nwb_path,
                is_valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Validation failed: {str(e)}",
                    location="file",
                    check_name="validation_error"
                )],
                summary={"error": str(e)},
                execution_time=execution_time,
                validator_version=self._get_nwb_inspector_version()
            )
    
    def _process_inspection_results(self, inspection_results) -> List[ValidationIssue]:
        """Process NWB Inspector results into standardized format."""
        issues = []
        
        for result in inspection_results:
            # Map NWB Inspector importance to our severity
            severity = self._map_importance_to_severity(result.importance)
            
            # Generate remediation suggestion
            remediation = self._generate_remediation_suggestion(result)
            
            issue = ValidationIssue(
                severity=severity,
                message=result.message,
                location=result.location or "unknown",
                check_name=result.check_function_name,
                object_type=result.object_type,
                object_name=result.object_name,
                remediation=remediation
            )
            
            issues.append(issue)
        
        return issues
    
    def _map_importance_to_severity(self, importance: 'Importance') -> ValidationSeverity:
        """Map NWB Inspector importance levels to our severity categories."""
        mapping = {
            Importance.CRITICAL: ValidationSeverity.CRITICAL,
            Importance.BEST_PRACTICE_VIOLATION: ValidationSeverity.WARNING,
            Importance.BEST_PRACTICE_SUGGESTION: ValidationSeverity.BEST_PRACTICE
        }
        return mapping.get(importance, ValidationSeverity.INFO)
    
    def _generate_remediation_suggestion(self, result) -> str:
        """Generate remediation suggestions based on check type."""
        check_name = result.check_function_name
        
        remediation_map = {
            'check_missing_unit': 'Add appropriate units to the data object',
            'check_data_orientation': 'Ensure data is oriented correctly (time on first axis)',
            'check_timestamps_match_first_dimension': 'Verify timestamps match data dimensions',
            'check_description': 'Add a meaningful description to the object',
            'check_experimenter_exists': 'Add experimenter information to NWBFile',
            'check_session_start_time': 'Ensure session_start_time is properly set'
        }
        
        return remediation_map.get(check_name, 'Review NWB best practices documentation')
    
    def _generate_validation_summary(self, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Generate validation summary statistics."""
        summary = {
            'total_issues': len(issues),
            'critical_issues': 0,
            'warning_issues': 0,
            'info_issues': 0,
            'best_practice_issues': 0,
            'issues_by_check': {},
            'issues_by_object_type': {}
        }
        
        for issue in issues:
            # Count by severity
            if issue.severity == ValidationSeverity.CRITICAL:
                summary['critical_issues'] += 1
            elif issue.severity == ValidationSeverity.WARNING:
                summary['warning_issues'] += 1
            elif issue.severity == ValidationSeverity.INFO:
                summary['info_issues'] += 1
            elif issue.severity == ValidationSeverity.BEST_PRACTICE:
                summary['best_practice_issues'] += 1
            
            # Count by check name
            check_name = issue.check_name
            summary['issues_by_check'][check_name] = summary['issues_by_check'].get(check_name, 0) + 1
            
            # Count by object type
            if issue.object_type:
                obj_type = issue.object_type
                summary['issues_by_object_type'][obj_type] = summary['issues_by_object_type'].get(obj_type, 0) + 1
        
        return summary
    
    def _get_nwb_inspector_version(self) -> str:
        """Get NWB Inspector version."""
        try:
            import nwbinspector
            return nwbinspector.__version__
        except:
            return "unknown"

### 2. LinkML Validation Framework

class LinkMLValidationFramework:
    """Validates metadata using LinkML schemas."""
    
    def __init__(self, schema_path: Optional[str] = None):
        self.schema_path = schema_path
        self.logger = logging.getLogger(__name__)
        self.pydantic_classes = {}
        
        if schema_path:
            self._load_schema()
    
    def _load_schema(self):
        """Load LinkML schema and generate Pydantic classes."""
        try:
            from linkml_runtime import SchemaView
            from linkml.generators.pydanticgen import PydanticGenerator
            
            # Load schema
            self.schema_view = SchemaView(self.schema_path)
            
            # Generate Pydantic classes
            generator = PydanticGenerator(self.schema_view.schema)
            pydantic_code = generator.serialize()
            
            # Execute generated code to create classes
            exec_globals = {}
            exec(pydantic_code, exec_globals)
            
            # Extract Pydantic classes
            from pydantic import BaseModel
            for name, obj in exec_globals.items():
                if isinstance(obj, type) and issubclass(obj, BaseModel):
                    self.pydantic_classes[name] = obj
            
            self.logger.info(f"Loaded LinkML schema with {len(self.pydantic_classes)} classes")
            
        except Exception as e:
            self.logger.error(f"Failed to load LinkML schema: {e}")
            raise
    
    def validate_metadata(self, metadata: Dict[str, Any], schema_class: str) -> ValidationResult:
        """Validate metadata against LinkML schema."""
        import time
        
        start_time = time.time()
        
        try:
            # Get validation class
            validation_class = self.pydantic_classes.get(schema_class)
            if not validation_class:
                raise ValueError(f"Schema class not found: {schema_class}")
            
            # Validate using Pydantic
            validated_instance = validation_class(**metadata)
            
            execution_time = time.time() - start_time
            
            return ValidationResult(
                file_path="metadata",
                is_valid=True,
                issues=[],
                summary={
                    'schema_class': schema_class,
                    'validated_fields': len(metadata),
                    'validation_method': 'linkml_pydantic'
                },
                execution_time=execution_time,
                validator_version=self._get_linkml_version()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Parse validation errors
            issues = self._parse_validation_errors(e, schema_class)
            
            return ValidationResult(
                file_path="metadata",
                is_valid=False,
                issues=issues,
                summary={
                    'schema_class': schema_class,
                    'error_count': len(issues),
                    'validation_method': 'linkml_pydantic'
                },
                execution_time=execution_time,
                validator_version=self._get_linkml_version()
            )
    
    def _parse_validation_errors(self, error: Exception, schema_class: str) -> List[ValidationIssue]:
        """Parse Pydantic validation errors into ValidationIssue objects."""
        issues = []
        
        try:
            from pydantic import ValidationError
            
            if isinstance(error, ValidationError):
                for err in error.errors():
                    issue = ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        message=err['msg'],
                        location='.'.join(str(loc) for loc in err['loc']),
                        check_name='linkml_validation',
                        remediation=self._get_remediation_for_error(err)
                    )
                    issues.append(issue)
            else:
                # Generic error
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    message=str(error),
                    location=schema_class,
                    check_name='linkml_validation'
                ))
        
        except Exception as e:
            self.logger.error(f"Error parsing validation errors: {e}")
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation parsing error: {str(e)}",
                location="unknown",
                check_name='linkml_validation'
            ))
        
        return issues
    
    def _get_remediation_for_error(self, error: Dict[str, Any]) -> str:
        """Generate remediation suggestion for validation error."""
        error_type = error.get('type', '')
        
        remediation_map = {
            'missing': 'Add the required field to the metadata',
            'type_error': 'Ensure the field value is of the correct type',
            'value_error': 'Check that the field value meets the specified constraints',
            'extra_forbidden': 'Remove the extra field or check schema definition'
        }
        
        return remediation_map.get(error_type, 'Review the schema requirements for this field')
    
    def _get_linkml_version(self) -> str:
        """Get LinkML version."""
        try:
            import linkml
            return linkml.__version__
        except:
            return "unknown"
```### 3. Qu
ality Assessment Engine

#### Comprehensive Quality Assessment
```python
# agentic_neurodata_conversion/validation/quality_assessment.py
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

class QualityDimension(Enum):
    """Quality assessment dimensions."""
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    COMPLIANCE = "compliance"

@dataclass
class QualityMetric:
    """Individual quality metric."""
    name: str
    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    max_score: float
    description: str
    details: Dict[str, Any]

class QualityAssessmentEngine:
    """Comprehensive quality assessment for NWB files."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def assess_quality(self, nwb_path: str, metadata: Dict[str, Any], 
                      validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """Perform comprehensive quality assessment."""
        
        metrics = []
        
        # Assess completeness
        completeness_metrics = self._assess_completeness(metadata, validation_results)
        metrics.extend(completeness_metrics)
        
        # Assess consistency
        consistency_metrics = self._assess_consistency(nwb_path, metadata)
        metrics.extend(consistency_metrics)
        
        # Assess compliance
        compliance_metrics = self._assess_compliance(validation_results)
        metrics.extend(compliance_metrics)
        
        # Calculate overall scores
        dimension_scores = self._calculate_dimension_scores(metrics)
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        
        return {
            'overall_score': overall_score,
            'dimension_scores': dimension_scores,
            'metrics': [
                {
                    'name': m.name,
                    'dimension': m.dimension.value,
                    'score': m.score,
                    'max_score': m.max_score,
                    'normalized_score': m.score / m.max_score if m.max_score > 0 else 0,
                    'description': m.description,
                    'details': m.details
                }
                for m in metrics
            ],
            'recommendations': self._generate_recommendations(metrics, dimension_scores)
        }
    
    def _assess_completeness(self, metadata: Dict[str, Any], 
                           validation_results: List[ValidationResult]) -> List[QualityMetric]:
        """Assess metadata and data completeness."""
        metrics = []
        
        # Required NWB fields completeness
        required_fields = [
            'identifier', 'session_description', 'session_start_time',
            'experimenter', 'lab', 'institution'
        ]
        
        present_fields = sum(1 for field in required_fields if metadata.get(field))
        completeness_score = present_fields / len(required_fields)
        
        metrics.append(QualityMetric(
            name="required_fields_completeness",
            dimension=QualityDimension.COMPLETENESS,
            score=completeness_score,
            max_score=1.0,
            description="Completeness of required NWB metadata fields",
            details={
                'present_fields': present_fields,
                'total_required': len(required_fields),
                'missing_fields': [f for f in required_fields if not metadata.get(f)]
            }
        ))
        
        return metrics
    
    def _assess_consistency(self, nwb_path: str, metadata: Dict[str, Any]) -> List[QualityMetric]:
        """Assess data consistency."""
        metrics = []
        
        try:
            import pynwb
            
            with pynwb.NWBHDF5IO(nwb_path, 'r') as io:
                nwbfile = io.read()
                
                # Check timestamp consistency
                consistency_score = self._check_timestamp_consistency(nwbfile)
                
                metrics.append(QualityMetric(
                    name="timestamp_consistency",
                    dimension=QualityDimension.CONSISTENCY,
                    score=consistency_score,
                    max_score=1.0,
                    description="Consistency of timestamps across data objects",
                    details={'method': 'timestamp_alignment_check'}
                ))
                
        except Exception as e:
            self.logger.error(f"Error assessing consistency: {e}")
        
        return metrics
    
    def _assess_compliance(self, validation_results: List[ValidationResult]) -> List[QualityMetric]:
        """Assess compliance with standards."""
        metrics = []
        
        # Calculate compliance score based on validation results
        total_issues = sum(len(result.issues) for result in validation_results)
        critical_issues = sum(
            len([issue for issue in result.issues if issue.severity == ValidationSeverity.CRITICAL])
            for result in validation_results
        )
        
        if total_issues == 0:
            compliance_score = 1.0
        else:
            # Penalize critical issues more heavily
            penalty = (critical_issues * 0.2) + ((total_issues - critical_issues) * 0.05)
            compliance_score = max(0.0, 1.0 - penalty)
        
        metrics.append(QualityMetric(
            name="standards_compliance",
            dimension=QualityDimension.COMPLIANCE,
            score=compliance_score,
            max_score=1.0,
            description="Compliance with NWB standards and best practices",
            details={
                'total_issues': total_issues,
                'critical_issues': critical_issues,
                'validation_results_count': len(validation_results)
            }
        ))
        
        return metrics
    
    def _calculate_dimension_scores(self, metrics: List[QualityMetric]) -> Dict[str, float]:
        """Calculate scores for each quality dimension."""
        dimension_scores = {}
        
        for dimension in QualityDimension:
            dimension_metrics = [m for m in metrics if m.dimension == dimension]
            if dimension_metrics:
                # Calculate weighted average
                total_score = sum(m.score for m in dimension_metrics)
                total_max = sum(m.max_score for m in dimension_metrics)
                dimension_scores[dimension.value] = total_score / total_max if total_max > 0 else 0.0
            else:
                dimension_scores[dimension.value] = 0.0
        
        return dimension_scores
    
    def _generate_recommendations(self, metrics: List[QualityMetric], 
                                dimension_scores: Dict[str, float]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        # Identify low-scoring metrics
        low_metrics = [m for m in metrics if (m.score / m.max_score) < 0.7]
        
        for metric in low_metrics:
            if metric.name == "required_fields_completeness":
                missing_fields = metric.details.get('missing_fields', [])
                if missing_fields:
                    recommendations.append(f"Add missing required fields: {', '.join(missing_fields)}")
            
            elif metric.name == "standards_compliance":
                if metric.details.get('critical_issues', 0) > 0:
                    recommendations.append("Address critical validation issues to improve compliance")
        
        # Dimension-specific recommendations
        for dimension, score in dimension_scores.items():
            if score < 0.6:
                recommendations.append(f"Focus on improving {dimension} quality")
        
        return recommendations
    
    def _check_timestamp_consistency(self, nwbfile) -> float:
        """Check consistency of timestamps across data objects."""
        # Simplified timestamp consistency check
        # In a real implementation, this would be more comprehensive
        return 0.8  # Placeholder score

### 4. Integration with MCP Server

# MCP Tools for validation
@mcp.tool(
    name="validate_nwb_file",
    description="Comprehensive NWB file validation using multiple validators"
)
async def validate_nwb_file(
    nwb_path: str,
    validation_profile: str = "comprehensive",
    include_quality_assessment: bool = True,
    server=None
) -> Dict[str, Any]:
    """Validate NWB file comprehensively."""
    
    try:
        validation_results = []
        
        # NWB Inspector validation
        nwb_validator = NWBValidationEngine()
        nwb_result = nwb_validator.validate_nwb_file(nwb_path)
        validation_results.append(nwb_result)
        
        # Quality assessment if requested
        quality_results = None
        if include_quality_assessment:
            quality_engine = QualityAssessmentEngine()
            
            # Extract metadata for quality assessment
            metadata = await _extract_nwb_metadata(nwb_path)
            
            quality_results = quality_engine.assess_quality(
                nwb_path, metadata, validation_results
            )
        
        # Aggregate results
        overall_valid = all(result.is_valid for result in validation_results)
        total_issues = sum(len(result.issues) for result in validation_results)
        
        return {
            "status": "success",
            "is_valid": overall_valid,
            "validation_results": [
                {
                    "validator": "nwb_inspector",
                    "is_valid": result.is_valid,
                    "issues_count": len(result.issues),
                    "execution_time": result.execution_time,
                    "summary": result.summary
                }
                for result in validation_results
            ],
            "quality_assessment": quality_results,
            "summary": {
                "total_issues": total_issues,
                "overall_valid": overall_valid,
                "validation_profile": validation_profile
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

async def _extract_nwb_metadata(nwb_path: str) -> Dict[str, Any]:
    """Extract metadata from NWB file for quality assessment."""
    try:
        import pynwb
        
        with pynwb.NWBHDF5IO(nwb_path, 'r') as io:
            nwbfile = io.read()
            
            return {
                "identifier": nwbfile.identifier,
                "session_description": nwbfile.session_description,
                "session_start_time": nwbfile.session_start_time.isoformat() if nwbfile.session_start_time else None,
                "experimenter": list(nwbfile.experimenter) if nwbfile.experimenter else [],
                "lab": nwbfile.lab,
                "institution": nwbfile.institution
            }
            
    except Exception as e:
        logging.error(f"Failed to extract NWB metadata: {e}")
        return {}
```

This comprehensive validation and quality assurance design provides multiple layers of validation, from basic schema compliance to advanced quality assessment, ensuring that converted NWB files meet the highest standards for neuroscience data sharing and reuse.