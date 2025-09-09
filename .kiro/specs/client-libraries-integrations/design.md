# Client Libraries and Integrations Design

## Overview

This design document outlines the client libraries and external integrations that interact with the MCP server. The primary focus is on a Python client library that provides a clean, robust interface for consuming the conversion pipeline, along with integration patterns for external tools and workflows.

## Architecture

### High-Level Client Architecture

```
Client Libraries and Integrations
├── Core Python Client Library
│   ├── MCP Server Communication Layer
│   ├── Pipeline State Management
│   ├── Error Handling and Recovery
│   └── Configuration Management
├── Integration Utilities
│   ├── Jupyter Notebook Integration
│   ├── Workflow System Adapters
│   ├── Cloud Storage Interfaces
│   └── Analysis Tool Exporters
├── Example Implementations
│   ├── Basic Usage Examples
│   ├── Advanced Workflow Examples
│   ├── Integration Patterns
│   └── Testing Utilities
└── Monitoring and Observability
    ├── Metrics Collection
    ├── Logging Integration
    ├── Performance Monitoring
    └── Diagnostic Tools
```

### Client Communication Flow

```
Client Application → Python Client Library → HTTP/API Layer → MCP Server
                           ↓
                    State Management → Progress Tracking → Error Recovery
                           ↓
                    Result Processing → Format Conversion → Integration Hooks
```

## Core Components

### 1. Core Python Client Library

