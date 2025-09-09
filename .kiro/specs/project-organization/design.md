# Design Document

## Overview

This design document outlines the reorganization of the agentic neurodata conversion project into a well-structured, maintainable, and collaborative codebase. The project currently contains sophisticated functionality for converting neuroscience data to NWB format using LLM-powered agents, but requires proper organization to support team development and AI-assisted workflows.

The design follows modern Python project patterns with clear separation of concerns, comprehensive testing infrastructure, and robust development tooling. The architecture supports both standalone usage and integration with external systems through well-defined APIs.

## Architecture

### High-Level Architecture

```
agentic-neurodata-conversion/
├── agentic_neurodata_conversion/    # Main package 
│   ├── core/                        # Core business logic
│   ├── agents/                      # Agent implementations
│   ├── interfaces/                  # Data interfaces and protocols
│   ├── utils/                       # Utility functions
│   └── config/                      # Configuration management
├── tests/                           # Test suite
├── docs/                            # Documentation
├── documents/                       # Reference documents for development
├── scripts/                         # Development and deployment scripts
├── examples/                        # Usage examples
├── data/                            # Sample data and fixtures
├── .env.dev.template                # Development environment template
├── .env.production.template         # Production environment template
└── deployment/                      # Containerization and deployment
```

### Package Structure

The main package `agentic_neurodata_conversion/` follows a layered architecture:

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

### Core Components (Based on Existing Implementation)

#### 1. Core Processing (`agentic_neurodata_conversion/core/`)

**Purpose**: Central orchestration of data conversion workflows

**Key Classes** (refactored from existing modules):
- `ConversionOrchestrator`: Main orchestrator (refactored from script-based logic)
- `EvaluationAgent`: Validates outputs and generates reports (exists in `evaluation_agent_final.py`)
- `FormatDetector`: Detects data formats (exists in `format_detector.py`)
- `KnowledgeGraphBuilder`: Creates RDF representations (exists in `knowledge_graph.py`)

**Interfaces**:
```python
class ConversionOrchestrator:
    def __init__(self, config: ConversionConfig)
    def detect_formats(self, dataset_path: Path) -> List[FormatMatch]
    def run_conversion_pipeline(self, dataset_path: Path) -> ConversionResult

class EvaluationAgent:  # Already implemented
    def validate_nwb(self, nwb_path: str) -> Dict[str, Any]
    def generate_ttl_and_outputs(self, nwb_path: str, **kwargs) -> Dict[str, Any]
    def write_context_and_report(self, nwb_path: str, eval_results: Dict) -> Dict[str, Any]

class FormatDetector:  # Already implemented
    def detect_formats(self, root: Path) -> List[Dict[str, Any]]
```

#### 2. Agent Framework (`agentic_neurodata_conversion/agents/`)

**Purpose**: LLM-powered agents for different aspects of conversion

**Key Classes** (refactored from existing modules):
- `BaseAgent`: Abstract base class for all agents (to be created)
- `ConversationAgent`: Handles metadata extraction (exists in `conversationAgent.py`)
- `ConversionAgent`: Generates conversion scripts (exists in `conversionagent.py`)
- `MetadataQuestioner`: Handles dynamic questioning (exists in `metadata_questioner.py`)

**Interfaces**:
```python
class ConversationAgent:  # Already implemented
    def analyze_dataset(self, dataset_dir: str, out_report_json: Optional[str] = None) -> Dict[str, Any]

class ConversionAgent:  # Already implemented  
    def synthesize_conversion_script(self, normalized_metadata: Dict, files_map: Dict, output_nwb_path: str) -> str
    def write_generated_script(self, code: str, out_path: str) -> str
    def run_generated_script(self, script_path: str) -> int

class MetadataQuestioner:  # Already implemented
    def get_required_fields(self, kg_file: str, experiment_type: str) -> List[Tuple[str, str]]
    def generate_dynamic_question(self, field: str, constraints: Dict, inferred: Any = None) -> str
```

#### 3. Integration Interfaces (`agentic_neurodata_conversion/interfaces/`)

**Purpose**: External system integrations and protocols

