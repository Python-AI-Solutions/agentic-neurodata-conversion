# Validation and Quality Assurance Design

## Overview

This design document outlines a comprehensive, modular validation and quality assurance system for NWB (Neurodata Without Borders) file conversions. The system is architected with clear separation of concerns, enhanced traceability, and granular modularity to facilitate development, testing, debugging, and maintenance using Claude Code.

## System Architecture

### High-Level Modular Architecture

```
Validation and Quality Assurance System
├── Module 1: Core Validation Framework
│   ├── base.py - Base validation infrastructure
│   ├── config.py - Configuration management
│   └── exceptions.py - Error handling and logging
├── Module 2: NWB Inspector Integration
│   ├── inspector.py - NWB Inspector engine
│   ├── schema.py - Schema compliance validation
│   └── best_practices.py - Best practices validation
├── Module 3: LinkML Schema Validation
│   ├── schema_manager.py - Schema definition management
│   ├── validator.py - Runtime validation engine
│   └── vocabulary.py - Controlled vocabulary validation
├── Module 4: Quality Assessment Engine
│   ├── metrics.py - Quality metrics framework
│   ├── completeness.py - Completeness analysis
│   └── integrity.py - Data integrity validation
├── Module 5: Domain Knowledge Validator
│   ├── plausibility.py - Scientific plausibility checker
│   ├── consistency.py - Experimental consistency validation
│   └── rules.py - Neuroscience domain rules
├── Module 6: Validation Orchestrator
│   ├── pipeline.py - Pipeline management
│   ├── aggregator.py - Results aggregation
│   └── optimizer.py - Workflow optimization
├── Module 7: Reporting and Analytics
│   ├── generator.py - Report generation
│   ├── analytics.py - Analytics and trends
│   └── dashboard.py - Interactive dashboards
└── Module 8: MCP Integration Layer
    ├── tools.py - MCP tools interface
    ├── service.py - Service integration
    └── scaling.py - Performance and scalability
```

## Module-by-Module Design

### Module 1: Core Validation Framework

**Purpose:** Provides the foundational infrastructure for all validation operations with standardized interfaces and shared utilities.

#### 1.1 Base Validation Infrastructure (`core/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union
import uuid

class ValidationSeverity(Enum):
    """Standardized validation issue severity levels."""
    CRITICAL = "critical"          # Prevents file usage
    WARNING = "warning"            # Significant issues requiring attention
    INFO = "info"                  # Informational messages
    BEST_PRACTICE = "best_practice" # Recommendations for improvement

class ValidationStatus(Enum):
    """Validation execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ValidationIssue:
    """Individual validation issue with complete context."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    severity: ValidationSeverity
    message: str
    location: str                    # Path or location in file/data
    check_name: str                  # Name of the validation check
    validator_name: str              # Name of the validator that found the issue
    object_type: Optional[str] = None
    object_name: Optional[str] = None
    remediation: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ValidationContext:
    """Context information for validation operations."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ValidationResult:
    """Complete validation result with metadata and traceability."""
    validator_name: str
    validation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: ValidationContext
    status: ValidationStatus
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    execution_time: float = 0.0
    validator_version: str = "unknown"
    completed_at: Optional[datetime] = None

class BaseValidator(ABC):
    """Abstract base class for all validators with standardized interface."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.version = self._get_version()

    @abstractmethod
    def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Perform validation and return results."""
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return validator capabilities and supported features."""
        pass

    def _get_version(self) -> str:
        """Get validator version."""
        return getattr(self, "__version__", "unknown")

    def _create_result(self, context: ValidationContext, is_valid: bool,
                      issues: List[ValidationIssue], **kwargs) -> ValidationResult:
        """Create standardized validation result."""
        return ValidationResult(
            validator_name=self.name,
            context=context,
            status=ValidationStatus.COMPLETED,
            is_valid=is_valid,
            issues=issues,
            validator_version=self.version,
            completed_at=datetime.utcnow(),
            **kwargs
        )

class ValidationRegistry:
    """Registry for discovering and managing validators."""

    def __init__(self):
        self._validators: Dict[str, type] = {}

    def register(self, validator_class: type, name: Optional[str] = None):
        """Register a validator class."""
        name = name or validator_class.__name__
        self._validators[name] = validator_class

    def get_validator(self, name: str, config: Optional[Dict[str, Any]] = None) -> BaseValidator:
        """Get validator instance by name."""
        if name not in self._validators:
            raise ValueError(f"Validator {name} not found")
        return self._validators[name](name, config)

    def list_validators(self) -> List[str]:
        """List all registered validators."""
        return list(self._validators.keys())

# Global registry instance
validator_registry = ValidationRegistry()
```

#### 1.2 Configuration Management (`core/config.py`)

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import yaml
import os
from enum import Enum

class Environment(Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class ValidationProfile:
    """Validation profile configuration."""
    name: str
    description: str
    enabled_validators: List[str]
    severity_threshold: ValidationSeverity
    configuration: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationConfig:
    """Complete validation system configuration."""
    environment: Environment = Environment.DEVELOPMENT
    profiles: Dict[str, ValidationProfile] = field(default_factory=dict)
    default_profile: str = "standard"

    # Global settings
    max_parallel_validations: int = 4
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    log_level: str = "INFO"

    # Performance settings
    memory_limit_mb: int = 2048
    timeout_seconds: int = 300
    chunk_size_mb: int = 100

    # Reporting settings
    report_formats: List[str] = field(default_factory=lambda: ["json", "html"])
    enable_analytics: bool = True

    # Security settings
    enable_audit_logging: bool = True
    sanitize_sensitive_data: bool = True

class ConfigManager:
    """Manages validation configuration with environment support."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else self._get_default_config_path()
        self._config: Optional[ValidationConfig] = None
        self._watchers: List[callable] = []

    def load_config(self) -> ValidationConfig:
        """Load configuration from file with environment override."""
        if not self.config_path.exists():
            self._config = self._create_default_config()
            self.save_config(self._config)
        else:
            self._config = self._load_from_file()

        # Apply environment-specific overrides
        self._apply_environment_overrides()

        return self._config

    def save_config(self, config: ValidationConfig):
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            if self.config_path.suffix == '.yaml':
                yaml.dump(config.__dict__, f, default_flow_style=False)
            else:
                json.dump(config.__dict__, f, indent=2, default=str)

    def get_profile(self, profile_name: Optional[str] = None) -> ValidationProfile:
        """Get validation profile by name."""
        if not self._config:
            self.load_config()

        profile_name = profile_name or self._config.default_profile

        if profile_name not in self._config.profiles:
            raise ValueError(f"Profile {profile_name} not found")

        return self._config.profiles[profile_name]

    def update_config(self, updates: Dict[str, Any]):
        """Update configuration and notify watchers."""
        if not self._config:
            self.load_config()

        for key, value in updates.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

        self.save_config(self._config)
        self._notify_watchers()

    def add_watcher(self, callback: callable):
        """Add configuration change watcher."""
        self._watchers.append(callback)

    def _create_default_config(self) -> ValidationConfig:
        """Create default configuration."""
        config = ValidationConfig()

        # Standard profile
        config.profiles["standard"] = ValidationProfile(
            name="standard",
            description="Standard validation with all checks enabled",
            enabled_validators=["nwb_inspector", "linkml", "quality_assessment"],
            severity_threshold=ValidationSeverity.WARNING
        )

        # Quick profile
        config.profiles["quick"] = ValidationProfile(
            name="quick",
            description="Quick validation with only critical checks",
            enabled_validators=["nwb_inspector"],
            severity_threshold=ValidationSeverity.CRITICAL
        )

        # Comprehensive profile
        config.profiles["comprehensive"] = ValidationProfile(
            name="comprehensive",
            description="Comprehensive validation with all checks and domain validation",
            enabled_validators=["nwb_inspector", "linkml", "quality_assessment", "domain_validator"],
            severity_threshold=ValidationSeverity.INFO
        )

        return config

    def _load_from_file(self) -> ValidationConfig:
        """Load configuration from file."""
        with open(self.config_path, 'r') as f:
            if self.config_path.suffix == '.yaml':
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        # Convert to ValidationConfig instance
        # (Implementation would include proper deserialization)
        return ValidationConfig(**data)

    def _apply_environment_overrides(self):
        """Apply environment-specific configuration overrides."""
        env = os.getenv('VALIDATION_ENV', 'development')

        if env == 'production':
            self._config.log_level = "WARNING"
            self._config.enable_audit_logging = True
        elif env == 'testing':
            self._config.cache_enabled = False
            self._config.log_level = "DEBUG"

    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        return Path.home() / ".agentic_neurodata_conversion" / "validation_config.yaml"

    def _notify_watchers(self):
        """Notify configuration change watchers."""
        for watcher in self._watchers:
            try:
                watcher(self._config)
            except Exception as e:
                # Log error but don't fail
                print(f"Configuration watcher failed: {e}")
```

#### 1.3 Error Handling and Logging (`core/exceptions.py`)

```python
import logging
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import json

class ValidationError(Exception):
    """Base exception for validation errors."""
    pass

class ConfigurationError(ValidationError):
    """Configuration-related errors."""
    pass

class ValidatorNotFoundError(ValidationError):
    """Validator not found in registry."""
    pass

class ValidationTimeoutError(ValidationError):
    """Validation operation timed out."""
    pass

class SchemaError(ValidationError):
    """Schema-related validation errors."""
    pass

class DataIntegrityError(ValidationError):
    """Data integrity validation errors."""
    pass

@dataclass
class ErrorContext:
    """Context information for errors."""
    validator_name: Optional[str] = None
    file_path: Optional[str] = None
    validation_id: Optional[str] = None
    timestamp: datetime = None
    additional_info: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.additional_info is None:
            self.additional_info = {}

class StructuredLogger:
    """Structured logger for validation operations."""

    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Setup logging handlers."""
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler for structured logs
        log_dir = Path.home() / ".agentic_neurodata_conversion" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "validation.log")
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def log_validation_start(self, validator_name: str, context: ValidationContext):
        """Log validation start."""
        self.logger.info(f"Starting validation: {validator_name}", extra={
            'event_type': 'validation_start',
            'validator_name': validator_name,
            'session_id': context.session_id,
            'file_path': context.file_path
        })

    def log_validation_complete(self, result: ValidationResult):
        """Log validation completion."""
        self.logger.info(f"Validation complete: {result.validator_name}", extra={
            'event_type': 'validation_complete',
            'validator_name': result.validator_name,
            'validation_id': result.validation_id,
            'is_valid': result.is_valid,
            'issue_count': len(result.issues),
            'execution_time': result.execution_time
        })

    def log_validation_error(self, error: Exception, context: ErrorContext):
        """Log validation error with context."""
        self.logger.error(f"Validation error: {str(error)}", extra={
            'event_type': 'validation_error',
            'error_type': type(error).__name__,
            'validator_name': context.validator_name,
            'file_path': context.file_path,
            'validation_id': context.validation_id,
            'traceback': traceback.format_exc()
        })

class ErrorRecoveryManager:
    """Manages error recovery strategies."""

    def __init__(self):
        self.recovery_strategies = {
            ValidationTimeoutError: self._handle_timeout,
            SchemaError: self._handle_schema_error,
            DataIntegrityError: self._handle_integrity_error
        }

    def handle_error(self, error: Exception, context: ErrorContext) -> Optional[ValidationResult]:
        """Handle error with appropriate recovery strategy."""
        error_type = type(error)

        if error_type in self.recovery_strategies:
            return self.recovery_strategies[error_type](error, context)

        # Default: create failed validation result
        return self._create_failed_result(error, context)

    def _handle_timeout(self, error: ValidationTimeoutError, context: ErrorContext) -> ValidationResult:
        """Handle validation timeout."""
        return ValidationResult(
            validator_name=context.validator_name or "unknown",
            context=ValidationContext(file_path=context.file_path),
            status=ValidationStatus.FAILED,
            is_valid=False,
            issues=[ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation timed out: {str(error)}",
                location="system",
                check_name="timeout_check",
                validator_name=context.validator_name or "unknown",
                remediation="Try validating smaller data chunks or increase timeout limit"
            )]
        )

    def _handle_schema_error(self, error: SchemaError, context: ErrorContext) -> ValidationResult:
        """Handle schema validation error."""
        return ValidationResult(
            validator_name=context.validator_name or "unknown",
            context=ValidationContext(file_path=context.file_path),
            status=ValidationStatus.FAILED,
            is_valid=False,
            issues=[ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=f"Schema validation failed: {str(error)}",
                location="schema",
                check_name="schema_validation",
                validator_name=context.validator_name or "unknown",
                remediation="Check schema definition and data format compatibility"
            )]
        )

    def _handle_integrity_error(self, error: DataIntegrityError, context: ErrorContext) -> ValidationResult:
        """Handle data integrity error."""
        return ValidationResult(
            validator_name=context.validator_name or "unknown",
            context=ValidationContext(file_path=context.file_path),
            status=ValidationStatus.FAILED,
            is_valid=False,
            issues=[ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=f"Data integrity check failed: {str(error)}",
                location="data",
                check_name="integrity_check",
                validator_name=context.validator_name or "unknown",
                remediation="Verify data source and check for corruption"
            )]
        )

    def _create_failed_result(self, error: Exception, context: ErrorContext) -> ValidationResult:
        """Create failed validation result for unhandled errors."""
        return ValidationResult(
            validator_name=context.validator_name or "unknown",
            context=ValidationContext(file_path=context.file_path),
            status=ValidationStatus.FAILED,
            is_valid=False,
            issues=[ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation failed: {str(error)}",
                location="system",
                check_name="system_error",
                validator_name=context.validator_name or "unknown"
            )]
        )

# Global logger instance
validation_logger = StructuredLogger("validation")
error_recovery = ErrorRecoveryManager()
```

### Module 2: NWB Inspector Integration

**Purpose:** Integrates with NWB Inspector for comprehensive NWB file validation, schema compliance, and best practices checking.

#### 2.1 NWB Inspector Engine (`nwb/inspector.py`)