#### Main Client Class
```python
# src/agentic_converter/client/mcp_client.py
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import requests
import json

class PipelineStatus(Enum):
    """Pipeline execution status."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    CONVERTING = "converting"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class ClientConfig:
    """Configuration for MCP client."""
    api_url: str = "http://127.0.0.1:8000"
    output_dir: str = "outputs"
    timeout: int = 300
    retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    enable_logging: bool = True
    log_level: str = "INFO"
    progress_callback: Optional[Callable[[str, float], None]] = None
    
@dataclass
class ConversionResult:
    """Result of a conversion operation."""
    success: bool
    status: PipelineStatus
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class MCPClient:
    """Main client for interacting with the MCP server."""
    
    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        self.logger = self._setup_logging()
        self.session = requests.Session()
        self.pipeline_state = {}
        self.status = PipelineStatus.IDLE
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_execution_time': 0.0
        }
        
        # Validate server connection on initialization
        self._validate_server_connection()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup client logging."""
        logger = logging.getLogger(f"mcp_client.{id(self)}")
        
        if self.config.enable_logging:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(getattr(logging, self.config.log_level))
        
        return logger
    
    def _validate_server_connection(self):
        """Validate connection to MCP server."""
        try:
            response = self.session.get(f"{self.config.api_url}/status", timeout=10)
            response.raise_for_status()
            self.logger.info("Successfully connected to MCP server")
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Could not connect to MCP server: {e}")
    
    async def call_tool(self, tool_name: str, payload: Optional[Dict[str, Any]] = None, 
                       timeout: Optional[int] = None) -> ConversionResult:
        """Call MCP server tool with retry logic and error handling."""
        start_time = time.time()
        timeout = timeout or self.config.timeout
        payload = payload or {}
        
        for attempt in range(self.config.retry_attempts):
            try:
                self.logger.debug(f"Calling tool {tool_name} (attempt {attempt + 1})")
                
                response = self.session.post(
                    f"{self.config.api_url}/tool/{tool_name}",
                    json=payload,
                    timeout=timeout
                )
                
                response.raise_for_status()
                result_data = response.json()
                
                execution_time = time.time() - start_time
                self._update_metrics(success=True, execution_time=execution_time)
                
                return ConversionResult(
                    success=result_data.get('status') == 'success',
                    status=self.status,
                    data=result_data,
                    execution_time=execution_time
                )
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Tool {tool_name} timed out (attempt {attempt + 1})")
                if attempt == self.config.retry_attempts - 1:
                    execution_time = time.time() - start_time
                    self._update_metrics(success=False, execution_time=execution_time)
                    return ConversionResult(
                        success=False,
                        status=PipelineStatus.ERROR,
                        error=f"Tool {tool_name} timed out after {timeout} seconds",
                        execution_time=execution_time
                    )
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Tool {tool_name} failed: {e}")
                if attempt == self.config.retry_attempts - 1:
                    execution_time = time.time() - start_time
                    self._update_metrics(success=False, execution_time=execution_time)
                    return ConversionResult(
                        success=False,
                        status=PipelineStatus.ERROR,
                        error=str(e),
                        execution_time=execution_time
                    )
            
            # Wait before retry with exponential backoff
            if attempt < self.config.retry_attempts - 1:
                delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                self.logger.info(f"Retrying in {delay:.1f} seconds...")
                await asyncio.sleep(delay)
    
    async def initialize_pipeline(self, output_dir: Optional[str] = None, 
                                use_llm: bool = False) -> ConversionResult:
        """Initialize the conversion pipeline."""
        self.status = PipelineStatus.IDLE
        output_dir = output_dir or self.config.output_dir
        
        self.logger.info("Initializing conversion pipeline")
        self._report_progress("Initializing pipeline", 0.0)
        
        result = await self.call_tool("initialize_pipeline", {
            "config": {
                "output_dir": output_dir,
                "use_llm": use_llm
            }
        })
        
        if result.success:
            self.pipeline_state.update(result.data.get('config', {}))
            self.logger.info("Pipeline initialized successfully")
        
        return result
    
    async def analyze_dataset(self, dataset_dir: str, use_llm: bool = False) -> ConversionResult:
        """Analyze dataset structure and extract metadata."""
        self.status = PipelineStatus.ANALYZING
        
        self.logger.info(f"Analyzing dataset: {dataset_dir}")
        self._report_progress("Analyzing dataset", 0.1)
        
        result = await self.call_tool("analyze_dataset", {
            "dataset_dir": dataset_dir,
            "use_llm": use_llm
        })
        
        if result.success:
            self.pipeline_state["normalized_metadata"] = result.data.get("result", {})\n            self.pipeline_state["last_analyzed_dataset"] = dataset_dir
            self.logger.info("Dataset analysis completed")
            self._report_progress("Dataset analysis complete", 0.3)
        else:
            self.status = PipelineStatus.ERROR
            self.logger.error(f"Dataset analysis failed: {result.error}")
        
        return result
    
    async def generate_conversion_script(self, files_map: Dict[str, str], 
                                       output_nwb_path: Optional[str] = None) -> ConversionResult:
        """Generate and execute conversion script."""
        self.status = PipelineStatus.CONVERTING
        
        if "normalized_metadata" not in self.pipeline_state:
            return ConversionResult(
                success=False,
                status=PipelineStatus.ERROR,
                error="No metadata available. Run analyze_dataset first."
            )
        
        self.logger.info("Generating conversion script")
        self._report_progress("Generating conversion script", 0.4)
        
        result = await self.call_tool("generate_conversion_script", {
            "normalized_metadata": self.pipeline_state["normalized_metadata"],
            "files_map": files_map,
            "output_nwb_path": output_nwb_path
        })
        
        if result.success:
            self.pipeline_state["nwb_path"] = result.data.get("output_nwb_path")
            self.pipeline_state["conversion_result"] = result.data
            self.logger.info("Conversion script generated and executed")
            self._report_progress("Conversion complete", 0.7)
        else:
            self.status = PipelineStatus.ERROR
            self.logger.error(f"Conversion failed: {result.error}")
        
        return result
    
    async def evaluate_nwb_file(self, nwb_path: Optional[str] = None, 
                              generate_report: bool = True) -> ConversionResult:
        """Evaluate generated NWB file."""
        self.status = PipelineStatus.EVALUATING
        
        nwb_path = nwb_path or self.pipeline_state.get("nwb_path")
        if not nwb_path:
            return ConversionResult(
                success=False,
                status=PipelineStatus.ERROR,
                error="No NWB file available for evaluation"
            )
        
        self.logger.info(f"Evaluating NWB file: {nwb_path}")
        self._report_progress("Evaluating NWB file", 0.8)
        
        result = await self.call_tool("evaluate_nwb_file", {
            "nwb_path": nwb_path,
            "generate_report": generate_report
        })
        
        if result.success:
            self.pipeline_state["evaluation_result"] = result.data
            self.logger.info("NWB evaluation completed")
            self._report_progress("Evaluation complete", 0.9)
        else:
            self.logger.error(f"NWB evaluation failed: {result.error}")
        
        return result
    
    async def generate_knowledge_graph(self, nwb_path: Optional[str] = None) -> ConversionResult:
        """Generate knowledge graph from NWB file."""
        nwb_path = nwb_path or self.pipeline_state.get("nwb_path")
        if not nwb_path:
            return ConversionResult(
                success=False,
                status=PipelineStatus.ERROR,
                error="No NWB file available for knowledge graph generation"
            )
        
        self.logger.info("Generating knowledge graph")
        self._report_progress("Generating knowledge graph", 0.95)
        
        result = await self.call_tool("generate_knowledge_graph", {
            "nwb_path": nwb_path
        })
        
        if result.success:
            self.pipeline_state["knowledge_graph_result"] = result.data
            self.logger.info("Knowledge graph generated")
        
        return result
    
    async def run_full_pipeline(self, dataset_dir: str, files_map: Dict[str, str], 
                              use_llm: bool = False, output_nwb_path: Optional[str] = None) -> ConversionResult:
        """Run the complete conversion pipeline."""
        self.logger.info("Starting full conversion pipeline")
        self._report_progress("Starting pipeline", 0.0)
        
        pipeline_results = {
            "initialization": None,
            "analysis": None,
            "conversion": None,
            "evaluation": None,
            "knowledge_graph": None
        }
        
        try:
            # Step 1: Initialize pipeline
            init_result = await self.initialize_pipeline(use_llm=use_llm)
            pipeline_results["initialization"] = init_result
            if not init_result.success:
                return self._create_pipeline_failure_result("initialization", init_result, pipeline_results)
            
            # Step 2: Analyze dataset
            analysis_result = await self.analyze_dataset(dataset_dir, use_llm)
            pipeline_results["analysis"] = analysis_result
            if not analysis_result.success:
                return self._create_pipeline_failure_result("analysis", analysis_result, pipeline_results)
            
            # Step 3: Generate conversion
            conversion_result = await self.generate_conversion_script(files_map, output_nwb_path)
            pipeline_results["conversion"] = conversion_result
            if not conversion_result.success:
                return self._create_pipeline_failure_result("conversion", conversion_result, pipeline_results)
            
            # Step 4: Evaluate NWB file
            evaluation_result = await self.evaluate_nwb_file()
            pipeline_results["evaluation"] = evaluation_result
            # Note: Evaluation failure doesn't stop the pipeline
            
            # Step 5: Generate knowledge graph
            kg_result = await self.generate_knowledge_graph()
            pipeline_results["knowledge_graph"] = kg_result
            # Note: KG generation failure doesn't stop the pipeline
            
            self.status = PipelineStatus.COMPLETED
            self._report_progress("Pipeline complete", 1.0)
            
            return ConversionResult(
                success=True,
                status=PipelineStatus.COMPLETED,
                data={
                    "pipeline_results": pipeline_results,
                    "final_state": self.pipeline_state.copy(),
                    "nwb_path": self.pipeline_state.get("nwb_path"),
                    "summary": self._generate_pipeline_summary(pipeline_results)
                }
            )
            
        except Exception as e:
            self.status = PipelineStatus.ERROR
            self.logger.error(f"Pipeline execution failed: {e}")
            return ConversionResult(
                success=False,
                status=PipelineStatus.ERROR,
                error=str(e),
                data={"pipeline_results": pipeline_results}
            )
    
    def _create_pipeline_failure_result(self, failed_step: str, failed_result: ConversionResult, 
                                      pipeline_results: Dict[str, Any]) -> ConversionResult:
        """Create result for pipeline failure."""
        self.status = PipelineStatus.ERROR
        return ConversionResult(
            success=False,
            status=PipelineStatus.ERROR,
            error=f"Pipeline failed at {failed_step}: {failed_result.error}",
            data={
                "failed_step": failed_step,
                "pipeline_results": pipeline_results
            }
        )
    
    def _generate_pipeline_summary(self, pipeline_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of pipeline execution."""
        summary = {
            "total_steps": len(pipeline_results),
            "successful_steps": sum(1 for r in pipeline_results.values() if r and r.success),
            "failed_steps": sum(1 for r in pipeline_results.values() if r and not r.success),
            "total_execution_time": sum(r.execution_time for r in pipeline_results.values() if r),
            "nwb_file_created": bool(self.pipeline_state.get("nwb_path")),
            "evaluation_passed": pipeline_results.get("evaluation", {}).success if pipeline_results.get("evaluation") else False,
            "knowledge_graph_generated": pipeline_results.get("knowledge_graph", {}).success if pipeline_results.get("knowledge_graph") else False
        }
        return summary
    
    def _report_progress(self, message: str, progress: float):
        """Report progress to callback if configured."""
        if self.config.progress_callback:
            self.config.progress_callback(message, progress)
        self.logger.info(f"Progress: {message} ({progress:.1%})")
    
    def _update_metrics(self, success: bool, execution_time: float):
        """Update client metrics."""
        self.metrics['total_requests'] += 1
        self.metrics['total_execution_time'] += execution_time
        
        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics."""
        total_requests = self.metrics['total_requests']
        return {
            **self.metrics,
            'success_rate': (
                self.metrics['successful_requests'] / total_requests
                if total_requests > 0 else 0.0
            ),
            'average_request_time': (
                self.metrics['total_execution_time'] / total_requests
                if total_requests > 0 else 0.0
            ),
            'current_status': self.status.value
        }
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get MCP server status."""
        try:
            response = self.session.get(f"{self.config.api_url}/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "unreachable"}
    
    def get_available_tools(self) -> Dict[str, Any]:
        """Get list of available tools from server."""
        try:
            response = self.session.get(f"{self.config.api_url}/tools", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "tools": {}}
    
    def reset_pipeline_state(self):
        """Reset pipeline state for new conversion."""
        self.pipeline_state.clear()
        self.status = PipelineStatus.IDLE
        self.logger.info("Pipeline state reset")
    
    def save_state(self, filepath: str):
        """Save current pipeline state to file."""
        state_data = {
            "pipeline_state": self.pipeline_state,
            "status": self.status.value,
            "metrics": self.metrics,
            "timestamp": time.time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(state_data, f, indent=2, default=str)
        
        self.logger.info(f"Pipeline state saved to {filepath}")
    
    def load_state(self, filepath: str):
        """Load pipeline state from file."""
        try:
            with open(filepath, 'r') as f:
                state_data = json.load(f)
            
            self.pipeline_state = state_data.get("pipeline_state", {})
            self.status = PipelineStatus(state_data.get("status", "idle"))
            self.metrics.update(state_data.get("metrics", {}))
            
            self.logger.info(f"Pipeline state loaded from {filepath}")
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to load state from {filepath}: {e}")
            raise
```

