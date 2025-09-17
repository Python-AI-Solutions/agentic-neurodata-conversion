# Evaluation and Reporting Design - Modular Architecture

## Overview

This design document outlines a modular evaluation and reporting system composed of independent, testable components that generate comprehensive assessments, interactive visualizations, and human-readable summaries of conversion results.

## Modular Architecture

### Component Hierarchy (Enhanced for Robustness)

```
Evaluation and Reporting System
├── Core Modules (Foundation)
│   ├── Module A: NWB Inspector Interface
│   ├── Module A-FB: Fallback Validation System
│   ├── Module B: Validation Results Parser
│   └── Module C: Configuration Manager
├── Assessment Modules (Analysis)
│   ├── Module D: Technical Quality Evaluator
│   ├── Module E: Scientific Quality Evaluator
│   ├── Module F: Usability Quality Evaluator
│   └── Module G: Quality Assessment Orchestrator (Enhanced)
├── Output Modules (Presentation)
│   ├── Module H: Report Generator
│   ├── Module I: Visualization Engine
│   └── Module J: Export Manager
├── Integration Modules (Connectivity)
│   ├── Module K: MCP Server Tools
│   ├── Module L: Review System Interface
│   └── Module M: External API Gateway
├── Resilience Modules (Robustness)
│   ├── Module R1: Circuit Breaker System
│   ├── Module R2: Resource Manager
│   ├── Module R3: Event Bus & Communication
│   └── Module R4: Data Integrity Checker
└── Utility Modules (Support)
    ├── Module N: Data Models & Schemas
    ├── Module O: Error Handling & Logging (Enhanced)
    └── Module P: Testing Utilities
```

### Enhanced Evaluation Pipeline Flow (Resilient)

```
[NWB File] → [Module A OR A-FB] → [Module B] → [Modules D,E,F] → [Module G] → [Modules H,I,J] → [Outputs]
     ↓              ↓                 ↓              ↓              ↓              ↓
 Configuration   Validation        Assessment    Orchestration  Generation    Export
 (Module C)     (Fallback)        (Parallel)    (Graceful)     (Resilient)   (Multiple)
     ↓              ↓                 ↓              ↓              ↓              ↓
[Circuit Breakers R1] [Data Integrity R4] [Resource Manager R2] [Event Bus R3]
```

### Fallback and Recovery Flow

```
Primary Path:   [Module A] → [Success] → [Continue Pipeline]
                    ↓
                [Failure]
                    ↓
Fallback Path:  [Module A-FB] → [Basic Validation] → [Continue with Degraded Mode]
                    ↓
                [Circuit Breaker Triggered] → [Graceful Degradation] → [Partial Results]
```

## Module Specifications

### Core Modules (Foundation Layer)

#### Module A: NWB Inspector Interface (Enhanced)
**Purpose**: Primary validation gateway using nwb-inspector with resilience features
**Dependencies**: Module R1 (Circuit Breaker), Module R2 (Resource Manager)
**Interfaces**: Configuration input, NWB file input, validation results output, fallback triggers
**Testability**: Mock nwb-inspector subprocess, test configuration validation, failure scenarios
**Resilience**: Circuit breaker protection, automatic fallback to Module A-FB

#### Module A-FB: Fallback Validation System
**Purpose**: Provide basic validation when nwb-inspector is unavailable
**Dependencies**: Module R4 (Data Integrity Checker)
**Interfaces**: NWB file input, basic validation results output, confidence indicators
**Testability**: Test basic validation algorithms, degraded mode scenarios
**Resilience**: Independent validation without external dependencies

#### Module B: Validation Results Parser (Enhanced)
**Purpose**: Parse and normalize validation outputs from multiple sources with integrity checking
**Dependencies**: Module A, Module A-FB, Module R4 (Data Integrity)
**Interfaces**: Raw validation data input, structured results output, integrity reports
**Testability**: Test with various validation result formats, corrupted data scenarios
**Resilience**: Data integrity validation, multi-source merging with conflict resolution

#### Module C: Configuration Manager
**Purpose**: Manage evaluation configurations and profiles
**Dependencies**: None
**Interfaces**: Configuration CRUD operations, profile management
**Testability**: Test configuration validation, profile loading/saving

### Assessment Modules (Analysis Layer)

#### Module D: Technical Quality Evaluator
**Purpose**: Assess technical aspects (schema, integrity, performance)
**Dependencies**: Module B
**Interfaces**: Validation results input, technical metrics output
**Testability**: Mock validation data, verify metric calculations

#### Module E: Scientific Quality Evaluator
**Purpose**: Assess scientific validity and completeness
**Dependencies**: Module B
**Interfaces**: Metadata input, scientific metrics output
**Testability**: Test with various metadata completeness scenarios