**Key Classes** (based on existing integrations):
- `MCPServer`: FastAPI-based MCP server (exists in `mcp_server.py`)
- `DataladManager`: DataLad integration for data management and provenance
- `LLMProvider`: Abstraction for different LLM providers (OpenRouter, Ollama)
- `ProvenanceTracker`: Tracks conversion history and data lineage

**Interfaces**:
```python
class MCPServer:  # Already implemented
    def __init__(self)
    async def initialize_pipeline(self, config: Optional[Dict] = None) -> Dict[str, Any]
    async def analyze_dataset(self, dataset_dir: str, **kwargs) -> Dict[str, Any]
    async def generate_conversion_script(self, normalized_metadata: Dict, files_map: Dict) -> Dict[str, Any]
    async def evaluate_nwb_file(self, nwb_path: str, **kwargs) -> Dict[str, Any]

class DataladManager:  # Critical for data management and provenance
    def __init__(self, dataset_path: Path)
    def create_dataset(self, path: Path, description: str) -> None
    def save_conversion_result(self, nwb_path: Path, metadata: Dict, message: str) -> str
    def track_provenance(self, input_files: List[Path], output_file: Path, conversion_metadata: Dict) -> None
    def install_subdataset(self, source: str, path: Path) -> None
    def get_file_history(self, file_path: Path) -> List[Dict[str, Any]]

class LLMProvider:  # To be abstracted from existing implementations
    def __init__(self, provider: str, model: str, **kwargs)
    async def generate_response(self, prompt: str, **kwargs) -> str
    def get_available_models(self) -> List[str]
    def extract_timeseries(self) -> List[TimeSeries]
    def get_electrode_info(self) -> ElectrodeTable
```

### DataLad Integration and Provenance Tracking

#### DataLad Architecture

DataLad serves two critical purposes in this project:

1. **Development Data Management**: Managing test datasets, evaluation data, and conversion examples
2. **Conversion Output Provenance**: Each conversion creates a DataLad repository tracking the iterative conversion process, decisions, and history

#### Development Data Management

**Dataset Structure**:
```
agentic-neurodata-conversion/  # Main DataLad dataset
├── data/                      # Test and evaluation datasets
│   ├── synthetic/             # Synthetic messy datasets
│   ├── evaluation/            # Ground truth datasets
│   └── samples/               # Small sample datasets
├── etl/                       # ETL workflows and data
│   ├── input-data/            # Subdatasets with conversion examples
│   └── evaluation-data/       # Evaluation datasets
└── results/                   # Conversion outputs (annexed for large files)
```

**Key Principles**:
- **Python API Only**: Always use `import datalad.api as dl`, never CLI commands
- **Proper Annexing**: Development files (.py, .md, .toml) stay in git, only large data files (>10MB) go to annex
- **Subdataset Strategy**: External conversion repositories as subdatasets for examples and testing

**DataLad Configuration**:
```python
class DataladManager:
    def __init__(self, dataset_path: Path):
        self.dataset_path = dataset_path
        self.dl = datalad.api
    
    def initialize_development_dataset(self) -> None:
        """Initialize project as DataLad dataset with proper configuration"""
        # Set up .gitattributes FIRST
        gitattributes_content = """
# Only use annex for large data files (>10MB)
* annex.backend=MD5E
**/.git* annex.largefiles=nothing

# Keep all development files in git (not annex)
*.py annex.largefiles=nothing
*.md annex.largefiles=nothing
*.toml annex.largefiles=nothing
*.json annex.largefiles=nothing
*.yaml annex.largefiles=nothing

# Default: only annex files larger than 10MB
* annex.largefiles=(largerthan=10mb)
"""
        (self.dataset_path / ".gitattributes").write_text(gitattributes_content)
        
        # Create dataset with text2git configuration
        self.dl.create(
            path=str(self.dataset_path),
            cfg_proc="text2git",
            description="Agentic neurodata conversion project",
            force=True
        )
    
    def install_conversion_examples(self) -> None:
        """Install CatalystNeuro conversion repositories as subdatasets"""
        conversion_repos = [
            ("https://github.com/catalystneuro/IBL-to-nwb", "etl/input-data/catalystneuro-conversions/IBL-to-nwb"),
            ("https://github.com/catalystneuro/buzsaki-lab-to-nwb", "etl/input-data/catalystneuro-conversions/buzsaki-lab-to-nwb"),
            # Add more as needed
        ]
        
        for source, path in conversion_repos:
            try:
                self.dl.install(dataset=str(self.dataset_path), path=path, source=source)
            except Exception as e:
                logger.warning(f"Failed to install {source}: {e}")
```

