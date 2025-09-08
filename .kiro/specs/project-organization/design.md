# Design Document

## Overview

This design document outlines the reorganization of the agentic neurodata conversion project into a well-structured, maintainable, and collaborative codebase. The project currently contains sophisticated functionality for converting neuroscience data to NWB format using LLM-powered agents, but requires proper organization to support team development and AI-assisted workflows.

The design follows modern Python project patterns with clear separation of concerns, comprehensive testing infrastructure, and robust development tooling. The architecture supports both standalone usage and integration with external systems through well-defined APIs.

## Architecture

### High-Level Architecture

```
agentic-neurodata-conversion/
├── src/
│   ├── core/                        # Core business logic
│   ├── agents/                      # Agent implementations
│   ├── interfaces/                  # Data interfaces and protocols
│   ├── utils/                       # Utility functions
│   └── config/                      # Configuration management
├── tests/                           # Test suite
├── docs/                            # Markdown Documentation
├── documents/                       # Documents relevant to the project
├── scripts/                         # Development and deployment scripts
├── examples/                        # Usage examples
├── data/                            # Sample data and fixtures
└── deployment/                      # Containerization and deployment
```

### Package Structure

The main package `src/` follows a layered architecture:

1. **Core Layer**: Contains fundamental business logic and domain models
2. **Agent Layer**: Implements LLM-powered agents for different tasks
3. **Interface Layer**: Defines data interfaces and external system integrations
4. **Utility Layer**: Provides common functionality and helpers
5. **Configuration Layer**: Manages settings and environment configuration

### Design Patterns

- **Factory Pattern**: For creating different types of data interfaces and agents
- **Strategy Pattern**: For different conversion strategies and validation approaches
- **Observer Pattern**: For monitoring conversion progress and events
- **Adapter Pattern**: For integrating with different data formats and external systems
- **Command Pattern**: For implementing reversible operations and workflow steps

## Components and Interfaces

### Core Components

#### 1. Conversion Engine (`src/core/`)

**Purpose**: Central orchestration of data conversion workflows

**Key Classes**:
- `ConversionEngine`: Main orchestrator for conversion workflows
- `ConversionPipeline`: Defines conversion steps and dependencies
- `ConversionContext`: Maintains state and metadata throughout conversion
- `ValidationEngine`: Handles NWB validation and quality checks

**Interfaces**:
```python
class ConversionEngine:
    def __init__(self, config: ConversionConfig)
    def register_interface(self, name: str, interface_class: Type[DataInterface])
    def run_conversion(self, source_data: Dict, metadata: Dict) -> ConversionResult
    def validate_output(self, nwb_path: Path) -> ValidationResult

class ConversionPipeline:
    def add_step(self, step: ConversionStep)
    def execute(self, context: ConversionContext) -> ConversionResult
    def rollback(self, context: ConversionContext)
```

#### 2. Agent Framework (`src/agents/`)

**Purpose**: LLM-powered agents for different aspects of conversion

**Key Classes**:
- `BaseAgent`: Abstract base class for all agents
- `ConversationAgent`: Handles metadata extraction and user interaction
- `ConversionAgent`: Generates conversion scripts and orchestrates conversion
- `EvaluationAgent`: Validates outputs and generates quality reports
- `KnowledgeGraphAgent`: Creates semantic representations of data

**Interfaces**:
```python
class BaseAgent:
    def __init__(self, llm_config: LLMConfig)
    async def process(self, input_data: Any) -> AgentResult
    def get_capabilities(self) -> List[str]

class ConversationAgent(BaseAgent):
    async def analyze_dataset(self, dataset_path: Path) -> AnalysisResult
    async def extract_metadata(self, source_data: Dict) -> MetadataResult
    async def ask_user_questions(self, questions: List[str]) -> Dict[str, str]
```

#### 3. Data Interfaces (`src/interfaces/`)

**Purpose**: Standardized interfaces for different data formats

**Key Classes**:
- `DataInterface`: Base interface for all data sources
- `NWBInterface`: Handles NWB file operations
- `CSVInterface`: Processes CSV time series data
- `EphysInterface`: Handles electrophysiology data formats
- `BehaviorInterface`: Processes behavioral data

**Interfaces**:
```python
class DataInterface:
    def __init__(self, source_data: Dict[str, Any])
    def get_metadata(self) -> Dict[str, Any]
    def validate_source(self) -> ValidationResult
    def run_conversion(self, nwbfile: NWBFile, metadata: Dict) -> None

class EphysInterface(DataInterface):
    def detect_format(self) -> str
    def extract_timeseries(self) -> List[TimeSeries]
    def get_electrode_info(self) -> ElectrodeTable
```

### External Integrations

#### 1. MCP Server Integration

**Purpose**: Expose functionality through Model Context Protocol

**Components**:
- `MCPServer`: FastAPI-based server exposing conversion tools
- `MCPToolRegistry`: Manages available tools and their schemas
- `MCPStateManager`: Handles pipeline state and workflow coordination

#### 2. DataLad Integration

**Purpose**: Data management and provenance tracking