#### Module F: Usability Quality Evaluator
**Purpose**: Assess documentation, discoverability, accessibility
**Dependencies**: Module B
**Interfaces**: File and metadata input, usability metrics output
**Testability**: Test accessibility checks, documentation scoring

#### Module G: Quality Assessment Orchestrator (Enhanced)
**Purpose**: Coordinate evaluators with graceful degradation and intelligent aggregation
**Dependencies**: Modules D, E, F, C, R1 (Circuit Breaker), R2 (Resource Manager), R3 (Event Bus)
**Interfaces**: Configuration and data input, comprehensive assessment output, degradation status
**Testability**: Test aggregation logic, weight application, partial failure scenarios
**Resilience**: Graceful degradation, partial evaluation modes, dynamic module selection

### Output Modules (Presentation Layer)

#### Module H: Report Generator
**Purpose**: Generate structured reports in multiple formats
**Dependencies**: Module G
**Interfaces**: Assessment results input, formatted reports output
**Testability**: Test report generation, format validation

#### Module I: Visualization Engine
**Purpose**: Create interactive visualizations and dashboards
**Dependencies**: Module G
**Interfaces**: Assessment data input, visualization files output
**Testability**: Test visualization generation, interactive features

#### Module J: Export Manager
**Purpose**: Handle output formatting and delivery
**Dependencies**: Modules H, I
**Interfaces**: Generated content input, exported files output
**Testability**: Test various export formats, file handling

### Integration Modules (Connectivity Layer)

#### Module K: MCP Server Tools
**Purpose**: Provide MCP endpoints for evaluation services
**Dependencies**: Modules A, G, H, I
**Interfaces**: MCP protocol input/output, service orchestration
**Testability**: Mock MCP requests, test endpoint responses

#### Module L: Review System Interface
**Purpose**: Support collaborative review workflows
**Dependencies**: Module G, H
**Interfaces**: Review session management, annotation handling
**Testability**: Test review workflows, annotation persistence

#### Module M: External API Gateway
**Purpose**: Interface with external systems and APIs
**Dependencies**: Module G
**Interfaces**: External API communication, data transformation
**Testability**: Mock external APIs, test data transformation

### Resilience Modules (Robustness Layer)

#### Module R1: Circuit Breaker System
**Purpose**: Prevent cascading failures and provide service protection
**Dependencies**: Module O (Enhanced Logging)
**Interfaces**: Circuit breaker registration, failure detection, state management
**Testability**: Test failure scenarios, circuit state transitions, recovery mechanisms
**Resilience**: Automatic failure detection, configurable thresholds, service isolation

#### Module R2: Resource Manager
**Purpose**: Manage system resources and prevent resource exhaustion
**Dependencies**: Module O (Enhanced Logging), Module R3 (Event Bus)
**Interfaces**: Resource allocation, monitoring, quota management
**Testability**: Test resource limits, allocation failures, cleanup scenarios
**Resilience**: Memory management, CPU throttling, concurrent evaluation limits

#### Module R3: Event Bus & Communication
**Purpose**: Decouple modules through event-driven communication
**Dependencies**: Module O (Enhanced Logging)
**Interfaces**: Event publishing, subscription management, message routing
**Testability**: Test event delivery, handler failures, message ordering
**Resilience**: Asynchronous communication, error isolation, retry mechanisms

#### Module R4: Data Integrity Checker
**Purpose**: Ensure data consistency and detect corruption across modules
**Dependencies**: Module N (Data Models)
**Interfaces**: Checksum generation, integrity validation, corruption detection
**Testability**: Test data validation, corruption scenarios, performance impact
**Resilience**: Cross-module validation, corruption recovery, data versioning

### Utility Modules (Support Layer)

#### Module N: Data Models & Schemas (Enhanced)
**Purpose**: Define data structures with integrity and versioning support
**Dependencies**: None
**Interfaces**: Type definitions, validation functions, schema migration
**Testability**: Test schema validation, data serialization, migration scenarios
**Resilience**: Schema versioning, backward compatibility, data validation

#### Module O: Error Handling & Logging (Enhanced)
**Purpose**: Centralized error handling with correlation and recovery
**Dependencies**: None
**Interfaces**: Error handling decorators, structured logging, correlation tracking
**Testability**: Test error scenarios, log output validation, correlation tracking
**Resilience**: Error correlation, recovery suggestions, performance monitoring

### Enhanced Error Handling Implementation

**File**: `agentic_neurodata_conversion/evaluation/utils/error_handling.py`
**Size**: ~120 lines
**Complexity**: Low