```python
from typing import Dict, Any, List, Optional, Union
import time
from pathlib import Path

from ..core.base import BaseValidator, ValidationResult, ValidationIssue, ValidationContext, ValidationSeverity
from ..core.exceptions import ValidationError, validation_logger

try:
    from nwbinspector import inspect_nwb, Importance
    from nwbinspector.checks import CheckResult
    NWB_INSPECTOR_AVAILABLE = True
except ImportError:
    NWB_INSPECTOR_AVAILABLE = False
    CheckResult = None

class NWBInspectorEngine(BaseValidator):
    """NWB Inspector integration for comprehensive NWB file validation."""

    def __init__(self, name: str = "nwb_inspector", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)

        if not NWB_INSPECTOR_AVAILABLE:
            raise ValidationError("NWB Inspector is required but not available. Install with: pip install nwbinspector")

        # Configure NWB Inspector settings
        self.inspector_config = {
            'importance_threshold': Importance.BEST_PRACTICE_SUGGESTION,
            'progress_bar': False,
            'detailed_errors': True,
            'skip_validate': False,
            **self.config.get('nwb_inspector', {})
        }

        # Issue severity mapping
        self.severity_mapping = {
            Importance.CRITICAL: ValidationSeverity.CRITICAL,
            Importance.BEST_PRACTICE_VIOLATION: ValidationSeverity.WARNING,
            Importance.BEST_PRACTICE_SUGGESTION: ValidationSeverity.BEST_PRACTICE
        }

        # Remediation guidance mapping
        self.remediation_guidance = self._load_remediation_guidance()

    def validate(self, data: Union[str, Path], context: ValidationContext) -> ValidationResult:
        """Validate NWB file using NWB Inspector."""
        file_path = str(data)
        start_time = time.time()

        validation_logger.log_validation_start(self.name, context)

        try:
            # Run NWB Inspector validation
            inspection_results = inspect_nwb(
                nwbfile_path=file_path,
                **self.inspector_config
            )

            # Process and categorize results
            issues = self._process_inspection_results(inspection_results)

            # Generate summary and metrics
            summary = self._generate_summary(issues, inspection_results)
            metrics = self._calculate_metrics(issues)

            # Determine overall validity
            is_valid = not any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)

            execution_time = time.time() - start_time

            result = self._create_result(
                context=context,
                is_valid=is_valid,
                issues=issues,
                summary=summary,
                metrics=metrics,
                execution_time=execution_time
            )

            validation_logger.log_validation_complete(result)
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            validation_logger.log_validation_error(e, ErrorContext(
                validator_name=self.name,
                file_path=file_path,
                validation_id=context.session_id
            ))

            # Create error result
            error_issue = ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=f"NWB Inspector validation failed: {str(e)}",
                location="file",
                check_name="nwb_inspector_error",
                validator_name=self.name,
                remediation="Check file format and NWB Inspector installation"
            )

            return self._create_result(
                context=context,
                is_valid=False,
                issues=[error_issue],
                summary={"error": str(e)},
                execution_time=execution_time
            )

    def get_capabilities(self) -> Dict[str, Any]:
        """Return NWB Inspector capabilities."""
        return {
            "supported_formats": ["nwb", "h5"],
            "validation_types": ["schema_compliance", "best_practices", "data_integrity"],
            "severity_levels": [s.value for s in ValidationSeverity],
            "configurable_thresholds": True,
            "supports_streaming": False,
            "max_file_size_mb": 10000  # Configurable limit
        }

    def _process_inspection_results(self, inspection_results: List[CheckResult]) -> List[ValidationIssue]:
        """Process NWB Inspector results into standardized format."""
        issues = []

        for result in inspection_results:
            # Map importance to severity
            severity = self.severity_mapping.get(result.importance, ValidationSeverity.INFO)

            # Generate remediation suggestion
            remediation = self._get_remediation_for_check(result.check_function_name, result)

            # Create validation issue
            issue = ValidationIssue(
                severity=severity,
                message=result.message,
                location=result.location or "unknown",
                check_name=result.check_function_name,
                validator_name=self.name,
                object_type=result.object_type,
                object_name=result.object_name,
                remediation=remediation,
                details={
                    'importance': result.importance.name if result.importance else None,
                    'file_path': getattr(result, 'file_path', None),
                    'object_id': getattr(result, 'object_id', None)
                }
            )

            issues.append(issue)

        return issues

    def _generate_summary(self, issues: List[ValidationIssue], inspection_results: List[CheckResult]) -> Dict[str, Any]:
        """Generate validation summary statistics."""
        summary = {
            'total_checks_run': len(inspection_results),
            'total_issues': len(issues),
            'critical_issues': sum(1 for i in issues if i.severity == ValidationSeverity.CRITICAL),
            'warning_issues': sum(1 for i in issues if i.severity == ValidationSeverity.WARNING),
            'info_issues': sum(1 for i in issues if i.severity == ValidationSeverity.INFO),
            'best_practice_issues': sum(1 for i in issues if i.severity == ValidationSeverity.BEST_PRACTICE),
            'checks_by_category': self._categorize_checks(issues),
            'object_types_with_issues': self._get_object_types_with_issues(issues),
            'most_common_issues': self._get_most_common_issues(issues)
        }

        return summary

    def _calculate_metrics(self, issues: List[ValidationIssue]) -> Dict[str, float]:
        """Calculate validation metrics."""
        total_issues = len(issues)

        if total_issues == 0:
            return {
                'compliance_score': 1.0,
                'best_practice_score': 1.0,
                'critical_issue_ratio': 0.0,
                'overall_quality_score': 1.0
            }

        critical_count = sum(1 for i in issues if i.severity == ValidationSeverity.CRITICAL)
        warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        best_practice_count = sum(1 for i in issues if i.severity == ValidationSeverity.BEST_PRACTICE)

        # Calculate scores (0.0 to 1.0)
        compliance_score = max(0.0, 1.0 - (critical_count * 0.3 + warning_count * 0.1) / max(total_issues, 1))
        best_practice_score = max(0.0, 1.0 - best_practice_count / max(total_issues, 1))
        critical_issue_ratio = critical_count / total_issues
        overall_quality_score = (compliance_score + best_practice_score) / 2

        return {
            'compliance_score': compliance_score,
            'best_practice_score': best_practice_score,
            'critical_issue_ratio': critical_issue_ratio,
            'overall_quality_score': overall_quality_score
        }

    def _get_remediation_for_check(self, check_name: str, result: CheckResult) -> str:
        """Get remediation guidance for specific check."""
        return self.remediation_guidance.get(check_name,
                                           "Review NWB best practices documentation for guidance")

    def _load_remediation_guidance(self) -> Dict[str, str]:
        """Load remediation guidance for common checks."""
        return {
            'check_missing_unit': 'Add appropriate units to the data object using the "unit" parameter',
            'check_data_orientation': 'Ensure data is oriented correctly with time on the first axis',
            'check_timestamps_match_first_dimension': 'Verify that timestamps array length matches the first dimension of data',
            'check_description': 'Add a meaningful description to the object explaining its contents and purpose',
            'check_experimenter_exists': 'Add experimenter information to the NWBFile metadata',
            'check_session_start_time': 'Ensure session_start_time is properly set as a datetime object',
            'check_electrode_table_index': 'Verify that electrode indices reference valid rows in the electrode table',
            'check_subject_exists': 'Add subject information to provide context about the experimental subject',
            'check_institution': 'Add institution information to specify where the experiment was conducted',
            'check_lab': 'Add lab information to specify which laboratory conducted the experiment',
            'check_session_description': 'Provide a detailed session description explaining the experimental session'
        }

    def _categorize_checks(self, issues: List[ValidationIssue]) -> Dict[str, int]:
        """Categorize checks by type."""
        categories = {}
        for issue in issues:
            # Extract category from check name (simplified)
            if 'metadata' in issue.check_name:
                category = 'metadata'
            elif 'data' in issue.check_name:
                category = 'data'
            elif 'table' in issue.check_name:
                category = 'table'
            elif 'electrode' in issue.check_name:
                category = 'electrode'
            else:
                category = 'general'

            categories[category] = categories.get(category, 0) + 1

        return categories

    def _get_object_types_with_issues(self, issues: List[ValidationIssue]) -> Dict[str, int]:
        """Get object types that have validation issues."""
        object_types = {}
        for issue in issues:
            if issue.object_type:
                object_types[issue.object_type] = object_types.get(issue.object_type, 0) + 1
        return object_types

    def _get_most_common_issues(self, issues: List[ValidationIssue]) -> List[Dict[str, Any]]:
        """Get most common validation issues."""
        check_counts = {}
        for issue in issues:
            check_counts[issue.check_name] = check_counts.get(issue.check_name, 0) + 1

        # Sort by frequency and return top 5
        sorted_checks = sorted(check_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return [
            {
                'check_name': check_name,
                'count': count,
                'percentage': round(count / len(issues) * 100, 1)
            }
            for check_name, count in sorted_checks
        ]
```

### Module 3: LinkML Schema Validation

**Purpose:** Provides LinkML-based metadata validation with runtime schema enforcement and controlled vocabulary validation.

#### 3.1 Schema Definition Management (`linkml/schema_manager.py`)

```python
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import yaml
import json
from dataclasses import dataclass, field

from ..core.base import BaseValidator, ValidationResult, ValidationIssue, ValidationContext, ValidationSeverity
from ..core.exceptions import SchemaError, validation_logger

try:
    from linkml_runtime import SchemaView
    from linkml.generators.pydanticgen import PydanticGenerator
    from linkml_runtime.utils.schemaview import SchemaView
    LINKML_AVAILABLE = True
except ImportError:
    LINKML_AVAILABLE = False

@dataclass
class SchemaInfo:
    """Information about a loaded schema."""
    name: str
    version: str
    path: str
    classes: Dict[str, Any] = field(default_factory=dict)
    enums: Dict[str, Any] = field(default_factory=dict)
    slots: Dict[str, Any] = field(default_factory=dict)
    loaded_at: datetime = field(default_factory=datetime.utcnow)

class SchemaManager:
    """Manages LinkML schema definitions and Pydantic class generation."""

    def __init__(self, schema_paths: Optional[List[str]] = None):
        if not LINKML_AVAILABLE:
            raise SchemaError("LinkML is required but not available. Install with: pip install linkml")

        self.schema_paths = schema_paths or []
        self.schemas: Dict[str, SchemaInfo] = {}
        self.pydantic_classes: Dict[str, type] = {}
        self.schema_views: Dict[str, SchemaView] = {}
        self.logger = validation_logger

    def load_schema(self, schema_path: str, name: Optional[str] = None) -> SchemaInfo:
        """Load a LinkML schema from file."""
        schema_path = Path(schema_path)
        if not schema_path.exists():
            raise SchemaError(f"Schema file not found: {schema_path}")

        name = name or schema_path.stem

        try:
            # Load schema using LinkML
            schema_view = SchemaView(str(schema_path))
            self.schema_views[name] = schema_view

            # Generate Pydantic classes
            pydantic_classes = self._generate_pydantic_classes(schema_view, name)
            self.pydantic_classes.update(pydantic_classes)

            # Create schema info
            schema_info = SchemaInfo(
                name=name,
                version=schema_view.schema.version or "unknown",
                path=str(schema_path),
                classes={cls_name: cls_def for cls_name, cls_def in schema_view.all_classes().items()},
                enums={enum_name: enum_def for enum_name, enum_def in schema_view.all_enums().items()},
                slots={slot_name: slot_def for slot_name, slot_def in schema_view.all_slots().items()}
            )

            self.schemas[name] = schema_info
            self.logger.info(f"Loaded schema: {name} from {schema_path}")

            return schema_info

        except Exception as e:
            raise SchemaError(f"Failed to load schema {name}: {str(e)}")

    def _generate_pydantic_classes(self, schema_view: SchemaView, schema_name: str) -> Dict[str, type]:
        """Generate Pydantic classes from LinkML schema."""
        try:
            generator = PydanticGenerator(schema_view.schema)
            pydantic_code = generator.serialize()

            # Execute generated code to create classes
            exec_globals = {'__builtins__': __builtins__}
            exec(pydantic_code, exec_globals)

            # Extract Pydantic classes
            from pydantic import BaseModel
            classes = {}
            for name, obj in exec_globals.items():
                if isinstance(obj, type) and issubclass(obj, BaseModel) and obj != BaseModel:
                    full_name = f"{schema_name}.{name}"
                    classes[full_name] = obj
                    classes[name] = obj  # Also store without prefix for convenience

            return classes

        except Exception as e:
            raise SchemaError(f"Failed to generate Pydantic classes: {str(e)}")

    def get_class(self, class_name: str, schema_name: Optional[str] = None) -> Optional[type]:
        """Get a Pydantic class by name."""
        if schema_name:
            full_name = f"{schema_name}.{class_name}"
            return self.pydantic_classes.get(full_name)

        return self.pydantic_classes.get(class_name)

    def validate_schema_compatibility(self, schema_name: str, target_version: str) -> bool:
        """Check if schema is compatible with target version."""
        if schema_name not in self.schemas:
            return False

        current_version = self.schemas[schema_name].version
        # Simplified version compatibility check
        return current_version == target_version

    def get_schema_documentation(self, schema_name: str) -> Dict[str, Any]:
        """Get documentation for a schema."""
        if schema_name not in self.schemas:
            raise SchemaError(f"Schema not found: {schema_name}")

        schema_info = self.schemas[schema_name]
        schema_view = self.schema_views[schema_name]

        return {
            'name': schema_info.name,
            'version': schema_info.version,
            'description': schema_view.schema.description,
            'classes': {
                name: {
                    'description': cls.description,
                    'slots': list(cls.slots) if cls.slots else []
                }
                for name, cls in schema_info.classes.items()
            },
            'enums': {
                name: {
                    'description': enum.description,
                    'values': list(enum.permissible_values.keys()) if enum.permissible_values else []
                }
                for name, enum in schema_info.enums.items()
            }
        }
```

#### 3.2 Runtime Validation Engine (`linkml/validator.py`)

```python
from typing import Dict, Any, List, Optional, Union
import time
from pydantic import ValidationError as PydanticValidationError

from ..core.base import BaseValidator, ValidationResult, ValidationIssue, ValidationContext, ValidationSeverity
from ..core.exceptions import validation_logger
from .schema_manager import SchemaManager

class LinkMLValidator(BaseValidator):
    """Runtime LinkML validation engine."""

    def __init__(self, name: str = "linkml_validator", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)

        self.schema_manager = SchemaManager()
        self.default_schema = self.config.get('default_schema')

        # Load configured schemas
        schema_paths = self.config.get('schema_paths', [])
        for path in schema_paths:
            try:
                self.schema_manager.load_schema(path)
            except Exception as e:
                validation_logger.error(f"Failed to load schema from {path}: {e}")

    def validate(self, data: Dict[str, Any], context: ValidationContext) -> ValidationResult:
        """Validate metadata against LinkML schema."""
        start_time = time.time()

        validation_logger.log_validation_start(self.name, context)

        try:
            # Determine schema and class to use
            schema_name = context.configuration.get('schema_name', self.default_schema)
            class_name = context.configuration.get('class_name')

            if not schema_name or not class_name:
                raise ValueError("schema_name and class_name must be specified in context configuration")

            # Get validation class
            validation_class = self.schema_manager.get_class(class_name, schema_name)
            if not validation_class:
                raise ValueError(f"Class {class_name} not found in schema {schema_name}")

            # Perform validation
            issues = []
            is_valid = True

            try:
                validated_instance = validation_class(**data)
                validation_logger.info(f"LinkML validation successful for {class_name}")

            except PydanticValidationError as e:
                is_valid = False
                issues = self._parse_pydantic_errors(e, class_name)
                validation_logger.warning(f"LinkML validation failed: {len(issues)} issues found")

            # Generate summary and metrics
            summary = self._generate_summary(data, schema_name, class_name, issues)
            metrics = self._calculate_metrics(data, issues)

            execution_time = time.time() - start_time

            result = self._create_result(
                context=context,
                is_valid=is_valid,
                issues=issues,
                summary=summary,
                metrics=metrics,
                execution_time=execution_time
            )

            validation_logger.log_validation_complete(result)
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            validation_logger.log_validation_error(e, ErrorContext(
                validator_name=self.name,
                validation_id=context.session_id
            ))

            error_issue = ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=f"LinkML validation failed: {str(e)}",
                location="schema",
                check_name="linkml_validation_error",
                validator_name=self.name,
                remediation="Check schema configuration and data format"
            )

            return self._create_result(
                context=context,
                is_valid=False,
                issues=[error_issue],
                summary={"error": str(e)},
                execution_time=execution_time
            )

    def get_capabilities(self) -> Dict[str, Any]:
        """Return LinkML validator capabilities."""
        return {
            "supported_formats": ["json", "yaml", "dict"],
            "validation_types": ["schema_compliance", "type_checking", "constraint_validation"],
            "features": ["runtime_validation", "pydantic_integration", "nested_validation"],
            "loaded_schemas": list(self.schema_manager.schemas.keys()),
            "available_classes": list(self.schema_manager.pydantic_classes.keys())
        }

    def _parse_pydantic_errors(self, error: PydanticValidationError, class_name: str) -> List[ValidationIssue]:
        """Parse Pydantic validation errors into ValidationIssue objects."""
        issues = []

        for err in error.errors():
            location = '.'.join(str(loc) for loc in err['loc']) if err['loc'] else class_name

            issue = ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=err['msg'],
                location=location,
                check_name='linkml_schema_validation',
                validator_name=self.name,
                object_type=class_name,
                remediation=self._get_remediation_for_error(err),
                details={
                    'error_type': err['type'],
                    'input_value': err.get('input'),
                    'field_path': err['loc']
                }
            )
            issues.append(issue)

        return issues

    def _get_remediation_for_error(self, error: Dict[str, Any]) -> str:
        """Generate remediation suggestion for validation error."""
        error_type = error.get('type', '')

        remediation_map = {
            'missing': 'Add the required field to the metadata',
            'type_error': 'Ensure the field value is of the correct type',
            'value_error': 'Check that the field value meets the specified constraints',
            'extra_forbidden': 'Remove the extra field or check schema definition',
            'string_too_short': 'Provide a longer string value',
            'string_too_long': 'Shorten the string value',
            'greater_than': 'Provide a value greater than the minimum',
            'less_than': 'Provide a value less than the maximum'
        }

        return remediation_map.get(error_type, 'Review the schema requirements for this field')

    def _generate_summary(self, data: Dict[str, Any], schema_name: str,
                         class_name: str, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Generate validation summary."""
        return {
            'schema_name': schema_name,
            'class_name': class_name,
            'fields_validated': len(data),
            'total_issues': len(issues),
            'critical_issues': sum(1 for i in issues if i.severity == ValidationSeverity.CRITICAL),
            'validation_method': 'linkml_pydantic',
            'field_coverage': self._calculate_field_coverage(data, class_name)
        }

    def _calculate_metrics(self, data: Dict[str, Any], issues: List[ValidationIssue]) -> Dict[str, float]:
        """Calculate validation metrics."""
        total_fields = len(data)
        error_fields = len(set(issue.location for issue in issues))

        return {
            'field_validation_rate': (total_fields - error_fields) / max(total_fields, 1),
            'error_density': len(issues) / max(total_fields, 1),
            'schema_compliance_score': 1.0 if len(issues) == 0 else max(0.0, 1.0 - len(issues) / max(total_fields, 1))
        }

    def _calculate_field_coverage(self, data: Dict[str, Any], class_name: str) -> float:
        """Calculate how many expected fields are present."""
        validation_class = self.schema_manager.get_class(class_name)
        if not validation_class:
            return 0.0

        # Get expected fields from Pydantic model
        expected_fields = set(validation_class.__fields__.keys())
        provided_fields = set(data.keys())

        if not expected_fields:
            return 1.0

        return len(provided_fields.intersection(expected_fields)) / len(expected_fields)
```

#### 3.3 Controlled Vocabulary Validation (`linkml/vocabulary.py`)

