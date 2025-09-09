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

#### Agentic Design Patterns

- **Reflection Pattern**: Agents analyze their own performance and learn from outcomes
- **Planning Pattern**: Multi-step reasoning for complex conversion workflows
- **Hierarchical Agent Pattern**: Meta-agents coordinate and monitor other agents
- **Tool Use Pattern**: Structured approach to tool selection and execution
- **Human-in-the-Loop Pattern**: Seamless integration of human expertise and oversight

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
- `BaseAgent`: Abstract base class for all agents with reflection capabilities (to be created)
- `ConversationAgent`: Handles metadata extraction (exists in `conversationAgent.py`)
- `ConversionAgent`: Generates conversion scripts (exists in `conversionagent.py`)
- `MetadataQuestioner`: Handles dynamic questioning (exists in `metadata_questioner.py`)
- `ReflectiveAgent`: Mixin for self-assessment and learning capabilities
- `PlanningAgent`: Enhanced planning and reasoning for complex workflows

**Interfaces**:
```python
class BaseAgent:  # New base class with reflection capabilities
    def execute_task(self, task: Task) -> TaskResult
    def reflect_on_performance(self, result: TaskResult) -> ReflectionReport
    def learn_from_feedback(self, feedback: HumanFeedback) -> None
    def get_performance_metrics(self) -> Dict[str, float]

class ConversationAgent(BaseAgent):  # Already implemented, enhanced with reflection
    def analyze_dataset(self, dataset_dir: str, out_report_json: Optional[str] = None) -> Dict[str, Any]
    def assess_analysis_quality(self, analysis_result: Dict) -> QualityScore

class ConversionAgent(BaseAgent):  # Already implemented, enhanced with planning
    def synthesize_conversion_script(self, normalized_metadata: Dict, files_map: Dict, output_nwb_path: str) -> str
    def create_conversion_plan(self, dataset_analysis: Dict) -> ConversionPlan
    def adapt_plan_on_failure(self, failed_step: str, error: Exception) -> ConversionPlan
    def write_generated_script(self, code: str, out_path: str) -> str
    def run_generated_script(self, script_path: str) -> int

class MetadataQuestioner(BaseAgent):  # Already implemented
    def get_required_fields(self, kg_file: str, experiment_type: str) -> List[Tuple[str, str]]
    def generate_dynamic_question(self, field: str, constraints: Dict, inferred: Any = None) -> str

class MetaAgent:  # New meta-agent for coordination
    def monitor_agent_performance(self, agent_id: str, metrics: Dict) -> PerformanceReport
    def coordinate_workflow(self, agents: List[BaseAgent], workflow: Workflow) -> WorkflowResult
    def optimize_agent_interactions(self, interaction_history: List[Dict]) -> OptimizationPlan
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

#### DataLad Architecture Overview

DataLad serves two critical and complementary purposes in this project:

1. **Development Data Management**: Managing test datasets, evaluation data, and conversion examples for the development team
2. **Conversion Output Provenance**: Each conversion creates a DataLad repository tracking the iterative conversion process, decisions, and history for end users

This dual approach ensures both development efficiency and production transparency, with clear separation of concerns between development infrastructure and user-facing conversion outputs.

#### Architectural Separation

```
Development Infrastructure (Team-Facing):
agentic-neurodata-conversion/  # Main development DataLad dataset
├── data/                      # Development and testing datasets
├── etl/                       # ETL workflows and examples
└── results/                   # Development conversion outputs

User Conversion Outputs (User-Facing):
user-specified-output-dir/
└── conversion-{dataset-name}-{timestamp}/  # Individual conversion repositories
    ├── input_data/            # Links to original data
    ├── output.nwb            # Final NWB file
    ├── conversion_script.py   # Generated conversion script
    └── [evaluation outputs]   # Knowledge graphs, reports, etc.
```

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

#### Agent Performance and Learning Framework

#### Reflection and Learning Architecture

The system implements sophisticated reflection and learning capabilities that allow agents to improve over time:

**Core Components**:
- **Performance Monitoring**: Continuous tracking of agent success rates, error patterns, and efficiency metrics
- **Reflection Engine**: Agents analyze their own outputs and decision-making processes
- **Learning Integration**: Feedback loops that incorporate human corrections and domain expert input
- **Meta-Evaluation**: Higher-level assessment of agent coordination and workflow optimization

**Implementation**:
```python
# agentic_neurodata_conversion/agents/reflection.py
class ReflectionEngine:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.performance_history = []
        self.learning_database = LearningDatabase()
    
    def reflect_on_task(self, task: Task, result: TaskResult) -> ReflectionReport:
        """Analyze task performance and identify improvement opportunities"""
        reflection = {
            "task_complexity": self._assess_task_complexity(task),
            "result_quality": self._assess_result_quality(result),
            "decision_points": self._identify_decision_points(task, result),
            "improvement_areas": self._identify_improvements(task, result),
            "confidence_calibration": self._assess_confidence_accuracy(result)
        }
        
        self.performance_history.append(reflection)
        return ReflectionReport(reflection)
    
    def learn_from_human_feedback(self, feedback: HumanFeedback) -> None:
        """Incorporate human corrections and preferences"""
        learning_update = {
            "feedback_type": feedback.type,
            "correction": feedback.correction,
            "context": feedback.context,
            "confidence_adjustment": feedback.confidence_impact
        }
        
        self.learning_database.update(learning_update)
        self._adjust_decision_patterns(learning_update)
    
    def get_performance_trends(self) -> Dict[str, List[float]]:
        """Analyze performance trends over time"""
        return {
            "success_rate": self._calculate_success_trend(),
            "efficiency": self._calculate_efficiency_trend(),
            "confidence_calibration": self._calculate_calibration_trend()
        }

class MetaLearningCoordinator:
    """Coordinates learning across multiple agents"""
    
    def __init__(self):
        self.agent_performances = {}
        self.interaction_patterns = []
        self.workflow_optimizations = []
    
    def analyze_multi_agent_performance(self, workflow_result: WorkflowResult) -> MetaAnalysis:
        """Analyze how agents work together and identify optimization opportunities"""
        analysis = {
            "coordination_efficiency": self._assess_coordination(workflow_result),
            "bottlenecks": self._identify_bottlenecks(workflow_result),
            "redundancies": self._find_redundant_work(workflow_result),
            "optimization_opportunities": self._suggest_optimizations(workflow_result)
        }
        
        return MetaAnalysis(analysis)
    
    def optimize_agent_allocation(self, task_queue: List[Task]) -> AllocationPlan:
        """Optimize which agents handle which tasks based on performance history"""
        return self._create_optimal_allocation(task_queue, self.agent_performances)
```

#### Human-in-the-Loop Learning Integration

**Enhanced Human Feedback Loop**:
```python
class HumanFeedbackIntegrator:
    def __init__(self):
        self.feedback_patterns = FeedbackPatternAnalyzer()
        self.expert_preferences = ExpertPreferenceModel()
    
    def process_expert_correction(self, agent_output: Dict, expert_correction: Dict) -> LearningUpdate:
        """Process expert corrections and extract learning patterns"""
        correction_analysis = {
            "error_type": self._classify_error(agent_output, expert_correction),
            "context_factors": self._extract_context(agent_output),
            "correction_pattern": self._analyze_correction_pattern(expert_correction),
            "generalization_scope": self._assess_generalization(correction_analysis)
        }
        
        return LearningUpdate(correction_analysis)
    
    def suggest_proactive_questions(self, uncertain_decisions: List[Dict]) -> List[str]:
        """Generate targeted questions for human experts based on uncertainty"""
        questions = []
        for decision in uncertain_decisions:
            if decision['confidence'] < 0.7:  # Low confidence threshold
                question = self._generate_clarification_question(decision)
                questions.append(question)
        
        return questions
```

### Complete DataLad Integration Implementation

**Development Data Management Implementation**:

```python
# agentic_neurodata_conversion/interfaces/datalad_manager.py
import datalad.api as dl
from pathlib import Path
import logging
import shutil
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DevelopmentDataManager:
    """Manages development datasets, test data, and conversion examples"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.etl_dir = project_root / "etl"
        self.results_dir = project_root / "results"
        
    def initialize_development_infrastructure(self) -> None:
        """Initialize the complete development DataLad infrastructure"""
        
        # Ensure project is a DataLad dataset
        if not (self.project_root / ".datalad").exists():
            self._create_main_dataset()
        
        # Set up directory structure
        self._create_directory_structure()
        
        # Install conversion example subdatasets
        self._install_conversion_examples()
        
        # Set up evaluation datasets
        self._setup_evaluation_datasets()
        
        logger.info("Development DataLad infrastructure initialized")
    
    def _create_main_dataset(self) -> None:
        """Create main project DataLad dataset with proper configuration"""
        
        # Create .gitattributes FIRST (critical for proper annexing)
        gitattributes_content = """
