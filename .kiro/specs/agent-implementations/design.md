# Agent Implementations Design

## Overview

This design document outlines the specialized agent modules that are
orchestrated by the MCP server to perform specific aspects of neuroscience data
conversion. The agents are designed as internal components of the MCP server,
each with distinct responsibilities: conversation agents provide dataset
analysis capabilities, conversion agents handle conversion orchestration,
evaluation agents coordinate validation processes, and metadata questioners
manage workflow handoff mechanisms through dynamic user interaction.

## Architecture

### High-Level Agent Architecture

```
Agent Implementations (Internal to MCP Server)
├── Base Agent Framework
│   ├── Abstract Agent Interface
│   ├── Common Error Handling
│   ├── Logging and Monitoring
│   └── Configuration Management
├── Conversation Agent
│   ├── Dataset Analysis Engine
│   ├── Format Detection System
│   ├── Metadata Extraction Logic
│   └── Domain Knowledge Integration
├── Conversion Agent
│   ├── NeuroConv Interface Manager
│   ├── Script Generation Engine
│   ├── Execution Environment
│   └── Provenance Tracking
├── Evaluation Agent
│   ├── Validation Coordinator
│   ├── Quality Assessment Manager
│   ├── Knowledge Graph Coordinator
│   └── Report Generation System
└── Metadata Questioner
    ├── Question Generation Engine
    ├── Response Validation System
    ├── Context Management
    └── Interactive Session Handler
```

### Agent Communication Flow

```
MCP Server Tool Call → Agent Selection → Agent Execution → Result Processing → Response
                           ↓
                    Agent Internal Flow:
                    Input Validation → Processing → External Service Calls → Result Assembly
                           ↓
                    Shared Services:
                    Configuration → Logging → Error Handling → Provenance Tracking
```

## Core Components

### 1. Base Agent Framework

#### Abstract Agent Interface

```python
# agentic_neurodata_conversion/agents/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging
import time
import uuid

class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class AgentResult:
    """Standardized agent result format."""
    status: AgentStatus
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    provenance: Dict[str, Any]
    execution_time: float
    agent_id: str
    error: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, config: 'AgentConfig', agent_type: str):
        self.config = config
        self.agent_type = agent_type
        self.agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"
        self.logger = logging.getLogger(f"agent.{agent_type}")
        self.status = AgentStatus.IDLE
        self.metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0.0
        }

    async def execute(self, **kwargs) -> AgentResult:
        """Execute agent with standardized error handling and metrics."""
        start_time = time.time()
        self.status = AgentStatus.PROCESSING

        try:
            # Validate inputs
            validated_inputs = await self._validate_inputs(**kwargs)

            # Execute agent-specific logic
            result_data = await self._execute_internal(**validated_inputs)

            # Process results
            processed_result = await self._process_results(result_data, **validated_inputs)

            # Create successful result
            execution_time = time.time() - start_time
            result = AgentResult(
                status=AgentStatus.COMPLETED,
                data=processed_result,
                metadata=self._generate_metadata(**validated_inputs),
                provenance=self._generate_provenance(**validated_inputs),
                execution_time=execution_time,
                agent_id=self.agent_id
            )

            # Update metrics
            self._update_metrics(execution_time, success=True)
            self.status = AgentStatus.COMPLETED

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Agent execution failed: {e}", exc_info=True)

            result = AgentResult(
                status=AgentStatus.ERROR,
                data={},
                metadata=self._generate_metadata(**kwargs),
                provenance=self._generate_provenance(**kwargs),
                execution_time=execution_time,
                agent_id=self.agent_id,
                error=str(e)
            )

            self._update_metrics(execution_time, success=False)
            self.status = AgentStatus.ERROR

            return result

    @abstractmethod
    async def _validate_inputs(self, **kwargs) -> Dict[str, Any]:
        """Validate and normalize inputs."""
        pass

    @abstractmethod
    async def _execute_internal(self, **kwargs) -> Dict[str, Any]:
        """Execute agent-specific logic."""
        pass

    async def _process_results(self, result_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Process and format results. Override if needed."""
        return result_data

    def _generate_metadata(self, **kwargs) -> Dict[str, Any]:
        """Generate execution metadata."""
        return {
            'agent_type': self.agent_type,
            'agent_id': self.agent_id,
            'timestamp': time.time(),
            'config_version': getattr(self.config, 'version', '1.0'),
            'inputs': {k: type(v).__name__ for k, v in kwargs.items()}
        }

    def _generate_provenance(self, **kwargs) -> Dict[str, Any]:
        """Generate provenance information."""
        return {
            'agent': self.agent_type,
            'agent_id': self.agent_id,
            'execution_timestamp': time.time(),
            'input_sources': self._identify_input_sources(**kwargs),
            'processing_steps': self._get_processing_steps(),
            'external_services': self._get_external_services_used()
        }

    def _identify_input_sources(self, **kwargs) -> Dict[str, str]:
        """Identify sources of input data."""
        return {k: 'user_provided' for k in kwargs.keys()}

    def _get_processing_steps(self) -> List[str]:
        """Get list of processing steps performed."""
        return [f"{self.agent_type}_processing"]

    def _get_external_services_used(self) -> List[str]:
        """Get list of external services used."""
        return []

    def _update_metrics(self, execution_time: float, success: bool):
        """Update agent performance metrics."""
        self.metrics['total_executions'] += 1
        if success:
            self.metrics['successful_executions'] += 1
        else:
            self.metrics['failed_executions'] += 1

        # Update average execution time
        total = self.metrics['total_executions']
        current_avg = self.metrics['average_execution_time']
        self.metrics['average_execution_time'] = (current_avg * (total - 1) + execution_time) / total

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        return {
            **self.metrics,
            'success_rate': (
                self.metrics['successful_executions'] / self.metrics['total_executions']
                if self.metrics['total_executions'] > 0 else 0.0
            ),
            'current_status': self.status.value
        }
```