```python
from typing import Dict, Any, List, Optional, Set, Union
from enum import Enum
from pathlib import Path
import requests
import json

from ..core.base import BaseValidator, ValidationResult, ValidationIssue, ValidationContext, ValidationSeverity
from ..core.exceptions import validation_logger

class VocabularySource(Enum):
    """Types of vocabulary sources."""
    ENUM = "enum"
    ONTOLOGY = "ontology"
    EXTERNAL_LIST = "external_list"
    FILE = "file"

@dataclass
class VocabularyDefinition:
    """Definition of a controlled vocabulary."""
    name: str
    source_type: VocabularySource
    source_location: str
    terms: Set[str] = field(default_factory=set)
    descriptions: Dict[str, str] = field(default_factory=dict)
    synonyms: Dict[str, List[str]] = field(default_factory=dict)
    hierarchy: Dict[str, List[str]] = field(default_factory=dict)  # parent -> children

class VocabularyValidator(BaseValidator):
    """Validates controlled vocabularies and provides completion suggestions."""

    def __init__(self, name: str = "vocabulary_validator", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)

        self.vocabularies: Dict[str, VocabularyDefinition] = {}
        self.field_vocabularies: Dict[str, str] = {}  # field_name -> vocabulary_name

        # Load configured vocabularies
        self._load_configured_vocabularies()

    def validate(self, data: Dict[str, Any], context: ValidationContext) -> ValidationResult:
        """Validate vocabulary usage in data."""
        start_time = time.time()

        validation_logger.log_validation_start(self.name, context)

        issues = []

        # Validate each field that has vocabulary constraints
        for field_name, value in data.items():
            if field_name in self.field_vocabularies:
                vocab_name = self.field_vocabularies[field_name]
                field_issues = self._validate_field_vocabulary(field_name, value, vocab_name)
                issues.extend(field_issues)

        # Check cross-field vocabulary consistency
        consistency_issues = self._check_cross_field_consistency(data)
        issues.extend(consistency_issues)

        is_valid = not any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)

        summary = self._generate_summary(data, issues)
        metrics = self._calculate_metrics(data, issues)

        execution_time = time.time() - start_time

        result = self._create_result(
            context=context,
            is_valid=is_valid,
            issues=issues,
            summary=summary,
            metrics=metrics,
            execution_time=execution_time
        )

        validation_logger.log_validation_complete(result)
        return result

    def get_capabilities(self) -> Dict[str, Any]:
        """Return vocabulary validator capabilities."""
        return {
            "supported_sources": [source.value for source in VocabularySource],
            "loaded_vocabularies": list(self.vocabularies.keys()),
            "field_mappings": self.field_vocabularies,
            "features": ["completion_suggestions", "synonym_resolution", "hierarchy_validation"]
        }

    def get_vocabulary_suggestions(self, field_name: str, partial_value: str, limit: int = 5) -> List[str]:
        """Get vocabulary completion suggestions for a partial value."""
        if field_name not in self.field_vocabularies:
            return []

        vocab_name = self.field_vocabularies[field_name]
        vocabulary = self.vocabularies.get(vocab_name)

        if not vocabulary:
            return []

        partial_lower = partial_value.lower()
        suggestions = []

        # Direct term matches
        for term in vocabulary.terms:
            if term.lower().startswith(partial_lower):
                suggestions.append(term)

        # Synonym matches
        for term, synonyms in vocabulary.synonyms.items():
            for synonym in synonyms:
                if synonym.lower().startswith(partial_lower) and term not in suggestions:
                    suggestions.append(term)

        return sorted(suggestions)[:limit]

    def _load_configured_vocabularies(self):
        """Load vocabularies from configuration."""
        vocab_configs = self.config.get('vocabularies', [])

        for vocab_config in vocab_configs:
            try:
                vocabulary = self._load_vocabulary(vocab_config)
                self.vocabularies[vocabulary.name] = vocabulary

                # Map fields to vocabularies
                field_mappings = vocab_config.get('fields', [])
                for field_name in field_mappings:
                    self.field_vocabularies[field_name] = vocabulary.name

            except Exception as e:
                validation_logger.error(f"Failed to load vocabulary {vocab_config.get('name')}: {e}")

    def _load_vocabulary(self, config: Dict[str, Any]) -> VocabularyDefinition:
        """Load a single vocabulary from configuration."""
        name = config['name']
        source_type = VocabularySource(config['source_type'])
        source_location = config['source_location']

        vocabulary = VocabularyDefinition(
            name=name,
            source_type=source_type,
            source_location=source_location
        )

        if source_type == VocabularySource.FILE:
            self._load_from_file(vocabulary, source_location)
        elif source_type == VocabularySource.EXTERNAL_LIST:
            self._load_from_url(vocabulary, source_location)
        elif source_type == VocabularySource.ENUM:
            self._load_from_enum(vocabulary, config.get('terms', []))

        return vocabulary

    def _load_from_file(self, vocabulary: VocabularyDefinition, file_path: str):
        """Load vocabulary from file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Vocabulary file not found: {file_path}")

        with open(path, 'r') as f:
            if path.suffix == '.json':
                data = json.load(f)
            elif path.suffix in ['.yml', '.yaml']:
                import yaml
                data = yaml.safe_load(f)
            else:
                # Plain text file, one term per line
                data = {'terms': [line.strip() for line in f if line.strip()]}

        vocabulary.terms = set(data.get('terms', []))
        vocabulary.descriptions = data.get('descriptions', {})
        vocabulary.synonyms = data.get('synonyms', {})

    def _load_from_url(self, vocabulary: VocabularyDefinition, url: str):
        """Load vocabulary from external URL."""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            vocabulary.terms = set(data.get('terms', []))
            vocabulary.descriptions = data.get('descriptions', {})
            vocabulary.synonyms = data.get('synonyms', {})

        except Exception as e:
            raise RuntimeError(f"Failed to load vocabulary from URL {url}: {e}")

    def _load_from_enum(self, vocabulary: VocabularyDefinition, terms: List[str]):
        """Load vocabulary from enumerated list."""
        vocabulary.terms = set(terms)

    def _validate_field_vocabulary(self, field_name: str, value: Union[str, List[str]],
                                  vocab_name: str) -> List[ValidationIssue]:
        """Validate a field's value against its vocabulary."""
        issues = []
        vocabulary = self.vocabularies.get(vocab_name)

        if not vocabulary:
            return [ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Vocabulary {vocab_name} not found for field {field_name}",
                location=field_name,
                check_name="vocabulary_not_found",
                validator_name=self.name
            )]

        # Handle single values and lists
        values_to_check = [value] if isinstance(value, str) else value

        for val in values_to_check:
            if not self._is_valid_term(val, vocabulary):
                suggestions = self.get_vocabulary_suggestions(field_name, val, 3)
                remediation = f"Use a valid term from {vocab_name} vocabulary"
                if suggestions:
                    remediation += f". Suggestions: {', '.join(suggestions)}"

                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Invalid vocabulary term '{val}' for field {field_name}",
                    location=field_name,
                    check_name="invalid_vocabulary_term",
                    validator_name=self.name,
                    remediation=remediation,
                    details={
                        'invalid_term': val,
                        'vocabulary': vocab_name,
                        'suggestions': suggestions
                    }
                ))

        return issues

    def _is_valid_term(self, term: str, vocabulary: VocabularyDefinition) -> bool:
        """Check if a term is valid in the vocabulary."""
        # Direct term match
        if term in vocabulary.terms:
            return True

        # Synonym match
        for valid_term, synonyms in vocabulary.synonyms.items():
            if term in synonyms:
                return True

        return False

    def _check_cross_field_consistency(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Check vocabulary consistency across related fields."""
        issues = []

        # Example: check that experimental_modality and data_type are consistent
        modality = data.get('experimental_modality')
        data_type = data.get('data_type')

        if modality and data_type:
            if not self._are_terms_compatible(modality, data_type):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Inconsistent vocabulary terms: {modality} and {data_type}",
                    location="experimental_modality,data_type",
                    check_name="vocabulary_consistency",
                    validator_name=self.name,
                    remediation="Ensure vocabulary terms are compatible across related fields"
                ))

        return issues

    def _are_terms_compatible(self, term1: str, term2: str) -> bool:
        """Check if two terms are compatible (simplified implementation)."""
        # This would contain domain-specific compatibility rules
        # For now, just return True as a placeholder
        return True

    def _generate_summary(self, data: Dict[str, Any], issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Generate vocabulary validation summary."""
        validated_fields = [field for field in data.keys() if field in self.field_vocabularies]

        return {
            'total_fields_checked': len(validated_fields),
            'vocabulary_issues': len(issues),
            'vocabularies_used': list(set(self.field_vocabularies[f] for f in validated_fields)),
            'fields_with_issues': list(set(issue.location for issue in issues))
        }

    def _calculate_metrics(self, data: Dict[str, Any], issues: List[ValidationIssue]) -> Dict[str, float]:
        """Calculate vocabulary validation metrics."""
        validated_fields = [field for field in data.keys() if field in self.field_vocabularies]

        if not validated_fields:
            return {'vocabulary_compliance_rate': 1.0}

        fields_with_issues = set(issue.location for issue in issues)
        compliant_fields = len(validated_fields) - len(fields_with_issues)

        return {
            'vocabulary_compliance_rate': compliant_fields / len(validated_fields),
            'vocabulary_coverage': len(validated_fields) / len(data),
            'average_issues_per_field': len(issues) / max(len(validated_fields), 1)
        }
```

### Module 4: Quality Assessment Engine

**Purpose:** Provides comprehensive quality assessment across multiple dimensions with extensible metrics framework.

#### 4.1 Quality Metrics Framework (`quality/metrics.py`)

```python
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import statistics

from ..core.base import BaseValidator, ValidationResult, ValidationIssue, ValidationContext, ValidationSeverity
from ..core.exceptions import validation_logger

class QualityDimension(Enum):
    """Quality assessment dimensions."""
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    COMPLIANCE = "compliance"
    USABILITY = "usability"

@dataclass
class QualityMetric:
    """Individual quality metric with scoring details."""
    name: str
    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    max_score: float
    weight: float = 1.0
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # Confidence in the metric calculation

@dataclass
class QualityReport:
    """Comprehensive quality assessment report."""
    overall_score: float
    dimension_scores: Dict[str, float]
    metrics: List[QualityMetric]
    recommendations: List[str]
    assessment_metadata: Dict[str, Any] = field(default_factory=dict)

class BaseQualityAssessor(ABC):
    """Base class for quality assessors."""

    @abstractmethod
    def assess(self, data: Any, context: ValidationContext,
              validation_results: List[ValidationResult]) -> List[QualityMetric]:
        """Assess quality and return metrics."""
        pass

    @abstractmethod
    def get_dimension(self) -> QualityDimension:
        """Get the quality dimension this assessor evaluates."""
        pass

class QualityMetricsFramework(BaseValidator):
    """Extensible framework for quality metrics calculation."""

    def __init__(self, name: str = "quality_metrics", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)

        self.assessors: Dict[QualityDimension, List[BaseQualityAssessor]] = {
            dimension: [] for dimension in QualityDimension
        }
        self.custom_metrics: Dict[str, Callable] = {}
        self.dimension_weights = self.config.get('dimension_weights', {
            QualityDimension.COMPLETENESS.value: 0.25,
            QualityDimension.CONSISTENCY.value: 0.25,
            QualityDimension.ACCURACY.value: 0.20,
            QualityDimension.COMPLIANCE.value: 0.20,
            QualityDimension.USABILITY.value: 0.10
        })

        # Initialize built-in assessors
        self._initialize_assessors()

    def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Perform comprehensive quality assessment."""
        start_time = time.time()

        validation_logger.log_validation_start(self.name, context)

        try:
            # Get previous validation results from context
            validation_results = context.metadata.get('validation_results', [])

            # Run all quality assessors
            all_metrics = []
            for dimension, assessors in self.assessors.items():
                for assessor in assessors:
                    try:
                        metrics = assessor.assess(data, context, validation_results)
                        all_metrics.extend(metrics)
                    except Exception as e:
                        validation_logger.error(f"Quality assessor {assessor.__class__.__name__} failed: {e}")

            # Add custom metrics
            custom_metrics = self._calculate_custom_metrics(data, context, validation_results)
            all_metrics.extend(custom_metrics)

            # Calculate overall quality report
            quality_report = self._generate_quality_report(all_metrics)

            # Convert to validation issues for consistency
            issues = self._convert_to_validation_issues(quality_report)

            is_valid = quality_report.overall_score >= self.config.get('minimum_quality_score', 0.7)

            execution_time = time.time() - start_time

            result = self._create_result(
                context=context,
                is_valid=is_valid,
                issues=issues,
                summary={
                    'quality_report': quality_report.__dict__,
                    'assessment_time': execution_time
                },
                metrics={
                    'overall_quality_score': quality_report.overall_score,
                    **quality_report.dimension_scores
                },
                execution_time=execution_time
            )

            validation_logger.log_validation_complete(result)
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            validation_logger.log_validation_error(e, ErrorContext(
                validator_name=self.name,
                validation_id=context.session_id
            ))

            error_issue = ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=f"Quality assessment failed: {str(e)}",
                location="quality_framework",
                check_name="quality_assessment_error",
                validator_name=self.name
            )

            return self._create_result(
                context=context,
                is_valid=False,
                issues=[error_issue],
                summary={"error": str(e)},
                execution_time=execution_time
            )

    def register_assessor(self, assessor: BaseQualityAssessor):
        """Register a quality assessor."""
        dimension = assessor.get_dimension()
        self.assessors[dimension].append(assessor)

    def register_custom_metric(self, name: str, metric_func: Callable):
        """Register a custom metric function."""
        self.custom_metrics[name] = metric_func

    def get_capabilities(self) -> Dict[str, Any]:
        """Return quality framework capabilities."""
        return {
            "supported_dimensions": [dim.value for dim in QualityDimension],
            "assessor_count": {dim.value: len(assessors) for dim, assessors in self.assessors.items()},
            "custom_metrics": list(self.custom_metrics.keys()),
            "features": ["weighted_scoring", "confidence_intervals", "custom_metrics", "extensible_assessors"]
        }

    def _initialize_assessors(self):
        """Initialize built-in quality assessors."""
        # This would be implemented with actual assessor classes
        pass

    def _calculate_custom_metrics(self, data: Any, context: ValidationContext,
                                 validation_results: List[ValidationResult]) -> List[QualityMetric]:
        """Calculate custom metrics."""
        metrics = []

        for metric_name, metric_func in self.custom_metrics.items():
            try:
                score = metric_func(data, context, validation_results)
                metric = QualityMetric(
                    name=metric_name,
                    dimension=QualityDimension.ACCURACY,  # Default dimension
                    score=score,
                    max_score=1.0,
                    description=f"Custom metric: {metric_name}"
                )
                metrics.append(metric)
            except Exception as e:
                validation_logger.error(f"Custom metric {metric_name} failed: {e}")

        return metrics

    def _generate_quality_report(self, metrics: List[QualityMetric]) -> QualityReport:
        """Generate comprehensive quality report."""
        # Calculate dimension scores
        dimension_scores = {}
        for dimension in QualityDimension:
            dimension_metrics = [m for m in metrics if m.dimension == dimension]
            if dimension_metrics:
                weighted_scores = []
                total_weight = 0

                for metric in dimension_metrics:
                    normalized_score = metric.score / metric.max_score if metric.max_score > 0 else 0
                    weighted_scores.append(normalized_score * metric.weight * metric.confidence)
                    total_weight += metric.weight * metric.confidence

                dimension_scores[dimension.value] = sum(weighted_scores) / max(total_weight, 1)
            else:
                dimension_scores[dimension.value] = 0.0

        # Calculate overall score
        overall_score = sum(
            score * self.dimension_weights.get(dim, 0)
            for dim, score in dimension_scores.items()
        ) / sum(self.dimension_weights.values())

        return QualityReport(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            metrics=metrics,
            timestamp=time.time(),
            recommendations=self._generate_recommendations(dimension_scores, metrics)
        )

    def _generate_recommendations(self, dimension_scores: Dict[str, float],
                                metrics: List[QualityMetric]) -> List[str]:
        """Generate improvement recommendations based on quality scores."""
        recommendations = []

        for dimension, score in dimension_scores.items():
            if score < 0.7:  # Below acceptable threshold
                recommendations.append(f"Improve {dimension} quality (current score: {score:.2f})")

        return recommendations

## Configuration Schema Definitions

### Core Configuration Schema

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Any
from enum import Enum
import yaml

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationMode(str, Enum):
    STRICT = "strict"
    PERMISSIVE = "permissive"
    DEVELOPMENT = "development"

class MemoryLimits(BaseModel):
    max_memory_gb: float = Field(default=8.0, ge=0.1, le=128.0)
    chunk_size_mb: float = Field(default=100.0, ge=1.0, le=1000.0)
    cache_size_mb: float = Field(default=500.0, ge=10.0, le=2000.0)

class StreamingConfig(BaseModel):
    enabled: bool = Field(default=True)
    buffer_size_mb: float = Field(default=50.0, ge=1.0, le=500.0)
    max_workers: int = Field(default=4, ge=1, le=16)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)

class ValidationConfig(BaseModel):
    mode: ValidationMode = Field(default=ValidationMode.STRICT)
    fail_fast: bool = Field(default=False)
    max_errors: int = Field(default=100, ge=1, le=10000)
    parallel_validation: bool = Field(default=True)
    skip_large_datasets: bool = Field(default=False)

class ModuleConfig(BaseModel):
    enabled: bool = Field(default=True)
    priority: int = Field(default=1, ge=1, le=10)
    timeout: int = Field(default=60, ge=10, le=3600)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    config: Dict[str, Any] = Field(default_factory=dict)

class ValidationSystemConfig(BaseModel):
    system_name: str = Field(default="NWB Validation System")
    version: str = Field(default="1.0.0")
    log_level: LogLevel = Field(default=LogLevel.INFO)

    # Core settings
    memory: MemoryLimits = Field(default_factory=MemoryLimits)
    streaming: StreamingConfig = Field(default_factory=StreamingConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)

    # Module configurations
    modules: Dict[str, ModuleConfig] = Field(default_factory=dict)

    # Output settings
    output_format: str = Field(default="json", regex="^(json|yaml|xml|html)$")
    output_directory: str = Field(default="./validation_results")
    detailed_reports: bool = Field(default=True)

    # Schema paths
    schema_paths: List[str] = Field(default_factory=list)
    custom_validators: List[str] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "ValidationSystemConfig":
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, yaml_path: str) -> None:
        with open(yaml_path, 'w') as f:
            yaml.dump(self.dict(), f, default_flow_style=False, indent=2)
```