# DataLad configuration for development project
* annex.backend=MD5E

# Never annex development files - keep in git
*.py annex.largefiles=nothing
*.md annex.largefiles=nothing
*.toml annex.largefiles=nothing
*.json annex.largefiles=nothing
*.yaml annex.largefiles=nothing
*.yml annex.largefiles=nothing
*.txt annex.largefiles=nothing
*.cfg annex.largefiles=nothing
*.ini annex.largefiles=nothing
.env* annex.largefiles=nothing
.git* annex.largefiles=nothing
Dockerfile* annex.largefiles=nothing
requirements*.txt annex.largefiles=nothing

# Only annex large data files (>10MB)
* annex.largefiles=(largerthan=10mb)

# Specific data file patterns that should always be annexed
*.nwb annex.largefiles=anything
*.dat annex.largefiles=anything
*.bin annex.largefiles=anything
*.h5 annex.largefiles=anything
*.hdf5 annex.largefiles=anything
"""
        (self.project_root / ".gitattributes").write_text(gitattributes_content)
        
        # Create dataset with text2git configuration
        dl.create(
            path=str(self.project_root),
            cfg_proc="text2git",
            description="Agentic neurodata conversion project - development infrastructure",
            force=True
        )
        
        # Initial commit of configuration
        dl.save(
            dataset=str(self.project_root),
            message="Initialize development DataLad infrastructure",
            path=[".gitattributes"]
        )
    
    def _create_directory_structure(self) -> None:
        """Create and document directory structure"""
        
        directories = {
            "data": "Test and evaluation datasets",
            "data/synthetic": "Synthetic messy datasets for testing",
            "data/evaluation": "Ground truth datasets for validation",
            "data/samples": "Small sample datasets for quick testing",
            "etl": "ETL workflows and data processing",
            "etl/input-data": "Conversion examples and reference implementations",
            "etl/evaluation-data": "Evaluation datasets and benchmarks",
            "results": "Development conversion outputs and experiments",
            "results/benchmarks": "Performance and quality benchmarks",
            "results/experiments": "Experimental conversion attempts"
        }
        
        for dir_path, description in directories.items():
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Create README for each directory
            readme_path = full_path / "README.md"
            if not readme_path.exists():
                readme_content = f"# {dir_path.replace('/', ' / ').title()}\n\n{description}\n"
                readme_path.write_text(readme_content)
        
        # Save directory structure
        dl.save(
            dataset=str(self.project_root),
            message="Create development directory structure",
            recursive=True
        )
    
    def _install_conversion_examples(self) -> None:
        """Install CatalystNeuro and other conversion repositories as subdatasets"""
        
        conversion_repos = [
            {
                "source": "https://github.com/catalystneuro/IBL-to-nwb",
                "path": "etl/input-data/catalystneuro/IBL-to-nwb",
                "description": "International Brain Laboratory conversion examples"
            },
            {
                "source": "https://github.com/catalystneuro/buzsaki-lab-to-nwb", 
                "path": "etl/input-data/catalystneuro/buzsaki-lab-to-nwb",
                "description": "Buzsaki Lab conversion examples"
            },
            {
                "source": "https://github.com/catalystneuro/allen-institute-to-nwb",
                "path": "etl/input-data/catalystneuro/allen-institute-to-nwb", 
                "description": "Allen Institute conversion examples"
            }
        ]
        
        installed_repos = []
        for repo in conversion_repos:
            try:
                logger.info(f"Installing conversion example: {repo['source']}")
                dl.install(
                    dataset=str(self.project_root),
                    path=repo["path"],
                    source=repo["source"],
                    description=repo["description"]
                )
                installed_repos.append(repo)
                logger.info(f"Successfully installed: {repo['path']}")
                
            except Exception as e:
                logger.warning(f"Failed to install {repo['source']}: {e}")
                # Continue with other repositories
        
        # Document installed repositories
        if installed_repos:
            repo_index = self.etl_dir / "input-data" / "installed_repositories.json"
            repo_index.write_text(json.dumps(installed_repos, indent=2))
            
            dl.save(
                dataset=str(self.project_root),
                message=f"Install {len(installed_repos)} conversion example repositories",
                path=["etl/input-data"]
            )
    
    def _setup_evaluation_datasets(self) -> None:
        """Set up evaluation datasets from documents/possible-datasets"""
        
        # Check if possible-datasets document exists
        possible_datasets_doc = self.project_root / "documents" / "possible-datasets.md"
        if not possible_datasets_doc.exists():
            logger.warning("documents/possible-datasets.md not found, skipping evaluation dataset setup")
            return
        
        # Create evaluation dataset registry
        eval_registry = {
            "description": "Evaluation datasets for testing conversion quality",
            "datasets": [],
            "setup_date": datetime.now().isoformat(),
            "source_document": "documents/possible-datasets.md"
        }
        
        # Save registry
        registry_path = self.data_dir / "evaluation" / "dataset_registry.json"
        registry_path.write_text(json.dumps(eval_registry, indent=2))
        
        # Create instructions for manual dataset addition
        instructions = """# Evaluation Dataset Setup

This directory contains datasets used for evaluating conversion quality.

## Adding Datasets

1. For public datasets, add as DataLad subdatasets:
   ```bash
   datalad install -d . -s <dataset_url> <local_path>
   ```

2. For private datasets, create symbolic links or copy data:
   ```bash
   ln -s /path/to/dataset ./private_dataset_name
   datalad save -m "Add private dataset link"
   ```

3. Update dataset_registry.json with dataset information

## Dataset Requirements

- Each dataset should have clear provenance information
- Include expected conversion outputs for validation
- Document any special handling requirements
- Provide metadata about experimental setup