**Components**:
- `DataladManager`: Handles dataset operations and version control
- `ProvenanceTracker`: Records conversion history and lineage
- `DatasetValidator`: Ensures data integrity and completeness

#### 3. Knowledge Graph Integration

**Purpose**: Semantic representation and querying of converted data

**Components**:
- `KnowledgeGraphBuilder`: Creates RDF representations
- `OntologyManager`: Manages NWB and domain ontologies
- `SPARQLInterface`: Provides query capabilities

## Data Models

### Core Data Models

#### ConversionConfig
```python
@dataclass
class ConversionConfig:
    output_dir: Path
    validation_level: ValidationLevel
    llm_config: LLMConfig
    interface_configs: Dict[str, Dict[str, Any]]
    logging_config: LoggingConfig
```

#### ConversionResult
```python
@dataclass
class ConversionResult:
    success: bool
    output_path: Optional[Path]
    validation_result: ValidationResult
    metadata: Dict[str, Any]
    errors: List[ConversionError]
    warnings: List[ConversionWarning]
    execution_time: float
```

#### ValidationResult
```python
@dataclass
class ValidationResult:
    passed: bool
    inspector_results: Dict[str, Any]
    quality_metrics: Dict[str, float]
    issues: List[ValidationIssue]
    recommendations: List[str]
```

### Agent Communication Models

#### AgentMessage
```python
@dataclass
class AgentMessage:
    agent_id: str
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime
    correlation_id: str
```

#### WorkflowState
```python
@dataclass
class WorkflowState:
    workflow_id: str
    current_step: str
    completed_steps: List[str]
    context: Dict[str, Any]
    errors: List[WorkflowError]
```

## Error Handling

### Error Hierarchy

```python
class AgenticConverterError(Exception):
    """Base exception for all converter errors"""
    pass

class ConversionError(AgenticConverterError):
    """Errors during data conversion"""
    pass

class ValidationError(AgenticConverterError):
    """Errors during validation"""
    pass

class AgentError(AgenticConverterError):
    """Errors from LLM agents"""
    pass

class ConfigurationError(AgenticConverterError):
    """Configuration and setup errors"""
    pass
```

### Error Handling Strategy

1. **Graceful Degradation**: System continues operation when non-critical components fail
2. **Detailed Error Context**: All errors include context about the operation being performed
3. **Recovery Mechanisms**: Automatic retry for transient failures
4. **User-Friendly Messages**: Clear error messages for end users
5. **Comprehensive Logging**: All errors logged with full context for debugging

### Retry and Circuit Breaker Patterns

```python
class RetryConfig:
    max_attempts: int = 3
    backoff_factor: float = 2.0
    max_delay: float = 60.0

class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 300.0
    half_open_max_calls: int = 3
```

## Testing Strategy

### Test Structure

```
tests/
├── unit/                           # Unit tests
│   ├── test_core/                  # Core component tests
│   ├── test_agents/                # Agent tests
│   ├── test_interfaces/            # Interface tests
│   └── test_utils/                 # Utility tests
├── integration/                    # Integration tests
│   ├── test_workflows/             # End-to-end workflow tests
│   ├── test_mcp_server/            # MCP server integration tests
│   └── test_external_systems/      # External system integration tests
├── evaluation/                     # Evaluation and benchmarking tests
│   ├── test_conversion_quality/    # Conversion quality tests
│   ├── test_performance/           # Performance benchmarks
│   └── test_agent_accuracy/        # Agent accuracy tests
├── fixtures/                       # Test data and fixtures
└── conftest.py                     # Pytest configuration
```

### Testing Approaches

#### 1. Unit Testing
- **Coverage Target**: 90%+ line coverage
- **Mocking Strategy**: Mock external dependencies (LLMs, file systems, networks)
- **Property-Based Testing**: Use Hypothesis for testing data conversion properties
- **Parameterized Tests**: Test multiple data formats and edge cases

#### 2. Integration Testing
- **Workflow Testing**: Test complete conversion workflows
- **Agent Interaction Testing**: Test agent communication and coordination
- **External System Testing**: Test integrations with DataLad, MCP, etc.
- **Performance Testing**: Measure conversion times and resource usage

#### 3. Evaluation Testing
- **Conversion Quality**: Compare outputs against known good conversions
- **Agent Accuracy**: Measure LLM agent performance on standardized tasks
- **Regression Testing**: Ensure changes don't break existing functionality
- **Benchmark Testing**: Track performance metrics over time

### Test Data Management

```python
class TestDataManager:
    def __init__(self, data_dir: Path)
    def get_sample_dataset(self, format: str, size: str = "small") -> Path
    def create_synthetic_dataset(self, spec: DatasetSpec) -> Path
    def cleanup_test_data(self)
```

### Continuous Integration

- **Pre-commit Hooks**: Code formatting, linting, and basic tests
- **CI Pipeline**: Full test suite on multiple Python versions
- **Coverage Reporting**: Automated coverage reports and trends
- **Performance Monitoring**: Track performance regressions
- **Security Scanning**: Automated security vulnerability scanning

## Configuration Management

### Configuration Architecture