### 2. Integration Utilities

#### Jupyter Notebook Integration
```python
# src/agentic_converter/client/jupyter_integration.py
from typing import Optional, Dict, Any
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from .mcp_client import MCPClient, ClientConfig

class JupyterMCPClient(MCPClient):
    """MCP Client with Jupyter notebook integration."""
    
    def __init__(self, config: Optional[ClientConfig] = None):
        super().__init__(config)
        self.progress_widget = None
        self.output_widget = None
        self._setup_jupyter_widgets()
    
    def _setup_jupyter_widgets(self):
        """Setup Jupyter widgets for progress tracking."""
        self.progress_widget = widgets.FloatProgress(
            value=0.0,
            min=0.0,
            max=1.0,
            description='Progress:',
            bar_style='info',
            style={'bar_color': '#1f77b4'},
            orientation='horizontal'
        )
        
        self.output_widget = widgets.Output()
        
        # Override progress callback
        self.config.progress_callback = self._jupyter_progress_callback
    
    def _jupyter_progress_callback(self, message: str, progress: float):
        """Progress callback for Jupyter notebooks."""
        self.progress_widget.value = progress
        self.progress_widget.description = f'Progress: {message}'
        
        with self.output_widget:
            clear_output(wait=True)
            print(f"{message} ({progress:.1%})")
    
    def display_widgets(self):
        """Display progress widgets in notebook."""
        display(widgets.VBox([self.progress_widget, self.output_widget]))
    
    async def run_full_pipeline_notebook(self, dataset_dir: str, files_map: Dict[str, str], 
                                       use_llm: bool = False) -> Dict[str, Any]:
        """Run pipeline with notebook-friendly output."""
        self.display_widgets()
        
        result = await self.run_full_pipeline(dataset_dir, files_map, use_llm)
        
        # Display results
        with self.output_widget:
            clear_output(wait=True)
            if result.success:
                print("✅ Pipeline completed successfully!")
                self._display_pipeline_summary(result.data.get("summary", {}))
            else:
                print(f"❌ Pipeline failed: {result.error}")
        
        return result.data
    
    def _display_pipeline_summary(self, summary: Dict[str, Any]):
        """Display pipeline summary in notebook."""
        html_content = f"""
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3>Pipeline Summary</h3>
            <ul>
                <li><strong>Total Steps:</strong> {summary.get('total_steps', 0)}</li>
                <li><strong>Successful Steps:</strong> {summary.get('successful_steps', 0)}</li>
                <li><strong>Execution Time:</strong> {summary.get('total_execution_time', 0):.2f}s</li>
                <li><strong>NWB File Created:</strong> {'✅' if summary.get('nwb_file_created') else '❌'}</li>
                <li><strong>Evaluation Passed:</strong> {'✅' if summary.get('evaluation_passed') else '❌'}</li>
                <li><strong>Knowledge Graph Generated:</strong> {'✅' if summary.get('knowledge_graph_generated') else '❌'}</li>
            </ul>
        </div>
        """
        display(HTML(html_content))

# Convenience function for notebook users
def create_notebook_client(api_url: str = "http://127.0.0.1:8000", 
                          output_dir: str = "outputs") -> JupyterMCPClient:
    """Create a Jupyter-optimized MCP client."""
    config = ClientConfig(
        api_url=api_url,
        output_dir=output_dir,
        enable_logging=True,
        log_level="INFO"
    )
    return JupyterMCPClient(config)
```