See documents/possible-datasets.md for candidate datasets.
"""
        
        instructions_path = self.data_dir / "evaluation" / "SETUP_INSTRUCTIONS.md"
        instructions_path.write_text(instructions)
        
        dl.save(
            dataset=str(self.project_root),
            message="Set up evaluation dataset infrastructure",
            path=["data/evaluation"]
        )
    
    def add_test_dataset(self, dataset_path: Path, name: str, description: str) -> None:
        """Add a test dataset to the development infrastructure"""
        
        target_path = self.data_dir / "samples" / name
        
        if dataset_path.is_dir():
            # For directories, create as subdataset if it's a DataLad dataset
            if (dataset_path / ".datalad").exists():
                dl.install(
                    dataset=str(self.project_root),
                    path=str(target_path),
                    source=str(dataset_path),
                    description=description
                )
            else:
                # Copy directory
                shutil.copytree(dataset_path, target_path)
        else:
            # For files, copy directly
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dataset_path, target_path)
        
        # Save addition
        dl.save(
            dataset=str(self.project_root),
            message=f"Add test dataset: {name}",
            path=[str(target_path)]
        )
        
        logger.info(f"Added test dataset: {name} at {target_path}")
    
    def get_available_datasets(self) -> Dict[str, List[Path]]:
        """Get list of available datasets for testing"""
        
        datasets = {
            "synthetic": list((self.data_dir / "synthetic").glob("*")) if (self.data_dir / "synthetic").exists() else [],
            "evaluation": list((self.data_dir / "evaluation").glob("*")) if (self.data_dir / "evaluation").exists() else [],
            "samples": list((self.data_dir / "samples").glob("*")) if (self.data_dir / "samples").exists() else [],
            "conversion_examples": []
        }
        
        # Get conversion examples from subdatasets
        try:
            subdatasets = dl.subdatasets(dataset=str(self.project_root), return_type='list')
            for subds in subdatasets:
                if "etl/input-data" in subds.get('path', ''):
                    datasets["conversion_examples"].append(Path(subds['path']))
        except Exception as e:
            logger.warning(f"Failed to get subdatasets: {e}")
        
        return datasets
    
    def ensure_dataset_available(self, dataset_path: Path) -> bool:
        """Ensure a dataset is available for use (install/get if needed)"""
        
        if not dataset_path.exists():
            # Try to install if it's a known subdataset
            try:
                dl.install(dataset=str(self.project_root), path=str(dataset_path))
                return True
            except Exception:
                logger.error(f"Failed to install dataset: {dataset_path}")
                return False
        
        # If it exists but files might be in annex, try to get them
        try:
            dl.get(path=str(dataset_path), dataset=str(self.project_root))
            return True
        except Exception as e:
            logger.warning(f"Failed to get dataset files: {e}")
            # Dataset exists but some files might not be available
            return dataset_path.exists()
```

**User Conversion Provenance Implementation**:

```python
# agentic_neurodata_conversion/interfaces/conversion_provenance.py
class UserConversionProvenanceManager:
    """Manages provenance tracking for individual user conversions"""
    
    def __init__(self, output_base_dir: Path):
        self.output_base_dir = output_base_dir
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_conversion_repository(self, input_dataset: Path, dataset_name: str, 
                                   user_metadata: Optional[Dict] = None) -> Path:
        """Create a new DataLad repository for tracking this specific conversion"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_name = f"conversion-{dataset_name}-{timestamp}"
        repo_path = self.output_base_dir / repo_name
        
        # Create DataLad dataset for this conversion
        dl.create(
            path=str(repo_path),
            description=f"Agentic conversion of {dataset_name} dataset",
            cfg_proc="text2git"  # Keep small files in git, large files in annex
        )
        
        # Set up .gitattributes for conversion outputs
        gitattributes_content = """
# Conversion output configuration
* annex.backend=MD5E

# Keep conversion metadata and scripts in git
*.py annex.largefiles=nothing
*.json annex.largefiles=nothing
*.jsonl annex.largefiles=nothing
*.txt annex.largefiles=nothing
*.md annex.largefiles=nothing
*.ttl annex.largefiles=nothing
*.nt annex.largefiles=nothing
*.jsonld annex.largefiles=nothing
*.html annex.largefiles=nothing

# Annex large data files
*.nwb annex.largefiles=anything
*.dat annex.largefiles=anything
*.bin annex.largefiles=anything
"""
        (repo_path / ".gitattributes").write_text(gitattributes_content)
        
        # Create initial README with conversion information
        readme_content = f"""# Conversion of {dataset_name}

**Conversion Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Input Dataset:** {input_dataset}
**Conversion Repository:** {repo_name}

## Contents

- `input_data/` - Links to original input data
- `output.nwb` - Final NWB output file
- `conversion_script.py` - Generated conversion script
- `validation_report.json` - NWB validation results
- `agent_log.jsonl` - Complete agent interaction log
- Knowledge graph outputs:
  - `{dataset_name}.data.ttl` - RDF in Turtle format
  - `{dataset_name}.data.nt` - RDF in N-Triples format
  - `{dataset_name}.data.jsonld` - RDF in JSON-LD format
  - `{dataset_name}.data.triples.txt` - Human-readable triples
  - `{dataset_name}.data.html` - Interactive visualization
- Quality reports:
  - `{dataset_name}_context.txt` - Human-readable context
  - `{dataset_name}_quality_report.txt` - Quality assessment

## Provenance

This repository tracks the complete conversion process using DataLad's
built-in version control. Each save operation creates a commit with
full provenance information.

Use `git log` to see the conversion history.
Use `datalad diff` to see changes between versions.
"""
        (repo_path / "README.md").write_text(readme_content)
        
        # Link to input data (DataLad handles this efficiently)
        if input_dataset.exists():
            if input_dataset.is_dir():
                # For directories, create subdataset or symlink
                try:
                    if (input_dataset / ".datalad").exists():
                        # Input is a DataLad dataset - install as subdataset
                        dl.install(
                            dataset=str(repo_path),
                            path="input_data",
                            source=str(input_dataset)
                        )
                    else:
                        # Regular directory - create symlink
                        (repo_path / "input_data").symlink_to(input_dataset.resolve())
                except Exception as e:
                    logger.warning(f"Failed to link input data: {e}")
                    # Fallback: copy small files, link large ones
                    self._smart_copy_input_data(input_dataset, repo_path / "input_data")
            else:
                # Single file - create symlink
                (repo_path / "input_data").symlink_to(input_dataset.resolve())
        
        # Save initial state
        dl.save(
            dataset=str(repo_path),
            message=f"Initialize conversion repository for {dataset_name}",
            recursive=True
        )
        
        logger.info(f"Created conversion repository: {repo_path}")
        return repo_path
    
    def _smart_copy_input_data(self, source: Path, target: Path) -> None:
        """Smart copy that links large files and copies small ones"""
        target.mkdir(parents=True, exist_ok=True)
        
        for item in source.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(source)
                target_file = target / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Link large files (>10MB), copy small ones
                if item.stat().st_size > 10 * 1024 * 1024:
                    target_file.symlink_to(item.resolve())
                else:
                    shutil.copy2(item, target_file)
    
    def save_conversion_iteration(self, repo_path: Path, 
                                conversion_outputs: Dict[str, Any],
                                agent_interactions: List[Dict],
                                iteration_message: str) -> str:
        """Save a conversion iteration with full provenance tracking"""
        
        # Update conversion outputs
        self._update_conversion_files(repo_path, conversion_outputs)
        
        # Append agent interactions to log
        self._append_agent_log(repo_path, agent_interactions)
        
        # Update conversion metadata
        self._update_conversion_metadata(repo_path, conversion_outputs)
        
        # DataLad save - this creates automatic provenance
        result = dl.save(
            dataset=str(repo_path),
            message=iteration_message,
            recursive=True,
            return_type='item-or-list'
        )
        
        # Extract commit hash for reference
        commit_hash = result.get('commit', 'unknown') if isinstance(result, dict) else 'unknown'
        
        logger.info(f"Saved conversion iteration: {iteration_message} (commit: {commit_hash})")
        return commit_hash
    
    def _update_conversion_files(self, repo_path: Path, outputs: Dict[str, Any]) -> None:
        """Update all conversion output files"""
        
        # Copy NWB output if provided
        if 'nwb_file' in outputs and outputs['nwb_file']:
            nwb_source = Path(outputs['nwb_file'])
            if nwb_source.exists():
                shutil.copy2(nwb_source, repo_path / "output.nwb")
        
        # Save conversion script
        if 'conversion_script' in outputs:
            (repo_path / "conversion_script.py").write_text(outputs['conversion_script'])
        
        # Save validation results
        if 'validation_results' in outputs:
            with open(repo_path / "validation_report.json", 'w') as f:
                json.dump(outputs['validation_results'], f, indent=2, default=str)
        
        # Copy knowledge graph files (generated by EvaluationAgent)
        if 'knowledge_graph_files' in outputs:
            for kg_file in outputs['knowledge_graph_files']:
                source_path = Path(kg_file)
                if source_path.exists():
                    shutil.copy2(source_path, repo_path / source_path.name)
        
        # Copy quality reports
        if 'quality_reports' in outputs:
            for report_file in outputs['quality_reports']:
                source_path = Path(report_file)
                if source_path.exists():
                    shutil.copy2(source_path, repo_path / source_path.name)
    
    def _append_agent_log(self, repo_path: Path, interactions: List[Dict]) -> None:
        """Append agent interactions to the log file"""
        log_file = repo_path / "agent_log.jsonl"
        
        with open(log_file, 'a') as f:
            for interaction in interactions:
                # Add timestamp if not present
                if 'timestamp' not in interaction:
                    interaction['timestamp'] = datetime.now().isoformat()
                f.write(json.dumps(interaction, default=str) + '\n')
    
    def _update_conversion_metadata(self, repo_path: Path, outputs: Dict[str, Any]) -> None:
        """Update conversion metadata file"""
        metadata_file = repo_path / "conversion_metadata.json"
        
        # Load existing metadata or create new
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "conversion_id": repo_path.name,
                "created": datetime.now().isoformat(),
                "iterations": []
            }
        
        # Add current iteration
        iteration_data = {
            "timestamp": datetime.now().isoformat(),
            "outputs": {k: str(v) if not isinstance(v, (dict, list)) else v 
                       for k, v in outputs.items()},
            "status": outputs.get('status', 'in_progress')
        }
        metadata["iterations"].append(iteration_data)
        metadata["last_updated"] = datetime.now().isoformat()
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def get_conversion_history(self, repo_path: Path) -> List[Dict[str, Any]]:
        """Get complete conversion history from DataLad/git log"""
        try:
            import subprocess
            
            # Get git log with detailed information
            result = subprocess.run([
                "git", "log", 
                "--pretty=format:%H|%ai|%s|%an|%ae",
                "--all"
            ], cwd=repo_path, capture_output=True, text=True)
            
            history = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        history.append({
                            "commit_hash": parts[0],
                            "timestamp": parts[1] if len(parts) > 1 else None,
                            "message": parts[2] if len(parts) > 2 else None,
                            "author_name": parts[3] if len(parts) > 3 else None,
                            "author_email": parts[4] if len(parts) > 4 else None
                        })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get conversion history: {e}")
            return []
    
    def tag_successful_conversion(self, repo_path: Path, version: str = None) -> None:
        """Tag a successful conversion for easy reference"""
        
        if version is None:
            version = f"success-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            dl.save(
                dataset=str(repo_path),
                message=f"Mark successful conversion - {version}",
                version_tag=version
            )
            logger.info(f"Tagged successful conversion: {version}")
            
        except Exception as e:
            logger.error(f"Failed to tag conversion: {e}")
    
    def export_conversion_summary(self, repo_path: Path) -> Dict[str, Any]:
        """Export a comprehensive summary of the conversion"""
        
        summary = {
            "repository": str(repo_path),
            "conversion_id": repo_path.name,
            "created": None,
            "status": "unknown",
            "history": self.get_conversion_history(repo_path),
            "files": [],
            "metadata": {}
        }
        
        # Load conversion metadata if available
        metadata_file = repo_path / "conversion_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                summary["metadata"] = json.load(f)
                summary["created"] = summary["metadata"].get("created")
                if summary["metadata"].get("iterations"):
                    last_iteration = summary["metadata"]["iterations"][-1]
                    summary["status"] = last_iteration.get("status", "unknown")
        
        # List all files in repository
        for item in repo_path.rglob("*"):
            if item.is_file() and not item.name.startswith('.'):
                summary["files"].append({
                    "path": str(item.relative_to(repo_path)),
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
        
        return summary
```

### Knowledge Graph and LinkML Schema Integration

#### Knowledge Graph Architecture

The knowledge graph system provides semantic representation of NWB data through RDF triples, enabling rich querying and metadata enrichment. The implementation is based on the existing `evaluation_agent_final.py` and LinkML tools.

#### Core Knowledge Graph Components

**KnowledgeGraphBuilder** (based on `evaluation_agent_final.py`):

```python
# agentic_neurodata_conversion/interfaces/knowledge_graph.py
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD
import h5py
import re

logger = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    """Builds RDF knowledge graphs from NWB files"""
    
    def __init__(self, base_uri: Optional[str] = None):
        self.base_uri = base_uri
    
    def build_instance_graph(self, nwb_path: Path, 
                           include_data: str = "stats",
                           sample_limit: int = 200,
                           max_bytes: int = 50_000_000,
                           stats_inline_limit: int = 500) -> Graph:
        """
        Build RDF graph representing NWB file structure and data
        
        Args:
            nwb_path: Path to NWB file
            include_data: Data inclusion policy ("none", "stats", "sample", "full")
            sample_limit: Maximum elements per dataset when sampling
            max_bytes: Hard cap on bytes per dataset values
            stats_inline_limit: Inline limit for 1D arrays in stats mode
            
        Returns:
            RDF Graph with NWB instance data
        """
        if not nwb_path.exists():
            raise FileNotFoundError(f"NWB file not found: {nwb_path}")
        
        g = Graph()
        base_uri = self.base_uri or f"http://example.org/{self._sanitize(nwb_path.stem)}#"
        BASE = Namespace(base_uri)
        EX = BASE
        
        # Define predicates
        Group = EX.Group
        Dataset = EX.Dataset
        hasChild = EX.hasChild
        hasValue = EX.hasValue
        hasDType = EX.hasDType
        hasShape = EX.hasShape
        hasChunks = EX.hasChunks
        hasCompression = EX.hasCompression
        
        with h5py.File(str(nwb_path), "r") as f:
            # Add root group
            root_subj = self._path_to_uri(BASE, "/")
            g.add((root_subj, RDF.type, Group))
            
            # Add root attributes
            self._add_attributes(g, root_subj, f.attrs, EX)
            
            # Visit all objects in file
            def visit(name, obj):
                subj = self._path_to_uri(BASE, name)
                
                if isinstance(obj, h5py.Group):
                    self._process_group(g, subj, obj, EX)
                else:
                    self._process_dataset(g, subj, obj, EX, include_data, 
                                        sample_limit, max_bytes, stats_inline_limit)
            
            f.visititems(visit)
            
            # Add parent-child relationships
            self._add_hierarchy(g, f, BASE, EX)
        
        return g
    
    def _sanitize(self, name: str) -> str:
        """Sanitize names for URI fragments"""
        return re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    
    def _path_to_uri(self, base: Namespace, h5_path: str) -> URIRef:
        """Convert HDF5 path to URI"""
        if not h5_path or h5_path == "/":
            return URIRef(str(base) + "root")
        frag = self._sanitize(h5_path.strip("/")) or "root"
        return URIRef(str(base) + frag)
    
    def _make_literal(self, value) -> Optional[Literal]:
        """Convert Python value to RDF literal"""
        try:
            import numpy as np
            if isinstance(value, (bytes, bytearray)):
                try:
                    return Literal(value.decode("utf-8"))
                except Exception:
                    return Literal(str(value))
            if isinstance(value, np.generic):
                return Literal(value.item())
            if isinstance(value, (str, int, float, bool)):
                return Literal(value)
            if isinstance(value, (list, tuple)) and len(value) > 0:
                if isinstance(value[0], (str, int, float, bool)):
                    return Literal(str(list(value)))
            s = str(value)
            if len(s) > 0:
                return Literal(s)
        except Exception:
            return None
        return None
    
    def _add_attributes(self, g: Graph, subj: URIRef, attrs, EX: Namespace):
        """Add HDF5 attributes as RDF properties"""
        try:
            for ak, av in attrs.items():
                pred = URIRef(str(EX) + f"attr_{self._sanitize(str(ak))}")
                lit = self._make_literal(av)
                if lit is not None:
                    g.add((subj, pred, lit))
        except Exception as e:
            logger.warning(f"Failed to add attributes for {subj}: {e}")
    
    def _process_group(self, g: Graph, subj: URIRef, group: h5py.Group, EX: Namespace):
        """Process HDF5 group"""
        g.add((subj, RDF.type, EX.Group))
        self._add_attributes(g, subj, group.attrs, EX)
    
    def _process_dataset(self, g: Graph, subj: URIRef, dataset: h5py.Dataset, 
                        EX: Namespace, include_data: str, sample_limit: int,
                        max_bytes: int, stats_inline_limit: int):
        """Process HDF5 dataset"""
        g.add((subj, RDF.type, EX.Dataset))
        
        # Add dataset metadata
        try:
            g.add((subj, EX.hasDType, Literal(str(dataset.dtype))))
            g.add((subj, EX.hasShape, Literal(str(tuple(dataset.shape)))))
            
            if dataset.chunks is not None:
                g.add((subj, EX.hasChunks, Literal(str(dataset.chunks))))
            if dataset.compression is not None:
                g.add((subj, EX.hasCompression, Literal(str(dataset.compression))))
        except Exception as e:
            logger.warning(f"Failed to add dataset metadata for {subj}: {e}")
        
        # Add attributes
        self._add_attributes(g, subj, dataset.attrs, EX)
        
        # Add data based on inclusion policy
        if include_data == "stats":
            self._add_stats(g, subj, dataset, EX, stats_inline_limit)
        elif include_data == "sample":
            self._add_sample_data(g, subj, dataset, EX, sample_limit, max_bytes)
        elif include_data == "full":
            self._add_full_data(g, subj, dataset, EX, max_bytes)
    
    def _add_stats(self, g: Graph, subj: URIRef, dataset: h5py.Dataset, 
                  EX: Namespace, stats_inline_limit: int):
        """Add statistical summary of dataset"""
        try:
            import numpy as np
            data = dataset[()]
            if data is None:
                return
            
            arr = np.array(data)
            
            # Always include size
            g.add((subj, EX.stat_size, Literal(int(arr.size))))
            
            # Numeric statistics
            if np.issubdtype(arr.dtype, np.number):
                g.add((subj, EX.stat_min, Literal(float(np.nanmin(arr)))))
                g.add((subj, EX.stat_max, Literal(float(np.nanmax(arr)))))
                g.add((subj, EX.stat_mean, Literal(float(np.nanmean(arr)))))
                g.add((subj, EX.stat_std, Literal(float(np.nanstd(arr)))))
            
            # Inline small arrays
            if arr.ndim == 0:  # Scalar
                lit = self._make_literal(data)
                if lit is not None:
                    g.add((subj, EX.hasValue, lit))
            elif arr.ndim == 1 and arr.size <= stats_inline_limit:
                for v in arr.tolist()[:stats_inline_limit]:
                    lit = self._make_literal(v)
                    if lit is not None:
                        g.add((subj, EX.hasValue, lit))
                        
        except Exception as e:
            logger.warning(f"Failed to add stats for {subj}: {e}")
    
    def _add_sample_data(self, g: Graph, subj: URIRef, dataset: h5py.Dataset,
                        EX: Namespace, sample_limit: int, max_bytes: int):
        """Add sampled data values"""
        try:
            data = dataset[()]
            if data is None:
                return
            
            import numpy as np
            flat = np.ravel(data)
            values = flat[:sample_limit] if sample_limit else flat
            
            total_bytes = 0
            for v in values:
                lit = self._make_literal(v)
                if lit is not None:
                    g.add((subj, EX.hasValue, lit))
                    total_bytes += len(str(lit))
                    if max_bytes > 0 and total_bytes >= max_bytes:
                        break
                        
        except Exception as e:
            logger.warning(f"Failed to add sample data for {subj}: {e}")
    
    def _add_full_data(self, g: Graph, subj: URIRef, dataset: h5py.Dataset,
                      EX: Namespace, max_bytes: int):
        """Add full data values (with size limit)"""
        try:
            data = dataset[()]
            if data is None:
                return
            
            import numpy as np
            
            # Check size limit
            if max_bytes > 0:
                estimated_bytes = getattr(data, "nbytes", 0)
                if estimated_bytes > max_bytes:
                    logger.warning(f"Dataset {subj} too large ({estimated_bytes} bytes), skipping full data")
                    return
            
            flat = np.ravel(data)
            total_bytes = 0
            
            for v in flat:
                lit = self._make_literal(v)
                if lit is not None:
                    g.add((subj, EX.hasValue, lit))
                    total_bytes += len(str(lit))
                    if max_bytes > 0 and total_bytes >= max_bytes:
                        break
                        
        except Exception as e:
            logger.warning(f"Failed to add full data for {subj}: {e}")
    
    def _add_hierarchy(self, g: Graph, f: h5py.File, BASE: Namespace, EX: Namespace):
        """Add parent-child relationships"""
        def visit_children(name, obj):
            parent = self._path_to_uri(BASE, name)
            if isinstance(obj, (h5py.Group, h5py.File)):
                for child_name in obj.keys():
                    child_path = name.rstrip("/") + "/" + child_name if name != "/" else "/" + child_name
                    child_uri = self._path_to_uri(BASE, child_path)
                    g.add((parent, EX.hasChild, child_uri))
        
        # Add root children
        visit_children("/", f)
        f.visititems(visit_children)

class KnowledgeGraphExporter:
    """Exports knowledge graphs to multiple formats"""
    
    def __init__(self, kg_builder: KnowledgeGraphBuilder):
        self.kg_builder = kg_builder
    
    def export_all_formats(self, nwb_path: Path, output_dir: Path,
                          include_data: str = "stats") -> Dict[str, Path]:
        """
        Export knowledge graph to all supported formats
        
        Returns:
            Dictionary mapping format names to output file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build the graph
        graph = self.kg_builder.build_instance_graph(nwb_path, include_data=include_data)
        
        stem = nwb_path.stem
        outputs = {}
        
        # TTL (Turtle)
        ttl_path = output_dir / f"{stem}.data.ttl"
        graph.serialize(destination=str(ttl_path), format="turtle")
        outputs["ttl"] = ttl_path
        
        # N-Triples
        nt_path = output_dir / f"{stem}.data.nt"
        graph.serialize(destination=str(nt_path), format="nt")
        outputs["nt"] = nt_path
        
        # JSON-LD
        jsonld_path = output_dir / f"{stem}.data.jsonld"
        graph.serialize(destination=str(jsonld_path), format="json-ld", indent=2)
        outputs["jsonld"] = jsonld_path
        
        # Human-readable triples
        triples_path = output_dir / f"{stem}.data.triples.txt"
        self._export_human_readable_triples(graph, triples_path)
        outputs["triples"] = triples_path
        
        # HTML visualization (if pyvis available)
        try:
            html_path = self._generate_html_visualization(graph, output_dir / f"{stem}.data.html")
            if html_path:
                outputs["html"] = html_path
        except ImportError:
            logger.info("pyvis not available, skipping HTML visualization")
        
        return outputs
    
    def _export_human_readable_triples(self, graph: Graph, output_path: Path):
        """Export human-readable triples with labels"""
        from rdflib.namespace import RDFS
        
        def get_label(node):
            if isinstance(node, URIRef):
                # Try to get RDFS label
                for o in graph.objects(node, RDFS.label):
                    return str(o)
                # Fall back to fragment or last path component
                s = str(node)
                if "#" in s:
                    return s.rsplit("#", 1)[-1]
                if "/" in s:
                    return s.rstrip("/").rsplit("/", 1)[-1]
                return s
            return str(node)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for s, p, o in graph:
                f.write(f"{get_label(s)}\t{get_label(p)}\t{get_label(o)}\n")
    
    def _generate_html_visualization(self, graph: Graph, output_path: Path,
                                   max_triples: int = 12000) -> Optional[Path]:
        """Generate interactive HTML visualization using pyvis"""
        try:
            from pyvis.network import Network
        except ImportError:
            return None
        
        # Build network from graph
        edges = []
        nodes = set()
        
        for s, p, o in graph:
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                ss, oo, pp = str(s), str(o), str(p)
                edges.append((ss, oo, pp))
                nodes.add(ss)
                nodes.add(oo)
                if len(edges) >= max_triples:
                    break
        
        # Create pyvis network
        net = Network(height="900px", width="100%", notebook=False)
        
        # Add nodes with labels
        for n in nodes:
            label = n.rsplit("#", 1)[-1] if "#" in n else n.rsplit("/", 1)[-1] if "/" in n else n
            net.add_node(n, label=label, title=n)
        
        # Add edges
        for s, o, p in edges:
            net.add_edge(s, o, title=p)
        
        # Save HTML
        net.save_graph(str(output_path))
        return output_path
```

#### LinkML Schema Management

**LinkMLSchemaManager** (based on `nwb_to_linkml.py`):

```python
# agentic_neurodata_conversion/interfaces/linkml_schema.py
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
import logging
import yaml
import h5py
import tempfile
import subprocess
from linkml_runtime.dumpers import yaml_dumper

logger = logging.getLogger(__name__)

class LinkMLSchemaManager:
    """Manages LinkML schema generation and validation for NWB files"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.cwd() / ".nwb_linkml_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def detect_namespaces(self, nwb_path: Path) -> Set[str]:
        """
        Detect all namespaces used in an NWB file
        
        Args:
            nwb_path: Path to NWB file
            
        Returns:
            Set of namespace names found in the file
        """
        namespaces = set()
        
        try:
            with h5py.File(str(nwb_path), 'r') as f:
                def visit(name, obj):
                    if hasattr(obj, 'attrs'):
                        for key, val in obj.attrs.items():
                            if key == 'namespace':
                                try:
                                    if isinstance(val, bytes):
                                        namespaces.add(val.decode('utf-8'))
                                    elif isinstance(val, str):
                                        namespaces.add(val)
                                    elif isinstance(val, (list, tuple)):
                                        for v in val:
                                            if isinstance(v, bytes):
                                                namespaces.add(v.decode('utf-8'))
                                            elif isinstance(v, str):
                                                namespaces.add(v)
                                except Exception:
                                    pass
                
                f.visititems(visit)
        except Exception as e:
            logger.error(f"Failed to detect namespaces in {nwb_path}: {e}")
        
        return namespaces
    
    def generate_schema(self, nwb_path: Path, 
                       output_path: Optional[Path] = None,
                       split_schema: bool = True,
                       auto_fetch_extensions: bool = True,
                       offline: bool = False) -> Path:
        """
        Generate LinkML schema for an NWB file
        
        Args:
            nwb_path: Path to NWB file
            output_path: Output path (file for monolithic, dir for split)
            split_schema: Whether to generate split schema files
            auto_fetch_extensions: Whether to auto-fetch extension schemas
            offline: Whether to work offline only
            
        Returns:
            Path to generated schema (file or directory)
        """
        if not nwb_path.exists():
            raise FileNotFoundError(f"NWB file not found: {nwb_path}")
        
        # Determine output path
        if output_path is None:
            if split_schema:
                output_path = nwb_path.with_suffix("").with_suffix(".linkml")
            else:
                output_path = nwb_path.with_suffix("").with_suffix(".linkml.yaml")
        
        # Detect namespaces in the file
        detected_namespaces = self.detect_namespaces(nwb_path)
        logger.info(f"Detected namespaces: {detected_namespaces}")
        
        # Resolve extension namespace files
        extension_files = []
        if not offline and auto_fetch_extensions:
            extension_files = self._resolve_extension_namespaces(detected_namespaces)
        
        # Generate schema using nwb-linkml
        try:
            result = self._build_linkml_schema(extension_files)
            
            if split_schema:
                output_path.mkdir(parents=True, exist_ok=True)
                self._write_split_schema(result.schemas, output_path)
            else:
                self._write_monolithic_schema(result.schemas, output_path)
            
            logger.info(f"Generated LinkML schema: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate LinkML schema: {e}")
            raise
    
    def validate_against_schema(self, nwb_path: Path, schema_path: Path) -> Dict[str, Any]:
        """
        Validate NWB file against LinkML schema
        
        Args:
            nwb_path: Path to NWB file
            schema_path: Path to LinkML schema
            
        Returns:
            Validation results dictionary
        """
        # This would integrate with LinkML validation tools
        # For now, return a placeholder structure
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "schema_path": str(schema_path),
            "nwb_path": str(nwb_path)
        }
    
    def _resolve_extension_namespaces(self, namespaces: Set[str]) -> List[Path]:
        """Resolve extension namespace YAML files"""
        extension_files = []
        
        for ns in namespaces:
            if ns in {'core', 'hdmf-common'}:
                continue
            
            # Check cache first
            cached_file = self._find_namespace_in_cache(ns)
            if cached_file:
                extension_files.append(cached_file)
                continue
            
            # Try to fetch from GitHub
            try:
                fetched_file = self._fetch_extension_namespace(ns)
                if fetched_file:
                    extension_files.append(fetched_file)
            except Exception as e:
                logger.warning(f"Failed to fetch extension {ns}: {e}")
        
        return extension_files
    
    def _find_namespace_in_cache(self, namespace: str) -> Optional[Path]:
        """Find namespace YAML in cache directory"""
        for yaml_file in self.cache_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict) and 'namespaces' in data:
                    for ns in data.get('namespaces', []):
                        if isinstance(ns, dict) and ns.get('name') == namespace:
                            return yaml_file
            except Exception:
                continue
        return None
    
    def _fetch_extension_namespace(self, namespace: str) -> Optional[Path]:
        """Fetch extension namespace from GitHub"""
        repo_url = f"https://github.com/nwb-extensions/{namespace}.git"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Clone repository
                subprocess.run([
                    'git', 'clone', '--depth', '1', repo_url, 
                    str(Path(temp_dir) / namespace)
                ], check=True, capture_output=True)
                
                # Find namespace YAML
                repo_path = Path(temp_dir) / namespace
                yaml_file = self._find_namespace_yaml_in_dir(repo_path, namespace)
                
                if yaml_file:
                    # Cache the file
                    cache_ns_dir = self.cache_dir / namespace
                    cache_ns_dir.mkdir(parents=True, exist_ok=True)
                    cached_file = cache_ns_dir / yaml_file.name
                    
                    import shutil
                    shutil.copy2(yaml_file, cached_file)
                    return cached_file
                    
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to clone {repo_url}: {e}")
        
        return None
    
    def _find_namespace_yaml_in_dir(self, directory: Path, namespace: str) -> Optional[Path]:
        """Find YAML file defining the given namespace in directory"""
        for yaml_file in directory.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict) and 'namespaces' in data:
                    for ns in data.get('namespaces', []):
                        if isinstance(ns, dict) and ns.get('name') == namespace:
                            return yaml_file
            except Exception:
                continue
        return None
    
    def _build_linkml_schema(self, extension_files: List[Path]):
        """Build LinkML schema using nwb-linkml"""
        # This would use the nwb-linkml library
        # For now, return a mock result structure
        class MockResult:
            def __init__(self):
                self.schemas = []
        
        return MockResult()
    
    def _write_split_schema(self, schemas: List, output_dir: Path):
        """Write split schema files"""
        output_dir.mkdir(parents=True, exist_ok=True)
        for schema in schemas:
            schema_file = output_dir / f"{schema.name}.yaml"
            yaml_dumper.dump(schema, str(schema_file))
    
    def _write_monolithic_schema(self, schemas: List, output_file: Path):
        """Write monolithic schema file"""
        # Combine all schemas into one
        # Implementation would merge schemas appropriately
        combined_schema = {"name": output_file.stem, "schemas": schemas}
        with open(output_file, 'w') as f:
            yaml.dump(combined_schema, f)

