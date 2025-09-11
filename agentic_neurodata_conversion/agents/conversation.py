"""
Conversation agent for dataset analysis and metadata extraction.

This agent handles interactive analysis of datasets, extracting metadata,
detecting formats, and generating questions for missing information.
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseAgent, AgentStatus, AgentConfig
from ..interfaces.format_detector import FormatDetector
from ..interfaces.llm_client import LLMClient
from ..core.domain_knowledge import DomainKnowledgeBase

logger = logging.getLogger(__name__)


class ConversationAgent(BaseAgent):
    """Agent for analyzing datasets and extracting metadata through conversation."""
    
    def __init__(self, config: AgentConfig):
        """Initialize the conversation agent."""
        super().__init__(config, "conversation")
        self.format_detector = FormatDetector()
        self.llm_client = LLMClient(config.llm_config) if config.use_llm else None
        self.domain_knowledge = DomainKnowledgeBase()
        self.session_state = {}
        
        logger.info(f"ConversationAgent {self.agent_id} initialized")
    
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
            # Add other format-specific extractors as needed
        
        return metadata
    
    async def _apply_domain_knowledge(self, basic_metadata: Dict[str, Any], format_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Apply domain knowledge to enrich metadata."""
        enriched = basic_metadata.copy()
        
        # Infer experimental type from formats and file patterns
        detected_format_names = [f['format'] for f in basic_metadata.get('detected_formats', [])]
        experimental_type = self.domain_knowledge.infer_experimental_type(
            formats=detected_format_names,
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
            formats=detected_format_names
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
                'detected_formats': [f['format'] for f in current_metadata.get('detected_formats', [])],
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
        return f"""
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
"""
    
    def _parse_question_response(self, response: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse LLM response into structured questions."""
        try:
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
    
    def _get_format_specific_missing_metadata(self, format_info: Dict[str, Any], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get format-specific missing metadata."""
        missing = []
        format_name = format_info['format']
        
        if format_name in ['open_ephys', 'spikeglx', 'neuralynx', 'blackrock', 'intan']:
            # Electrophysiology-specific metadata
            if 'sampling_rate' not in metadata:
                missing.append({
                    'field': 'sampling_rate',
                    'description': 'The sampling rate of the recording in Hz',
                    'required': True,
                    'category': 'recording'
                })
            
            if 'channel_count' not in metadata:
                missing.append({
                    'field': 'channel_count',
                    'description': 'Number of recording channels',
                    'required': True,
                    'category': 'recording'
                })
        
        return missing
    
    async def _extract_open_ephys_metadata(self, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Open Ephys specific metadata."""
        return {
            'recording_system': 'Open Ephys',
            'format_confidence': format_info.get('confidence', 0.0)
        }
    
    async def _extract_spikeglx_metadata(self, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract SpikeGLX specific metadata."""
        return {
            'recording_system': 'SpikeGLX',
            'format_confidence': format_info.get('confidence', 0.0)
        }
    
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
    
    async def process_user_responses(self, responses: Dict[str, Any], 
                                   session_id: str = 'default') -> Dict[str, Any]:
        """
        Process user responses to questions and validate them.
        
        Args:
            responses: Dictionary mapping field names to user responses
            session_id: Session identifier for tracking
            
        Returns:
            Dictionary containing processed and validated responses
        """
        processed_responses = {}
        validation_errors = []
        warnings = []
        
        for field, response in responses.items():
            try:
                # Validate and process the response
                validated_response = await self._validate_response(field, response)
                processed_responses[field] = validated_response
                
            except ValueError as e:
                validation_errors.append({
                    'field': field,
                    'error': str(e),
                    'original_response': response
                })
        
        # Apply domain knowledge validation
        domain_warnings = await self._validate_responses_with_domain_knowledge(processed_responses)
        warnings.extend(domain_warnings)
        
        return {
            'processed_responses': processed_responses,
            'validation_errors': validation_errors,
            'warnings': warnings,
            'session_id': session_id,
            'provenance': {
                'source': 'user_provided',
                'timestamp': time.time(),
                'validation_method': 'conversation_agent'
            }
        }
    
    async def _validate_response(self, field: str, response: Any) -> Any:
        """
        Validate a single user response.
        
        Args:
            field: The metadata field name
            response: The user's response
            
        Returns:
            Validated and potentially transformed response
            
        Raises:
            ValueError: If the response is invalid
        """
        if response is None or (isinstance(response, str) and not response.strip()):
            raise ValueError(f"Response for {field} cannot be empty")
        
        # Field-specific validation
        if field == 'session_start_time':
            return self._validate_datetime(response)
        elif field == 'age':
            return self._validate_age(response)
        elif field == 'sex':
            return self._validate_sex(response)
        elif field == 'sampling_rate':
            return self._validate_sampling_rate(response)
        elif field == 'channel_count':
            return self._validate_channel_count(response)
        else:
            # Default validation - ensure it's a non-empty string
            return str(response).strip()
    
    def _validate_datetime(self, response: Any) -> str:
        """Validate datetime response."""
        import datetime
        
        if isinstance(response, str):
            # Try to parse common datetime formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%m/%d/%Y %H:%M:%S',
                '%m/%d/%Y',
                '%Y-%m-%dT%H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.datetime.strptime(response, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            raise ValueError(f"Invalid datetime format: {response}")
        
        return str(response)
    
    def _validate_age(self, response: Any) -> str:
        """Validate age response."""
        if isinstance(response, (int, float)):
            if response < 0:
                raise ValueError("Age cannot be negative")
            return str(int(response)) if response == int(response) else str(response)
        
        if isinstance(response, str):
            response_str = response.strip()
            
            # Check if it's a pure numeric string (possibly with decimal)
            import re
            if re.match(r'^-?\d+(?:\.\d+)?$', response_str):
                age = float(response_str)
                if age < 0:
                    raise ValueError("Age cannot be negative")
                # Return as integer string if it's a whole number
                return str(int(age)) if age == int(age) else str(age)
            
            # For descriptive ages like "P30", "adult", etc., check for negative signs
            if '-' in response_str and re.search(r'-\d', response_str):
                raise ValueError("Age cannot be negative")
        
        # Return as-is for descriptive ages like "adult", "P30" etc.
        return str(response).strip()
    
    def _validate_sex(self, response: Any) -> str:
        """Validate sex response."""
        response_str = str(response).strip().upper()
        
        valid_values = {
            'M': 'M', 'MALE': 'M',
            'F': 'F', 'FEMALE': 'F',
            'U': 'U', 'UNKNOWN': 'U', 'OTHER': 'U'
        }
        
        if response_str in valid_values:
            return valid_values[response_str]
        
        raise ValueError(f"Invalid sex value: {response}. Must be M/F/U or Male/Female/Unknown")
    
    def _validate_sampling_rate(self, response: Any) -> float:
        """Validate sampling rate response."""
        try:
            rate = float(response)
            if rate <= 0:
                raise ValueError("Sampling rate must be positive")
            return rate
        except (ValueError, TypeError):
            raise ValueError(f"Invalid sampling rate: {response}. Must be a positive number")
    
    def _validate_channel_count(self, response: Any) -> int:
        """Validate channel count response."""
        try:
            count = int(response)
            if count <= 0:
                raise ValueError("Channel count must be positive")
            return count
        except (ValueError, TypeError):
            raise ValueError(f"Invalid channel count: {response}. Must be a positive integer")
    
    async def _validate_responses_with_domain_knowledge(self, responses: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validate responses using domain knowledge.
        
        Args:
            responses: Dictionary of validated responses
            
        Returns:
            List of warnings about potentially inconsistent responses
        """
        warnings = []
        
        # Check for consistency between experimental type and other metadata
        if 'experimental_type' in responses:
            exp_type = responses['experimental_type']
            
            # Check sampling rate consistency
            if 'sampling_rate' in responses:
                rate = float(responses['sampling_rate'])
                if exp_type == 'electrophysiology' and rate < 1000:
                    warnings.append({
                        'field': 'sampling_rate',
                        'warning': f'Sampling rate {rate} Hz seems low for electrophysiology',
                        'suggestion': 'Typical electrophysiology sampling rates are 10-50 kHz'
                    })
        
        # Check species and age consistency
        if 'species' in responses and 'age' in responses:
            species = responses['species'].lower()
            age_str = str(responses['age']).lower()
            
            if species == 'mouse' and 'year' in age_str:
                warnings.append({
                    'field': 'age',
                    'warning': 'Mouse age specified in years seems unusual',
                    'suggestion': 'Mouse ages are typically specified in days or weeks'
                })
        
        return warnings
    
    async def generate_follow_up_questions(self, current_responses: Dict[str, Any],
                                         missing_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate follow-up questions based on current responses.
        
        Args:
            current_responses: Current user responses
            missing_metadata: Still missing metadata fields
            
        Returns:
            List of follow-up questions
        """
        follow_up_questions = []
        
        # Generate context-aware follow-up questions
        if 'experimental_type' in current_responses:
            exp_type = current_responses['experimental_type']
            
            if exp_type == 'electrophysiology':
                # Ask about electrode configuration
                if not any(item['field'] == 'electrode_config' for item in missing_metadata):
                    follow_up_questions.append({
                        'field': 'electrode_config',
                        'question': 'What type of electrodes were used in this recording?',
                        'explanation': 'Electrode information helps with data interpretation',
                        'priority': 'medium',
                        'category': 'recording'
                    })
        
        # Generate questions based on detected formats
        if 'recording_system' in current_responses:
            system = current_responses['recording_system']
            
            if system == 'Open Ephys':
                follow_up_questions.append({
                    'field': 'open_ephys_version',
                    'question': 'What version of Open Ephys was used?',
                    'explanation': 'Version information helps with format compatibility',
                    'priority': 'low',
                    'category': 'technical'
                })
        
        return follow_up_questions