```python
class ErrorContext:
    """Simple error context for tracking issues across modules."""

    def __init__(self, operation_id: str, module_name: str):
        self.operation_id = operation_id
        self.module_name = module_name
        self.correlation_id = f"{operation_id}_{int(time.time())}"
        self.errors = []
        self.logger = logging.getLogger(f"{module_name}.{self.__class__.__name__}")

    def add_error(self, error: Exception, context: str = ""):
        """Add error to context."""
        error_info = {
            "timestamp": time.time(),
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "module": self.module_name
        }
        self.errors.append(error_info)

        self.logger.error(
            f"[{self.correlation_id}] {self.module_name}: {error_info['error_type']} - {error_info['message']}",
            extra={"correlation_id": self.correlation_id, "error_context": error_info}
        )

    def has_critical_errors(self) -> bool:
        """Check if there are critical errors that should stop processing."""
        critical_error_types = ["FileNotFoundError", "PermissionError", "CircuitBreakerOpenError"]
        return any(error["error_type"] in critical_error_types for error in self.errors)

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors in this context."""
        return {
            "correlation_id": self.correlation_id,
            "operation_id": self.operation_id,
            "module_name": self.module_name,
            "total_errors": len(self.errors),
            "has_critical": self.has_critical_errors(),
            "errors": self.errors
        }

def with_error_context(operation_id: str, module_name: str):
    """Decorator to add error context to functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            context = ErrorContext(operation_id, module_name)
            try:
                return func(*args, error_context=context, **kwargs)
            except Exception as e:
                context.add_error(e, f"Function: {func.__name__}")
                if context.has_critical_errors():
                    raise
                return None
        return wrapper
    return decorator

class SimpleHealthChecker:
    """Basic health checking for modules."""

    def __init__(self):
        self.health_status = {}
        self.logger = logging.getLogger(__name__)

    def register_module(self, module_name: str, health_check_func: callable):
        """Register a module's health check function."""
        self.health_status[module_name] = {
            "check_func": health_check_func,
            "last_check": 0,
            "status": "unknown"
        }

    def check_module_health(self, module_name: str) -> bool:
        """Check health of a specific module."""
        if module_name not in self.health_status:
            return False

        try:
            status = self.health_status[module_name]["check_func"]()
            self.health_status[module_name]["status"] = "healthy" if status else "unhealthy"
            self.health_status[module_name]["last_check"] = time.time()
            return status
        except Exception as e:
            self.logger.error(f"Health check failed for {module_name}: {e}")
            self.health_status[module_name]["status"] = "unhealthy"
            return False

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        healthy_modules = sum(1 for status in self.health_status.values()
                            if status["status"] == "healthy")
        total_modules = len(self.health_status)

        return {
            "overall_health": healthy_modules / total_modules if total_modules > 0 else 0,
            "healthy_modules": healthy_modules,
            "total_modules": total_modules,
            "module_status": {name: info["status"] for name, info in self.health_status.items()}
        }

# Global health checker
_health_checker = SimpleHealthChecker()

def get_health_checker() -> SimpleHealthChecker:
    return _health_checker
```

#### Module P: Testing Utilities (Enhanced)
**Purpose**: Common testing fixtures with failure simulation
**Dependencies**: Module N, Module R1 (Circuit Breaker)
**Interfaces**: Test data generation, mock utilities, failure injection
**Testability**: Self-testing framework validation, chaos testing capabilities
**Resilience**: Failure injection, load testing, resilience validation

## Implementation Guidelines

### Development Principles

1. **Single Responsibility**: Each module has one clear purpose
2. **Dependency Injection**: Modules receive dependencies through constructors
3. **Interface Segregation**: Modules expose minimal, focused interfaces
4. **Testability First**: Every module designed for easy unit testing
5. **Error Boundaries**: Each module handles its own errors gracefully
6. **Configuration Driven**: Behavior controlled through configuration

### Module Implementation Pattern

```python
# Standard module structure
class ModuleX:
    """Module X: Brief description of purpose.

    Dependencies: List of required modules
    Interfaces: Input/output interfaces
    Configuration: Required configuration parameters
    """

    def __init__(self, config: ModuleXConfig, dependencies: ModuleXDependencies):
        self.config = config
        self.dependencies = dependencies
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate module configuration."""
        pass

    def process(self, input_data: ModuleXInput) -> ModuleXOutput:
        """Main processing method."""
        try:
            self.logger.info(f"Processing {type(input_data).__name__}")
            result = self._do_processing(input_data)
            self.logger.info("Processing completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise ModuleXError(f"Module X processing failed: {e}") from e

    def _do_processing(self, input_data: ModuleXInput) -> ModuleXOutput:
        """Internal processing logic."""
        raise NotImplementedError

    def health_check(self) -> bool:
        """Check module health and dependencies."""
        return True
```