class OntologyManager:
    """Manages NWB and domain ontologies for knowledge graph enrichment"""
    
    def __init__(self, ontology_cache_dir: Optional[Path] = None):
        self.cache_dir = ontology_cache_dir or Path.cwd() / ".ontology_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_nwb_ontology(self) -> Graph:
        """Load NWB core ontology"""
        # This would load the official NWB ontology
        # For now, return empty graph
        return Graph()
    
    def enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich metadata using ontological knowledge
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Enriched metadata with additional semantic information
        """
        enriched = metadata.copy()
        
        # Example enrichments:
        # - Species name -> taxonomy URI
        # - Device name -> device ontology URI
        # - Protocol -> protocol ontology URI
        
        if 'species' in metadata:
            enriched['species_uri'] = self._resolve_species_uri(metadata['species'])
        
        if 'device' in metadata:
            enriched['device_uri'] = self._resolve_device_uri(metadata['device'])
        
        return enriched
    
    def _resolve_species_uri(self, species_name: str) -> Optional[str]:
        """Resolve species name to taxonomy URI"""
        # This would use NCBI taxonomy or similar
        species_mappings = {
            'mouse': 'http://purl.obolibrary.org/obo/NCBITaxon_10090',
            'rat': 'http://purl.obolibrary.org/obo/NCBITaxon_10116',
            'human': 'http://purl.obolibrary.org/obo/NCBITaxon_9606'
        }
        return species_mappings.get(species_name.lower())
    
    def _resolve_device_uri(self, device_name: str) -> Optional[str]:
        """Resolve device name to device ontology URI"""
        # This would use device ontologies
        return None

class SPARQLInterface:
    """Provides SPARQL query capabilities for knowledge graphs"""
    
    def __init__(self, graph: Graph):
        self.graph = graph
    
    def query(self, sparql_query: str) -> List[Dict[str, Any]]:
        """
        Execute SPARQL query against the knowledge graph
        
        Args:
            sparql_query: SPARQL query string
            
        Returns:
            Query results as list of dictionaries
        """
        try:
            results = self.graph.query(sparql_query)
            return [dict(row.asdict()) for row in results]
        except Exception as e:
            logger.error(f"SPARQL query failed: {e}")
            return []
    
    def get_dataset_summary(self) -> Dict[str, Any]:
        """Get high-level summary of the dataset"""
        query = """
        PREFIX ex: <http://example.org/>
        SELECT ?dataset ?dtype ?shape WHERE {
            ?dataset a ex:Dataset .
            ?dataset ex:hasDType ?dtype .
            ?dataset ex:hasShape ?shape .
        }
        """
        results = self.query(query)
        return {"datasets": results}
    
    def find_timeseries_data(self) -> List[Dict[str, Any]]:
        """Find all timeseries datasets"""
        query = """
        PREFIX ex: <http://example.org/>
        SELECT ?dataset ?shape WHERE {
            ?dataset a ex:Dataset .
            ?dataset ex:hasShape ?shape .
            FILTER(CONTAINS(?shape, ","))
        }
        """
        return self.query(query)
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
- `KnowledgeGraphBuilder`: Creates RDF representations from NWB files
- `LinkMLSchemaManager`: Manages LinkML schema generation and validation
- `OntologyManager`: Manages NWB and domain ontologies
- `SPARQLInterface`: Provides query capabilities for knowledge graphs

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
    """Main settings container with nested configuration
    
    Agent-Specific LLM Configuration Rationale:
    
    Each agent has different performance requirements and cost sensitivities:
    
    - ConversationAgent: Needs strong reasoning for metadata extraction and user interaction.
      High accuracy is critical for understanding experimental context.
      Cost: Medium (frequent use, but shorter interactions)
      
    - ConversionAgent: Requires excellent code generation capabilities for NeuroConv scripts.
      Accuracy is critical as errors break the conversion pipeline.
      Cost: High (complex code generation, longer contexts)
      
    - EvaluationAgent: Performs validation and quality assessment tasks.
      Can use smaller/cheaper models as tasks are more structured.
      Cost: Low (structured validation tasks, can use local models)
      
    This flexibility allows optimization for both performance and cost across different
    deployment scenarios (development, CI, production).
    """
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
        agents_to_check = ['conversation_agent', 'conversion_agent', 'evaluation_agent']
        
        for agent_name in agents_to_check:
            agent_config = info.data.get(agent_name, {})
            if isinstance(agent_config, dict) and agent_config.get('llm_provider') == 'openrouter':
                if not v:
                    raise ValueError(f"OpenRouter API key required when {agent_name} uses OpenRouter provider")
            elif hasattr(agent_config, 'llm_provider') and agent_config.llm_provider == 'openrouter':
                if not v:
                    raise ValueError(f"OpenRouter API key required when {agent_name} uses OpenRouter provider")
        
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

# Agent LLM Configuration - Development Optimized
# Rationale: Balance between cost, speed, and accuracy for development

# Conversation Agent: Local model for fast iteration during development
# Reasoning: Frequent use during development, local model reduces API costs
CONVERSATION_AGENT__LLM_PROVIDER=ollama
CONVERSATION_AGENT__MODEL=llama3.2:3b
CONVERSATION_AGENT__TEMPERATURE=0.2
CONVERSATION_AGENT__TIMEOUT=30
CONVERSATION_AGENT__MAX_RETRIES=3

# Conversion Agent: Cloud model for reliable code generation
# Reasoning: Code generation quality is critical, worth the API cost
CONVERSION_AGENT__LLM_PROVIDER=openrouter
CONVERSION_AGENT__MODEL=anthropic/claude-3.5-sonnet
CONVERSION_AGENT__TEMPERATURE=0.1
CONVERSION_AGENT__TIMEOUT=60
CONVERSION_AGENT__MAX_RETRIES=3

# Evaluation Agent: Local model for structured validation tasks
# Reasoning: Validation tasks are more structured, local model sufficient
EVALUATION_AGENT__LLM_PROVIDER=ollama
EVALUATION_AGENT__MODEL=llama3.2:3b
EVALUATION_AGENT__TEMPERATURE=0.0
EVALUATION_AGENT__TIMEOUT=30

# LLM Provider Settings
OPENROUTER_API_KEY=your_key_here
OLLAMA_ENDPOINT=http://localhost:11434

# DataLad Settings (required for all conversions)
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

# Agent LLM Configuration - Production Optimized
# Rationale: Prioritize reliability and consistency over cost

# Conversation Agent: High-quality model for accurate metadata extraction
# Reasoning: User interactions must be accurate, worth premium model cost
CONVERSATION_AGENT__LLM_PROVIDER=openrouter
CONVERSATION_AGENT__MODEL=anthropic/claude-3.5-sonnet
CONVERSATION_AGENT__TEMPERATURE=0.2
CONVERSATION_AGENT__TIMEOUT=45
CONVERSATION_AGENT__MAX_RETRIES=5

# Conversion Agent: Premium model for critical code generation
# Reasoning: Conversion failures are expensive, use best available model
CONVERSION_AGENT__LLM_PROVIDER=openrouter
CONVERSION_AGENT__MODEL=anthropic/claude-3.5-sonnet
CONVERSION_AGENT__TEMPERATURE=0.1
CONVERSION_AGENT__TIMEOUT=90
CONVERSION_AGENT__MAX_RETRIES=5

# Evaluation Agent: Cost-optimized model for structured validation
# Reasoning: Validation tasks are structured, cheaper model acceptable
EVALUATION_AGENT__LLM_PROVIDER=openrouter
EVALUATION_AGENT__MODEL=anthropic/claude-3.5-haiku
EVALUATION_AGENT__TEMPERATURE=0.0
EVALUATION_AGENT__TIMEOUT=45

# Required in production - will raise error if missing
OPENROUTER_API_KEY=  # Must be set

# DataLad Settings (required for all conversions)
DATALAD__AUTO_CREATE_REPOS=true
DATALAD__DEFAULT_REMOTE=gin
DATALAD__CACHE_DIR=/var/cache/datalad

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
```

### Agent-Specific LLM Provider Implementation

```python
# agentic_neurodata_conversion/interfaces/llm_provider.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import httpx
import ollama
from agentic_neurodata_conversion.config import settings

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        pass

class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider for cloud models"""
    
    def __init__(self, api_key: str, model: str, temperature: float = 0.1, 
                 timeout: int = 30, max_retries: int = 3):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = "https://openrouter.ai/api/v1"
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.temperature),
            **kwargs
        }
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    def get_available_models(self) -> List[str]:
        """Get available models from OpenRouter"""
        # This would typically make an API call to get current models
        return [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3.5-haiku", 
            "openai/gpt-4o",
            "openai/gpt-4o-mini"
        ]