### 2. Conversation Agent

#### Dataset Analysis and Metadata Extraction

```python
# agentic_neurodata_conversion/agents/conversation.py
from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
from .base import BaseAgent, AgentResult
from ..interfaces.format_detector import FormatDetector
from ..interfaces.llm_client import LLMClient
from ..core.domain_knowledge import DomainKnowledgeBase

class ConversationAgent(BaseAgent):
    """Agent for analyzing datasets and extracting metadata through conversation."""

    def __init__(self, config: 'AgentConfig'):
        super().__init__(config, "conversation")
        self.format_detector = FormatDetector()
        self.llm_client = LLMClient(config.llm_config) if config.use_llm else None
        self.domain_knowledge = DomainKnowledgeBase()
        self.session_state = {}

    async def _validate_inputs(self, **kwargs) -> Dict[str, Any]:
        """Validate conversation agent inputs."""
        dataset_dir = kwargs.get('dataset_dir')
        if not dataset_dir:
            raise ValueError("dataset_dir is required")

        dataset_path = Path(dataset_dir)
        if not dataset_path.exists():
            raise ValueError(f"Dataset directory does not exist: {dataset_dir}")

        return {
            'dataset_dir': str(dataset_path.absolute()),
            'use_llm': kwargs.get('use_llm', False),
            'session_id': kwargs.get('session_id', 'default'),
            'existing_metadata': kwargs.get('existing_metadata', {})
        }

    async def _execute_internal(self, **kwargs) -> Dict[str, Any]:
        """Execute dataset analysis and metadata extraction."""
        dataset_dir = kwargs['dataset_dir']
        use_llm = kwargs['use_llm']
        session_id = kwargs['session_id']
        existing_metadata = kwargs['existing_metadata']

        # Step 1: Detect data formats
        self.logger.info(f"Analyzing dataset structure: {dataset_dir}")
        format_analysis = await self.format_detector.analyze_directory(dataset_dir)

        # Step 2: Extract basic metadata from files
        basic_metadata = await self._extract_basic_metadata(dataset_dir, format_analysis)

        # Step 3: Apply domain knowledge
        enriched_metadata = await self._apply_domain_knowledge(basic_metadata, format_analysis)

        # Step 4: Identify missing critical metadata
        missing_metadata = await self._identify_missing_metadata(enriched_metadata, format_analysis)

        # Step 5: Generate questions for missing metadata (if LLM available)
        questions = []
        if use_llm and missing_metadata and self.llm_client:
            questions = await self._generate_questions(missing_metadata, enriched_metadata, format_analysis)

        return {
            'format_analysis': format_analysis,
            'basic_metadata': basic_metadata,
            'enriched_metadata': enriched_metadata,
            'missing_metadata': missing_metadata,
            'questions': questions,
            'session_id': session_id,
            'requires_user_input': len(missing_metadata) > 0
        }

    async def _extract_basic_metadata(self, dataset_dir: str, format_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic metadata from files and directory structure."""
        metadata = {
            'dataset_path': dataset_dir,
            'detected_formats': format_analysis.get('formats', []),
            'file_count': format_analysis.get('file_count', 0),
            'total_size': format_analysis.get('total_size', 0),
            'directory_structure': format_analysis.get('structure', {}),
            'timestamps': {
                'earliest_file': format_analysis.get('earliest_timestamp'),
                'latest_file': format_analysis.get('latest_timestamp')
            }
        }

        # Extract metadata from specific file types
        for format_info in format_analysis.get('formats', []):
            format_name = format_info['format']
            if format_name == 'open_ephys':
                metadata.update(await self._extract_open_ephys_metadata(format_info))
            elif format_name == 'spikeglx':
                metadata.update(await self._extract_spikeglx_metadata(format_info))
            # Add other format-specific extractors

        return metadata

    async def _apply_domain_knowledge(self, basic_metadata: Dict[str, Any], format_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Apply domain knowledge to enrich metadata."""
        enriched = basic_metadata.copy()

        # Infer experimental type from formats and file patterns
        experimental_type = self.domain_knowledge.infer_experimental_type(
            formats=basic_metadata.get('detected_formats', []),
            file_patterns=format_analysis.get('file_patterns', [])
        )
        if experimental_type:
            enriched['experimental_type'] = experimental_type

        # Infer species from directory names or file patterns
        species = self.domain_knowledge.infer_species(
            directory_path=basic_metadata['dataset_path'],
            file_patterns=format_analysis.get('file_patterns', [])
        )
        if species:
            enriched['species'] = species

        # Infer recording device from format
        device_info = self.domain_knowledge.infer_device_from_format(
            formats=basic_metadata.get('detected_formats', [])
        )
        if device_info:
            enriched['device'] = device_info

        return enriched

    async def _identify_missing_metadata(self, metadata: Dict[str, Any], format_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical metadata that is missing."""
        missing = []

        # Required NWB fields
        required_fields = {
            'session_description': 'A description of the experimental session',
            'identifier': 'A unique identifier for this dataset',
            'session_start_time': 'The start time of the recording session',
            'experimenter': 'The person(s) who performed the experiment',
            'lab': 'The laboratory where the experiment was conducted',
            'institution': 'The institution where the experiment was conducted'
        }

        for field, description in required_fields.items():
            if field not in metadata or not metadata[field]:
                missing.append({
                    'field': field,
                    'description': description,
                    'required': True,
                    'category': 'session_info'
                })

        # Subject information
        if 'subject' not in metadata:
            missing.extend([
                {
                    'field': 'subject_id',
                    'description': 'A unique identifier for the experimental subject',
                    'required': True,
                    'category': 'subject'
                },
                {
                    'field': 'age',
                    'description': 'Age of the subject at time of experiment',
                    'required': False,
                    'category': 'subject'
                },
                {
                    'field': 'sex',
                    'description': 'Sex of the subject (M/F/U)',
                    'required': False,
                    'category': 'subject'
                }
            ])

        # Format-specific missing metadata
        for format_info in format_analysis.get('formats', []):
            format_missing = self._get_format_specific_missing_metadata(format_info, metadata)
            missing.extend(format_missing)

        return missing

    async def _generate_questions(self, missing_metadata: List[Dict[str, Any]],
                                 current_metadata: Dict[str, Any],
                                 format_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate natural language questions for missing metadata."""
        if not self.llm_client:
            return []

        # Group missing metadata by category
        categories = {}
        for item in missing_metadata:
            category = item.get('category', 'general')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)

        questions = []

        for category, items in categories.items():
            # Generate contextual questions for each category
            context = {
                'detected_formats': current_metadata.get('detected_formats', []),
                'experimental_type': current_metadata.get('experimental_type'),
                'category': category,
                'missing_fields': items
            }

            category_questions = await self._generate_category_questions(context)
            questions.extend(category_questions)

        return questions

    async def _generate_category_questions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate questions for a specific category of missing metadata."""
        prompt = self._build_question_prompt(context)

        try:
            response = await self.llm_client.generate_completion(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )

            # Parse response into structured questions
            questions = self._parse_question_response(response, context)
            return questions

        except Exception as e:
            self.logger.error(f"Failed to generate questions: {e}")
            # Fallback to template-based questions
            return self._generate_template_questions(context)

    def _build_question_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for question generation."""
        return f\"\"\"
You are helping a neuroscience researcher provide metadata for their dataset conversion to NWB format.

Dataset Context:
- Detected formats: {context['detected_formats']}
- Experimental type: {context.get('experimental_type', 'unknown')}
- Category: {context['category']}

Missing Information:
{chr(10).join([f"- {item['field']}: {item['description']}" for item in context['missing_fields']])}

Generate clear, concise questions that a researcher can easily answer. Focus on the most critical missing information first.
Provide context for why each piece of information is needed.

Format your response as a JSON list of questions with this structure:
[
  {{
    "field": "field_name",
    "question": "Clear question text",
    "explanation": "Why this information is needed",
    "priority": "high|medium|low"
  }}
]
\"\"\"

    def _parse_question_response(self, response: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse LLM response into structured questions."""
        try:
            import json
            questions = json.loads(response)

            # Validate and enhance questions
            validated_questions = []
            for q in questions:
                if all(key in q for key in ['field', 'question', 'explanation']):
                    q['category'] = context['category']
                    validated_questions.append(q)

            return validated_questions

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse question response: {e}")
            return self._generate_template_questions(context)

    def _generate_template_questions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate template-based questions as fallback."""
        questions = []

        for item in context['missing_fields']:
            question = {
                'field': item['field'],
                'question': f"What is the {item['field'].replace('_', ' ')} for this experiment?",
                'explanation': item['description'],
                'priority': 'high' if item.get('required', False) else 'medium',
                'category': context['category']
            }
            questions.append(question)

        return questions

    def _get_processing_steps(self) -> List[str]:
        """Get processing steps for provenance."""
        return [
            'format_detection',
            'basic_metadata_extraction',
            'domain_knowledge_application',
            'missing_metadata_identification',
            'question_generation'
        ]

    def _get_external_services_used(self) -> List[str]:
        """Get external services used."""
        services = []
        if self.llm_client:
            services.append('llm_service')
        return services

    async def _extract_open_ephys_metadata(self, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Open Ephys specific metadata."""
        # Implementation for Open Ephys metadata extraction
        return {
            'recording_system': 'Open Ephys',
            'sampling_rate': format_info.get('sampling_rate'),
            'channel_count': format_info.get('channel_count')
        }

    async def _extract_spikeglx_metadata(self, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract SpikeGLX specific metadata."""
        # Implementation for SpikeGLX metadata extraction
        return {
            'recording_system': 'SpikeGLX',
            'probe_type': format_info.get('probe_type'),
            'sampling_rate': format_info.get('sampling_rate')
        }
```