### Error Handling Strategy

```python
# Module-specific exceptions
class ModuleXError(Exception):
    """Base exception for Module X."""
    pass

class ModuleXConfigurationError(ModuleXError):
    """Configuration-related errors."""
    pass

class ModuleXProcessingError(ModuleXError):
    """Processing-related errors."""
    pass

# Error context preservation
@dataclass
class ErrorContext:
    module_name: str
    operation: str
    input_summary: str
    timestamp: datetime
    correlation_id: str
```

## Detailed Module Designs

### Module A: NWB Inspector Interface

**File**: `agentic_neurodata_conversion/evaluation/modules/nwb_inspector_interface.py`
**Size**: ~200 lines
**Complexity**: Medium (subprocess management, error handling)

```python
# agentic_neurodata_conversion/evaluation/modules/nwb_inspector_interface.py
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import subprocess
import json
import logging
import time
from ..models.validation_models import NWBInspectorResult, ValidationConfig

@dataclass
class NWBInspectorConfig:
    """Configuration for NWB Inspector interface."""
    timeout_seconds: int = 300
    importance_threshold: Optional[str] = None
    skip_validate: bool = False
    config_file: Optional[str] = None
    output_format: str = "json"

class NWBInspectorInterface:
    """Interface to nwb-inspector tool with robust error handling."""

    def __init__(self, config: NWBInspectorConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_environment()

    def _validate_environment(self) -> None:
        """Validate nwb-inspector is available."""
        try:
            result = subprocess.run(
                ["nwbinspector", "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise EnvironmentError("nwb-inspector not available")
            self.logger.info(f"nwb-inspector available: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise EnvironmentError(f"nwb-inspector not found: {e}")

    def analyze_file(self, nwb_path: Path) -> NWBInspectorResult:
        """Analyze NWB file using nwb-inspector."""
        start_time = time.time()

        if not nwb_path.exists():
            raise FileNotFoundError(f"NWB file not found: {nwb_path}")

        cmd = self._build_command(nwb_path)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.config.timeout_seconds
            )

            execution_time = time.time() - start_time
            return self._parse_result(result, str(nwb_path), execution_time)

        except subprocess.TimeoutExpired:
            self.logger.error(f"nwb-inspector timed out after {self.config.timeout_seconds}s")
            return self._create_timeout_result(str(nwb_path), self.config.timeout_seconds)

    def _build_command(self, nwb_path: Path) -> list[str]:
        """Build nwb-inspector command."""
        cmd = ["nwbinspector", str(nwb_path), "--output-format", self.config.output_format]

        if self.config.skip_validate:
            cmd.append("--skip-validate")
        if self.config.importance_threshold:
            cmd.extend(["--importance-threshold", self.config.importance_threshold])
        if self.config.config_file:
            cmd.extend(["--config", self.config.config_file])

        return cmd

    def _parse_result(self, result: subprocess.CompletedProcess,
                     file_path: str, execution_time: float) -> NWBInspectorResult:
        """Parse nwb-inspector output into structured result."""
        issues = []
        summary = {}
        validation_status = "passed"

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                issues = data.get("messages", [])
                summary = self._create_summary(issues)
                validation_status = self._determine_status(summary)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse nwb-inspector output: {e}")
                validation_status = "failed"
                summary = {"parse_error": str(e)}

        return NWBInspectorResult(
            file_path=file_path,
            validation_status=validation_status,
            issues=issues,
            summary=summary,
            raw_output=result.stdout or result.stderr,
            execution_time=execution_time
        )

    def _create_summary(self, issues: list[Dict[str, Any]]) -> Dict[str, int]:
        """Create summary statistics from issues."""
        return {
            "total_issues": len(issues),
            "critical_issues": len([i for i in issues if i.get("severity") == "critical"]),
            "error_issues": len([i for i in issues if i.get("severity") == "error"]),
            "warning_issues": len([i for i in issues if i.get("severity") == "warning"]),
            "info_issues": len([i for i in issues if i.get("severity") == "info"])
        }

    def _determine_status(self, summary: Dict[str, int]) -> str:
        """Determine validation status from summary."""
        if summary.get("critical_issues", 0) > 0 or summary.get("error_issues", 0) > 0:
            return "failed"
        elif summary.get("warning_issues", 0) > 0:
            return "warnings"
        return "passed"

    def _create_timeout_result(self, file_path: str, timeout: int) -> NWBInspectorResult:
        """Create result for timeout scenario."""
        return NWBInspectorResult(
            file_path=file_path,
            validation_status="failed",
            issues=[{
                "severity": "critical",
                "message": f"nwb-inspector analysis timed out after {timeout} seconds",
                "location": "file_level"
            }],
            summary={"timeout_error": True},
            raw_output=f"Timeout after {timeout} seconds",
            execution_time=float(timeout)
        )

    def health_check(self) -> bool:
        """Check if nwb-inspector is available and functional."""
        try:
            self._validate_environment()
            return True
        except EnvironmentError:
            return False
```