```python
class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None)
    def load_config(self) -> Config
    def validate_config(self, config: Config) -> ValidationResult
    def get_environment_overrides(self) -> Dict[str, Any]
    def merge_configs(self, *configs: Config) -> Config
```

### Configuration Sources (Priority Order)

1. **Command Line Arguments**: Highest priority
2. **Environment Variables**: Override file-based settings
3. **User Configuration File**: `~/.agentic-converter/config.yaml`
4. **Project Configuration File**: `pyproject.toml` or `config.yaml`
5. **Default Configuration**: Built-in defaults

### Environment-Specific Configuration

```yaml
# config.yaml
default: &default
  logging:
    level: INFO
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  conversion:
    validation_level: strict
    output_format: nwb
    
  agents:
    llm_provider: openai
    model: gpt-5-mini
    temperature: 0.2

development:
  <<: *default
  logging:
    level: DEBUG
  agents:
    model: gpt-5-mini

production:
  <<: *default
  logging:
    level: WARNING
  conversion:
    validation_level: strict
```

### Secrets Management

- **Environment Variables**: For API keys and sensitive configuration
- **Key Management**: Integration with cloud key management services
- **Local Development**: Support for `.env` files (not committed to git)
- **Validation**: Ensure required secrets are present at startup

## Logging and Monitoring

### Logging Architecture

```python
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: List[str] = ["console", "file"]
    file_path: Optional[Path] = None
    max_file_size: str = "10MB"
    backup_count: int = 5
```

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Usage examples
logger.info("conversion_started", 
           dataset_path=str(dataset_path),
           conversion_id=conversion_id,
           user_id=user_id)

logger.error("conversion_failed",
            dataset_path=str(dataset_path),
            error=str(error),
            stack_trace=traceback.format_exc())
```

### Metrics and Observability

#### Key Metrics
- **Conversion Success Rate**: Percentage of successful conversions
- **Processing Time**: Time taken for different conversion steps
- **Agent Response Time**: LLM agent response times
- **Validation Pass Rate**: Percentage of outputs passing validation
- **Error Rates**: Frequency and types of errors

#### Monitoring Integration
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Dashboards and visualization
- **OpenTelemetry**: Distributed tracing for complex workflows
- **Health Checks**: Endpoint monitoring for services

### Audit Logging

```python
class AuditLogger:
    def __init__(self, log_dir: Path)
    def log_conversion_start(self, conversion_id: str, dataset_info: Dict)
    def log_conversion_complete(self, conversion_id: str, result: ConversionResult)
    def log_agent_interaction(self, agent_id: str, action: str, context: Dict)
    def log_file_operation(self, operation: str, file_path: Path, metadata: Dict)
    def export_audit_trail(self, output_path: Path) -> None
```

## Development Workflow

### Development Environment Setup

```bash
# Clone repository
git clone https://github.com/org/agentic-neurodata-conversion.git
cd agentic-neurodata-conversion

# Install development dependencies
pixi install --all-features

# Setup pre-commit hooks
pre-commit install

# Run tests
pixi run test

# Start development server
pixi run dev
```

### Code Quality Tools

#### Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: check-toml
      - id: check-json
      - id: mixed-line-ending

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

#### Code Quality Standards
- **Ruff**: Code formatting, linting, and import sorting
- **mypy**: Static type checking
- **bandit**: Security vulnerability scanning
- **pytest-cov**: Test coverage measurement

### Git Workflow

#### Branch Strategy
- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/***: Individual feature development
- **hotfix/***: Critical bug fixes
- **release/***: Release preparation

#### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Release Management

#### Semantic Versioning
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

#### Release Process
1. Create release branch from develop
2. Update version numbers and changelog
3. Run full test suite and quality checks
4. Create release PR to main
5. Tag release and create GitHub release
6. Deploy to production environments
7. Merge back to develop

## Deployment and Infrastructure

### Containerization

#### Dockerfile
```dockerfile
FROM ghcr.io/prefix-dev/pixi:debian:bookworm-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml pixi.toml ./
RUN pip install pixi && pixi install --frozen

# Copy application code
COPY src/ src/
COPY scripts/ scripts/

# Set up entrypoint
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["pixi", "run", "serve"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  converter:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OLLAMA_ENDPOINT=http://ollama:11434/api/chat
    volumes:
      - ./data:/app/data
      - ./config:/app/config
      - ./results:/app/results
      - ./etl:/app/etl
      - datalad_cache:/app/.datalad
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0

volumes:
  ollama_data:
  datalad_cache:
```

### Cloud Deployment

#### Kubernetes Manifests
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentic-converter
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentic-converter
  template:
    metadata:
      labels:
        app: agentic-converter
    spec:
      containers:
      - name: converter
        image: agentic-converter:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### Infrastructure as Code

#### Terraform Configuration
```hcl
# infrastructure/main.tf
provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "agentic-converter-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
}

module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = "agentic-converter"
  cluster_version = "1.27"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
}
```

This comprehensive design provides a solid foundation for reorganizing the project while maintaining its sophisticated functionality and enabling collaborative development with AI assistance.