#### Workflow System Adapters
```python
# src/agentic_converter/client/workflow_adapters.py
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml
import json
from .mcp_client import MCPClient, ClientConfig

class SnakemakeAdapter:
    """Adapter for Snakemake workflow integration."""
    
    def __init__(self, client: MCPClient):
        self.client = client
    
    def generate_snakemake_rule(self, rule_name: str = "convert_to_nwb") -> str:
        """Generate Snakemake rule for NWB conversion."""
        rule_template = f'''
rule {rule_name}:
    input:
        dataset_dir="{{{rule_name}_dataset_dir}}",
        files_map="{{{rule_name}_files_map}}"
    output:
        nwb_file="{{{rule_name}_output}}"
    params:
        api_url=config.get("mcp_server_url", "http://127.0.0.1:8000"),
        use_llm=config.get("use_llm", False)
    script:
        "scripts/run_mcp_conversion.py"
'''
        return rule_template
    
    def create_conversion_script(self, output_path: str = "scripts/run_mcp_conversion.py"):
        """Create Python script for Snakemake rule."""
        script_content = '''
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.agentic_converter.client.mcp_client import MCPClient, ClientConfig

async def main():
    # Get parameters from Snakemake
    dataset_dir = snakemake.input.dataset_dir
    files_map_path = snakemake.input.files_map
    output_nwb = snakemake.output.nwb_file
    api_url = snakemake.params.api_url
    use_llm = snakemake.params.use_llm
    
    # Load files map
    with open(files_map_path, 'r') as f:
        files_map = json.load(f)
    
    # Create client and run conversion
    config = ClientConfig(api_url=api_url)
    client = MCPClient(config)
    
    result = await client.run_full_pipeline(
        dataset_dir=dataset_dir,
        files_map=files_map,
        use_llm=use_llm,
        output_nwb_path=output_nwb
    )
    
    if not result.success:
        raise RuntimeError(f"Conversion failed: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(script_content)

class NextflowAdapter:
    """Adapter for Nextflow workflow integration."""
    
    def __init__(self, client: MCPClient):
        self.client = client
    
    def generate_nextflow_process(self, process_name: str = "CONVERT_TO_NWB") -> str:
        """Generate Nextflow process for NWB conversion."""
        process_template = f'''
process {process_name} {{
    tag "${{dataset_id}}"
    publishDir "${{params.outdir}}", mode: 'copy'
    
    input:
    tuple val(dataset_id), path(dataset_dir), path(files_map)
    
    output:
    tuple val(dataset_id), path("*.nwb"), emit: nwb_files
    tuple val(dataset_id), path("*_report.html"), emit: reports, optional: true
    
    script:
    """
    python ${{projectDir}}/bin/run_mcp_conversion.py \\
        --dataset-dir ${{dataset_dir}} \\
        --files-map ${{files_map}} \\
        --output-nwb ${{dataset_id}}.nwb \\
        --api-url ${{params.mcp_server_url}} \\
        --use-llm ${{params.use_llm}}
    """
}}
'''
        return process_template

class CWLAdapter:
    """Adapter for Common Workflow Language (CWL) integration."""
    
    def __init__(self, client: MCPClient):
        self.client = client
    
    def generate_cwl_tool(self) -> Dict[str, Any]:
        """Generate CWL tool definition for NWB conversion."""
        cwl_tool = {
            "cwlVersion": "v1.2",
            "class": "CommandLineTool",
            "id": "nwb-conversion",
            "label": "NWB Conversion Tool",
            "doc": "Convert neuroscience data to NWB format using MCP server",
            "requirements": {
                "DockerRequirement": {
                    "dockerPull": "agentic-converter:latest"
                }
            },
            "inputs": {
                "dataset_dir": {
                    "type": "Directory",
                    "doc": "Input dataset directory"
                },
                "files_map": {
                    "type": "File",
                    "doc": "JSON file mapping file types to paths"
                },
                "api_url": {
                    "type": "string",
                    "default": "http://127.0.0.1:8000",
                    "doc": "MCP server API URL"
                },
                "use_llm": {
                    "type": "boolean",
                    "default": False,
                    "doc": "Whether to use LLM for metadata extraction"
                }
            },
            "outputs": {
                "nwb_file": {
                    "type": "File",
                    "outputBinding": {
                        "glob": "*.nwb"
                    }
                },
                "evaluation_report": {
                    "type": "File?",
                    "outputBinding": {
                        "glob": "*_report.html"
                    }
                }
            },
            "baseCommand": ["python", "/app/bin/run_mcp_conversion.py"],
            "arguments": [
                "--dataset-dir", "$(inputs.dataset_dir.path)",
                "--files-map", "$(inputs.files_map.path)",
                "--api-url", "$(inputs.api_url)",
                "--use-llm", "$(inputs.use_llm)"
            ]
        }
        return cwl_tool
```