### Module-Specific Configuration Schemas

```python
class CoreValidationConfig(ModuleConfig):
    strict_mode: bool = Field(default=True)
    validate_extensions: bool = Field(default=True)
    check_file_integrity: bool = Field(default=True)

class LinkMLValidationConfig(ModuleConfig):
    schema_version: str = Field(default="latest")
    custom_constraints: List[str] = Field(default_factory=list)
    validation_depth: int = Field(default=3, ge=1, le=10)

class QualityAssessmentConfig(ModuleConfig):
    metrics: List[str] = Field(default_factory=lambda: ["completeness", "consistency", "accuracy"])
    thresholds: Dict[str, float] = Field(default_factory=dict)
    generate_plots: bool = Field(default=False)

class DomainValidationConfig(ModuleConfig):
    check_scientific_validity: bool = Field(default=True)
    reference_standards: List[str] = Field(default_factory=list)
    custom_rules: List[str] = Field(default_factory=list)

class ReportingConfig(ModuleConfig):
    include_warnings: bool = Field(default=True)
    include_suggestions: bool = Field(default=True)
    max_report_size_mb: float = Field(default=10.0, ge=0.1, le=100.0)

class MCPIntegrationConfig(ModuleConfig):
    endpoint: str = Field(default="http://localhost:8080")
    api_key: Optional[str] = Field(default=None)
    timeout: int = Field(default=30, ge=5, le=300)
```

### Configuration Factory and Loader

```python
class ConfigurationManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "validation_config.yaml"
        self._config = None

    def load_config(self) -> ValidationSystemConfig:
        if self._config is None:
            if Path(self.config_path).exists():
                self._config = ValidationSystemConfig.from_yaml(self.config_path)
            else:
                self._config = self.create_default_config()
                self._config.to_yaml(self.config_path)
        return self._config

    def create_default_config(self) -> ValidationSystemConfig:
        config = ValidationSystemConfig()

        # Set up default module configurations
        config.modules = {
            "core_validation": CoreValidationConfig(
                priority=1,
                config={
                    "strict_mode": True,
                    "validate_extensions": True
                }
            ).dict(),
            "linkml_validation": LinkMLValidationConfig(
                priority=2,
                config={
                    "schema_version": "latest",
                    "validation_depth": 3
                }
            ).dict(),
            "quality_assessment": QualityAssessmentConfig(
                priority=3,
                config={
                    "metrics": ["completeness", "consistency"],
                    "generate_plots": False
                }
            ).dict(),
            "domain_validation": DomainValidationConfig(
                priority=4,
                config={
                    "check_scientific_validity": True
                }
            ).dict(),
            "reporting": ReportingConfig(
                priority=5,
                config={
                    "include_warnings": True,
                    "max_report_size_mb": 10.0
                }
            ).dict(),
            "mcp_integration": MCPIntegrationConfig(
                enabled=False,
                priority=6,
                config={
                    "endpoint": "http://localhost:8080"
                }
            ).dict()
        }

        return config

    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        config = self.load_config()
        return config.modules.get(module_name, {})

    def update_module_config(self, module_name: str, updates: Dict[str, Any]) -> None:
        config = self.load_config()
        if module_name in config.modules:
            config.modules[module_name]["config"].update(updates)
            config.to_yaml(self.config_path)
```

### Environment-Specific Configurations

```python
class EnvironmentConfig:
    @staticmethod
    def development() -> ValidationSystemConfig:
        config = ValidationSystemConfig()
        config.log_level = LogLevel.DEBUG
        config.validation.mode = ValidationMode.DEVELOPMENT
        config.validation.fail_fast = False
        config.memory.max_memory_gb = 4.0
        config.streaming.max_workers = 2
        return config

    @staticmethod
    def production() -> ValidationSystemConfig:
        config = ValidationSystemConfig()
        config.log_level = LogLevel.INFO
        config.validation.mode = ValidationMode.STRICT
        config.validation.fail_fast = True
        config.memory.max_memory_gb = 16.0
        config.streaming.max_workers = 8
        return config

    @staticmethod
    def testing() -> ValidationSystemConfig:
        config = ValidationSystemConfig()
        config.log_level = LogLevel.WARNING
        config.validation.mode = ValidationMode.PERMISSIVE
        config.memory.max_memory_gb = 2.0
        config.streaming.enabled = False
        return config
```

## Testing Framework Design

### Comprehensive Testing Architecture

```python
import pytest
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from unittest.mock import Mock, patch
import tempfile
import shutil

class TestCategory(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    REGRESSION = "regression"
    END_TO_END = "end_to_end"

@dataclass
class TestConfig:
    category: TestCategory
    timeout: int = 60
    memory_limit_mb: int = 1000
    requires_test_data: bool = False
    parallel_safe: bool = True
    tags: List[str] = None

class BaseValidationTest(ABC):
    def __init__(self, config: TestConfig):
        self.config = config
        self.test_data_manager = TestDataManager()
        self.validation_system = None

    @abstractmethod
    def setup_test(self) -> None:
        pass

    @abstractmethod
    def teardown_test(self) -> None:
        pass

    @abstractmethod
    def run_test(self) -> Dict[str, Any]:
        pass

class TestDataManager:
    def __init__(self):
        self.test_data_dir = Path("tests/data")
        self.temp_dirs = []

    def create_test_nwb_file(self, spec: Dict[str, Any]) -> Path:
        """Create synthetic NWB file for testing."""
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)

        nwb_path = Path(temp_dir) / "test.nwb"
        # Implementation would create actual NWB file based on spec
        return nwb_path

    def cleanup(self):
        """Clean up temporary test files."""
        for temp_dir in self.temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
        self.temp_dirs.clear()

class ModuleTestSuite:
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.tests = []
        self.setup_hooks = []
        self.teardown_hooks = []

    def add_test(self, test: BaseValidationTest):
        self.tests.append(test)

    def add_setup_hook(self, hook: Callable):
        self.setup_hooks.append(hook)

    def add_teardown_hook(self, hook: Callable):
        self.teardown_hooks.append(hook)

    def run_suite(self) -> Dict[str, Any]:
        results = {
            "module": self.module_name,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failures": [],
            "performance_metrics": {}
        }

        # Run setup hooks
        for hook in self.setup_hooks:
            hook()

        try:
            for test in self.tests:
                try:
                    test.setup_test()
                    test_result = test.run_test()

                    results["tests_run"] += 1
                    if test_result.get("passed", False):
                        results["tests_passed"] += 1
                    else:
                        results["tests_failed"] += 1
                        results["failures"].append({
                            "test": test.__class__.__name__,
                            "error": test_result.get("error", "Unknown error")
                        })

                    # Collect performance metrics
                    if "performance" in test_result:
                        results["performance_metrics"][test.__class__.__name__] = test_result["performance"]

                except Exception as e:
                    results["tests_failed"] += 1
                    results["failures"].append({
                        "test": test.__class__.__name__,
                        "error": str(e)
                    })
                finally:
                    test.teardown_test()

        finally:
            # Run teardown hooks
            for hook in self.teardown_hooks:
                hook()

        return results

class ValidationTestFramework:
    def __init__(self):
        self.test_suites = {}
        self.global_config = None
        self.test_data_manager = TestDataManager()

    def register_test_suite(self, suite: ModuleTestSuite):
        self.test_suites[suite.module_name] = suite

    def run_all_tests(self, categories: List[TestCategory] = None) -> Dict[str, Any]:
        if categories is None:
            categories = list(TestCategory)

        results = {
            "timestamp": time.time(),
            "categories_run": [cat.value for cat in categories],
            "suite_results": {},
            "summary": {
                "total_tests": 0,
                "total_passed": 0,
                "total_failed": 0,
                "success_rate": 0.0
            }
        }

        for suite_name, suite in self.test_suites.items():
            # Filter tests by category
            filtered_tests = [
                test for test in suite.tests
                if test.config.category in categories
            ]

            if filtered_tests:
                suite.tests = filtered_tests
                suite_result = suite.run_suite()
                results["suite_results"][suite_name] = suite_result

                # Update summary
                results["summary"]["total_tests"] += suite_result["tests_run"]
                results["summary"]["total_passed"] += suite_result["tests_passed"]
                results["summary"]["total_failed"] += suite_result["tests_failed"]

        # Calculate success rate
        total_tests = results["summary"]["total_tests"]
        if total_tests > 0:
            results["summary"]["success_rate"] = results["summary"]["total_passed"] / total_tests

        return results

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive test report."""
        report = f"""
# Validation System Test Report

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results['timestamp']))}

## Summary
- **Total Tests:** {results['summary']['total_tests']}
- **Passed:** {results['summary']['total_passed']}
- **Failed:** {results['summary']['total_failed']}
- **Success Rate:** {results['summary']['success_rate']:.2%}

## Module Results
"""

        for module, result in results["suite_results"].items():
            report += f"""
### {module.title()} Module
- Tests Run: {result['tests_run']}
- Passed: {result['tests_passed']}
- Failed: {result['tests_failed']}
"""

            if result["failures"]:
                report += "\n**Failures:**\n"
                for failure in result["failures"]:
                    report += f"- {failure['test']}: {failure['error']}\n"

        return report

class ValidationTestOrchestrator:
    def __init__(self, config_path: str = None):
        self.framework = ValidationTestFramework()
        self.config = self._load_test_config(config_path)
        self._setup_test_suites()

    def _load_test_config(self, config_path: str) -> Dict[str, Any]:
        """Load test configuration."""
        default_config = {
            "parallel_execution": True,
            "max_workers": 4,
            "timeout_multiplier": 1.0,
            "memory_limit_mb": 2000,
            "cleanup_after_tests": True
        }

        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)

        return default_config

    def _setup_test_suites(self):
        """Initialize all test suites."""
        # This would be implemented to register actual test suites
        pass

    def run_tests(self, categories: List[str] = None, modules: List[str] = None) -> Dict[str, Any]:
        """Run tests with specified filters."""
        test_categories = [TestCategory(cat) for cat in categories] if categories else None

        if modules:
            # Filter test suites by module names
            filtered_suites = {k: v for k, v in self.framework.test_suites.items() if k in modules}
            original_suites = self.framework.test_suites
            self.framework.test_suites = filtered_suites

            try:
                return self.framework.run_all_tests(test_categories)
            finally:
                self.framework.test_suites = original_suites
        else:
            return self.framework.run_all_tests(test_categories)
```

### Sample Test Implementations

```python
class CoreValidationUnitTest(BaseValidationTest):
    def __init__(self):
        super().__init__(TestConfig(
            category=TestCategory.UNIT,
            timeout=30,
            parallel_safe=True,
            tags=["core", "validation"]
        ))

    def setup_test(self):
        self.validator = CoreValidator()
        self.test_nwb = self.test_data_manager.create_test_nwb_file({
            "size_mb": 10,
            "has_required_fields": True
        })

    def teardown_test(self):
        self.test_data_manager.cleanup()

    def run_test(self) -> Dict[str, Any]:
        start_time = time.time()

        try:
            context = ValidationContext(
                file_path=str(self.test_nwb),
                session_id="test_session"
            )

            result = self.validator.validate(context)
            execution_time = time.time() - start_time

            return {
                "passed": result.is_valid,
                "execution_time": execution_time,
                "issues_count": len(result.issues),
                "performance": {
                    "execution_time_ms": execution_time * 1000,
                    "memory_usage_mb": self._get_memory_usage()
                }
            }

        except Exception as e:
            return {
                "passed": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

class StreamingValidationPerformanceTest(BaseValidationTest):
    def __init__(self):
        super().__init__(TestConfig(
            category=TestCategory.PERFORMANCE,
            timeout=300,
            memory_limit_mb=4000,
            requires_test_data=True,
            tags=["streaming", "performance"]
        ))

    def setup_test(self):
        self.stream_validator = StreamValidator()
        self.large_test_file = self.test_data_manager.create_test_nwb_file({
            "size_mb": 1000,  # 1GB test file
            "dataset_count": 100
        })

    def teardown_test(self):
        self.test_data_manager.cleanup()

    def run_test(self) -> Dict[str, Any]:
        start_time = time.time()
        peak_memory = 0

        try:
            context = ValidationContext(
                file_path=str(self.large_test_file),
                session_id="perf_test"
            )

            results = []
            async for result in self.stream_validator.validate_stream(str(self.large_test_file), context):
                results.append(result)
                current_memory = self._get_memory_usage()
                peak_memory = max(peak_memory, current_memory)

            execution_time = time.time() - start_time

            return {
                "passed": all(r.is_valid for r in results),
                "execution_time": execution_time,
                "chunks_processed": len(results),
                "performance": {
                    "execution_time_ms": execution_time * 1000,
                    "peak_memory_mb": peak_memory,
                    "throughput_mb_per_sec": 1000 / execution_time,
                    "memory_efficiency": peak_memory < 2000  # Should stay under 2GB
                }
            }

        except Exception as e:
            return {
                "passed": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
                "performance": {"peak_memory_mb": peak_memory}
            }
```
            for dim, score in dimension_scores.items()
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, dimension_scores)

        return QualityReport(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            metrics=metrics,
            recommendations=recommendations,
            assessment_metadata={
                'metrics_count': len(metrics),
                'dimensions_assessed': len([d for d, s in dimension_scores.items() if s > 0]),
                'confidence_average': statistics.mean([m.confidence for m in metrics]) if metrics else 0
            }
        )

    def _generate_recommendations(self, metrics: List[QualityMetric],
                                 dimension_scores: Dict[str, float]) -> List[str]:
        """Generate quality improvement recommendations."""
        recommendations = []

        # Low scoring dimensions
        for dimension, score in dimension_scores.items():
            if score < 0.6:
                recommendations.append(f"Improve {dimension} quality (current score: {score:.2f})")

        # Specific metric recommendations
        low_metrics = [m for m in metrics if (m.score / m.max_score) < 0.7]
        for metric in low_metrics[:5]:  # Top 5 issues
            recommendations.append(f"Address {metric.name}: {metric.description}")

        return recommendations

    def _convert_to_validation_issues(self, quality_report: QualityReport) -> List[ValidationIssue]:
        """Convert quality assessment to validation issues."""
        issues = []

        # Create issues for low-scoring metrics
        for metric in quality_report.metrics:
            normalized_score = metric.score / metric.max_score if metric.max_score > 0 else 0

            if normalized_score < 0.5:
                severity = ValidationSeverity.WARNING
            elif normalized_score < 0.3:
                severity = ValidationSeverity.CRITICAL
            else:
                continue  # No issue for acceptable scores

            issue = ValidationIssue(
                severity=severity,
                message=f"Low quality score for {metric.name}: {normalized_score:.2f}",
                location=f"quality.{metric.dimension.value}",
                check_name=f"quality_{metric.name}",
                validator_name=self.name,
                remediation=f"Improve {metric.description}",
                details=metric.details
            )
            issues.append(issue)

        return issues
```

### Module 5: Domain Knowledge Validator

**Purpose:** Provides neuroscience-specific validation with scientific plausibility checking and domain expertise.

#### 5.1 Scientific Plausibility Checker (`domain/plausibility.py`)

```python
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import math

from ..core.base import BaseValidator, ValidationResult, ValidationIssue, ValidationContext, ValidationSeverity
from ..core.exceptions import validation_logger

class ExperimentType(Enum):
    """Types of neuroscience experiments."""
    ELECTROPHYSIOLOGY = "electrophysiology"
    IMAGING = "imaging"
    BEHAVIORAL = "behavioral"
    OPTOGENETICS = "optogenetics"
    PHARMACOLOGY = "pharmacology"

@dataclass
class ParameterRange:
    """Scientific parameter range with units."""
    min_value: float
    max_value: float
    unit: str
    description: str
    references: List[str] = None