### 3. Conversion Agent

#### NeuroConv Script Generation and Execution

```python
# agentic_neurodata_conversion/agents/conversion.py
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile
import subprocess
import sys
from .base import BaseAgent, AgentResult
from ..interfaces.neuroconv_wrapper import NeuroConvWrapper
from ..core.script_templates import ScriptTemplateManager

class ConversionAgent(BaseAgent):
    """Agent for generating and executing NeuroConv conversion scripts."""

    def __init__(self, config: 'AgentConfig'):
        super().__init__(config, "conversion")
        self.neuroconv_wrapper = NeuroConvWrapper()
        self.script_templates = ScriptTemplateManager()
        self.execution_timeout = config.conversion_timeout

    async def _validate_inputs(self, **kwargs) -> Dict[str, Any]:
        """Validate conversion agent inputs."""
        normalized_metadata = kwargs.get('normalized_metadata')
        files_map = kwargs.get('files_map')

        if not normalized_metadata:
            raise ValueError("normalized_metadata is required")
        if not files_map:
            raise ValueError("files_map is required")

        # Validate file paths exist
        for file_type, file_path in files_map.items():
            if not Path(file_path).exists():
                raise ValueError(f"File not found: {file_path} (type: {file_type})")

        return {
            'normalized_metadata': normalized_metadata,
            'files_map': files_map,
            'output_nwb_path': kwargs.get('output_nwb_path'),
            'dry_run': kwargs.get('dry_run', False)
        }

    async def _execute_internal(self, **kwargs) -> Dict[str, Any]:
        """Execute conversion script generation and execution."""
        normalized_metadata = kwargs['normalized_metadata']
        files_map = kwargs['files_map']
        output_nwb_path = kwargs['output_nwb_path']
        dry_run = kwargs['dry_run']

        # Step 1: Select appropriate DataInterface classes
        self.logger.info("Selecting NeuroConv DataInterface classes")
        interface_selection = await self._select_data_interfaces(files_map, normalized_metadata)

        # Step 2: Generate conversion script
        self.logger.info("Generating conversion script")
        script_content = await self._generate_conversion_script(
            interface_selection, normalized_metadata, files_map, output_nwb_path
        )

        # Step 3: Validate script syntax
        await self._validate_script_syntax(script_content)

        if dry_run:
            return {
                'script_content': script_content,
                'interface_selection': interface_selection,
                'dry_run': True,
                'validation': 'passed'
            }

        # Step 4: Execute conversion script
        self.logger.info("Executing conversion script")
        execution_result = await self._execute_conversion_script(script_content, output_nwb_path)

        # Step 5: Validate output
        if execution_result['success'] and execution_result.get('nwb_path'):
            validation_result = await self._validate_nwb_output(execution_result['nwb_path'])
            execution_result['output_validation'] = validation_result

        return {
            'script_content': script_content,
            'interface_selection': interface_selection,
            'execution_result': execution_result,
            'nwb_path': execution_result.get('nwb_path'),
            'success': execution_result['success']
        }

    async def _select_data_interfaces(self, files_map: Dict[str, str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate NeuroConv DataInterface classes."""
        interface_selection = {}

        for file_type, file_path in files_map.items():
            # Detect format if not specified
            detected_format = await self._detect_file_format(file_path, file_type)

            # Map format to NeuroConv interface
            interface_class = self.neuroconv_wrapper.get_interface_for_format(detected_format)

            if interface_class:
                interface_selection[file_type] = {
                    'interface_class': interface_class,
                    'detected_format': detected_format,
                    'file_path': file_path,
                    'interface_kwargs': self._get_interface_kwargs(detected_format, file_path, metadata)
                }
            else:
                self.logger.warning(f"No interface found for format: {detected_format}")

        return interface_selection

    async def _generate_conversion_script(self, interface_selection: Dict[str, Any],
                                        metadata: Dict[str, Any],
                                        files_map: Dict[str, str],
                                        output_nwb_path: Optional[str]) -> str:
        """Generate Python conversion script."""

        # Determine output path
        if not output_nwb_path:
            dataset_name = metadata.get('identifier', 'converted_data')
            output_nwb_path = f"{dataset_name}.nwb"

        # Build script context
        script_context = {
            'interfaces': interface_selection,
            'metadata': metadata,
            'files_map': files_map,
            'output_path': output_nwb_path,
            'timestamp': time.time()
        }

        # Generate script from template
        script_content = self.script_templates.generate_conversion_script(script_context)

        return script_content

    async def _validate_script_syntax(self, script_content: str):
        """Validate Python script syntax."""
        try:
            compile(script_content, '<conversion_script>', 'exec')
        except SyntaxError as e:
            raise ValueError(f"Generated script has syntax error: {e}")

    async def _execute_conversion_script(self, script_content: str, output_nwb_path: str) -> Dict[str, Any]:
        """Execute the conversion script in a controlled environment."""

        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
            temp_script.write(script_content)
            temp_script_path = temp_script.name

        try:
            # Execute script with timeout
            process = await asyncio.create_subprocess_exec(
                sys.executable, temp_script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.execution_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise RuntimeError(f"Conversion script timed out after {self.execution_timeout} seconds")

            # Check execution result
            if process.returncode == 0:
                return {
                    'success': True,
                    'nwb_path': output_nwb_path,
                    'stdout': stdout.decode(),
                    'stderr': stderr.decode(),
                    'return_code': process.returncode
                }
            else:
                return {
                    'success': False,
                    'error': stderr.decode(),
                    'stdout': stdout.decode(),
                    'return_code': process.returncode
                }

        finally:
            # Clean up temporary script
            Path(temp_script_path).unlink(missing_ok=True)

    async def _validate_nwb_output(self, nwb_path: str) -> Dict[str, Any]:
        """Validate the generated NWB file."""
        try:
            # Basic file existence check
            nwb_file = Path(nwb_path)
            if not nwb_file.exists():
                return {'valid': False, 'error': 'NWB file was not created'}

            # Try to open with pynwb
            import pynwb
            with pynwb.NWBHDF5IO(nwb_path, 'r') as io:
                nwbfile = io.read()

                # Basic validation checks
                validation_results = {
                    'valid': True,
                    'file_size': nwb_file.stat().st_size,
                    'has_identifier': bool(nwbfile.identifier),
                    'has_session_description': bool(nwbfile.session_description),
                    'has_session_start_time': bool(nwbfile.session_start_time),
                    'object_count': len(nwbfile.objects),
                    'acquisition_count': len(nwbfile.acquisition),
                    'processing_modules': list(nwbfile.processing.keys()) if nwbfile.processing else []
                }

                return validation_results

        except Exception as e:
            return {
                'valid': False,
                'error': f"NWB validation failed: {str(e)}"
            }

    def _get_processing_steps(self) -> List[str]:
        """Get processing steps for provenance."""
        return [
            'interface_selection',
            'script_generation',
            'syntax_validation',
            'script_execution',
            'output_validation'
        ]

    def _get_external_services_used(self) -> List[str]:
        """Get external services used."""
        return ['neuroconv', 'pynwb']

    async def _detect_file_format(self, file_path: str, file_type: str) -> str:
        """Detect file format from path and type."""
        # Implementation would use format detection logic
        # This is a simplified version
        path = Path(file_path)

        if 'open_ephys' in str(path).lower():
            return 'open_ephys'
        elif path.suffix == '.bin' and 'spikeglx' in str(path).lower():
            return 'spikeglx'
        elif path.suffix == '.ncs':
            return 'neuralynx'
        else:
            return 'unknown'

    def _get_interface_kwargs(self, format_name: str, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Get interface-specific keyword arguments."""
        kwargs = {'file_path': file_path}

        if format_name == 'open_ephys':
            kwargs.update({
                'folder_path': str(Path(file_path).parent),
                'stream_name': metadata.get('stream_name', 'Record Node')
            })
        elif format_name == 'spikeglx':
            kwargs.update({
                'file_path': file_path,
                'stream_name': metadata.get('stream_name', 'imec0.ap')
            })

        return kwargs
```