#### Conversion Output Provenance Tracking

**Each conversion creates its own DataLad repository** that leverages DataLad's natural git/git-annex history for provenance tracking. The repository contains the conversion outputs and DataLad automatically tracks all changes, versions, and history.

**Simple Conversion Repository Structure**:
```
conversion-{dataset-name}-{timestamp}/  # DataLad repository for this conversion
├── input_data/                         # Original input data (linked via DataLad)
├── output.nwb                          # Final NWB output (annexed if large)
├── conversion_script.py                # Final conversion script
├── validation_report.json              # NWB validation results
├── {dataset-name}.data.ttl             # RDF knowledge graph (turtle format)
├── {dataset-name}.data.nt              # RDF in N-Triples format
├── {dataset-name}.data.jsonld          # RDF in JSON-LD format
├── {dataset-name}.data.triples.txt     # Human-readable triples with labels
├── {dataset-name}.data.html            # Interactive knowledge graph visualization
├── {dataset-name}_context.txt          # Human-readable evaluation context
├── {dataset-name}_quality_report.txt   # Quality assessment report
├── agent_log.jsonl                     # Agent interactions log
└── README.md                           # Basic conversion info
```

**Provenance Implementation** (leveraging DataLad's natural capabilities):
```python
class ConversionProvenanceManager:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.dl = datalad.api
    
    def create_conversion_repository(self, input_dataset: Path, dataset_name: str) -> Path:
        """Create a new DataLad repository for this conversion"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_name = f"conversion-{dataset_name}-{timestamp}"
        repo_path = self.output_dir / repo_name
        
        # Create DataLad dataset
        self.dl.create(
            path=str(repo_path),
            description=f"Agentic conversion of {dataset_name}",
            cfg_proc="text2git"
        )
        
        # Link input data (DataLad handles this efficiently)
        if input_dataset.is_dir():
            self.dl.install(
                dataset=str(repo_path),
                path="input_data",
                source=str(input_dataset)
            )
        
        # Initial commit
        self.dl.save(
            dataset=str(repo_path),
            message=f"Initialize conversion of {dataset_name}"
        )
        
        return repo_path
    
    def save_conversion_iteration(self, repo_path: Path, output_nwb: Optional[Path],
                                conversion_script: str, validation_results: Dict,
                                agent_interactions: List[Dict], message: str) -> None:
        """Save a conversion iteration - DataLad handles the versioning"""
        
        # Update files (matching actual EvaluationAgent outputs)
        if output_nwb and output_nwb.exists():
            shutil.copy2(output_nwb, repo_path / "output.nwb")
        
        (repo_path / "conversion_script.py").write_text(conversion_script)
        
        with open(repo_path / "validation_report.json", 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)
        
        # Copy knowledge graph files if they exist (generated by EvaluationAgent)
        dataset_name = repo_path.name.split('-')[1]  # Extract from repo name
        kg_files = [
            f"{dataset_name}.data.ttl",
            f"{dataset_name}.data.nt", 
            f"{dataset_name}.data.jsonld",
            f"{dataset_name}.data.triples.txt",
            f"{dataset_name}.data.html",
            f"{dataset_name}_context.txt",
            f"{dataset_name}_quality_report.txt"
        ]
        
        for kg_file in kg_files:
            source_path = Path(output_nwb).parent / kg_file
            if source_path.exists():
                shutil.copy2(source_path, repo_path / kg_file)
        
        # Append agent interactions to log
        with open(repo_path / "agent_log.jsonl", 'a') as f:
            for interaction in agent_interactions:
                f.write(json.dumps(interaction, default=str) + '\n')
        
        # DataLad save - this creates the provenance automatically
        self.dl.save(
            dataset=str(repo_path),
            message=message,
            recursive=True
        )
    
    def get_conversion_history(self, repo_path: Path) -> List[Dict[str, Any]]:
        """Get conversion history from DataLad's git log"""
        try:
            # Use DataLad's git interface to get history
            import subprocess
            result = subprocess.run(
                ["git", "log", "--oneline", "--all"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            history = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    commit_hash, message = line.split(' ', 1)
                    history.append({
                        "commit": commit_hash,
                        "message": message,
                        "timestamp": None  # Could get from git log --format if needed
                    })
            
            return history
        except Exception:
            return []
    
    def tag_successful_conversion(self, repo_path: Path) -> None:
        """Tag a successful conversion"""
        self.dl.save(
            dataset=str(repo_path),
            message="Mark successful conversion",
            version_tag="success"
        )
```

#### DataLad Best Practices for Development

```python
# Always use Python API, never CLI
import datalad.api as dl

# Check subdataset status
def check_subdatasets():
    subdatasets = dl.subdatasets(dataset=".", return_type='list')
    for subds in subdatasets:
        if subds['state'] == 'absent':
            print(f"Missing subdataset: {subds['path']}")
            # Install if needed
            dl.install(dataset=".", path=subds['path'])

# Handle large files selectively
def get_evaluation_data():
    # Get only specific files, not entire datasets
    dl.get(path="data/evaluation/small_dataset.nwb")
    # Avoid: dl.get(path="data/", recursive=True)  # Downloads everything
```

**Common Issues and Solutions**:
1. **Subdataset not initialized**: Use `dl.install()` with proper paths
2. **Files in annex when they shouldn't be**: Check `.gitattributes` configuration
3. **Large file downloads**: Use selective `dl.get()` calls
4. **Permission issues**: Files may be locked by git-annex, handle gracefully

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

## Configuration Management

**Pydantic-Settings Based Configuration**: All configuration uses pydantic-settings with `.env` files for environment-specific overrides, following the pattern established in the config-example.

### Configuration Architecture

```python
# agentic_neurodata_conversion/config.py
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Dict, Any, List
from pathlib import Path

class ConversationAgentConfig(BaseModel):
    """Configuration for conversation agent"""
    llm_provider: str = "openrouter"
    model: str = "anthropic/claude-3.5-sonnet"
    temperature: float = 0.2
    timeout: int = 30
    max_retries: int = 3

class ConversionAgentConfig(BaseModel):
    """Configuration for conversion agent"""
    llm_provider: str = "openrouter"
    model: str = "anthropic/claude-3.5-sonnet"
    temperature: float = 0.1  # Lower temperature for code generation
    timeout: int = 60
    max_retries: int = 3

class EvaluationAgentConfig(BaseModel):
    """Configuration for evaluation agent"""
    llm_provider: str = "ollama"  # Can use local model for evaluation
    model: str = "llama3.2:3b"
    temperature: float = 0.0
    timeout: int = 30

class DataladConfig(BaseModel):
    """DataLad configuration"""
    auto_create_repos: bool = True
    default_remote: str = "gin"
    cache_dir: str = ".datalad_cache"
    
    @field_validator("cache_dir")
    @classmethod
    def validate_cache_dir(cls, v: str) -> str:
        """Ensure cache directory is valid"""
        path = Path(v)
        if path.is_absolute():
            raise ValueError("Cache directory should be relative to project root")
        return v

class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: str = "10MB"
    backup_count: int = 5

class Settings(BaseSettings):
    """Main settings container with nested configuration"""
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Core settings
    debug: bool = False
    environment: str = "development"
    
    # Logging
    logging: LoggingConfig = LoggingConfig()
    
    # Agent configurations (agent-specific LLM settings)
    conversation_agent: ConversationAgentConfig = ConversationAgentConfig()
    conversion_agent: ConversionAgentConfig = ConversionAgentConfig()
    evaluation_agent: EvaluationAgentConfig = EvaluationAgentConfig()
    
    # DataLad configuration (required for all conversions)
    datalad: DataladConfig = DataladConfig()
    
    # LLM Provider settings
    openrouter_api_key: Optional[str] = Field(None, description="Required when using OpenRouter")
    ollama_endpoint: str = "http://localhost:11434"
    
    # MCP Server settings
    mcp_server_host: str = "127.0.0.1"
    mcp_server_port: int = 8000
    
    @field_validator("openrouter_api_key")
    @classmethod
    def validate_openrouter_key(cls, v: Optional[str], info) -> Optional[str]:
        """Validate OpenRouter API key when required"""
        # Check if any agent is configured to use OpenRouter
        if hasattr(info.data, 'conversation_agent') and info.data.get('conversation_agent', {}).get('llm_provider') == 'openrouter':
            if not v:
                raise ValueError("OpenRouter API key required when using OpenRouter provider")
        return v

# Global settings instance
settings = Settings()
```

### Environment Configuration Templates

**.env.dev.template**:
```bash
# Development Configuration
DEBUG=true
ENVIRONMENT=development

# Logging
LOGGING__LEVEL=DEBUG
LOGGING__FILE_PATH=logs/development.log

# Conversation Agent (using local model for development)
CONVERSATION_AGENT__LLM_PROVIDER=ollama
CONVERSATION_AGENT__MODEL=llama3.2:3b
CONVERSATION_AGENT__TEMPERATURE=0.2

# Conversion Agent (using cloud model for better code generation)
CONVERSION_AGENT__LLM_PROVIDER=openrouter
CONVERSION_AGENT__MODEL=anthropic/claude-3.5-sonnet
CONVERSION_AGENT__TEMPERATURE=0.1

# Evaluation Agent (local model is sufficient)
EVALUATION_AGENT__LLM_PROVIDER=ollama
EVALUATION_AGENT__MODEL=llama3.2:3b

# LLM Provider Settings
OPENROUTER_API_KEY=your_key_here
OLLAMA_ENDPOINT=http://localhost:11434

# DataLad Settings (required)
DATALAD__AUTO_CREATE_REPOS=true
DATALAD__CACHE_DIR=.datalad_cache
DATALAD__DEFAULT_REMOTE=gin

# MCP Server
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8000
```

**.env.production.template**:
```bash
# Production Configuration
DEBUG=false
ENVIRONMENT=production

# Logging
LOGGING__LEVEL=INFO
LOGGING__FILE_PATH=logs/production.log
LOGGING__MAX_FILE_SIZE=50MB
LOGGING__BACKUP_COUNT=10

# All agents use cloud models in production
CONVERSATION_AGENT__LLM_PROVIDER=openrouter
CONVERSATION_AGENT__MODEL=anthropic/claude-3.5-sonnet

CONVERSION_AGENT__LLM_PROVIDER=openrouter
CONVERSION_AGENT__MODEL=anthropic/claude-3.5-sonnet

EVALUATION_AGENT__LLM_PROVIDER=openrouter
EVALUATION_AGENT__MODEL=anthropic/claude-3.5-haiku  # Cheaper model for evaluation

# Required in production
OPENROUTER_API_KEY=  # Must be set - will raise error if missing

# DataLad Settings (required)
DATALAD__AUTO_CREATE_REPOS=true
DATALAD__DEFAULT_REMOTE=gin
DATALAD__CACHE_DIR=/var/cache/datalad

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
```

### Configuration Loading

```python
# agentic_neurodata_conversion/config/__init__.py
from .config import settings, Settings
from .find_env_file import find_envfile

__all__ = ["settings", "Settings", "find_envfile"]
```

```python
# agentic_neurodata_conversion/config/find_env_file.py
import logging
from pathlib import Path
import dotenv

logger = logging.getLogger(__name__)

def find_envfile():
    """Find .env file following the config-example pattern"""
    env_file = dotenv.find_dotenv()
    if not env_file:
        # Look for template files
        project_root = Path(__file__).resolve().parent.parent.parent
        dev_template = project_root / '.env.dev.template'
        if dev_template.exists():
            logger.warning(f"No .env found, copy {dev_template} to .env to get started")
        raise ValueError("Failed to find .env file")

    env_file = Path(env_file).resolve()
    logger.info(f"Loading environment variables from {env_file}")
    return env_file
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

#### Resource-Based Test Clusters (using pytest marks)

**Priority Order** (from lowest to highest cost):

1. **Direct Functionality Tests** (`@pytest.mark.unit`)
   - No external dependencies
   - Pure function testing
   - Data model validation
   - Configuration loading

2. **Mocked LLM Tests** (`@pytest.mark.mock_llm`)
   - Mock LLM responses for deterministic testing
   - Agent workflow testing with predictable outputs
   - Low maintenance burden
   - Based on existing `testing_pipeline_pytest.py` pattern

3. **Small Local Model Tests** (`@pytest.mark.small_model`)
   - <3B parameter models (e.g., Ministral 3B, llama3.2:3b, OLMo-2-1B, Gemma 270M)
   - Basic agent functionality validation
   - Requires local Ollama installation

4. **Large Local Model Tests** (`@pytest.mark.large_model_minimal`)
   - 7B parameter models with minimal context
   - More complex reasoning tests
   - Requires significant RAM

5. **Large Local Model Extended Tests** (`@pytest.mark.large_model_extended`)
   - ~7B parameter models with full context (e.g. gpt-oss-20B , NVIDIA Nemotron Nano 9B V2, Mistral 7B, Gemma 7B)
   - End-to-end workflow testing
   - Requires high RAM availability

6. **Cheap API Tests** (`@pytest.mark.cheap_api`)
   - Inexpensive cloud models (gpt-oss-120B (high), GPT-5 mini (medium), Grok 3 mini Reasoning (high), Gemini 2.5 Flash )
   - Integration testing with real APIs
   - Rate-limited execution

7. **Frontier API Tests** (`@pytest.mark.frontier_api`)
   - Latest/most expensive models (Claude 4.1 Opus, Claude 4 Sonnet, GPT-5 (high), Gemini 2.5 Pro)
   - Final validation and benchmarking
   - Minimal usage, high confidence tests

#### Integration with Existing Test Infrastructure

Building on the existing `testing_pipeline_pytest.py`:

```python
# tests/conftest.py
import pytest
from pathlib import Path
import tempfile
import datalad.api as dl
from agentic_neurodata_conversion.config import settings

@pytest.fixture
def temp_datalad_repo():
    """Create temporary DataLad repository for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "test_repo"
        dl.create(path=str(repo_path), description="Test repository")
        yield repo_path
        # Cleanup handled by tempfile

@pytest.fixture
def mock_llm_responses():
    """Provide mock LLM responses for testing"""
    return {
        "analyze_dataset": {"status": "success", "result": {"metadata": "test"}},
        "generate_script": {"status": "success", "script": "# test script"},
        "evaluate_nwb": {"status": "success", "validation": {"passed": True}}
    }

# Pytest marks for resource-based testing
pytest.mark.unit = pytest.mark.unit
pytest.mark.mock_llm = pytest.mark.mock_llm
pytest.mark.small_model = pytest.mark.small_model
pytest.mark.large_model_minimal = pytest.mark.large_model_minimal
pytest.mark.large_model_extended = pytest.mark.large_model_extended
pytest.mark.cheap_api = pytest.mark.cheap_api
pytest.mark.frontier_api = pytest.mark.frontier_api
```

#### DataLad Testing Strategy

Following DataLad project patterns for temporary repository testing:

```python
# tests/test_datalad_integration.py
import pytest
import tempfile
from pathlib import Path
import datalad.api as dl
from agentic_neurodata_conversion.core.provenance import ConversionProvenanceManager

@pytest.mark.unit
def test_datalad_repo_creation():
    """Test DataLad repository creation without external dependencies"""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ConversionProvenanceManager(Path(temp_dir))
        repo_path = manager.create_conversion_repository(
            Path("test_input"), "test_dataset"
        )
        assert repo_path.exists()
        assert (repo_path / ".datalad").exists()

@pytest.mark.mock_llm
def test_conversion_with_mocked_agents(temp_datalad_repo, mock_llm_responses):
    """Test full conversion workflow with mocked LLM responses"""
    # Test implementation using existing testing_pipeline_pytest.py pattern
    pass
```

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
COPY agentic_neurodata_conversion/ agentic_neurodata_conversion/
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
      - LLM_PROVIDER=${LLM_PROVIDER:-openrouter}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - OLLAMA_ENDPOINT=${OLLAMA_ENDPOINT:-http://ollama:11434}
      - LLM_MODEL=${LLM_MODEL:-anthropic/claude-sonnet-4}
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
    profiles:
      - local-llm

volumes:
  ollama_data:
  datalad_cache:
```

### Production Deployment

The system is designed for simple deployment using Docker Compose, suitable for single-server or small-scale deployments. For larger scale needs, the containerized services can be deployed to any container orchestration platform.

#### Environment Configuration
```bash
# .env.production
ENVIRONMENT=production
LOG_LEVEL=INFO

# LLM Provider Configuration (choose one)
LLM_PROVIDER=openrouter  # or 'ollama' for local models
OPENROUTER_API_KEY=your_openrouter_key_here
LLM_MODEL=anthropic/claude-sonnet-4

# For local Ollama deployment
# LLM_PROVIDER=ollama
# OLLAMA_ENDPOINT=http://localhost:11434
# LLM_MODEL=mistral:7b

MCP_SERVER_PORT=8000
```

#### Health Checks and Monitoring
```yaml
# Additional health check configuration for docker-compose.yml
services:
  converter:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Design Decisions and Migration Strategy

### 1. Interface Strategy
- **Current Interfaces**: Maintain existing script interfaces during refactoring
- **MCP Integration**: Each agent requires MCP interface for AI tool integration
- **Chat Interface**: Conversation agent provides user-facing chat interface
- **Pipeline Scripts**: Maintain current pipeline scripts (including final_script.py) as part of iterative agentic system

### 2. Package Structure Migration
- **Target**: `agentic_neurodata_conversion/` package structure 
- **Migration**: Complete refactoring with no backward compatibility considerations
- **Approach**: All-at-once migration, reusing current working implementation
- **Imports**: Follow standard Python package best practices, avoid circular imports

### 3. Configuration Management
- **Implementation**: Pydantic-settings with nested configuration classes
- **Environment Files**: `.env.dev.template` and `.env.production.template` for easy setup
- **Agent-Specific Config**: Each agent has its own configuration section
- **Validation**: Required settings raise errors when missing, sensible defaults for optional settings

### 4. DataLad Integration Scope
- **Development**: Required for project development and testing
- **Conversion Output**: Required - every conversion starts by creating DataLad repository
- **DANDI Integration**: Essential for eventual upload to DANDI (DataLad-backed data store)
- **Status**: Hard requirement, not optional

### 5. LLM Provider Flexibility
- **Agent-Specific Configuration**: Each agent configured independently via pydantic-settings
- **Registration Pattern**: Each agent registers its own MCP tools
- **Provider Interface**: Abstract interface with wrapping classes for provider-specific features
- **Fallback Strategy**: Single implementation when abstraction breaks, prioritizing working system

### 6. Testing Strategy
- **Existing Integration**: Build on current `testing_pipeline_pytest.py` infrastructure
- **Resource-Based Clusters**: Pytest marks for different resource availability levels
- **DataLad Testing**: Temporary repositories using DataLad project patterns
- **Priority Order**: Unit → Mock → Small Models → Large Models → APIs (cheap to expensive)

### 7. Migration Approach
- **No Backward Compatibility**: Complete refactoring prioritizing future maintainability
- **Reuse Working Code**: Leverage current implementation as it represents complete working system
- **Modular Design**: Restructure for testability and maintainability
- **Standard Practices**: Follow Python packaging best practices

### 8. Interface Coexistence and Entry Points
- **Preserve Current Interfaces**: Maintain existing script entry points during refactoring
- **Script Renaming**: Rename scripts for clarity (e.g., `final_script.py` → `pipeline_runner.py`)
- **Shared Functionality**: All interfaces import from common package modules
- **DataLad Repository Creation**: Idempotent function callable from any interface
- **MCP Tool Registration**: Each agent registers its own tools independently

### 9. Documentation and Reference Materials
- **Documents Directory**: Contains reference documents for development (may not be included in final package)
- **Architecture Documents**: Moved from `various-documents/` to `documents/architecture-documents/`
- **Development Reference**: Documents serve as reference during refactoring but are not part of the runtime package

### 10. Error Handling Standardization
- **Unified Hierarchy**: Implement the proposed error hierarchy across all modules
- **Current Logic Integration**: Incorporate existing error handling patterns where appropriate
- **Consistent Patterns**: Standardize error handling, logging, and recovery mechanisms

This design provides a clear foundation for refactoring the existing working prototype into a maintainable, modular package while preserving all current functionality and enabling future development.