class ScientificPlausibilityChecker(BaseValidator):
    """Validates scientific plausibility of experimental parameters."""

    def __init__(self, name: str = "plausibility_checker", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)

        # Initialize scientific parameter ranges
        self.parameter_ranges = self._initialize_parameter_ranges()
        self.experiment_specific_rules = self._initialize_experiment_rules()

    def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Validate scientific plausibility of experimental data."""
        start_time = time.time()

        validation_logger.log_validation_start(self.name, context)

        issues = []

        try:
            # Determine experiment type
            experiment_type = self._determine_experiment_type(data)

            # Validate general parameters
            general_issues = self._validate_general_parameters(data)
            issues.extend(general_issues)

            # Validate experiment-specific parameters
            if experiment_type:
                specific_issues = self._validate_experiment_specific(data, experiment_type)
                issues.extend(specific_issues)

            # Validate biological plausibility
            bio_issues = self._validate_biological_plausibility(data)
            issues.extend(bio_issues)

            # Validate equipment consistency
            equipment_issues = self._validate_equipment_consistency(data)
            issues.extend(equipment_issues)

            is_valid = not any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)

            summary = self._generate_summary(data, experiment_type, issues)
            metrics = self._calculate_metrics(issues)

            execution_time = time.time() - start_time

            result = self._create_result(
                context=context,
                is_valid=is_valid,
                issues=issues,
                summary=summary,
                metrics=metrics,
                execution_time=execution_time
            )

            validation_logger.log_validation_complete(result)
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            validation_logger.log_validation_error(e, ErrorContext(
                validator_name=self.name,
                validation_id=context.session_id
            ))

            error_issue = ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message=f"Plausibility checking failed: {str(e)}",
                location="plausibility_checker",
                check_name="plausibility_error",
                validator_name=self.name
            )

            return self._create_result(
                context=context,
                is_valid=False,
                issues=[error_issue],
                summary={"error": str(e)},
                execution_time=execution_time
            )

    def get_capabilities(self) -> Dict[str, Any]:
        """Return plausibility checker capabilities."""
        return {
            "experiment_types": [exp_type.value for exp_type in ExperimentType],
            "parameter_categories": list(self.parameter_ranges.keys()),
            "validation_types": ["parameter_ranges", "biological_plausibility", "equipment_consistency"],
            "features": ["scientific_references", "domain_expertise", "species_specific_validation"]
        }

    def _initialize_parameter_ranges(self) -> Dict[str, ParameterRange]:
        """Initialize scientifically validated parameter ranges."""
        return {
            # Electrophysiology parameters
            'sampling_rate': ParameterRange(
                min_value=1000, max_value=100000, unit='Hz',
                description='Electrophysiology sampling rate',
                references=['Nyquist theorem', 'Best practices in electrophysiology']
            ),
            'electrode_impedance': ParameterRange(
                min_value=0.1, max_value=50, unit='MΩ',
                description='Electrode impedance for extracellular recording'
            ),
            'spike_amplitude': ParameterRange(
                min_value=10, max_value=2000, unit='μV',
                description='Action potential amplitude'
            ),

            # Imaging parameters
            'frame_rate': ParameterRange(
                min_value=0.1, max_value=10000, unit='Hz',
                description='Imaging frame rate'
            ),
            'pixel_size': ParameterRange(
                min_value=0.01, max_value=100, unit='μm',
                description='Imaging pixel size'
            ),
            'exposure_time': ParameterRange(
                min_value=0.001, max_value=10, unit='s',
                description='Camera exposure time'
            ),

            # Behavioral parameters
            'session_duration': ParameterRange(
                min_value=60, max_value=28800, unit='s',
                description='Behavioral session duration (1 min to 8 hours)'
            ),
            'reaction_time': ParameterRange(
                min_value=0.05, max_value=10, unit='s',
                description='Behavioral reaction time'
            ),

            # Biological parameters
            'animal_age': ParameterRange(
                min_value=0, max_value=3650, unit='days',
                description='Animal age (up to 10 years)'
            ),
            'animal_weight': ParameterRange(
                min_value=0.01, max_value=100, unit='kg',
                description='Animal weight'
            )
        }

    def _initialize_experiment_rules(self) -> Dict[ExperimentType, Dict[str, Any]]:
        """Initialize experiment-specific validation rules."""
        return {
            ExperimentType.ELECTROPHYSIOLOGY: {
                'required_parameters': ['sampling_rate', 'electrode_impedance'],
                'parameter_relationships': [
                    ('sampling_rate', 'high_pass_filter', lambda sr, hpf: sr > 2 * hpf),
                    ('electrode_impedance', 'noise_level', lambda ei, nl: ei < 10 or nl < 50)
                ]
            },
            ExperimentType.IMAGING: {
                'required_parameters': ['frame_rate', 'pixel_size'],
                'parameter_relationships': [
                    ('frame_rate', 'exposure_time', lambda fr, et: et < 1/fr),
                    ('pixel_size', 'field_of_view', lambda ps, fov: ps * 1000 < fov)
                ]
            },
            ExperimentType.BEHAVIORAL: {
                'required_parameters': ['session_duration'],
                'parameter_relationships': [
                    ('session_duration', 'trial_count', lambda sd, tc: tc > 0 and tc < sd/2)
                ]
            }
        }

    def _determine_experiment_type(self, data: Dict[str, Any]) -> Optional[ExperimentType]:
        """Determine experiment type from data."""
        # Check for explicit experiment type
        exp_type_str = data.get('experiment_type', '').lower()
        for exp_type in ExperimentType:
            if exp_type.value in exp_type_str:
                return exp_type

        # Infer from available parameters
        if 'sampling_rate' in data or 'electrode_impedance' in data:
            return ExperimentType.ELECTROPHYSIOLOGY
        elif 'frame_rate' in data or 'pixel_size' in data:
            return ExperimentType.IMAGING
        elif 'session_duration' in data or 'trial_count' in data:
            return ExperimentType.BEHAVIORAL

        return None

    def _validate_general_parameters(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate general scientific parameters."""
        issues = []

        for param_name, value in data.items():
            if param_name in self.parameter_ranges:
                param_range = self.parameter_ranges[param_name]

                if isinstance(value, (int, float)):
                    if not (param_range.min_value <= value <= param_range.max_value):
                        severity = ValidationSeverity.WARNING
                        if value < param_range.min_value * 0.1 or value > param_range.max_value * 10:
                            severity = ValidationSeverity.CRITICAL

                        issue = ValidationIssue(
                            severity=severity,
                            message=f"{param_name} value {value} {param_range.unit} outside expected range",
                            location=param_name,
                            check_name="parameter_range_validation",
                            validator_name=self.name,
                            remediation=f"Expected range: {param_range.min_value}-{param_range.max_value} {param_range.unit}",
                            details={
                                'value': value,
                                'expected_range': (param_range.min_value, param_range.max_value),
                                'unit': param_range.unit,
                                'description': param_range.description
                            }
                        )
                        issues.append(issue)

        return issues

    def _validate_experiment_specific(self, data: Dict[str, Any],
                                    experiment_type: ExperimentType) -> List[ValidationIssue]:
        """Validate experiment-specific parameters and relationships."""
        issues = []
        rules = self.experiment_specific_rules.get(experiment_type, {})

        # Check required parameters
        required_params = rules.get('required_parameters', [])
        for param in required_params:
            if param not in data:
                issue = ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Missing recommended parameter for {experiment_type.value}: {param}",
                    location=param,
                    check_name="required_parameter_missing",
                    validator_name=self.name,
                    remediation=f"Add {param} parameter for better {experiment_type.value} validation"
                )
                issues.append(issue)

        # Check parameter relationships
        relationships = rules.get('parameter_relationships', [])
        for param1, param2, validation_func in relationships:
            if param1 in data and param2 in data:
                try:
                    if not validation_func(data[param1], data[param2]):
                        issue = ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message=f"Inconsistent relationship between {param1} and {param2}",
                            location=f"{param1},{param2}",
                            check_name="parameter_relationship_validation",
                            validator_name=self.name,
                            remediation=f"Check the relationship between {param1} and {param2} parameters"
                        )
                        issues.append(issue)
                except Exception as e:
                    validation_logger.warning(f"Failed to validate relationship {param1}-{param2}: {e}")

        return issues

    def _validate_biological_plausibility(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate biological plausibility of measurements."""
        issues = []

        # Species-specific validation
        species = data.get('species', '').lower()
        if species:
            species_issues = self._validate_species_specific_parameters(data, species)
            issues.extend(species_issues)

        # Cross-parameter biological validation
        bio_issues = self._validate_biological_relationships(data)
        issues.extend(bio_issues)

        return issues

    def _validate_species_specific_parameters(self, data: Dict[str, Any], species: str) -> List[ValidationIssue]:
        """Validate parameters specific to species."""
        issues = []

        # Example species-specific validation
        species_ranges = {
            'mouse': {'animal_weight': (0.015, 0.050)},  # 15-50g
            'rat': {'animal_weight': (0.200, 0.800)},    # 200-800g
            'monkey': {'animal_weight': (3.0, 15.0)},    # 3-15kg
        }

        if species in species_ranges:
            for param, (min_val, max_val) in species_ranges[species].items():
                if param in data:
                    value = data[param]
                    if isinstance(value, (int, float)) and not (min_val <= value <= max_val):
                        issue = ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message=f"{param} {value} unusual for {species}",
                            location=param,
                            check_name="species_specific_validation",
                            validator_name=self.name,
                            remediation=f"Expected {param} range for {species}: {min_val}-{max_val}",
                            details={'species': species, 'expected_range': (min_val, max_val)}
                        )
                        issues.append(issue)

        return issues

    def _validate_biological_relationships(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate biological relationships between parameters."""
        issues = []

        # Example: animal age vs weight relationship
        age = data.get('animal_age')
        weight = data.get('animal_weight')
        species = data.get('species', '').lower()

        if age and weight and species == 'mouse':
            # Very simplified growth curve validation
            expected_weight = 0.020 + (age / 365) * 0.025  # Rough mouse growth
            if abs(weight - expected_weight) > expected_weight * 0.5:
                issue = ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    message=f"Animal weight {weight}kg unusual for age {age} days in {species}",
                    location="animal_age,animal_weight",
                    check_name="biological_relationship_validation",
                    validator_name=self.name,
                    remediation="Verify animal age and weight measurements"
                )
                issues.append(issue)

        return issues

    def _validate_equipment_consistency(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate equipment and methodology consistency."""
        issues = []

        # Check equipment compatibility
        equipment_type = data.get('equipment_type', '').lower()
        manufacturer = data.get('manufacturer', '').lower()

        # Example equipment validation
        if 'tetrode' in equipment_type and 'sampling_rate' in data:
            sampling_rate = data['sampling_rate']
            if sampling_rate > 50000:
                issue = ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    message=f"High sampling rate {sampling_rate}Hz for tetrode recording",
                    location="equipment_type,sampling_rate",
                    check_name="equipment_consistency",
                    validator_name=self.name,
                    remediation="Verify sampling rate is appropriate for tetrode recordings"
                )
                issues.append(issue)

        return issues

    def _generate_summary(self, data: Dict[str, Any], experiment_type: Optional[ExperimentType],
                         issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Generate plausibility validation summary."""
        return {
            'experiment_type': experiment_type.value if experiment_type else 'unknown',
            'parameters_checked': len([k for k in data.keys() if k in self.parameter_ranges]),
            'total_issues': len(issues),
            'critical_issues': sum(1 for i in issues if i.severity == ValidationSeverity.CRITICAL),
            'warning_issues': sum(1 for i in issues if i.severity == ValidationSeverity.WARNING),
            'species': data.get('species', 'not_specified')
        }

    def _calculate_metrics(self, issues: List[ValidationIssue]) -> Dict[str, float]:
        """Calculate plausibility metrics."""
        total_issues = len(issues)
        critical_issues = sum(1 for i in issues if i.severity == ValidationSeverity.CRITICAL)

        return {
            'plausibility_score': 1.0 if total_issues == 0 else max(0.0, 1.0 - critical_issues * 0.3),
            'parameter_compliance_rate': 1.0 if total_issues == 0 else max(0.0, 1.0 - total_issues * 0.1),
            'biological_plausibility_score': 1.0 if critical_issues == 0 else 0.5
        }
```

### Module 6: Validation Orchestrator

**Purpose:** Coordinates execution of multiple validation engines with pipeline management, result aggregation, and workflow optimization.

#### 6.1 Pipeline Management (`orchestrator/pipeline.py`)

```python
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core.base import BaseValidator, ValidationResult, ValidationIssue, ValidationContext, ValidationSeverity, validator_registry
from ..core.config import ValidationConfig
from ..core.exceptions import validation_logger, ValidationError

class ExecutionMode(Enum):
    """Pipeline execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"

@dataclass
class ValidatorSpec:
    """Specification for validator in pipeline."""
    name: str
    validator_class: str
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    timeout_seconds: Optional[int] = None
    retry_count: int = 0

@dataclass
class PipelineStage:
    """A stage in validation pipeline."""
    name: str
    validators: List[ValidatorSpec]
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL
    continue_on_failure: bool = True
    timeout_seconds: Optional[int] = None

class ValidationPipeline:
    """Manages validation pipeline execution with dependency resolution."""

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()
        self.stages: List[PipelineStage] = []
        self.validator_instances: Dict[str, BaseValidator] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.logger = validation_logger

    def add_stage(self, stage: PipelineStage):
        """Add a validation stage to the pipeline."""
        self.stages.append(stage)
        self.logger.info(f"Added pipeline stage: {stage.name}")

    def add_validator(self, validator_spec: ValidatorSpec, stage_name: str = "default"):
        """Add validator to specific stage."""
        # Find or create stage
        stage = self._find_or_create_stage(stage_name)
        stage.validators.append(validator_spec)

        # Initialize validator instance
        self._initialize_validator(validator_spec)

    async def execute(self, data: Any, context: ValidationContext) -> List[ValidationResult]:
        """Execute complete validation pipeline."""
        start_time = time.time()
        all_results = []

        self.logger.info(f"Starting pipeline execution with {len(self.stages)} stages")

        try:
            for stage_idx, stage in enumerate(self.stages):
                self.logger.info(f"Executing stage {stage_idx + 1}/{len(self.stages)}: {stage.name}")

                # Update context with previous results
                context.metadata['validation_results'] = all_results

                stage_results = await self._execute_stage(stage, data, context)
                all_results.extend(stage_results)

                # Check if we should continue based on results
                if not stage.continue_on_failure and self._has_critical_failures(stage_results):
                    self.logger.warning(f"Stopping pipeline due to critical failures in stage {stage.name}")
                    break

            execution_time = time.time() - start_time
            self.logger.info(f"Pipeline execution completed in {execution_time:.2f}s")

            # Record execution history
            self._record_execution(data, context, all_results, execution_time)

            return all_results

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Pipeline execution failed after {execution_time:.2f}s: {e}")
            raise ValidationError(f"Pipeline execution failed: {str(e)}")

    async def _execute_stage(self, stage: PipelineStage, data: Any,
                           context: ValidationContext) -> List[ValidationResult]:
        """Execute a single pipeline stage."""
        stage_start = time.time()
        enabled_validators = [v for v in stage.validators if v.enabled]

        if not enabled_validators:
            self.logger.warning(f"No enabled validators in stage {stage.name}")
            return []

        # Resolve dependencies
        execution_order = self._resolve_dependencies(enabled_validators)

        results = []

        if stage.execution_mode == ExecutionMode.SEQUENTIAL:
            results = await self._execute_sequential(execution_order, data, context, stage.timeout_seconds)
        elif stage.execution_mode == ExecutionMode.PARALLEL:
            results = await self._execute_parallel(execution_order, data, context, stage.timeout_seconds)
        elif stage.execution_mode == ExecutionMode.CONDITIONAL:
            results = await self._execute_conditional(execution_order, data, context, stage.timeout_seconds)

        stage_time = time.time() - stage_start
        self.logger.info(f"Stage {stage.name} completed in {stage_time:.2f}s with {len(results)} results")

        return results

    async def _execute_sequential(self, validator_specs: List[ValidatorSpec],
                                data: Any, context: ValidationContext,
                                timeout: Optional[int]) -> List[ValidationResult]:
        """Execute validators sequentially."""
        results = []

        for spec in validator_specs:
            try:
                validator = self.validator_instances[spec.name]
                result = await self._execute_validator_with_timeout(
                    validator, data, context, spec.timeout_seconds or timeout
                )
                results.append(result)

                # Update context with new result
                context.metadata.setdefault('validation_results', []).append(result)

            except Exception as e:
                self.logger.error(f"Validator {spec.name} failed: {e}")
                if spec.retry_count > 0:
                    results.extend(await self._retry_validator(spec, data, context))

        return results

    async def _execute_parallel(self, validator_specs: List[ValidatorSpec],
                              data: Any, context: ValidationContext,
                              timeout: Optional[int]) -> List[ValidationResult]:
        """Execute validators in parallel."""
        tasks = []

        for spec in validator_specs:
            validator = self.validator_instances[spec.name]
            task = asyncio.create_task(
                self._execute_validator_with_timeout(
                    validator, data, context, spec.timeout_seconds or timeout
                )
            )
            tasks.append((task, spec))

        results = []
        for task, spec in tasks:
            try:
                result = await task
                results.append(result)
            except Exception as e:
                self.logger.error(f"Validator {spec.name} failed: {e}")
                if spec.retry_count > 0:
                    retry_results = await self._retry_validator(spec, data, context)
                    results.extend(retry_results)

        return results

    async def _execute_conditional(self, validator_specs: List[ValidatorSpec],
                                 data: Any, context: ValidationContext,
                                 timeout: Optional[int]) -> List[ValidationResult]:
        """Execute validators conditionally based on previous results."""
        results = []

        for spec in validator_specs:
            # Check if conditions are met based on previous results
            if self._should_execute_validator(spec, context):
                try:
                    validator = self.validator_instances[spec.name]
                    result = await self._execute_validator_with_timeout(
                        validator, data, context, spec.timeout_seconds or timeout
                    )
                    results.append(result)
                    context.metadata.setdefault('validation_results', []).append(result)
                except Exception as e:
                    self.logger.error(f"Conditional validator {spec.name} failed: {e}")

        return results

    async def _execute_validator_with_timeout(self, validator: BaseValidator,
                                            data: Any, context: ValidationContext,
                                            timeout: Optional[int]) -> ValidationResult:
        """Execute validator with timeout."""
        if timeout:
            return await asyncio.wait_for(
                self._run_validator_async(validator, data, context),
                timeout=timeout
            )
        else:
            return await self._run_validator_async(validator, data, context)

    async def _run_validator_async(self, validator: BaseValidator,
                                 data: Any, context: ValidationContext) -> ValidationResult:
        """Run validator in async context."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, validator.validate, data, context)

    def _resolve_dependencies(self, validator_specs: List[ValidatorSpec]) -> List[ValidatorSpec]:
        """Resolve validator dependencies and return execution order."""
        # Simple topological sort
        resolved = []
        remaining = validator_specs.copy()

        while remaining:
            made_progress = False

            for spec in remaining[:]:
                dependencies_met = all(
                    dep in [r.name for r in resolved]
                    for dep in spec.dependencies
                )

                if dependencies_met:
                    resolved.append(spec)
                    remaining.remove(spec)
                    made_progress = True

            if not made_progress and remaining:
                # Circular dependency or missing dependency
                raise ValidationError(f"Cannot resolve dependencies for validators: {[s.name for s in remaining]}")

        return resolved

    def _should_execute_validator(self, spec: ValidatorSpec, context: ValidationContext) -> bool:
        """Determine if validator should execute based on conditions."""
        # Check if dependencies produced valid results
        previous_results = context.metadata.get('validation_results', [])

        for dep_name in spec.dependencies:
            dep_results = [r for r in previous_results if r.validator_name == dep_name]
            if not dep_results or not any(r.is_valid for r in dep_results):
                return False

        return True

    async def _retry_validator(self, spec: ValidatorSpec, data: Any,
                             context: ValidationContext) -> List[ValidationResult]:
        """Retry failed validator."""
        results = []

        for retry in range(spec.retry_count):
            try:
                self.logger.info(f"Retrying validator {spec.name} (attempt {retry + 1}/{spec.retry_count})")
                validator = self.validator_instances[spec.name]
                result = await self._execute_validator_with_timeout(
                    validator, data, context, spec.timeout_seconds
                )
                results.append(result)
                break
            except Exception as e:
                self.logger.warning(f"Retry {retry + 1} for {spec.name} failed: {e}")

        return results

    def _has_critical_failures(self, results: List[ValidationResult]) -> bool:
        """Check if results contain critical failures."""
        return any(
            not result.is_valid and
            any(issue.severity == ValidationSeverity.CRITICAL for issue in result.issues)
            for result in results
        )

    def _find_or_create_stage(self, stage_name: str) -> PipelineStage:
        """Find existing stage or create new one."""
        for stage in self.stages:
            if stage.name == stage_name:
                return stage

        new_stage = PipelineStage(name=stage_name, validators=[])
        self.stages.append(new_stage)
        return new_stage

    def _initialize_validator(self, spec: ValidatorSpec):
        """Initialize validator instance."""
        if spec.name not in self.validator_instances:
            try:
                validator = validator_registry.get_validator(spec.validator_class, spec.config)
                self.validator_instances[spec.name] = validator
                self.logger.info(f"Initialized validator: {spec.name}")
            except Exception as e:
                raise ValidationError(f"Failed to initialize validator {spec.name}: {e}")

    def _record_execution(self, data: Any, context: ValidationContext,
                         results: List[ValidationResult], execution_time: float):
        """Record pipeline execution for analysis."""
        execution_record = {
            'timestamp': time.time(),
            'session_id': context.session_id,
            'stages_executed': len(self.stages),
            'total_validators': sum(len(stage.validators) for stage in self.stages),
            'total_results': len(results),
            'execution_time': execution_time,
            'success_rate': sum(1 for r in results if r.is_valid) / max(len(results), 1),
            'critical_issues': sum(
                sum(1 for issue in r.issues if issue.severity == ValidationSeverity.CRITICAL)
                for r in results
            )
        }

        self.execution_history.append(execution_record)

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline execution statistics."""
        if not self.execution_history:
            return {'executions': 0}

        recent_executions = self.execution_history[-10:]  # Last 10 executions

        return {
            'total_executions': len(self.execution_history),
            'average_execution_time': sum(e['execution_time'] for e in recent_executions) / len(recent_executions),
            'average_success_rate': sum(e['success_rate'] for e in recent_executions) / len(recent_executions),
            'total_critical_issues': sum(e['critical_issues'] for e in recent_executions),
            'configured_stages': len(self.stages),
            'total_validators': sum(len(stage.validators) for stage in self.stages)
        }
```

#### 6.2 Results Aggregation (`orchestrator/aggregator.py`)

```python
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from ..core.base import ValidationResult, ValidationIssue, ValidationSeverity
from ..core.exceptions import validation_logger

@dataclass
class AggregatedResult:
    """Aggregated validation results from multiple validators."""
    overall_status: bool
    total_issues: int
    issues_by_severity: Dict[ValidationSeverity, int]
    issues_by_validator: Dict[str, int]
    consolidated_issues: List[ValidationIssue]
    validator_results: List[ValidationResult]
    summary_statistics: Dict[str, Any]
    quality_scores: Dict[str, float]
    recommendations: List[str]

class ResultsAggregator:
    """Aggregates and consolidates results from multiple validators."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.deduplication_threshold = self.config.get('deduplication_threshold', 0.8)
        self.logger = validation_logger

    def aggregate(self, results: List[ValidationResult]) -> AggregatedResult:
        """Aggregate multiple validation results into unified report."""
        if not results:
            return self._create_empty_result()

        self.logger.info(f"Aggregating {len(results)} validation results")

        # Consolidate and deduplicate issues
        consolidated_issues = self._consolidate_issues(results)

        # Calculate overall status
        overall_status = self._calculate_overall_status(results, consolidated_issues)

        # Generate statistics
        statistics_dict = self._generate_statistics(results, consolidated_issues)

        # Calculate quality scores
        quality_scores = self._calculate_quality_scores(results)

        # Generate recommendations
        recommendations = self._generate_recommendations(results, consolidated_issues)

        aggregated = AggregatedResult(
            overall_status=overall_status,
            total_issues=len(consolidated_issues),
            issues_by_severity=self._count_by_severity(consolidated_issues),
            issues_by_validator=self._count_by_validator(consolidated_issues),
            consolidated_issues=consolidated_issues,
            validator_results=results,
            summary_statistics=statistics_dict,
            quality_scores=quality_scores,
            recommendations=recommendations
        )

        self.logger.info(f"Aggregation complete: {aggregated.total_issues} issues, status: {overall_status}")
        return aggregated

    def _consolidate_issues(self, results: List[ValidationResult]) -> List[ValidationIssue]:
        """Consolidate and deduplicate issues from multiple validators."""
        all_issues = []
        for result in results:
            all_issues.extend(result.issues)

        if not all_issues:
            return []

        # Group similar issues
        issue_groups = self._group_similar_issues(all_issues)

        # Create consolidated issues
        consolidated = []
        for group in issue_groups:
            if len(group) == 1:
                consolidated.append(group[0])
            else:
                consolidated_issue = self._merge_issues(group)
                consolidated.append(consolidated_issue)

        # Sort by severity and frequency
        consolidated.sort(key=lambda x: (x.severity.value, -getattr(x, 'occurrence_count', 1)))

        return consolidated

    def _group_similar_issues(self, issues: List[ValidationIssue]) -> List[List[ValidationIssue]]:
        """Group similar issues together for deduplication."""
        groups = []
        processed = set()

        for i, issue in enumerate(issues):
            if i in processed:
                continue

            group = [issue]
            processed.add(i)

            for j, other_issue in enumerate(issues[i+1:], i+1):
                if j in processed:
                    continue

                if self._are_issues_similar(issue, other_issue):
                    group.append(other_issue)
                    processed.add(j)

            groups.append(group)

        return groups

    def _are_issues_similar(self, issue1: ValidationIssue, issue2: ValidationIssue) -> bool:
        """Determine if two issues are similar enough to merge."""
        # Same check name and severity
        if issue1.check_name != issue2.check_name or issue1.severity != issue2.severity:
            return False

        # Similar location
        if self._calculate_location_similarity(issue1.location, issue2.location) < self.deduplication_threshold:
            return False

        # Similar message (simplified text similarity)
        if self._calculate_message_similarity(issue1.message, issue2.message) < self.deduplication_threshold:
            return False

        return True

    def _calculate_location_similarity(self, loc1: str, loc2: str) -> float:
        """Calculate similarity between issue locations."""
        if loc1 == loc2:
            return 1.0

        # Split locations and compare components
        parts1 = set(loc1.split('.'))
        parts2 = set(loc2.split('.'))

        if not parts1 or not parts2:
            return 0.0

        intersection = len(parts1.intersection(parts2))
        union = len(parts1.union(parts2))

        return intersection / union if union > 0 else 0.0

    def _calculate_message_similarity(self, msg1: str, msg2: str) -> float:
        """Calculate similarity between issue messages."""
        if msg1 == msg2:
            return 1.0

        # Simple word-based similarity
        words1 = set(msg1.lower().split())
        words2 = set(msg2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _merge_issues(self, issues: List[ValidationIssue]) -> ValidationIssue:
        """Merge multiple similar issues into one consolidated issue."""
        primary_issue = issues[0]
        occurrence_count = len(issues)

        # Collect all validator names
        validator_names = list(set(issue.validator_name for issue in issues))

        # Merge locations
        locations = list(set(issue.location for issue in issues))

        # Create consolidated issue
        consolidated = ValidationIssue(
            severity=primary_issue.severity,
            message=f"{primary_issue.message} (occurred {occurrence_count} times)",
            location=", ".join(locations),
            check_name=primary_issue.check_name,
            validator_name=", ".join(validator_names),
            object_type=primary_issue.object_type,
            object_name=primary_issue.object_name,
            remediation=primary_issue.remediation,
            details={
                **primary_issue.details,
                'occurrence_count': occurrence_count,
                'merged_from_validators': validator_names,
                'all_locations': locations
            }
        )

        # Add occurrence count as attribute for sorting
        setattr(consolidated, 'occurrence_count', occurrence_count)

        return consolidated

    def _calculate_overall_status(self, results: List[ValidationResult],
                                issues: List[ValidationIssue]) -> bool:
        """Calculate overall validation status."""
        # Check if any validator failed completely
        if any(not result.is_valid for result in results):
            return False

        # Check for critical issues
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        return len(critical_issues) == 0

    def _count_by_severity(self, issues: List[ValidationIssue]) -> Dict[ValidationSeverity, int]:
        """Count issues by severity level."""
        counts = {severity: 0 for severity in ValidationSeverity}
        for issue in issues:
            counts[issue.severity] += 1
        return counts

    def _count_by_validator(self, issues: List[ValidationIssue]) -> Dict[str, int]:
        """Count issues by validator."""
        counts = defaultdict(int)
        for issue in issues:
            # Handle merged validator names
            validator_names = issue.validator_name.split(", ")
            for validator_name in validator_names:
                counts[validator_name] += 1
        return dict(counts)

    def _generate_statistics(self, results: List[ValidationResult],
                           issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Generate summary statistics."""
        execution_times = [r.execution_time for r in results if r.execution_time > 0]

        return {
            'total_validators': len(results),
            'successful_validators': sum(1 for r in results if r.is_valid),
            'total_execution_time': sum(execution_times),
            'average_execution_time': statistics.mean(execution_times) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0,
            'total_unique_issues': len(issues),
            'most_common_check': self._get_most_common_check(issues),
            'validators_with_issues': len(set(issue.validator_name for issue in issues)),
            'issue_density': len(issues) / len(results) if results else 0
        }

    def _calculate_quality_scores(self, results: List[ValidationResult]) -> Dict[str, float]:
        """Calculate aggregated quality scores."""
        quality_scores = {}

        # Collect all metrics from results
        all_metrics = {}
        for result in results:
            for metric_name, value in result.metrics.items():
                if metric_name not in all_metrics:
                    all_metrics[metric_name] = []
                all_metrics[metric_name].append(value)

        # Calculate aggregate scores
        for metric_name, values in all_metrics.items():
            if values:
                quality_scores[f"avg_{metric_name}"] = statistics.mean(values)
                quality_scores[f"min_{metric_name}"] = min(values)
                quality_scores[f"max_{metric_name}"] = max(values)

        # Calculate overall quality score
        validator_success_rate = sum(1 for r in results if r.is_valid) / len(results)
        quality_scores['overall_quality_score'] = validator_success_rate

        return quality_scores

    def _generate_recommendations(self, results: List[ValidationResult],
                                issues: List[ValidationIssue]) -> List[str]:
        """Generate actionable recommendations based on aggregated results."""
        recommendations = []

        # Critical issues recommendations
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        if critical_issues:
            recommendations.append(f"Address {len(critical_issues)} critical issues before proceeding")

        # High-frequency issues
        issue_frequency = defaultdict(int)
        for issue in issues:
            issue_frequency[issue.check_name] += getattr(issue, 'occurrence_count', 1)

        high_freq_issues = sorted(issue_frequency.items(), key=lambda x: x[1], reverse=True)[:3]
        for check_name, count in high_freq_issues:
            if count > 1:
                recommendations.append(f"Review '{check_name}' validation - appears {count} times")

        # Performance recommendations
        execution_times = [r.execution_time for r in results if r.execution_time > 0]
        if execution_times and max(execution_times) > 60:  # More than 1 minute
            slow_validators = [r.validator_name for r in results if r.execution_time > 60]
            recommendations.append(f"Optimize performance for slow validators: {', '.join(slow_validators)}")

        # Validator-specific recommendations
        failed_validators = [r.validator_name for r in results if not r.is_valid]
        if failed_validators:
            recommendations.append(f"Review configuration for failed validators: {', '.join(failed_validators)}")

        return recommendations[:10]  # Limit to top 10 recommendations

    def _get_most_common_check(self, issues: List[ValidationIssue]) -> str:
        """Get the most frequently occurring check name."""
        if not issues:
            return "none"

        check_counts = defaultdict(int)
        for issue in issues:
            check_counts[issue.check_name] += getattr(issue, 'occurrence_count', 1)

        return max(check_counts.items(), key=lambda x: x[1])[0] if check_counts else "none"

    def _create_empty_result(self) -> AggregatedResult:
        """Create empty aggregated result."""
        return AggregatedResult(
            overall_status=True,
            total_issues=0,
            issues_by_severity={severity: 0 for severity in ValidationSeverity},
            issues_by_validator={},
            consolidated_issues=[],
            validator_results=[],
            summary_statistics={'total_validators': 0},
            quality_scores={'overall_quality_score': 1.0},
            recommendations=[]
        )
```

### Module 7: Reporting and Analytics

**Purpose:** Generates comprehensive reports and provides analytics capabilities for validation results and quality trends.

#### 7.1 Report Generation (`reporting/generator.py`)

```python
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json
import time
from datetime import datetime

from ..core.base import ValidationResult, ValidationIssue
from ..orchestrator.aggregator import AggregatedResult
from ..core.exceptions import validation_logger

class ReportFormat(Enum):
    """Supported report formats."""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "md"

@dataclass
class ReportTemplate:
    """Report template configuration."""
    name: str
    format: ReportFormat
    template_path: Optional[str] = None
    custom_sections: List[str] = None
    include_charts: bool = True
    include_details: bool = True

class ReportGenerator:
    """Generates validation reports in multiple formats."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.templates: Dict[str, ReportTemplate] = {}
        self.output_directory = Path(self.config.get('output_directory', './reports'))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.logger = validation_logger

        # Initialize default templates
        self._initialize_default_templates()

    def generate_report(self, aggregated_result: AggregatedResult,
                       template_name: str = "standard",
                       output_filename: Optional[str] = None) -> str:
        """Generate validation report using specified template."""

        if template_name not in self.templates:
            raise ValueError(f"Template {template_name} not found")

        template = self.templates[template_name]

        # Generate filename if not provided
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"validation_report_{timestamp}.{template.format.value}"

        output_path = self.output_directory / output_filename

        self.logger.info(f"Generating {template.format.value} report: {output_path}")

        # Generate report based on format
        if template.format == ReportFormat.JSON:
            content = self._generate_json_report(aggregated_result, template)
        elif template.format == ReportFormat.HTML:
            content = self._generate_html_report(aggregated_result, template)
        elif template.format == ReportFormat.PDF:
            content = self._generate_pdf_report(aggregated_result, template)
        elif template.format == ReportFormat.MARKDOWN:
            content = self._generate_markdown_report(aggregated_result, template)
        else:
            raise ValueError(f"Unsupported format: {template.format}")

        # Write report to file
        if template.format == ReportFormat.PDF:
            # Binary content for PDF
            with open(output_path, 'wb') as f:
                f.write(content)
        else:
            # Text content for other formats
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

        self.logger.info(f"Report generated successfully: {output_path}")
        return str(output_path)

    def _generate_json_report(self, result: AggregatedResult, template: ReportTemplate) -> str:
        """Generate JSON format report."""
        report_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'template': template.name,
                'generator_version': '1.0.0'
            },
            'summary': {
                'overall_status': result.overall_status,
                'total_issues': result.total_issues,
                'issues_by_severity': {k.value: v for k, v in result.issues_by_severity.items()},
                'quality_scores': result.quality_scores,
                'statistics': result.summary_statistics
            },
            'validators': [
                {
                    'name': vr.validator_name,
                    'status': vr.is_valid,
                    'execution_time': vr.execution_time,
                    'issue_count': len(vr.issues),
                    'metrics': vr.metrics
                }
                for vr in result.validator_results
            ],
            'issues': [
                {
                    'id': issue.id,
                    'severity': issue.severity.value,
                    'message': issue.message,
                    'location': issue.location,
                    'check_name': issue.check_name,
                    'validator': issue.validator_name,
                    'remediation': issue.remediation,
                    'details': issue.details
                }
                for issue in result.consolidated_issues
            ] if template.include_details else [],
            'recommendations': result.recommendations
        }

        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def _generate_html_report(self, result: AggregatedResult, template: ReportTemplate) -> str:
        """Generate HTML format report."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 5px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #333; }
        .metric-label { color: #666; font-size: 0.9em; }
        .status-pass { color: #28a745; }
        .status-fail { color: #dc3545; }
        .issue { border-left: 4px solid #ddd; padding: 10px; margin-bottom: 10px; }
        .issue.critical { border-left-color: #dc3545; background: #f8d7da; }
        .issue.warning { border-left-color: #ffc107; background: #fff3cd; }
        .issue.info { border-left-color: #17a2b8; background: #d1ecf1; }
        .recommendations { background: #e7f3ff; padding: 20px; border-radius: 5px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>NWB Validation Report</h1>
        <p>Generated: {timestamp}</p>
        <p>Overall Status: <span class="{status_class}">{overall_status}</span></p>
    </div>

    <div class="summary">
        <div class="metric-card">
            <div class="metric-value">{total_issues}</div>
            <div class="metric-label">Total Issues</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{critical_count}</div>
            <div class="metric-label">Critical Issues</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{validator_count}</div>
            <div class="metric-label">Validators Run</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{quality_score:.2f}</div>
            <div class="metric-label">Quality Score</div>
        </div>
    </div>

    <h2>Validation Results</h2>
    <table>
        <thead>
            <tr>
                <th>Validator</th>
                <th>Status</th>
                <th>Issues</th>
                <th>Execution Time</th>
            </tr>
        </thead>
        <tbody>
            {validator_rows}
        </tbody>
    </table>

    {issues_section}

    <div class="recommendations">
        <h2>Recommendations</h2>
        <ul>
            {recommendation_items}
        </ul>
    </div>
</body>
</html>
        """

        # Prepare template variables
        status_class = "status-pass" if result.overall_status else "status-fail"
        overall_status = "PASS" if result.overall_status else "FAIL"

        validator_rows = "\n".join([
            f"""<tr>
                <td>{vr.validator_name}</td>
                <td><span class="{'status-pass' if vr.is_valid else 'status-fail'}">
                    {'PASS' if vr.is_valid else 'FAIL'}</span></td>
                <td>{len(vr.issues)}</td>
                <td>{vr.execution_time:.2f}s</td>
            </tr>"""
            for vr in result.validator_results
        ])

        issues_section = ""
        if template.include_details and result.consolidated_issues:
            issue_items = "\n".join([
                f"""<div class="issue {issue.severity.value}">
                    <strong>{issue.severity.value.upper()}:</strong> {issue.message}<br>
                    <small>Location: {issue.location} | Check: {issue.check_name}</small>
                    {f'<br><em>Remediation: {issue.remediation}</em>' if issue.remediation else ''}
                </div>"""
                for issue in result.consolidated_issues[:20]  # Limit to first 20 issues
            ])
            issues_section = f"<h2>Issues Found</h2>\n{issue_items}"

        recommendation_items = "\n".join([
            f"<li>{rec}</li>" for rec in result.recommendations
        ])

        return html_template.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status_class=status_class,
            overall_status=overall_status,
            total_issues=result.total_issues,
            critical_count=result.issues_by_severity.get(ValidationSeverity.CRITICAL, 0),
            validator_count=len(result.validator_results),
            quality_score=result.quality_scores.get('overall_quality_score', 0.0),
            validator_rows=validator_rows,
            issues_section=issues_section,
            recommendation_items=recommendation_items
        )

    def _generate_markdown_report(self, result: AggregatedResult, template: ReportTemplate) -> str:
        """Generate Markdown format report."""
        report = f"""# NWB Validation Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Overall Status:** {'✅ PASS' if result.overall_status else '❌ FAIL'}

## Summary

| Metric | Value |
|--------|-------|
| Total Issues | {result.total_issues} |
| Critical Issues | {result.issues_by_severity.get(ValidationSeverity.CRITICAL, 0)} |
| Warning Issues | {result.issues_by_severity.get(ValidationSeverity.WARNING, 0)} |
| Validators Run | {len(result.validator_results)} |
| Quality Score | {result.quality_scores.get('overall_quality_score', 0.0):.2f} |

## Validator Results

| Validator | Status | Issues | Execution Time |
|-----------|--------|--------|----------------|
"""

        for vr in result.validator_results:
            status_icon = "✅" if vr.is_valid else "❌"
            report += f"| {vr.validator_name} | {status_icon} | {len(vr.issues)} | {vr.execution_time:.2f}s |\n"

        if template.include_details and result.consolidated_issues:
            report += "\n## Issues Found\n\n"

            for issue in result.consolidated_issues[:20]:  # Limit to first 20
                severity_icon = {
                    ValidationSeverity.CRITICAL: "🔴",
                    ValidationSeverity.WARNING: "🟡",
                    ValidationSeverity.INFO: "🔵",
                    ValidationSeverity.BEST_PRACTICE: "💡"
                }.get(issue.severity, "⚪")

                report += f"""### {severity_icon} {issue.severity.value.upper()}: {issue.message}

**Location:** {issue.location}
**Check:** {issue.check_name}
**Validator:** {issue.validator_name}
"""
                if issue.remediation:
                    report += f"**Remediation:** {issue.remediation}\n"

                report += "\n---\n\n"

        if result.recommendations:
            report += "## Recommendations\n\n"
            for i, rec in enumerate(result.recommendations, 1):
                report += f"{i}. {rec}\n"

        return report

    def _generate_pdf_report(self, result: AggregatedResult, template: ReportTemplate) -> bytes:
        """Generate PDF format report."""
        # This would require a PDF library like reportlab or weasyprint
        # For now, return placeholder
        html_content = self._generate_html_report(result, template)

        # Convert HTML to PDF (placeholder implementation)
        # In a real implementation, you would use a library like:
        # - weasyprint: HTML/CSS to PDF
        # - reportlab: Direct PDF generation
        # - pdfkit: wkhtmltopdf wrapper

        return html_content.encode('utf-8')  # Placeholder

    def _initialize_default_templates(self):
        """Initialize default report templates."""
        self.templates = {
            "standard": ReportTemplate(
                name="standard",
                format=ReportFormat.HTML,
                include_charts=True,
                include_details=True
            ),
            "summary": ReportTemplate(
                name="summary",
                format=ReportFormat.JSON,
                include_charts=False,
                include_details=False
            ),
            "detailed": ReportTemplate(
                name="detailed",
                format=ReportFormat.HTML,
                include_charts=True,
                include_details=True
            ),
            "markdown": ReportTemplate(
                name="markdown",
                format=ReportFormat.MARKDOWN,
                include_charts=False,
                include_details=True
            )
        }

    def register_template(self, template: ReportTemplate):
        """Register a custom report template."""
        self.templates[template.name] = template
        self.logger.info(f"Registered custom template: {template.name}")

    def list_templates(self) -> List[str]:
        """List available report templates."""
        return list(self.templates.keys())