class OllamaProvider(LLMProvider):
    """Ollama provider for local models"""
    
    def __init__(self, endpoint: str, model: str, temperature: float = 0.1, timeout: int = 30):
        self.endpoint = endpoint
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.client = ollama.Client(host=endpoint)
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Ollama"""
        try:
            response = await asyncio.to_thread(
                self.client.generate,
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "timeout": self.timeout
                }
            )
            return response["response"]
            
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}")
    
    def get_available_models(self) -> List[str]:
        """Get available local models"""
        try:
            models = self.client.list()
            return [model["name"] for model in models["models"]]
        except Exception:
            return []

class LLMProviderFactory:
    """Factory for creating LLM providers based on configuration"""
    
    @staticmethod
    def create_provider(provider_type: str, config: Dict[str, Any]) -> LLMProvider:
        """Create appropriate LLM provider based on configuration"""
        
        if provider_type == "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError("OpenRouter API key required but not configured")
            
            return OpenRouterProvider(
                api_key=settings.openrouter_api_key,
                model=config["model"],
                temperature=config.get("temperature", 0.1),
                timeout=config.get("timeout", 30),
                max_retries=config.get("max_retries", 3)
            )
        
        elif provider_type == "ollama":
            return OllamaProvider(
                endpoint=settings.ollama_endpoint,
                model=config["model"],
                temperature=config.get("temperature", 0.1),
                timeout=config.get("timeout", 30)
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")

# Agent-specific provider creation
def get_conversation_agent_provider() -> LLMProvider:
    """Get LLM provider configured for conversation agent"""
    config = settings.conversation_agent.dict()
    return LLMProviderFactory.create_provider(
        settings.conversation_agent.llm_provider, 
        config
    )

def get_conversion_agent_provider() -> LLMProvider:
    """Get LLM provider configured for conversion agent"""
    config = settings.conversion_agent.dict()
    return LLMProviderFactory.create_provider(
        settings.conversion_agent.llm_provider,
        config
    )

def get_evaluation_agent_provider() -> LLMProvider:
    """Get LLM provider configured for evaluation agent"""
    config = settings.evaluation_agent.dict()
    return LLMProviderFactory.create_provider(
        settings.evaluation_agent.llm_provider,
        config
    )
```

### Configuration Usage Examples

**Scenario 1: Development with Mixed Providers**
```bash
# .env.development
CONVERSATION_AGENT__LLM_PROVIDER=ollama
CONVERSATION_AGENT__MODEL=llama3.2:3b

CONVERSION_AGENT__LLM_PROVIDER=openrouter  
CONVERSION_AGENT__MODEL=anthropic/claude-3.5-sonnet

EVALUATION_AGENT__LLM_PROVIDER=ollama
EVALUATION_AGENT__MODEL=llama3.2:3b
```

**Scenario 2: CI/Testing with All Local Models**
```bash
# .env.ci
CONVERSATION_AGENT__LLM_PROVIDER=ollama
CONVERSATION_AGENT__MODEL=llama3.2:3b

CONVERSION_AGENT__LLM_PROVIDER=ollama
CONVERSION_AGENT__MODEL=codellama:7b

EVALUATION_AGENT__LLM_PROVIDER=ollama
EVALUATION_AGENT__MODEL=llama3.2:3b
```

**Scenario 3: Production with All Cloud Models**
```bash
# .env.production
CONVERSATION_AGENT__LLM_PROVIDER=openrouter
CONVERSATION_AGENT__MODEL=anthropic/claude-3.5-sonnet

CONVERSION_AGENT__LLM_PROVIDER=openrouter
CONVERSION_AGENT__MODEL=anthropic/claude-3.5-sonnet

EVALUATION_AGENT__LLM_PROVIDER=openrouter
EVALUATION_AGENT__MODEL=anthropic/claude-3.5-haiku
```

**Scenario 4: Cost-Optimized Production**
```bash
# .env.production-budget
CONVERSATION_AGENT__LLM_PROVIDER=openrouter
CONVERSATION_AGENT__MODEL=openai/gpt-4o-mini

CONVERSION_AGENT__LLM_PROVIDER=openrouter
CONVERSION_AGENT__MODEL=anthropic/claude-3.5-sonnet  # Keep premium for code

EVALUATION_AGENT__LLM_PROVIDER=ollama  # Use local for validation
EVALUATION_AGENT__MODEL=llama3.2:3b
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
from unittest.mock import Mock, AsyncMock
import json

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
        "conversation_agent": {
            "analyze_dataset": {
                "detected_formats": ["open_ephys", "spikeglx"],
                "missing_metadata": ["subject_id", "session_description"],
                "questions": [
                    "What is the subject ID for this recording?",
                    "Please describe the experimental session."
                ]
            }
        },
        "conversion_agent": {
            "synthesize_conversion_script": """