### 4. Evaluation Agent

#### Validation and Quality Assessment Coordination

```python
# agentic_neurodata_conversion/agents/evaluation.py
from typing import Dict, Any, List, Optional
from pathlib import Path
from .base import BaseAgent, AgentResult

class EvaluationAgent(BaseAgent):
    """Agent for coordinating validation and quality assessment processes."""

    def __init__(self, config: 'AgentConfig'):
        super().__init__(config, "evaluation")
        self.validation_systems = self._initialize_validation_systems()
        self.quality_assessors = self._initialize_quality_assessors()
        self.report_generators = self._initialize_report_generators()

    def _initialize_validation_systems(self) -> Dict[str, Any]:
        """Initialize validation system interfaces."""
        from ..interfaces.nwb_inspector import NWBInspectorInterface
        from ..interfaces.linkml_validator import LinkMLValidatorInterface

        return {
            'nwb_inspector': NWBInspectorInterface(),
            'linkml_validator': LinkMLValidatorInterface(),
            'schema_validator': self._create_schema_validator()
        }

    def _initialize_quality_assessors(self) -> Dict[str, Any]:
        """Initialize quality assessment interfaces."""
        return {
            'metadata_completeness': self._create_metadata_assessor(),
            'data_integrity': self._create_data_integrity_assessor(),
            'best_practices': self._create_best_practices_assessor()
        }

    def _initialize_report_generators(self) -> Dict[str, Any]:
        """Initialize report generation systems."""
        return {
            'html_reporter': self._create_html_reporter(),
            'json_reporter': self._create_json_reporter(),
            'visualization_generator': self._create_visualization_generator()
        }

    async def _validate_inputs(self, **kwargs) -> Dict[str, Any]:
        """Validate evaluation agent inputs."""
        nwb_path = kwargs.get('nwb_path')
        if not nwb_path:
            raise ValueError("nwb_path is required")

        nwb_file = Path(nwb_path)
        if not nwb_file.exists():
            raise ValueError(f"NWB file not found: {nwb_path}")

        return {
            'nwb_path': str(nwb_file.absolute()),
            'generate_report': kwargs.get('generate_report', True),
            'include_visualizations': kwargs.get('include_visualizations', True),
            'output_dir': kwargs.get('output_dir', 'evaluation_outputs'),
            'validation_level': kwargs.get('validation_level', 'comprehensive')
        }

    async def _execute_internal(self, **kwargs) -> Dict[str, Any]:
        """Execute comprehensive evaluation process."""
        nwb_path = kwargs['nwb_path']
        generate_report = kwargs['generate_report']
        include_visualizations = kwargs['include_visualizations']
        output_dir = kwargs['output_dir']
        validation_level = kwargs['validation_level']

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        evaluation_results = {}

        # Step 1: Run validation systems
        self.logger.info("Running validation systems")
        validation_results = await self._run_validation_systems(nwb_path, validation_level)
        evaluation_results['validation'] = validation_results

        # Step 2: Run quality assessments
        self.logger.info("Running quality assessments")
        quality_results = await self._run_quality_assessments(nwb_path, validation_results)
        evaluation_results['quality_assessment'] = quality_results

        # Step 3: Generate knowledge graph (if requested)
        if kwargs.get('generate_knowledge_graph', True):
            self.logger.info("Generating knowledge graph")
            kg_results = await self._generate_knowledge_graph(nwb_path, output_path)
            evaluation_results['knowledge_graph'] = kg_results

        # Step 4: Generate reports and visualizations
        if generate_report:
            self.logger.info("Generating evaluation reports")
            report_results = await self._generate_reports(
                evaluation_results, output_path, include_visualizations
            )
            evaluation_results['reports'] = report_results

        # Step 5: Calculate overall quality score
        overall_score = self._calculate_overall_quality_score(evaluation_results)
        evaluation_results['overall_quality_score'] = overall_score

        return evaluation_results

    async def _run_validation_systems(self, nwb_path: str, validation_level: str) -> Dict[str, Any]:
        """Run all validation systems."""
        validation_results = {}

        # NWB Inspector validation
        try:
            nwb_inspector_result = await self.validation_systems['nwb_inspector'].validate(
                nwb_path, level=validation_level
            )
            validation_results['nwb_inspector'] = nwb_inspector_result
        except Exception as e:
            self.logger.error(f"NWB Inspector validation failed: {e}")
            validation_results['nwb_inspector'] = {'error': str(e), 'status': 'failed'}

        # LinkML validation
        try:
            linkml_result = await self.validation_systems['linkml_validator'].validate(nwb_path)
            validation_results['linkml'] = linkml_result
        except Exception as e:
            self.logger.error(f"LinkML validation failed: {e}")
            validation_results['linkml'] = {'error': str(e), 'status': 'failed'}

        # Schema validation
        try:
            schema_result = await self.validation_systems['schema_validator'].validate(nwb_path)
            validation_results['schema'] = schema_result
        except Exception as e:
            self.logger.error(f"Schema validation failed: {e}")
            validation_results['schema'] = {'error': str(e), 'status': 'failed'}

        return validation_results

    async def _run_quality_assessments(self, nwb_path: str, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Run quality assessment systems."""
        quality_results = {}

        # Metadata completeness assessment
        metadata_assessment = await self.quality_assessors['metadata_completeness'].assess(
            nwb_path, validation_results
        )
        quality_results['metadata_completeness'] = metadata_assessment

        # Data integrity assessment
        integrity_assessment = await self.quality_assessors['data_integrity'].assess(
            nwb_path, validation_results
        )
        quality_results['data_integrity'] = integrity_assessment

        # Best practices assessment
        best_practices_assessment = await self.quality_assessors['best_practices'].assess(
            nwb_path, validation_results
        )
        quality_results['best_practices'] = best_practices_assessment

        return quality_results

    async def _generate_knowledge_graph(self, nwb_path: str, output_path: Path) -> Dict[str, Any]:
        """Generate knowledge graph from NWB file."""
        try:
            from ..interfaces.knowledge_graph_generator import KnowledgeGraphGenerator

            kg_generator = KnowledgeGraphGenerator()
            kg_result = await kg_generator.generate_from_nwb(
                nwb_path=nwb_path,
                output_dir=str(output_path)
            )

            return kg_result

        except Exception as e:
            self.logger.error(f"Knowledge graph generation failed: {e}")
            return {'error': str(e), 'status': 'failed'}

    async def _generate_reports(self, evaluation_results: Dict[str, Any],
                              output_path: Path, include_visualizations: bool) -> Dict[str, Any]:
        """Generate evaluation reports."""
        report_results = {}

        # Generate HTML report
        try:
            html_report_path = output_path / "evaluation_report.html"
            await self.report_generators['html_reporter'].generate(
                evaluation_results, html_report_path, include_visualizations
            )
            report_results['html_report'] = str(html_report_path)
        except Exception as e:
            self.logger.error(f"HTML report generation failed: {e}")
            report_results['html_report'] = {'error': str(e)}

        # Generate JSON report
        try:
            json_report_path = output_path / "evaluation_report.json"
            await self.report_generators['json_reporter'].generate(
                evaluation_results, json_report_path
            )
            report_results['json_report'] = str(json_report_path)
        except Exception as e:
            self.logger.error(f"JSON report generation failed: {e}")
            report_results['json_report'] = {'error': str(e)}

        # Generate visualizations
        if include_visualizations:
            try:
                viz_results = await self.report_generators['visualization_generator'].generate(
                    evaluation_results, output_path / "visualizations"
                )
                report_results['visualizations'] = viz_results
            except Exception as e:
                self.logger.error(f"Visualization generation failed: {e}")
                report_results['visualizations'] = {'error': str(e)}

        return report_results

    def _calculate_overall_quality_score(self, evaluation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall quality score from evaluation results."""
        scores = {}
        weights = {
            'validation': 0.4,
            'quality_assessment': 0.4,
            'knowledge_graph': 0.2
        }

        # Calculate validation score
        validation_results = evaluation_results.get('validation', {})
        validation_score = self._calculate_validation_score(validation_results)
        scores['validation'] = validation_score

        # Calculate quality assessment score
        quality_results = evaluation_results.get('quality_assessment', {})
        quality_score = self._calculate_quality_score(quality_results)
        scores['quality_assessment'] = quality_score

        # Calculate knowledge graph score
        kg_results = evaluation_results.get('knowledge_graph', {})
        kg_score = self._calculate_kg_score(kg_results)
        scores['knowledge_graph'] = kg_score

        # Calculate weighted overall score
        overall_score = sum(scores[key] * weights[key] for key in scores.keys())

        return {
            'overall_score': overall_score,
            'component_scores': scores,
            'weights': weights,
            'grade': self._score_to_grade(overall_score)
        }

    def _calculate_validation_score(self, validation_results: Dict[str, Any]) -> float:
        """Calculate validation score from validation results."""
        # Implementation would analyze validation results and return score 0-1
        # This is a simplified version
        total_issues = 0
        critical_issues = 0

        for validator, results in validation_results.items():
            if isinstance(results, dict) and 'issues' in results:
                issues = results['issues']
                total_issues += len(issues)
                critical_issues += len([i for i in issues if i.get('severity') == 'critical'])

        if total_issues == 0:
            return 1.0
        elif critical_issues > 0:
            return max(0.0, 0.5 - (critical_issues * 0.1))
        else:
            return max(0.5, 1.0 - (total_issues * 0.05))

    def _calculate_quality_score(self, quality_results: Dict[str, Any]) -> float:
        """Calculate quality score from quality assessment results."""
        # Implementation would analyze quality results
        return 0.8  # Placeholder

    def _calculate_kg_score(self, kg_results: Dict[str, Any]) -> float:
        """Calculate knowledge graph score."""
        if kg_results.get('status') == 'failed':
            return 0.0
        return 1.0 if kg_results.get('entities_count', 0) > 0 else 0.5

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 0.9:
            return 'A'
        elif score >= 0.8:
            return 'B'
        elif score >= 0.7:
            return 'C'
        elif score >= 0.6:
            return 'D'
        else:
            return 'F'

    def _get_processing_steps(self) -> List[str]:
        """Get processing steps for provenance."""
        return [
            'validation_systems_execution',
            'quality_assessment',
            'knowledge_graph_generation',
            'report_generation',
            'score_calculation'
        ]

    def _get_external_services_used(self) -> List[str]:
        """Get external services used."""
        return ['nwb_inspector', 'linkml_validator', 'knowledge_graph_generator']

    # Helper methods for creating system components
    def _create_schema_validator(self):
        """Create schema validator."""
        # Implementation would create schema validator
        pass

    def _create_metadata_assessor(self):
        """Create metadata completeness assessor."""
        # Implementation would create metadata assessor
        pass

    def _create_data_integrity_assessor(self):
        """Create data integrity assessor."""
        # Implementation would create data integrity assessor
        pass

    def _create_best_practices_assessor(self):
        """Create best practices assessor."""
        # Implementation would create best practices assessor
        pass

    def _create_html_reporter(self):
        """Create HTML report generator."""
        # Implementation would create HTML reporter
        pass

    def _create_json_reporter(self):
        """Create JSON report generator."""
        # Implementation would create JSON reporter
        pass

    def _create_visualization_generator(self):
        """Create visualization generator."""
        # Implementation would create visualization generator
        pass
```