### Module B: Validation Results Parser

**File**: `agentic_neurodata_conversion/evaluation/modules/validation_parser.py`
**Size**: ~150 lines
**Complexity**: Low (data transformation)

```python
# agentic_neurodata_conversion/evaluation/modules/validation_parser.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
from ..models.validation_models import ValidationResult, QualityIssue, IssueSeverity

@dataclass
class ValidationParserConfig:
    """Configuration for validation results parser."""
    severity_mapping: Dict[str, IssueSeverity] = None
    location_normalization: bool = True
    issue_deduplication: bool = True

    def __post_init__(self):
        if self.severity_mapping is None:
            self.severity_mapping = {
                "critical": IssueSeverity.CRITICAL,
                "error": IssueSeverity.HIGH,
                "warning": IssueSeverity.MEDIUM,
                "info": IssueSeverity.LOW
            }

class ValidationResultsParser:
    """Parse and normalize validation results from multiple sources."""

    def __init__(self, config: ValidationParserConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse_nwb_inspector_result(self, raw_result: Dict[str, Any]) -> ValidationResult:
        """Parse NWB Inspector results into standardized format."""
        nwb_data = raw_result.get("nwb_inspector", {})

        issues = self._parse_issues(nwb_data.get("issues", []))

        if self.config.issue_deduplication:
            issues = self._deduplicate_issues(issues)

        return ValidationResult(
            source="nwb_inspector",
            status=nwb_data.get("status", "unknown"),
            issues=issues,
            summary=nwb_data.get("summary", {}),
            execution_time=nwb_data.get("execution_time", 0.0),
            metadata={
                "raw_output": nwb_data.get("raw_output", ""),
                "file_path": raw_result.get("file_path", "")
            }
        )

    def _parse_issues(self, raw_issues: List[Dict[str, Any]]) -> List[QualityIssue]:
        """Convert raw issues to QualityIssue objects."""
        issues = []

        for i, raw_issue in enumerate(raw_issues):
            severity_str = raw_issue.get("severity", "warning")
            severity = self.config.severity_mapping.get(severity_str, IssueSeverity.MEDIUM)

            location = raw_issue.get("location", "unknown")
            if self.config.location_normalization:
                location = self._normalize_location(location)

            issue = QualityIssue(
                id=f"nwb_inspector_{i}",
                severity=severity,
                title=f"NWB Inspector: {severity_str}",
                description=raw_issue.get("message", "No description"),
                location=location,
                recommendation=self._generate_recommendation(severity_str),
                source="nwb_inspector",
                metadata=raw_issue
            )
            issues.append(issue)

        return issues

    def _normalize_location(self, location: str) -> str:
        """Normalize location strings for consistency."""
        # Remove common prefixes and standardize format
        normalized = location.replace("/", ".").strip()
        if normalized.startswith("."):
            normalized = normalized[1:]
        return normalized or "file_level"

    def _generate_recommendation(self, severity: str) -> str:
        """Generate recommendation based on issue severity."""
        recommendations = {
            "critical": "Immediate action required - file may not be readable",
            "error": "Address this issue to ensure proper file functionality",
            "warning": "Consider fixing to improve file quality",
            "info": "Optional improvement for better compliance"
        }
        return recommendations.get(severity, "Review and address as needed")

    def _deduplicate_issues(self, issues: List[QualityIssue]) -> List[QualityIssue]:
        """Remove duplicate issues based on description and location."""
        seen = set()
        unique_issues = []

        for issue in issues:
            key = (issue.description, issue.location)
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        return unique_issues

    def merge_validation_results(self, results: List[ValidationResult]) -> ValidationResult:
        """Merge multiple validation results into one comprehensive result."""
        if not results:
            raise ValueError("No validation results to merge")

        all_issues = []
        combined_summary = {}
        total_execution_time = 0.0
        sources = []

        for result in results:
            all_issues.extend(result.issues)
            sources.append(result.source)
            total_execution_time += result.execution_time

            # Merge summaries
            for key, value in result.summary.items():
                if key in combined_summary:
                    if isinstance(value, (int, float)):
                        combined_summary[key] += value
                    elif isinstance(value, list):
                        combined_summary[key].extend(value)
                else:
                    combined_summary[key] = value

        # Determine overall status
        statuses = [r.status for r in results]
        if "failed" in statuses:
            overall_status = "failed"
        elif "warnings" in statuses:
            overall_status = "warnings"
        else:
            overall_status = "passed"

        return ValidationResult(
            source=f"merged_{'+'.join(sources)}",
            status=overall_status,
            issues=all_issues,
            summary=combined_summary,
            execution_time=total_execution_time,
            metadata={
                "merged_sources": sources,
                "result_count": len(results)
            }
        )
```