```

### Module 8: MCP Integration Layer

**Purpose:** Provides MCP (Model Context Protocol) integration for seamless API access and service integration.

#### 8.1 MCP Tools Interface (`mcp/tools.py`)

```python
from typing import Dict, Any, List, Optional, Union, Callable
import asyncio
import json
from datetime import datetime

from ..core.base import ValidationContext, ValidationResult
from ..orchestrator.pipeline import ValidationPipeline
from ..orchestrator.aggregator import ResultsAggregator
from ..reporting.generator import ReportGenerator
from ..core.config import ConfigManager
from ..core.exceptions import validation_logger, ValidationError

class MCPToolsInterface:
    """MCP tools interface for validation system."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.pipeline = ValidationPipeline()
        self.aggregator = ResultsAggregator()
        self.report_generator = ReportGenerator()
        self.config_manager = ConfigManager()
        self.logger = validation_logger

        # Initialize MCP tools
        self.tools = self._initialize_tools()

    def _initialize_tools(self) -> Dict[str, Callable]:
        """Initialize available MCP tools."""
        return {
            "validate_nwb_file": self._validate_nwb_file,
            "validate_metadata": self._validate_metadata,
            "run_validation_pipeline": self._run_validation_pipeline,
            "generate_validation_report": self._generate_validation_report,
            "get_validation_status": self._get_validation_status,
            "configure_validators": self._configure_validators,
            "list_available_validators": self._list_available_validators,
            "get_validator_capabilities": self._get_validator_capabilities,
            "analyze_validation_trends": self._analyze_validation_trends,
            "export_validation_results": self._export_validation_results
        }

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool with given parameters."""
        if tool_name not in self.tools:
            raise ValidationError(f"Unknown tool: {tool_name}")

        try:
            self.logger.info(f"Executing MCP tool: {tool_name}")
            result = await self.tools[tool_name](**parameters)

            return {
                "success": True,
                "tool": tool_name,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_name} - {str(e)}")
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _validate_nwb_file(self, file_path: str,
                                validation_profile: str = "standard",
                                **kwargs) -> Dict[str, Any]:
        """Validate a single NWB file."""
        context = ValidationContext(
            file_path=file_path,
            configuration={"profile": validation_profile, **kwargs}
        )

        # Configure pipeline based on profile
        profile = self.config_manager.get_profile(validation_profile)
        self._configure_pipeline_from_profile(profile)

        # Run validation
        results = await self.pipeline.execute(file_path, context)

        # Aggregate results
        aggregated = self.aggregator.aggregate(results)

        return {
            "file_path": file_path,
            "overall_status": aggregated.overall_status,
            "total_issues": aggregated.total_issues,
            "issues_by_severity": {k.value: v for k, v in aggregated.issues_by_severity.items()},
            "quality_scores": aggregated.quality_scores,
            "execution_summary": aggregated.summary_statistics,
            "validation_id": context.session_id
        }

    async def _validate_metadata(self, metadata: Dict[str, Any],
                                schema_name: str,
                                class_name: str,
                                **kwargs) -> Dict[str, Any]:
        """Validate metadata against LinkML schema."""
        from ..linkml.validator import LinkMLValidator

        validator = LinkMLValidator(config={
            'schema_name': schema_name,
            'class_name': class_name,
            **kwargs
        })

        context = ValidationContext(
            configuration={'schema_name': schema_name, 'class_name': class_name}
        )

        result = validator.validate(metadata, context)

        return {
            "is_valid": result.is_valid,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "location": issue.location,
                    "remediation": issue.remediation
                }
                for issue in result.issues
            ],
            "metrics": result.metrics,
            "validation_id": result.validation_id
        }

    async def _run_validation_pipeline(self, data: Any,
                                     pipeline_config: Dict[str, Any],
                                     **kwargs) -> Dict[str, Any]:
        """Run custom validation pipeline."""
        # Configure pipeline from provided config
        pipeline = ValidationPipeline()
        self._configure_pipeline_from_config(pipeline, pipeline_config)

        context = ValidationContext(configuration=kwargs)
        results = await pipeline.execute(data, context)

        aggregated = self.aggregator.aggregate(results)

        return {
            "pipeline_status": aggregated.overall_status,
            "total_validators": len(results),
            "successful_validators": sum(1 for r in results if r.is_valid),
            "total_issues": aggregated.total_issues,
            "quality_scores": aggregated.quality_scores,
            "recommendations": aggregated.recommendations,
            "execution_stats": pipeline.get_pipeline_stats(),
            "validation_id": context.session_id
        }

    async def _generate_validation_report(self, validation_id: str,
                                        template_name: str = "standard",
                                        output_format: str = "html",
                                        **kwargs) -> Dict[str, Any]:
        """Generate validation report."""
        # In a real implementation, you would retrieve results by validation_id
        # For now, this is a placeholder

        # Mock aggregated result for demonstration
        from ..orchestrator.aggregator import AggregatedResult
        aggregated = AggregatedResult(
            overall_status=True,
            total_issues=0,
            issues_by_severity={},
            issues_by_validator={},
            consolidated_issues=[],
            validator_results=[],
            summary_statistics={},
            quality_scores={'overall_quality_score': 1.0},
            recommendations=[]
        )

        report_path = self.report_generator.generate_report(
            aggregated, template_name, **kwargs
        )

        return {
            "report_path": report_path,
            "format": output_format,
            "template": template_name,
            "validation_id": validation_id
        }

    async def _get_validation_status(self, validation_id: str) -> Dict[str, Any]:
        """Get status of validation operation."""
        # Placeholder implementation
        return {
            "validation_id": validation_id,
            "status": "completed",
            "progress": 100,
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        }

    async def _configure_validators(self, validator_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Configure validators in the pipeline."""
        configured_count = 0

        for config in validator_configs:
            try:
                # Add validator to pipeline
                # Implementation would depend on actual pipeline configuration
                configured_count += 1
            except Exception as e:
                self.logger.error(f"Failed to configure validator: {e}")

        return {
            "configured_validators": configured_count,
            "total_requested": len(validator_configs),
            "success": configured_count == len(validator_configs)
        }

    async def _list_available_validators(self) -> Dict[str, Any]:
        """List all available validators."""
        from ..core.base import validator_registry

        validators = validator_registry.list_validators()

        return {
            "available_validators": validators,
            "count": len(validators)
        }

    async def _get_validator_capabilities(self, validator_name: str) -> Dict[str, Any]:
        """Get capabilities of specific validator."""
        from ..core.base import validator_registry

        try:
            validator = validator_registry.get_validator(validator_name)
            capabilities = validator.get_capabilities()

            return {
                "validator_name": validator_name,
                "capabilities": capabilities,
                "version": validator.version
            }
        except Exception as e:
            return {
                "validator_name": validator_name,
                "error": str(e)
            }

    async def _analyze_validation_trends(self, time_period: str = "30d",
                                       aggregation: str = "daily") -> Dict[str, Any]:
        """Analyze validation trends over time."""
        # Placeholder for trend analysis
        return {
            "time_period": time_period,
            "aggregation": aggregation,
            "trends": {
                "total_validations": 150,
                "success_rate": 0.85,
                "average_issues_per_validation": 2.3,
                "most_common_issues": [
                    "missing_metadata", "schema_compliance", "data_integrity"
                ]
            }
        }

    async def _export_validation_results(self, validation_ids: List[str],
                                       export_format: str = "json",
                                       include_details: bool = True) -> Dict[str, Any]:
        """Export validation results."""
        # Placeholder for result export
        return {
            "exported_validations": len(validation_ids),
            "format": export_format,
            "export_path": f"/exports/validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}",
            "include_details": include_details
        }

    def _configure_pipeline_from_profile(self, profile):
        """Configure pipeline from validation profile."""
        # Implementation would configure the pipeline based on profile settings
        pass

    def _configure_pipeline_from_config(self, pipeline: ValidationPipeline, config: Dict[str, Any]):
        """Configure pipeline from provided configuration."""
        # Implementation would configure the pipeline based on provided config
        pass

    def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get schema definition for MCP tool."""
        schemas = {
            "validate_nwb_file": {
                "type": "function",
                "function": {
                    "name": "validate_nwb_file",
                    "description": "Validate a single NWB file using specified validation profile",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the NWB file to validate"
                            },
                            "validation_profile": {
                                "type": "string",
                                "enum": ["standard", "quick", "comprehensive"],
                                "default": "standard",
                                "description": "Validation profile to use"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            "validate_metadata": {
                "type": "function",
                "function": {
                    "name": "validate_metadata",
                    "description": "Validate metadata against LinkML schema",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "metadata": {
                                "type": "object",
                                "description": "Metadata to validate"
                            },
                            "schema_name": {
                                "type": "string",
                                "description": "Name of the LinkML schema"
                            },
                            "class_name": {
                                "type": "string",
                                "description": "Name of the class in the schema"
                            }
                        },
                        "required": ["metadata", "schema_name", "class_name"]
                    }
                }
            },
            "generate_validation_report": {
                "type": "function",
                "function": {
                    "name": "generate_validation_report",
                    "description": "Generate validation report in specified format",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "validation_id": {
                                "type": "string",
                                "description": "ID of the validation to report on"
                            },
                            "template_name": {
                                "type": "string",
                                "enum": ["standard", "summary", "detailed", "markdown"],
                                "default": "standard",
                                "description": "Report template to use"
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["html", "json", "pdf", "markdown"],
                                "default": "html",
                                "description": "Output format for the report"
                            }
                        },
                        "required": ["validation_id"]
                    }
                }
            }
        }

        return schemas.get(tool_name, {})

    def list_tools(self) -> List[str]:
        """List all available MCP tools."""
        return list(self.tools.keys())