### 5. Testing and Mock Support

#### Agent Testing Framework

```python
# tests/unit/test_agents.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.agentic_converter.agents.conversation import ConversationAgent
from src.agentic_converter.agents.conversion import ConversionAgent
from src.agentic_converter.agents.evaluation import EvaluationAgent
from src.agentic_converter.core.config import AgentConfig

@pytest.fixture
def mock_agent_config():
    """Mock agent configuration."""
    config = Mock(spec=AgentConfig)
    config.use_llm = False
    config.conversion_timeout = 300
    config.llm_config = Mock()
    return config

class TestConversationAgent:
    """Test conversation agent functionality."""

    @pytest.fixture
    def conversation_agent(self, mock_agent_config):
        """Conversation agent instance for testing."""
        return ConversationAgent(mock_agent_config)

    @pytest.mark.asyncio
    async def test_dataset_analysis_without_llm(self, conversation_agent, tmp_path):
        """Test dataset analysis without LLM."""
        # Create test dataset structure
        test_dataset = tmp_path / "test_dataset"
        test_dataset.mkdir()
        (test_dataset / "recording.dat").touch()

        # Mock format detector
        with patch.object(conversation_agent.format_detector, 'analyze_directory') as mock_analyze:
            mock_analyze.return_value = {
                'formats': [{'format': 'open_ephys', 'confidence': 0.9}],
                'file_count': 1,
                'total_size': 1024
            }

            result = await conversation_agent.execute(
                dataset_dir=str(test_dataset),
                use_llm=False
            )

            assert result.status.value == 'completed'
            assert 'format_analysis' in result.data
            assert 'enriched_metadata' in result.data

    @pytest.mark.asyncio
    async def test_question_generation_with_llm(self, conversation_agent, tmp_path):
        """Test question generation with LLM."""
        conversation_agent.config.use_llm = True
        conversation_agent.llm_client = AsyncMock()
        conversation_agent.llm_client.generate_completion.return_value = '''
        [
            {
                "field": "experimenter",
                "question": "Who performed this experiment?",
                "explanation": "Required for NWB metadata",
                "priority": "high"
            }
        ]
        '''

        test_dataset = tmp_path / "test_dataset"
        test_dataset.mkdir()
        (test_dataset / "recording.dat").touch()

        with patch.object(conversation_agent.format_detector, 'analyze_directory') as mock_analyze:
            mock_analyze.return_value = {
                'formats': [{'format': 'open_ephys'}],
                'file_count': 1
            }

            result = await conversation_agent.execute(
                dataset_dir=str(test_dataset),
                use_llm=True
            )

            assert result.status.value == 'completed'
            assert len(result.data['questions']) > 0
            assert result.data['questions'][0]['field'] == 'experimenter'

class TestConversionAgent:
    """Test conversion agent functionality."""

    @pytest.fixture
    def conversion_agent(self, mock_agent_config):
        """Conversion agent instance for testing."""
        return ConversionAgent(mock_agent_config)

    @pytest.mark.asyncio
    async def test_dry_run_conversion(self, conversion_agent, tmp_path):
        """Test dry run conversion without execution."""
        # Create test files
        test_file = tmp_path / "test_recording.dat"
        test_file.touch()

        normalized_metadata = {
            'identifier': 'test_session',
            'session_description': 'Test session',
            'experimenter': 'Test User'
        }

        files_map = {
            'recording': str(test_file)
        }

        with patch.object(conversion_agent, '_select_data_interfaces') as mock_select:
            mock_select.return_value = {
                'recording': {
                    'interface_class': 'OpenEphysRecordingInterface',
                    'detected_format': 'open_ephys'
                }
            }

            result = await conversion_agent.execute(
                normalized_metadata=normalized_metadata,
                files_map=files_map,
                dry_run=True
            )

            assert result.status.value == 'completed'
            assert result.data['dry_run'] is True
            assert 'script_content' in result.data
            assert result.data['validation'] == 'passed'

class TestEvaluationAgent:
    """Test evaluation agent functionality."""

    @pytest.fixture
    def evaluation_agent(self, mock_agent_config):
        """Evaluation agent instance for testing."""
        return EvaluationAgent(mock_agent_config)

    @pytest.mark.asyncio
    async def test_nwb_evaluation(self, evaluation_agent, tmp_path):
        """Test NWB file evaluation."""
        # Create mock NWB file
        test_nwb = tmp_path / "test.nwb"
        test_nwb.touch()

        # Mock validation systems
        with patch.object(evaluation_agent, '_run_validation_systems') as mock_validation:
            mock_validation.return_value = {
                'nwb_inspector': {'status': 'passed', 'issues': []},
                'linkml': {'status': 'passed', 'errors': []}
            }

            with patch.object(evaluation_agent, '_run_quality_assessments') as mock_quality:
                mock_quality.return_value = {
                    'metadata_completeness': {'score': 0.9},
                    'data_integrity': {'score': 0.95}
                }

                result = await evaluation_agent.execute(
                    nwb_path=str(test_nwb),
                    generate_report=False
                )

                assert result.status.value == 'completed'
                assert 'validation' in result.data
                assert 'quality_assessment' in result.data
                assert 'overall_quality_score' in result.data
```

This design provides a comprehensive framework for agent implementations that
are orchestrated by the MCP server, with clear interfaces, error handling,
provenance tracking, and testing support.