### Module C: Configuration Manager

**File**: `agentic_neurodata_conversion/evaluation/modules/config_manager.py`
**Size**: ~180 lines
**Complexity**: Low (CRUD operations, file I/O)

```python
# agentic_neurodata_conversion/evaluation/modules/config_manager.py
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import logging
from ..models.config_models import EvaluationConfig, ProfileConfig

@dataclass
class ConfigManagerSettings:
    """Settings for configuration manager."""
    config_directory: Path = Path.cwd() / ".evaluation_configs"
    default_profile: str = "default"
    auto_backup: bool = True
    validation_enabled: bool = True

class ConfigurationManager:
    """Manage evaluation configurations and profiles."""

    def __init__(self, settings: ConfigManagerSettings):
        self.settings = settings
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._ensure_config_directory()
        self._load_profiles()

    def _ensure_config_directory(self) -> None:
        """Create configuration directory if it doesn't exist."""
        self.settings.config_directory.mkdir(parents=True, exist_ok=True)

    def _load_profiles(self) -> None:
        """Load available configuration profiles."""
        self._profiles = {}

        # Load built-in profiles
        self._profiles.update(self._get_builtin_profiles())

        # Load custom profiles from files
        for config_file in self.settings.config_directory.glob("*.json"):
            try:
                profile_name = config_file.stem
                with open(config_file, 'r') as f:
                    profile_data = json.load(f)
                    self._profiles[profile_name] = ProfileConfig.from_dict(profile_data)
                    self.logger.info(f"Loaded profile: {profile_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load profile {config_file}: {e}")

    def _get_builtin_profiles(self) -> Dict[str, ProfileConfig]:
        """Get built-in configuration profiles."""
        return {
            "default": ProfileConfig(
                name="default",
                description="Default evaluation configuration",
                nwb_inspector_config={
                    "timeout_seconds": 300,
                    "importance_threshold": "warning"
                },
                quality_thresholds={
                    "technical_minimum": 0.7,
                    "scientific_minimum": 0.6,
                    "usability_minimum": 0.5
                }
            ),
            "strict": ProfileConfig(
                name="strict",
                description="Strict evaluation for high-quality requirements",
                nwb_inspector_config={
                    "timeout_seconds": 600,
                    "importance_threshold": "info"
                },
                quality_thresholds={
                    "technical_minimum": 0.9,
                    "scientific_minimum": 0.85,
                    "usability_minimum": 0.8
                }
            ),
            "development": ProfileConfig(
                name="development",
                description="Lenient evaluation for development phase",
                nwb_inspector_config={
                    "timeout_seconds": 120,
                    "importance_threshold": "error"
                },
                quality_thresholds={
                    "technical_minimum": 0.5,
                    "scientific_minimum": 0.4,
                    "usability_minimum": 0.3
                }
            )
        }

    def get_profile(self, name: str) -> ProfileConfig:
        """Get configuration profile by name."""
        if name not in self._profiles:
            self.logger.warning(f"Profile '{name}' not found, using default")
            name = self.settings.default_profile

        return self._profiles.get(name, self._profiles[self.settings.default_profile])

    def save_profile(self, profile: ProfileConfig) -> None:
        """Save configuration profile to file."""
        if self.settings.validation_enabled:
            self._validate_profile(profile)

        config_file = self.settings.config_directory / f"{profile.name}.json"

        if self.settings.auto_backup and config_file.exists():
            backup_file = config_file.with_suffix(".json.bak")
            config_file.rename(backup_file)
            self.logger.info(f"Created backup: {backup_file}")

        try:
            with open(config_file, 'w') as f:
                json.dump(asdict(profile), f, indent=2)

            self._profiles[profile.name] = profile
            self.logger.info(f"Saved profile: {profile.name}")

        except Exception as e:
            self.logger.error(f"Failed to save profile {profile.name}: {e}")
            raise

    def delete_profile(self, name: str) -> bool:
        """Delete configuration profile."""
        if name in self._get_builtin_profiles():
            raise ValueError(f"Cannot delete built-in profile: {name}")

        config_file = self.settings.config_directory / f"{name}.json"

        if config_file.exists():
            config_file.unlink()
            self._profiles.pop(name, None)
            self.logger.info(f"Deleted profile: {name}")
            return True

        return False

    def list_profiles(self) -> List[str]:
        """List all available configuration profiles."""
        return sorted(self._profiles.keys())

    def _validate_profile(self, profile: ProfileConfig) -> None:
        """Validate configuration profile."""
        if not profile.name:
            raise ValueError("Profile name cannot be empty")

        if not profile.name.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Profile name must be alphanumeric (with _ or -)")

        # Validate thresholds are in valid range
        for key, value in profile.quality_thresholds.items():
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"Quality threshold '{key}' must be between 0 and 1")

    def create_evaluation_config(self, profile_name: str,
                               overrides: Optional[Dict[str, Any]] = None) -> EvaluationConfig:
        """Create evaluation configuration from profile."""
        profile = self.get_profile(profile_name)

        config = EvaluationConfig(
            profile_name=profile.name,
            nwb_inspector_config=profile.nwb_inspector_config.copy(),
            quality_thresholds=profile.quality_thresholds.copy(),
            output_formats=profile.output_formats.copy(),
            metadata=profile.metadata.copy()
        )

        # Apply overrides
        if overrides:
            for key, value in overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    config.metadata[key] = value

        return config

    def health_check(self) -> bool:
        """Check configuration manager health."""
        try:
            # Check directory accessibility
            test_file = self.settings.config_directory / ".health_check"
            test_file.touch()
            test_file.unlink()

            # Check profiles are loadable
            default_profile = self.get_profile(self.settings.default_profile)
            return default_profile is not None

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
```