```

### Module Design Patterns

Each module follows consistent design patterns:

1. **Standardized Interfaces:** All validators inherit from `BaseValidator`
2. **Dependency Injection:** Configuration passed through constructor
3. **Error Handling:** Comprehensive error handling with recovery strategies
4. **Logging:** Structured logging for traceability
5. **Metrics:** Quantitative assessment of validation results
6. **Extensibility:** Plugin architecture for custom validators

## Streaming and Large File Handling

### Stream Processing Framework

The validation system supports streaming validation for large NWB files that exceed available memory through a dedicated streaming framework:

#### Stream Validator Interface

```python
from abc import ABC, abstractmethod
from typing import Iterator, Any, Optional, AsyncIterator
import asyncio
from pathlib import Path

class StreamChunk:
    """Represents a chunk of data in the stream."""
    def __init__(self, data: Any, chunk_id: int, metadata: Optional[Dict[str, Any]] = None):
        self.data = data
        self.chunk_id = chunk_id
        self.metadata = metadata or {}
        self.size_bytes = self._calculate_size()

    def _calculate_size(self) -> int:
        """Calculate approximate size of chunk in bytes."""
        # Implementation would depend on data type
        return len(str(self.data).encode('utf-8'))

class StreamValidator(BaseValidator):
    """Base class for streaming validators."""

    def __init__(self, chunk_size_mb: int = 100, overlap_size_mb: int = 10):
        super().__init__()
        self.chunk_size_bytes = chunk_size_mb * 1024 * 1024
        self.overlap_size_bytes = overlap_size_mb * 1024 * 1024

    async def validate_stream(self, file_path: str, context: ValidationContext) -> AsyncIterator[ValidationResult]:
        """Validate file using streaming approach."""
        chunk_iterator = self._create_chunk_iterator(file_path)

        async for chunk in chunk_iterator:
            try:
                chunk_result = await self._validate_chunk(chunk, context)
                yield chunk_result
            except Exception as e:
                error_result = self._create_error_result(chunk, e, context)
                yield error_result

    @abstractmethod
    async def _validate_chunk(self, chunk: StreamChunk, context: ValidationContext) -> ValidationResult:
        """Validate individual chunk."""
        pass

    @abstractmethod
    def _create_chunk_iterator(self, file_path: str) -> AsyncIterator[StreamChunk]:
        """Create iterator for file chunks."""
        pass