### 3. Example Implementations

#### Basic Usage Examples
```python
# examples/python_client/basic_usage.py
"""
Basic usage examples for the MCP client library.
"""
import asyncio
from pathlib import Path
from agentic_converter.client.mcp_client import MCPClient, ClientConfig

async def basic_conversion_example():
    """Basic conversion example."""
    print("=== Basic Conversion Example ===")
    
    # Create client with default configuration
    client = MCPClient()
    
    # Check server status
    status = client.get_server_status()
    print(f"Server status: {status}")
    
    # Define dataset and files
    dataset_dir = "/path/to/your/dataset"
    files_map = {
        "recording": "/path/to/recording.dat",
        "events": "/path/to/events.txt"
    }
    
    try:
        # Run full pipeline
        result = await client.run_full_pipeline(
            dataset_dir=dataset_dir,
            files_map=files_map,
            use_llm=False  # Set to True if you have LLM configured
        )
        
        if result.success:
            print("✅ Conversion completed successfully!")
            print(f"NWB file created: {result.data['nwb_path']}")
            print(f"Summary: {result.data['summary']}")
        else:
            print(f"❌ Conversion failed: {result.error}")
            
    except Exception as e:
        print(f"Error: {e}")

async def step_by_step_example():
    """Step-by-step conversion example."""
    print("=== Step-by-Step Conversion Example ===")
    
    # Create client with custom configuration
    config = ClientConfig(
        api_url="http://localhost:8000",
        output_dir="my_outputs",
        timeout=600,  # 10 minutes
        retry_attempts=5
    )
    client = MCPClient(config)
    
    dataset_dir = "/path/to/your/dataset"
    files_map = {"recording": "/path/to/recording.dat"}
    
    try:
        # Step 1: Initialize
        print("Step 1: Initializing pipeline...")
        init_result = await client.initialize_pipeline()
        if not init_result.success:
            print(f"Initialization failed: {init_result.error}")
            return
        
        # Step 2: Analyze dataset
        print("Step 2: Analyzing dataset...")
        analysis_result = await client.analyze_dataset(dataset_dir)
        if not analysis_result.success:
            print(f"Analysis failed: {analysis_result.error}")
            return
        
        print(f"Detected formats: {analysis_result.data.get('format_analysis', {}).get('formats', [])}")
        
        # Step 3: Generate conversion
        print("Step 3: Converting to NWB...")
        conversion_result = await client.generate_conversion_script(files_map)
        if not conversion_result.success:
            print(f"Conversion failed: {conversion_result.error}")
            return
        
        print(f"NWB file created: {conversion_result.data.get('nwb_path')}")
        
        # Step 4: Evaluate
        print("Step 4: Evaluating NWB file...")
        evaluation_result = await client.evaluate_nwb_file()
        if evaluation_result.success:
            print("Evaluation completed successfully")
        else:
            print(f"Evaluation had issues: {evaluation_result.error}")
        
        # Step 5: Generate knowledge graph
        print("Step 5: Generating knowledge graph...")
        kg_result = await client.generate_knowledge_graph()
        if kg_result.success:
            print("Knowledge graph generated successfully")
        
        print("Pipeline completed!")
        
    except Exception as e:
        print(f"Error: {e}")

async def error_handling_example():
    """Example demonstrating error handling."""
    print("=== Error Handling Example ===")
    
    # Create client with aggressive retry settings
    config = ClientConfig(
        api_url="http://localhost:8000",
        retry_attempts=3,
        retry_delay=2.0,
        retry_backoff=2.0
    )
    client = MCPClient(config)
    
    # Try to analyze a non-existent dataset
    result = await client.analyze_dataset("/non/existent/path")
    
    if not result.success:
        print(f"Expected error: {result.error}")
        print(f"Status: {result.status}")
    
    # Check client metrics
    metrics = client.get_metrics()
    print(f"Client metrics: {metrics}")

def progress_callback_example(message: str, progress: float):
    """Example progress callback."""
    print(f"Progress: {message} - {progress:.1%}")

async def custom_progress_example():
    """Example with custom progress reporting."""
    print("=== Custom Progress Example ===")
    
    config = ClientConfig(
        progress_callback=progress_callback_example
    )
    client = MCPClient(config)
    
    # This will call the progress callback during execution
    result = await client.run_full_pipeline(
        dataset_dir="/path/to/dataset",
        files_map={"recording": "/path/to/file.dat"}
    )

if __name__ == "__main__":
    # Run examples
    asyncio.run(basic_conversion_example())
    asyncio.run(step_by_step_example())
    asyncio.run(error_handling_example())
    asyncio.run(custom_progress_example())
```