### Module A-FB: Fallback Validation System

**File**: `agentic_neurodata_conversion/evaluation/modules/fallback_validator.py`
**Size**: ~200 lines
**Complexity**: Low-Medium

```python
class FallbackValidator:
    """Provides basic validation when nwb-inspector is unavailable."""

    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.basic_checks = [
            self._check_file_format,
            self._check_file_accessibility,
            self._check_basic_structure
        ]

    def validate_nwb_file(self, nwb_path: Path) -> ValidationResult:
        """Perform basic validation without nwb-inspector."""
        issues = []
        confidence_score = 0.8  # Lower confidence in fallback mode

        # Add fallback mode warning
        issues.append(self._create_fallback_warning())

        for check in self.basic_checks:
            try:
                result = check(nwb_path)
                issues.extend(result.issues)
                confidence_score *= result.confidence
            except Exception as e:
                issues.append(self._create_check_failure_issue(check.__name__, e))

        return ValidationResult(
            source="fallback_validator",
            status=self._determine_status(issues),
            issues=issues,
            summary={"confidence_score": confidence_score, "fallback_mode": True},
            execution_time=0.0,
            metadata={"validation_mode": "fallback"}
        )

    def _check_file_format(self, nwb_path: Path):
        """Basic HDF5 format check."""
        try:
            with h5py.File(nwb_path, 'r') as f:
                has_version = 'nwb_version' in f.attrs
            return CheckResult([], 1.0 if has_version else 0.7)
        except OSError:
            return CheckResult([self._create_hdf5_error()], 0.0)
```

### Module R1: Circuit Breaker System

**File**: `agentic_neurodata_conversion/evaluation/modules/circuit_breaker.py`
**Size**: ~150 lines
**Complexity**: Low-Medium

```python
class CircuitBreaker:
    """Simple circuit breaker for service protection."""

    def __init__(self, name: str, failure_threshold: int = 3, timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        with self.lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = "HALF_OPEN"
                else:
                    raise CircuitBreakerOpenError(f"Service {self.name} unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        with self.lock:
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
            self.failure_count = 0

    def _on_failure(self):
        with self.lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_failure_time = time.time()

# Global circuit breaker manager
_circuit_breakers = {}

def with_circuit_breaker(name: str):
    """Decorator for circuit breaker protection."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if name not in _circuit_breakers:
                _circuit_breakers[name] = CircuitBreaker(name)
            return _circuit_breakers[name].call(func, *args, **kwargs)
        return wrapper
    return decorator
```

### Module R2: Resource Manager

**File**: `agentic_neurodata_conversion/evaluation/modules/resource_manager.py`
**Size**: ~180 lines
**Complexity**: Low-Medium