class NWBStreamValidator(StreamValidator):
    """Streaming validator for large NWB files."""

    async def _validate_chunk(self, chunk: StreamChunk, context: ValidationContext) -> ValidationResult:
        """Validate NWB data chunk."""
        issues = []

        # Validate chunk-specific aspects
        if hasattr(chunk.data, 'datasets'):
            for dataset_name, dataset in chunk.data.datasets.items():
                dataset_issues = self._validate_dataset_chunk(dataset_name, dataset, chunk.chunk_id)
                issues.extend(dataset_issues)

        # Check for temporal consistency across chunks
        if chunk.chunk_id > 0:
            temporal_issues = self._validate_temporal_continuity(chunk, context)
            issues.extend(temporal_issues)

        return self._create_result(
            context=context,
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.CRITICAL]) == 0,
            issues=issues,
            summary={'chunk_id': chunk.chunk_id, 'chunk_size': chunk.size_bytes}
        )

    def _create_chunk_iterator(self, file_path: str) -> AsyncIterator[StreamChunk]:
        """Create iterator for NWB file chunks."""
        async def chunk_generator():
            try:
                import h5py
                with h5py.File(file_path, 'r') as f:
                    chunk_id = 0

                    # Stream through large datasets
                    for dataset_path in self._find_large_datasets(f):
                        dataset = f[dataset_path]

                        # Calculate optimal chunk size based on dataset shape
                        chunk_shape = self._calculate_chunk_shape(dataset.shape, dataset.dtype)

                        # Iterate through dataset chunks
                        for chunk_slice in self._generate_chunk_slices(dataset.shape, chunk_shape):
                            chunk_data = dataset[chunk_slice]

                            chunk = StreamChunk(
                                data=chunk_data,
                                chunk_id=chunk_id,
                                metadata={
                                    'dataset_path': dataset_path,
                                    'slice': chunk_slice,
                                    'shape': chunk_data.shape,
                                    'dtype': str(dataset.dtype)
                                }
                            )

                            yield chunk
                            chunk_id += 1

                            # Memory management
                            await asyncio.sleep(0)  # Allow other coroutines to run

            except Exception as e:
                # Fallback to non-streaming validation
                raise StreamingError(f"Failed to create chunk iterator: {e}")

        return chunk_generator()

    def _find_large_datasets(self, h5_file, size_threshold_mb: int = 100) -> List[str]:
        """Find datasets larger than threshold."""
        large_datasets = []
        threshold_bytes = size_threshold_mb * 1024 * 1024

        def visit_func(name, obj):
            if isinstance(obj, h5py.Dataset):
                size_bytes = obj.size * obj.dtype.itemsize
                if size_bytes > threshold_bytes:
                    large_datasets.append(name)

        h5_file.visititems(visit_func)
        return large_datasets

    def _calculate_chunk_shape(self, dataset_shape: tuple, dtype) -> tuple:
        """Calculate optimal chunk shape for streaming."""
        # Aim for chunks around target size
        target_size = self.chunk_size_bytes
        element_size = dtype.itemsize
        target_elements = target_size // element_size

        # Simple chunking strategy - chunk along first dimension
        if len(dataset_shape) == 1:
            chunk_size = min(target_elements, dataset_shape[0])
            return (chunk_size,)
        else:
            # For multi-dimensional, chunk first dimension
            remaining_elements = 1
            for dim in dataset_shape[1:]:
                remaining_elements *= dim

            chunk_first_dim = min(target_elements // remaining_elements, dataset_shape[0])
            chunk_first_dim = max(1, chunk_first_dim)  # At least 1

            return (chunk_first_dim,) + dataset_shape[1:]

    def _generate_chunk_slices(self, dataset_shape: tuple, chunk_shape: tuple) -> Iterator[tuple]:
        """Generate slices for chunked iteration."""
        if len(dataset_shape) != len(chunk_shape):
            raise ValueError("Shape mismatch between dataset and chunk")

        # Generate slices for first dimension
        for start in range(0, dataset_shape[0], chunk_shape[0]):
            end = min(start + chunk_shape[0], dataset_shape[0])

            # Create full slice tuple
            slice_tuple = tuple([slice(start, end)] + [slice(None)] * (len(dataset_shape) - 1))
            yield slice_tuple

class StreamingError(Exception):
    """Streaming-specific validation error."""
    pass
```

#### Memory Management

```python
class MemoryManager:
    """Manages memory usage during streaming validation."""

    def __init__(self, max_memory_mb: int = 2048, warning_threshold: float = 0.8):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.warning_threshold_bytes = int(self.max_memory_bytes * warning_threshold)
        self.current_usage = 0
        self.active_chunks = {}

    def allocate_chunk(self, chunk_id: int, size_bytes: int) -> bool:
        """Allocate memory for chunk, return False if not enough memory."""
        if self.current_usage + size_bytes > self.max_memory_bytes:
            # Try to free some memory
            self._free_oldest_chunks(size_bytes)

            if self.current_usage + size_bytes > self.max_memory_bytes:
                return False

        self.current_usage += size_bytes
        self.active_chunks[chunk_id] = size_bytes
        return True

    def free_chunk(self, chunk_id: int):
        """Free memory for chunk."""
        if chunk_id in self.active_chunks:
            self.current_usage -= self.active_chunks[chunk_id]
            del self.active_chunks[chunk_id]

    def _free_oldest_chunks(self, needed_bytes: int):
        """Free oldest chunks to make space."""
        # Simple LRU strategy
        sorted_chunks = sorted(self.active_chunks.items())
        freed_bytes = 0

        for chunk_id, size_bytes in sorted_chunks:
            if freed_bytes >= needed_bytes:
                break

            self.free_chunk(chunk_id)
            freed_bytes += size_bytes

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        return {
            'current_usage_mb': self.current_usage / (1024 * 1024),
            'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
            'usage_percentage': (self.current_usage / self.max_memory_bytes) * 100,
            'active_chunks': len(self.active_chunks),
            'warning_threshold_exceeded': self.current_usage > self.warning_threshold_bytes
        }
```

#### Progressive Validation

```python
class ProgressiveValidator:
    """Coordinates progressive validation across streaming chunks."""

    def __init__(self, validators: List[StreamValidator]):
        self.validators = validators
        self.chunk_results = defaultdict(list)
        self.global_state = {}
        self.memory_manager = MemoryManager()

    async def validate_progressively(self, file_path: str,
                                   context: ValidationContext) -> AsyncIterator[ValidationResult]:
        """Perform progressive validation with state accumulation."""

        # Initialize global state for cross-chunk validation
        self._initialize_global_state(file_path, context)

        # Stream through each validator
        for validator in self.validators:
            validator_name = validator.name

            async for chunk_result in validator.validate_stream(file_path, context):
                # Update global state with chunk result
                self._update_global_state(validator_name, chunk_result)

                # Check for cross-chunk issues
                cross_chunk_issues = self._validate_cross_chunk_consistency(chunk_result)
                if cross_chunk_issues:
                    chunk_result.issues.extend(cross_chunk_issues)

                # Store chunk result
                self.chunk_results[validator_name].append(chunk_result)

                # Memory management
                self.memory_manager.free_chunk(chunk_result.summary.get('chunk_id', 0))

                yield chunk_result

        # Generate final consolidated result
        final_result = self._generate_final_result(context)
        yield final_result

    def _initialize_global_state(self, file_path: str, context: ValidationContext):
        """Initialize state for cross-chunk validation."""
        self.global_state = {
            'file_path': file_path,
            'total_chunks': 0,
            'temporal_continuity': {},
            'dataset_schemas': {},
            'global_metadata': {},
            'chunk_summaries': []
        }

    def _update_global_state(self, validator_name: str, chunk_result: ValidationResult):
        """Update global state with chunk validation result."""
        chunk_id = chunk_result.summary.get('chunk_id', 0)

        # Update chunk count
        self.global_state['total_chunks'] = max(
            self.global_state['total_chunks'],
            chunk_id + 1
        )

        # Store chunk summary
        self.global_state['chunk_summaries'].append({
            'chunk_id': chunk_id,
            'validator': validator_name,
            'is_valid': chunk_result.is_valid,
            'issue_count': len(chunk_result.issues),
            'execution_time': chunk_result.execution_time
        })

        # Update temporal continuity tracking
        if 'temporal_data' in chunk_result.summary:
            self.global_state['temporal_continuity'][chunk_id] = chunk_result.summary['temporal_data']

    def _validate_cross_chunk_consistency(self, chunk_result: ValidationResult) -> List[ValidationIssue]:
        """Validate consistency across chunks."""
        issues = []
        chunk_id = chunk_result.summary.get('chunk_id', 0)

        # Check temporal continuity
        if chunk_id > 0:
            temporal_issues = self._check_temporal_continuity(chunk_id, chunk_result)
            issues.extend(temporal_issues)

        # Check dataset schema consistency
        schema_issues = self._check_schema_consistency(chunk_result)
        issues.extend(schema_issues)

        return issues

    def _check_temporal_continuity(self, chunk_id: int, chunk_result: ValidationResult) -> List[ValidationIssue]:
        """Check temporal continuity between chunks."""
        issues = []

        if chunk_id - 1 in self.global_state['temporal_continuity']:
            prev_temporal = self.global_state['temporal_continuity'][chunk_id - 1]
            curr_temporal = chunk_result.summary.get('temporal_data', {})

            # Check for temporal gaps or overlaps
            if 'end_time' in prev_temporal and 'start_time' in curr_temporal:
                prev_end = prev_temporal['end_time']
                curr_start = curr_temporal['start_time']

                if curr_start < prev_end:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Temporal overlap detected between chunks {chunk_id-1} and {chunk_id}",
                        location=f"chunk_{chunk_id}",
                        check_name="temporal_continuity",
                        validator_name="progressive_validator",
                        remediation="Check for duplicate or overlapping time segments"
                    ))
                elif curr_start > prev_end + 1:  # Allow 1 unit tolerance
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        message=f"Temporal gap detected between chunks {chunk_id-1} and {chunk_id}",
                        location=f"chunk_{chunk_id}",
                        check_name="temporal_continuity",
                        validator_name="progressive_validator",
                        remediation="Verify if temporal gap is expected"
                    ))

        return issues

    def _generate_final_result(self, context: ValidationContext) -> ValidationResult:
        """Generate final consolidated result from all chunks."""
        all_issues = []
        total_execution_time = 0
        all_valid = True

        # Aggregate all chunk results
        for validator_results in self.chunk_results.values():
            for result in validator_results:
                all_issues.extend(result.issues)
                total_execution_time += result.execution_time
                if not result.is_valid:
                    all_valid = False

        # Generate summary statistics
        summary = {
            'validation_type': 'progressive_streaming',
            'total_chunks': self.global_state['total_chunks'],
            'total_validators': len(self.validators),
            'chunk_results_count': sum(len(results) for results in self.chunk_results.values()),
            'memory_stats': self.memory_manager.get_memory_stats(),
            'file_path': self.global_state['file_path']
        }

        # Calculate streaming-specific metrics
        metrics = {
            'chunks_per_validator': self.global_state['total_chunks'] / len(self.validators),
            'average_chunk_execution_time': total_execution_time / max(summary['chunk_results_count'], 1),
            'streaming_efficiency': 1.0 - (self.memory_manager.current_usage / self.memory_manager.max_memory_bytes)
        }

        return ValidationResult(
            validator_name="progressive_streaming_validator",
            context=context,
            status=ValidationStatus.COMPLETED,
            is_valid=all_valid,
            issues=all_issues,
            summary=summary,
            metrics=metrics,
            execution_time=total_execution_time,
            completed_at=datetime.utcnow()
        )
```

## Module Communication Patterns

### Event-Driven Architecture

The validation system implements an event-driven architecture for loose coupling between modules:

```python
from enum import Enum
from typing import Callable, Dict, List, Any
import asyncio
from dataclasses import dataclass
from datetime import datetime

class EventType(Enum):
    """Types of validation events."""
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    VALIDATION_FAILED = "validation_failed"
    ISSUE_FOUND = "issue_found"
    QUALITY_SCORE_CALCULATED = "quality_score_calculated"
    REPORT_GENERATED = "report_generated"

@dataclass
class ValidationEvent:
    """Validation system event."""
    event_type: EventType
    source_module: str
    data: Dict[str, Any]
    timestamp: datetime = None
    event_id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())

class EventBus:
    """Central event bus for module communication."""

    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_history: List[ValidationEvent] = []
        self.middleware: List[Callable] = []

    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to events of specific type."""
        self.subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from events."""
        if handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)

    async def publish(self, event: ValidationEvent):
        """Publish event to all subscribers."""
        # Apply middleware
        for middleware_func in self.middleware:
            event = await middleware_func(event)
            if event is None:
                return  # Event was filtered out

        # Store in history
        self.event_history.append(event)

        # Notify subscribers
        handlers = self.subscribers.get(event.event_type, [])

        # Execute handlers concurrently
        if handlers:
            await asyncio.gather(*[
                self._safe_handle(handler, event)
                for handler in handlers
            ], return_exceptions=True)

    async def _safe_handle(self, handler: Callable, event: ValidationEvent):
        """Safely execute event handler."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            validation_logger.error(f"Event handler failed: {e}")

# Global event bus instance
event_bus = EventBus()
```

### Inter-Module Communication

```python
class ModuleCommunicationMixin:
    """Mixin for module communication capabilities."""

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.event_bus = event_bus
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Setup module-specific event handlers."""
        # Override in subclasses
        pass

    async def emit_event(self, event_type: EventType, data: Dict[str, Any]):
        """Emit event from this module."""
        event = ValidationEvent(
            event_type=event_type,
            source_module=self.module_name,
            data=data
        )
        await self.event_bus.publish(event)

    def on_event(self, event_type: EventType):
        """Decorator for event handlers."""
        def decorator(handler_func):
            self.event_bus.subscribe(event_type, handler_func)
            return handler_func
        return decorator

# Example: NWB Inspector with communication
class CommunicatingNWBInspector(NWBInspectorEngine, ModuleCommunicationMixin):
    """NWB Inspector with event communication."""

    def __init__(self, name: str = "nwb_inspector", config: Optional[Dict[str, Any]] = None):
        NWBInspectorEngine.__init__(self, name, config)
        ModuleCommunicationMixin.__init__(self, "nwb_inspector")

    def _setup_event_handlers(self):
        """Setup NWB Inspector event handlers."""
        @self.on_event(EventType.VALIDATION_STARTED)
        async def on_validation_started(event: ValidationEvent):
            self.logger.info(f"Validation started: {event.data}")

    async def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Enhanced validate with events."""
        # Emit validation started event
        await self.emit_event(EventType.VALIDATION_STARTED, {
            'validator': self.name,
            'session_id': context.session_id,
            'file_path': context.file_path
        })

        # Run normal validation
        result = await super().validate(data, context)

        # Emit completion event
        event_type = EventType.VALIDATION_COMPLETED if result.is_valid else EventType.VALIDATION_FAILED
        await self.emit_event(event_type, {
            'validator': self.name,
            'result_id': result.validation_id,
            'is_valid': result.is_valid,
            'issue_count': len(result.issues)
        })

        # Emit individual issue events
        for issue in result.issues:
            await self.emit_event(EventType.ISSUE_FOUND, {
                'validator': self.name,
                'issue_id': issue.id,
                'severity': issue.severity.value,
                'location': issue.location
            })

        return result
```

### Integration Points

- **Module Dependencies:** Clear dependency graph prevents circular imports
- **Data Flow:** Standardized data structures flow between modules
- **Configuration:** Centralized configuration with module-specific sections
- **Error Propagation:** Consistent error handling across module boundaries
- **Event Communication:** Loose coupling through event-driven patterns
- **Streaming Support:** Memory-efficient processing for large files

### Testing Strategy

- **Unit Tests:** Each module has isolated unit tests
- **Integration Tests:** Test module interactions and event flows
- **End-to-End Tests:** Complete validation workflows including streaming
- **Performance Tests:** Scalability and resource usage validation
- **Memory Tests:** Streaming validation memory efficiency
- **Event Tests:** Event-driven communication patterns

This modular design ensures maintainability, testability, and extensibility while providing clear separation of concerns and efficient handling of large files through streaming capabilities.