import neuroconv
from pathlib import Path

# Generated conversion script
def convert_data():
    # Mock conversion implementation
    pass
""",
            "validation_result": {"success": True, "errors": []}
        },
        "evaluation_agent": {
            "validate_nwb": {
                "passed": True,
                "inspector_results": {"errors": [], "warnings": []},
                "quality_metrics": {"completeness": 0.95, "compliance": 1.0}
            }
        }
    }

@pytest.fixture
def mock_agents(mock_llm_responses):
    """Create mock agent instances for testing"""
    conversation_agent = Mock()
    conversation_agent.analyze_dataset.return_value = mock_llm_responses["conversation_agent"]["analyze_dataset"]
    
    conversion_agent = Mock()
    conversion_agent.synthesize_conversion_script.return_value = mock_llm_responses["conversion_agent"]["synthesize_conversion_script"]
    
    evaluation_agent = Mock()
    evaluation_agent.validate_nwb.return_value = mock_llm_responses["evaluation_agent"]["validate_nwb"]
    
    return {
        "conversation": conversation_agent,
        "conversion": conversion_agent,
        "evaluation": evaluation_agent
    }

@pytest.fixture
def sample_dataset_structure():
    """Create sample dataset structure for testing"""
    return {
        "root": "test_dataset",
        "files": [
            "continuous.dat",
            "structure.oebin",
            "sync_messages.txt",
            "experiment1/recording1/continuous/Neuropix-PXI-100.0/continuous.dat"
        ],
        "metadata": {
            "subject_id": "mouse_001",
            "session_description": "Test recording session",
            "experimenter": "Test User"
        }
    }

@pytest.fixture
def test_config():
    """Provide test configuration"""
    return {
        "conversation_agent": {
            "llm_provider": "mock",
            "model": "test_model",
            "temperature": 0.0
        },
        "conversion_agent": {
            "llm_provider": "mock", 
            "model": "test_model",
            "temperature": 0.0
        },
        "evaluation_agent": {
            "llm_provider": "mock",
            "model": "test_model", 
            "temperature": 0.0
        }
    }
```

#### Test Execution Strategy

**Pytest Marks Configuration** (`pytest.ini`):
```ini
[tool:pytest]
markers =
    unit: Unit tests with no external dependencies
    mock_llm: Tests using mocked LLM responses
    small_model: Tests using small local models (<3B parameters)
    large_model_minimal: Tests using 7B models with minimal context
    large_model_extended: Tests using 7B models with full context
    cheap_api: Tests using inexpensive cloud models
    frontier_api: Tests using latest/expensive models
    integration: Integration tests requiring multiple components
    evaluation: Evaluation and benchmarking tests
    slow: Tests that take significant time to run
    requires_datalad: Tests requiring DataLad installation
    requires_ollama: Tests requiring Ollama installation
```

**Test Execution Commands**:
```bash
# Run only unit tests (fastest)
pytest -m "unit"

# Run tests with mocked LLMs (development)
pytest -m "unit or mock_llm"

# Run tests with small local models (CI)
pytest -m "unit or mock_llm or small_model"

# Run comprehensive tests (pre-release)
pytest -m "not frontier_api"

# Run all tests including expensive ones (release validation)
pytest
```

#### Test Categories and Examples

**Unit Tests** (`tests/unit/`):
```python
# tests/unit/test_core/test_format_detector.py
import pytest
from agentic_neurodata_conversion.core import FormatDetector

@pytest.mark.unit
def test_format_detector_open_ephys(sample_dataset_structure):
    detector = FormatDetector()
    formats = detector.detect_formats(sample_dataset_structure["files"])
    assert "open_ephys" in [f["format"] for f in formats]

@pytest.mark.unit
def test_conversion_config_validation():
    from agentic_neurodata_conversion.config import ConversionConfig
    config = ConversionConfig(
        output_dir="/tmp/test",
        validation_level="strict"
    )
    assert config.output_dir == "/tmp/test"
```

**Mock LLM Tests** (`tests/integration/`):
```python
# tests/integration/test_agent_workflows.py
import pytest
from agentic_neurodata_conversion.core import ConversionOrchestrator

@pytest.mark.mock_llm
def test_full_conversion_workflow(mock_agents, temp_datalad_repo, test_config):
    orchestrator = ConversionOrchestrator(config=test_config)
    orchestrator.conversation_agent = mock_agents["conversation"]
    orchestrator.conversion_agent = mock_agents["conversion"]
    orchestrator.evaluation_agent = mock_agents["evaluation"]
    
    result = orchestrator.run_conversion_pipeline(temp_datalad_repo)
    assert result.success is True
    assert result.output_path is not None
```

**Small Model Tests** (`tests/evaluation/`):
```python
# tests/evaluation/test_agent_accuracy.py
import pytest
from agentic_neurodata_conversion.agents import ConversationAgent

@pytest.mark.small_model
@pytest.mark.requires_ollama
def test_conversation_agent_basic_analysis():
    agent = ConversationAgent(
        llm_provider="ollama",
        model="llama3.2:3b",
        temperature=0.0
    )
    
    # Test with simple dataset
    result = agent.analyze_dataset("tests/fixtures/simple_dataset")
    assert "detected_formats" in result
    assert len(result["detected_formats"]) > 0
```

#### Continuous Integration Integration

**GitHub Actions Workflow** (`.github/workflows/test.yml`):
```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-pixi@v0.8.1
      - run: pixi run pytest -m "unit"
  
  mock-llm-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-pixi@v0.8.1
      - run: pixi run pytest -m "unit or mock_llm"
  
  small-model-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-pixi@v0.8.1
      - name: Install Ollama
        run: |
          curl -fsSL https://ollama.ai/install.sh | sh
          ollama serve &
          sleep 10
          ollama pull llama3.2:3b
      - run: pixi run pytest -m "unit or mock_llm or small_model"
```

#### Performance and Quality Metrics

**Test Coverage Requirements**:
- Unit tests: >90% coverage for core modules
- Integration tests: >80% coverage for agent workflows  
- End-to-end tests: >70% coverage for complete pipelines

**Performance Benchmarks**:
- Unit tests: <30 seconds total
- Mock LLM tests: <2 minutes total
- Small model tests: <10 minutes total
- Integration tests: <30 minutes total

**Quality Gates**:
- All unit and mock_llm tests must pass for merge
- Small model tests must pass for release candidates
- Performance regression tests for conversion speed
- Memory usage monitoring for large dataset processing
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