```python
class ResourceManager:
    """Simple resource management for evaluation operations."""

    def __init__(self, max_memory_mb: int = 2048, max_concurrent: int = 3):
        self.max_memory_mb = max_memory_mb
        self.max_concurrent = max_concurrent
        self.current_evaluations = 0
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def allocate_evaluation_slot(self, operation_id: str):
        """Allocate resources for evaluation operation."""
        with self.lock:
            if self.current_evaluations >= self.max_concurrent:
                raise ResourceExhaustionError(
                    f"Maximum concurrent evaluations ({self.max_concurrent}) reached"
                )

            self.current_evaluations += 1
            self.logger.info(f"Allocated slot for {operation_id} ({self.current_evaluations}/{self.max_concurrent})")

        try:
            yield
        finally:
            with self.lock:
                self.current_evaluations -= 1
                self.logger.info(f"Released slot for {operation_id} ({self.current_evaluations}/{self.max_concurrent})")

    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource usage status."""
        return {
            "current_evaluations": self.current_evaluations,
            "max_concurrent": self.max_concurrent,
            "available_slots": self.max_concurrent - self.current_evaluations,
            "memory_limit_mb": self.max_memory_mb
        }

    def check_memory_usage(self) -> bool:
        """Simple memory usage check."""
        try:
            import psutil
            process = psutil.Process()
            current_mb = process.memory_info().rss / (1024 * 1024)
            return current_mb < self.max_memory_mb
        except ImportError:
            return True  # Can't check, assume OK

# Global resource manager
_resource_manager = None

def get_resource_manager() -> ResourceManager:
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager
```

### Enhanced Module G: Graceful Degradation Orchestrator

**Additional methods for Module G**:

```python
class QualityAssessmentOrchestrator:
    # ... existing methods ...

    def assess_with_degradation(self, nwb_path: str, config: EvaluationConfig) -> EvaluationResult:
        """Perform assessment with graceful degradation."""
        available_modules = self._check_module_availability()
        degradation_level = self._calculate_degradation_level(available_modules)

        if degradation_level > 0.5:  # Significant degradation
            return self._perform_minimal_evaluation(nwb_path, available_modules)
        else:
            return self._perform_full_evaluation(nwb_path, available_modules, config)

    def _check_module_availability(self) -> Dict[str, bool]:
        """Check which modules are currently available."""
        availability = {}

        # Check nwb-inspector availability
        try:
            result = subprocess.run(["nwbinspector", "--version"],
                                  capture_output=True, timeout=5)
            availability["nwb_inspector"] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            availability["nwb_inspector"] = False

        # Check evaluator module health
        for module_name, evaluator in [("technical", self.technical_evaluator),
                                       ("scientific", self.scientific_evaluator),
                                       ("usability", self.usability_evaluator)]:
            try:
                availability[module_name] = evaluator.health_check()
            except Exception:
                availability[module_name] = False

        return availability

    def _perform_minimal_evaluation(self, nwb_path: str, available_modules: Dict[str, bool]) -> EvaluationResult:
        """Perform minimal evaluation when most modules are unavailable."""
        issues = []

        # Use fallback validator if nwb-inspector unavailable
        if not available_modules.get("nwb_inspector", False):
            fallback_validator = FallbackValidator(FallbackValidationConfig())
            validation_result = fallback_validator.validate_nwb_file(Path(nwb_path))
            issues.extend(validation_result.issues)

        return EvaluationResult(
            overall_score=0.5,  # Low confidence score
            dimension_scores={"technical": 0.5, "scientific": 0.3, "usability": 0.3},
            issues=issues,
            confidence_level="low",
            degradation_mode=True,
            available_modules=available_modules
        )
```

This enhanced modular design provides:

1. **Robust Failure Handling**: Circuit breakers prevent cascading failures
2. **Fallback Mechanisms**: Independent validation when primary tools fail
3. **Resource Protection**: Prevents system overload with simple resource management
4. **Graceful Degradation**: Continues operation with reduced functionality
5. **Small, Implementable Chunks**: Each component ~150-200 lines, perfect for Claude Code
6. **Enhanced Error Recovery**: Automatic detection and recovery mechanisms
7. **Simple Monitoring**: Basic health checks and status reporting

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Restructure evaluation-reporting specs into modular architecture", "status": "completed", "activeForm": "Restructuring evaluation-reporting specs into modular architecture"}, {"content": "Update design.md with modular component breakdown", "status": "completed", "activeForm": "Updating design.md with modular component breakdown"}, {"content": "Update requirements.md with module-specific requirements", "status": "in_progress", "activeForm": "Updating requirements.md with module-specific requirements"}, {"content": "Update tasks.md with granular implementation steps", "status": "pending", "activeForm": "Updating tasks.md with granular implementation steps"}]