#### Advanced Integration Example
```python
# examples/python_client/advanced_integration.py
"""
Advanced integration examples showing complex usage patterns.
"""
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any
from agentic_converter.client.mcp_client import MCPClient, ClientConfig
from agentic_converter.client.jupyter_integration import JupyterMCPClient

class BatchConverter:
    """Batch conversion utility for multiple datasets."""
    
    def __init__(self, client: MCPClient):
        self.client = client
        self.results = []
    
    async def convert_batch(self, datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert multiple datasets in batch."""
        results = []
        
        for i, dataset_info in enumerate(datasets):
            print(f"Processing dataset {i+1}/{len(datasets)}: {dataset_info['name']}")
            
            try:
                # Reset client state for each dataset
                self.client.reset_pipeline_state()
                
                result = await self.client.run_full_pipeline(
                    dataset_dir=dataset_info['dataset_dir'],
                    files_map=dataset_info['files_map'],
                    use_llm=dataset_info.get('use_llm', False)
                )
                
                results.append({
                    'dataset_name': dataset_info['name'],
                    'success': result.success,
                    'nwb_path': result.data.get('nwb_path') if result.success else None,
                    'error': result.error,
                    'summary': result.data.get('summary', {})
                })
                
            except Exception as e:
                results.append({
                    'dataset_name': dataset_info['name'],
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def generate_batch_report(self, results: List[Dict[str, Any]], output_path: str):
        """Generate batch processing report."""
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        report = {
            'summary': {
                'total_datasets': len(results),
                'successful': len(successful),
                'failed': len(failed),
                'success_rate': len(successful) / len(results) if results else 0
            },
            'successful_conversions': successful,
            'failed_conversions': failed
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Batch report saved to {output_path}")

class CloudStorageIntegration:
    """Integration with cloud storage services."""
    
    def __init__(self, client: MCPClient):
        self.client = client
    
    async def convert_from_s3(self, s3_bucket: str, s3_prefix: str, 
                            local_temp_dir: str = "/tmp/conversion") -> Dict[str, Any]:
        """Convert dataset from S3 storage."""
        import boto3
        
        # Download dataset from S3
        s3_client = boto3.client('s3')
        local_path = Path(local_temp_dir)
        local_path.mkdir(parents=True, exist_ok=True)
        
        # List and download files
        response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_prefix)
        files_map = {}
        
        for obj in response.get('Contents', []):
            key = obj['Key']
            local_file = local_path / Path(key).name
            s3_client.download_file(s3_bucket, key, str(local_file))
            
            # Determine file type based on extension or name
            if 'recording' in key.lower():
                files_map['recording'] = str(local_file)
            elif 'events' in key.lower():
                files_map['events'] = str(local_file)
        
        # Run conversion
        result = await self.client.run_full_pipeline(
            dataset_dir=str(local_path),
            files_map=files_map
        )
        
        # Upload results back to S3 if successful
        if result.success and result.data.get('nwb_path'):
            nwb_path = result.data['nwb_path']
            s3_key = f"{s3_prefix}/converted/{Path(nwb_path).name}"
            s3_client.upload_file(nwb_path, s3_bucket, s3_key)
            result.data['s3_nwb_path'] = f"s3://{s3_bucket}/{s3_key}"
        
        # Cleanup local files
        import shutil
        shutil.rmtree(local_path)
        
        return result

async def batch_conversion_example():
    """Example of batch conversion."""
    print("=== Batch Conversion Example ===")
    
    client = MCPClient()
    batch_converter = BatchConverter(client)
    
    # Define multiple datasets
    datasets = [
        {
            'name': 'experiment_001',
            'dataset_dir': '/data/experiment_001',
            'files_map': {'recording': '/data/experiment_001/recording.dat'},
            'use_llm': False
        },
        {
            'name': 'experiment_002',
            'dataset_dir': '/data/experiment_002',
            'files_map': {'recording': '/data/experiment_002/recording.dat'},
            'use_llm': False
        }
    ]
    
    # Run batch conversion
    results = await batch_converter.convert_batch(datasets)
    
    # Generate report
    batch_converter.generate_batch_report(results, 'batch_report.json')
    
    # Print summary
    successful = sum(1 for r in results if r['success'])
    print(f"Batch conversion completed: {successful}/{len(results)} successful")

async def monitoring_example():
    """Example of monitoring and metrics collection."""
    print("=== Monitoring Example ===")
    
    client = MCPClient()
    
    # Run several operations
    for i in range(3):
        await client.get_server_status()
        await asyncio.sleep(1)
    
    # Get client metrics
    metrics = client.get_metrics()
    print(f"Client metrics: {json.dumps(metrics, indent=2)}")
    
    # Save metrics to file
    with open('client_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    asyncio.run(batch_conversion_example())
    asyncio.run(monitoring_example())
```

### 4. Testing Utilities

#### Client Testing Framework
```python
# tests/integration/test_client_library.py
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from agentic_converter.client.mcp_client import MCPClient, ClientConfig, ConversionResult, PipelineStatus

@pytest.fixture
def mock_client_config():
    """Mock client configuration for testing."""
    return ClientConfig(
        api_url="http://test-server:8000",
        timeout=30,
        retry_attempts=2,
        enable_logging=False
    )

@pytest.fixture
def mcp_client(mock_client_config):
    """MCP client instance for testing."""
    with patch.object(MCPClient, '_validate_server_connection'):
        return MCPClient(mock_client_config)

class TestMCPClient:
    """Test MCP client functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_tool_call(self, mcp_client):
        """Test successful tool call."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": "success", "data": "test"}
        
        with patch.object(mcp_client.session, 'post', return_value=mock_response):
            result = await mcp_client.call_tool("test_tool", {"param": "value"})
            
            assert result.success is True
            assert result.data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_tool_call_with_retry(self, mcp_client):
        """Test tool call with retry on failure."""
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = Exception("Network error")
        
        mock_response_success = Mock()
        mock_response_success.raise_for_status.return_value = None
        mock_response_success.json.return_value = {"status": "success"}
        
        with patch.object(mcp_client.session, 'post', side_effect=[mock_response_fail, mock_response_success]):
            result = await mcp_client.call_tool("test_tool")
            
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, mcp_client):
        """Test successful full pipeline execution."""
        # Mock all tool responses
        mock_responses = {
            "initialize_pipeline": {"status": "success", "config": {}},
            "analyze_dataset": {"status": "success", "result": {"metadata": "test"}},
            "generate_conversion_script": {"status": "success", "output_nwb_path": "/test/output.nwb"},
            "evaluate_nwb_file": {"status": "success", "evaluation": "passed"},
            "generate_knowledge_graph": {"status": "success", "kg_data": "test"}
        }
        
        async def mock_call_tool(tool_name, payload=None):
            return ConversionResult(
                success=True,
                status=PipelineStatus.COMPLETED,
                data=mock_responses.get(tool_name, {})
            )
        
        with patch.object(mcp_client, 'call_tool', side_effect=mock_call_tool):
            result = await mcp_client.run_full_pipeline(
                dataset_dir="/test/dataset",
                files_map={"recording": "/test/file.dat"}
            )
            
            assert result.success is True
            assert result.status == PipelineStatus.COMPLETED
            assert "pipeline_results" in result.data
    
    @pytest.mark.asyncio
    async def test_pipeline_failure_recovery(self, mcp_client):
        """Test pipeline failure and recovery."""
        # Mock analysis failure
        async def mock_call_tool(tool_name, payload=None):
            if tool_name == "analyze_dataset":
                return ConversionResult(
                    success=False,
                    status=PipelineStatus.ERROR,
                    error="Analysis failed"
                )
            return ConversionResult(success=True, status=PipelineStatus.COMPLETED, data={})
        
        with patch.object(mcp_client, 'call_tool', side_effect=mock_call_tool):
            result = await mcp_client.run_full_pipeline(
                dataset_dir="/test/dataset",
                files_map={"recording": "/test/file.dat"}
            )
            
            assert result.success is False
            assert "Analysis failed" in result.error
            assert result.data["failed_step"] == "analysis"
    
    def test_metrics_tracking(self, mcp_client):
        """Test client metrics tracking."""
        # Simulate some operations
        mcp_client._update_metrics(success=True, execution_time=1.5)
        mcp_client._update_metrics(success=False, execution_time=0.5)
        mcp_client._update_metrics(success=True, execution_time=2.0)
        
        metrics = mcp_client.get_metrics()
        
        assert metrics['total_requests'] == 3
        assert metrics['successful_requests'] == 2
        assert metrics['failed_requests'] == 1
        assert metrics['success_rate'] == 2/3
        assert metrics['average_request_time'] == (1.5 + 0.5 + 2.0) / 3
    
    def test_state_persistence(self, mcp_client, tmp_path):
        """Test pipeline state save/load."""
        # Set some state
        mcp_client.pipeline_state = {"test_key": "test_value"}
        mcp_client.status = PipelineStatus.COMPLETED
        
        # Save state
        state_file = tmp_path / "test_state.json"
        mcp_client.save_state(str(state_file))
        
        # Create new client and load state
        new_client = MCPClient(mcp_client.config)
        new_client.load_state(str(state_file))
        
        assert new_client.pipeline_state["test_key"] == "test_value"
        assert new_client.status == PipelineStatus.COMPLETED

class TestJupyterIntegration:
    """Test Jupyter notebook integration."""
    
    @pytest.fixture
    def jupyter_client(self, mock_client_config):
        """Jupyter MCP client for testing."""
        with patch('agentic_converter.client.jupyter_integration.widgets'):
            from agentic_converter.client.jupyter_integration import JupyterMCPClient
            with patch.object(JupyterMCPClient, '_validate_server_connection'):
                return JupyterMCPClient(mock_client_config)
    
    def test_progress_widget_creation(self, jupyter_client):
        """Test progress widget creation."""
        assert jupyter_client.progress_widget is not None
        assert jupyter_client.output_widget is not None
        assert jupyter_client.config.progress_callback is not None
    
    def test_jupyter_progress_callback(self, jupyter_client):
        """Test Jupyter progress callback."""
        # This would test widget updates in a real Jupyter environment
        jupyter_client._jupyter_progress_callback("Test message", 0.5)
        
        assert jupyter_client.progress_widget.value == 0.5
        assert "Test message" in jupyter_client.progress_widget.description

# Mock server for integration testing
class MockMCPServer:
    """Mock MCP server for testing."""
    
    def __init__(self):
        self.tools = {
            "initialize_pipeline": self._mock_initialize,
            "analyze_dataset": self._mock_analyze,
            "generate_conversion_script": self._mock_convert,
            "evaluate_nwb_file": self._mock_evaluate,
            "generate_knowledge_graph": self._mock_kg
        }
    
    async def _mock_initialize(self, **kwargs):
        return {"status": "success", "config": kwargs.get("config", {})}
    
    async def _mock_analyze(self, **kwargs):
        return {
            "status": "success",
            "result": {
                "format_analysis": {"formats": ["open_ephys"]},
                "metadata": {"experimenter": "Test User"}
            }
        }
    
    async def _mock_convert(self, **kwargs):
        return {
            "status": "success",
            "output_nwb_path": "/mock/output.nwb",
            "script_content": "# Mock conversion script"
        }
    
    async def _mock_evaluate(self, **kwargs):
        return {
            "status": "success",
            "validation": {"nwb_inspector": {"status": "passed"}},
            "quality_score": 0.95
        }
    
    async def _mock_kg(self, **kwargs):
        return {
            "status": "success",
            "ttl_path": "/mock/output.ttl",
            "entities_count": 42
        }

@pytest.fixture
def mock_server():
    """Mock MCP server for testing."""
    return MockMCPServer()

@pytest.mark.asyncio
async def test_end_to_end_with_mock_server(mock_server, mock_client_config):
    """Test end-to-end pipeline with mock server."""
    
    async def mock_call_tool(tool_name, payload=None):
        tool_func = mock_server.tools.get(tool_name)
        if tool_func:
            data = await tool_func(**(payload or {}))
            return ConversionResult(
                success=data.get("status") == "success",
                status=PipelineStatus.COMPLETED,
                data=data
            )
        else:
            return ConversionResult(
                success=False,
                status=PipelineStatus.ERROR,
                error=f"Tool not found: {tool_name}"
            )
    
    with patch.object(MCPClient, '_validate_server_connection'):
        client = MCPClient(mock_client_config)
        
        with patch.object(client, 'call_tool', side_effect=mock_call_tool):
            result = await client.run_full_pipeline(
                dataset_dir="/mock/dataset",
                files_map={"recording": "/mock/recording.dat"}
            )
            
            assert result.success is True
            assert result.data["nwb_path"] == "/mock/output.nwb"
            assert result.data["summary"]["nwb_file_created"] is True
```

This design provides a comprehensive client library and integration framework that makes the MCP server accessible to various types of users and workflows, with robust error handling, monitoring, and extensibility features.