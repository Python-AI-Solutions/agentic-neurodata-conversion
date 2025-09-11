"""
Conversation agent for dataset analysis and metadata extraction.

This agent handles interactive analysis of datasets, extracting metadata,
detecting formats, and generating questions for missing information.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from .base import BaseAgent, AgentCapability, AgentStatus

logger = logging.getLogger(__name__)


class ConversationAgent(BaseAgent):
    """
    Agent responsible for dataset analysis and conversational metadata extraction.
    
    This agent analyzes dataset structures, extracts available metadata,
    detects data formats, and can generate questions to gather missing
    information required for NWB conversion.
    """
    
    def __init__(self, config: Optional[Any] = None, agent_id: Optional[str] = None):
        """
        Initialize the conversation agent.
        
        Args:
            config: Agent configuration containing LLM settings and analysis parameters.
            agent_id: Optional agent identifier.
        """
        self.llm_client = None
        self.analysis_cache: Dict[str, Any] = {}
        self.supported_formats = [
            "open_ephys", "spikeglx", "neuralynx", "blackrock", "intan",
            "axon", "plexon", "tdt", "mcs", "biocam"
        ]
        
        super().__init__(config, agent_id)
    
    def _initialize(self) -> None:
        """Initialize conversation agent specific components."""
        # Register capabilities
        self.add_capability(AgentCapability.DATASET_ANALYSIS)
        self.add_capability(AgentCapability.METADATA_EXTRACTION)
        self.add_capability(AgentCapability.FORMAT_DETECTION)
        self.add_capability(AgentCapability.CONVERSATION)
        
        # Initialize LLM client if configuration is available
        if self.config:
            self._initialize_llm_client()
        
        # Update metadata
        self.update_metadata({
            "supported_formats": self.supported_formats,
            "llm_available": self.llm_client is not None,
            "cache_size": 0
        })
        
        logger.info(f"ConversationAgent {self.agent_id} initialized with {len(self.supported_formats)} supported formats")
    
    def _initialize_llm_client(self) -> None:
        """
        Initialize LLM client based on configuration.
        
        This method sets up the appropriate LLM client (OpenAI, Anthropic, or local)
        based on the agent configuration.
        """
        try:
            # This is a placeholder for LLM client initialization
            # In a real implementation, this would set up the actual LLM client
            # based on the configuration (OpenAI, Anthropic, local model, etc.)
            
            model_name = getattr(self.config, 'conversation_model', 'gpt-4') if self.config else 'gpt-4'
            
            # Placeholder LLM client setup
            self.llm_client = {
                "model": model_name,
                "initialized": True,
                "type": "placeholder"
            }
            
            logger.info(f"Initialized LLM client with model: {model_name}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}")
            self.llm_client = None
    
    def get_capabilities(self) -> Set[AgentCapability]:
        """Get the capabilities provided by this agent."""
        return {
            AgentCapability.DATASET_ANALYSIS,
            AgentCapability.METADATA_EXTRACTION,
            AgentCapability.FORMAT_DETECTION,
            AgentCapability.CONVERSATION
        }
    
    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task assigned to the conversation agent.
        
        Args:
            task: Task dictionary containing task type and parameters.
            
        Returns:
            Dictionary containing the processing result.
        """
        task_type = task.get("type")
        
        if task_type == "dataset_analysis":
            return await self._analyze_dataset(task)
        elif task_type == "metadata_extraction":
            return await self._extract_metadata(task)
        elif task_type == "format_detection":
            return await self._detect_format(task)
        elif task_type == "conversation":
            return await self._handle_conversation(task)
        else:
            raise NotImplementedError(f"Task type '{task_type}' not supported by ConversationAgent")
    
    async def _analyze_dataset(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a dataset directory structure and contents.
        
        Args:
            task: Task containing dataset_dir and optional parameters.
            
        Returns:
            Dictionary containing analysis results.
        """
        dataset_dir = task.get("dataset_dir")
        use_llm = task.get("use_llm", False)
        
        if not dataset_dir:
            raise ValueError("dataset_dir is required for dataset analysis")
        
        dataset_path = Path(dataset_dir)
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
        
        # Check cache first
        cache_key = f"analysis_{dataset_path.resolve()}"
        if cache_key in self.analysis_cache:
            logger.info(f"Returning cached analysis for {dataset_dir}")
            return self.analysis_cache[cache_key]
        
        try:
            # Perform basic file system analysis
            analysis_result = await self._perform_filesystem_analysis(dataset_path)
            
            # Enhance with LLM analysis if requested and available
            if use_llm and self.llm_client:
                llm_analysis = await self._perform_llm_analysis(dataset_path, analysis_result)
                analysis_result.update(llm_analysis)
            
            # Cache the result
            self.analysis_cache[cache_key] = analysis_result
            self.update_metadata({"cache_size": len(self.analysis_cache)})
            
            return {
                "status": "success",
                "result": analysis_result,
                "agent_id": self.agent_id,
                "cached": False
            }
            
        except Exception as e:
            logger.error(f"Dataset analysis failed for {dataset_dir}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "agent_id": self.agent_id
            }
    
    async def _perform_filesystem_analysis(self, dataset_path: Path) -> Dict[str, Any]:
        """
        Perform basic filesystem analysis of the dataset.
        
        Args:
            dataset_path: Path to the dataset directory.
            
        Returns:
            Dictionary containing filesystem analysis results.
        """
        analysis = {
            "dataset_path": str(dataset_path.resolve()),
            "total_files": 0,
            "total_size_bytes": 0,
            "file_extensions": {},
            "directory_structure": {},
            "detected_formats": [],
            "metadata_files": [],
            "data_files": [],
            "potential_issues": []
        }
        
        try:
            # Analyze directory structure and files
            for item in dataset_path.rglob("*"):
                if item.is_file():
                    analysis["total_files"] += 1
                    
                    try:
                        file_size = item.stat().st_size
                        analysis["total_size_bytes"] += file_size
                    except (OSError, PermissionError):
                        analysis["potential_issues"].append(f"Cannot access file: {item}")
                        continue
                    
                    # Track file extensions
                    ext = item.suffix.lower()
                    if ext:
                        analysis["file_extensions"][ext] = analysis["file_extensions"].get(ext, 0) + 1
                    
                    # Categorize files
                    if self._is_metadata_file(item):
                        analysis["metadata_files"].append(str(item.relative_to(dataset_path)))
                    elif self._is_data_file(item):
                        analysis["data_files"].append(str(item.relative_to(dataset_path)))
            
            # Detect potential data formats
            analysis["detected_formats"] = self._detect_formats_from_files(analysis)
            
            # Build directory structure summary
            analysis["directory_structure"] = self._build_directory_structure(dataset_path)
            
            logger.info(f"Filesystem analysis completed: {analysis['total_files']} files, "
                       f"{len(analysis['detected_formats'])} formats detected")
            
        except Exception as e:
            analysis["potential_issues"].append(f"Analysis error: {str(e)}")
            logger.error(f"Filesystem analysis error: {e}")
        
        return analysis
    
    def _is_metadata_file(self, file_path: Path) -> bool:
        """Check if a file is likely a metadata file."""
        metadata_patterns = [
            "metadata", "info", "session", "experiment", "config",
            "settings", "params", "description", "readme"
        ]
        metadata_extensions = [".json", ".xml", ".yaml", ".yml", ".txt", ".md", ".ini"]
        
        filename_lower = file_path.name.lower()
        
        # Check for metadata patterns in filename
        for pattern in metadata_patterns:
            if pattern in filename_lower:
                return True
        
        # Check for metadata file extensions
        return file_path.suffix.lower() in metadata_extensions
    
    def _is_data_file(self, file_path: Path) -> bool:
        """Check if a file is likely a data file."""
        data_extensions = [
            ".dat", ".bin", ".h5", ".hdf5", ".mat", ".npy", ".npz",
            ".continuous", ".spikes", ".events", ".lfp", ".mda",
            ".rhd", ".rhs", ".plx", ".nex", ".smr", ".abf"
        ]
        
        return file_path.suffix.lower() in data_extensions
    
    def _detect_formats_from_files(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Detect data formats based on file patterns and extensions.
        
        Args:
            analysis: Current analysis results containing file information.
            
        Returns:
            List of detected format names.
        """
        detected_formats = []
        extensions = analysis.get("file_extensions", {})
        
        # Format detection rules
        format_rules = {
            "open_ephys": [".continuous", ".spikes", ".events"],
            "spikeglx": [".bin", ".meta"],
            "neuralynx": [".ncs", ".nev", ".ntt", ".nse"],
            "blackrock": [".ns1", ".ns2", ".ns3", ".ns4", ".ns5", ".ns6", ".nev"],
            "intan": [".rhd", ".rhs"],
            "axon": [".abf", ".atf"],
            "plexon": [".plx", ".pl2"],
            "tdt": [".sev", ".tev"],
            "matlab": [".mat"],
            "hdf5": [".h5", ".hdf5"]
        }
        
        for format_name, format_extensions in format_rules.items():
            if any(ext in extensions for ext in format_extensions):
                detected_formats.append(format_name)
        
        return detected_formats
    
    def _build_directory_structure(self, dataset_path: Path, max_depth: int = 3) -> Dict[str, Any]:
        """
        Build a summary of the directory structure.
        
        Args:
            dataset_path: Path to analyze.
            max_depth: Maximum depth to traverse.
            
        Returns:
            Dictionary representing directory structure.
        """
        structure = {
            "name": dataset_path.name,
            "type": "directory",
            "children": []
        }
        
        try:
            if max_depth > 0:
                for item in sorted(dataset_path.iterdir()):
                    if item.is_dir():
                        child_structure = self._build_directory_structure(item, max_depth - 1)
                        structure["children"].append(child_structure)
                    else:
                        structure["children"].append({
                            "name": item.name,
                            "type": "file",
                            "size": item.stat().st_size if item.exists() else 0
                        })
        except (PermissionError, OSError) as e:
            structure["error"] = str(e)
        
        return structure
    
    async def _perform_llm_analysis(self, dataset_path: Path, basic_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform LLM-enhanced analysis of the dataset.
        
        Args:
            dataset_path: Path to the dataset.
            basic_analysis: Results from basic filesystem analysis.
            
        Returns:
            Dictionary containing LLM analysis results.
        """
        # This is a placeholder for LLM analysis
        # In a real implementation, this would use the LLM client to analyze
        # the dataset structure and provide intelligent insights
        
        llm_analysis = {
            "llm_insights": {
                "format_confidence": {},
                "missing_metadata": [],
                "suggested_questions": [],
                "conversion_readiness": "unknown"
            },
            "llm_model_used": self.llm_client.get("model", "unknown") if self.llm_client else None
        }
        
        # Simulate LLM analysis based on detected formats
        detected_formats = basic_analysis.get("detected_formats", [])
        
        for format_name in detected_formats:
            llm_analysis["llm_insights"]["format_confidence"][format_name] = 0.8
        
        # Generate sample questions for missing metadata
        if not basic_analysis.get("metadata_files"):
            llm_analysis["llm_insights"]["missing_metadata"].extend([
                "session_description",
                "experimenter",
                "institution",
                "lab"
            ])
            
            llm_analysis["llm_insights"]["suggested_questions"].extend([
                "What is the description of this experimental session?",
                "Who conducted this experiment?",
                "Which institution/lab collected this data?"
            ])
        
        logger.info("LLM analysis completed (placeholder implementation)")
        return llm_analysis
    
    async def _extract_metadata(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from dataset files.
        
        Args:
            task: Task containing file paths and extraction parameters.
            
        Returns:
            Dictionary containing extracted metadata.
        """
        # Placeholder implementation for metadata extraction
        file_paths = task.get("file_paths", [])
        
        extracted_metadata = {
            "session_metadata": {},
            "file_metadata": {},
            "extraction_method": "filesystem_analysis"
        }
        
        for file_path in file_paths:
            path = Path(file_path)
            if path.exists() and self._is_metadata_file(path):
                # In a real implementation, this would parse JSON, XML, etc.
                extracted_metadata["file_metadata"][str(path)] = {
                    "size": path.stat().st_size,
                    "modified": path.stat().st_mtime,
                    "type": "metadata_file"
                }
        
        return {
            "status": "success",
            "result": extracted_metadata,
            "agent_id": self.agent_id
        }
    
    async def _detect_format(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect the data format of specific files.
        
        Args:
            task: Task containing file paths to analyze.
            
        Returns:
            Dictionary containing format detection results.
        """
        file_paths = task.get("file_paths", [])
        
        format_results = {}
        
        for file_path in file_paths:
            path = Path(file_path)
            if path.exists():
                # Simple format detection based on extension and filename patterns
                detected_format = self._detect_single_file_format(path)
                format_results[str(path)] = detected_format
        
        return {
            "status": "success",
            "result": {
                "format_results": format_results,
                "supported_formats": self.supported_formats
            },
            "agent_id": self.agent_id
        }
    
    def _detect_single_file_format(self, file_path: Path) -> Dict[str, Any]:
        """
        Detect format for a single file.
        
        Args:
            file_path: Path to the file to analyze.
            
        Returns:
            Dictionary containing format detection result.
        """
        extension = file_path.suffix.lower()
        filename = file_path.name.lower()
        
        # Format detection logic
        if extension == ".continuous" or "continuous" in filename:
            return {"format": "open_ephys", "confidence": 0.9, "type": "continuous_data"}
        elif extension in [".bin", ".meta"] and "imec" in filename:
            return {"format": "spikeglx", "confidence": 0.9, "type": "neural_data"}
        elif extension in [".ncs", ".nev", ".ntt"]:
            return {"format": "neuralynx", "confidence": 0.9, "type": "neural_data"}
        elif extension in [".rhd", ".rhs"]:
            return {"format": "intan", "confidence": 0.8, "type": "neural_data"}
        elif extension == ".abf":
            return {"format": "axon", "confidence": 0.8, "type": "patch_clamp"}
        else:
            return {"format": "unknown", "confidence": 0.0, "type": "unknown"}
    
    async def _handle_conversation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle conversational interactions for gathering missing metadata.
        
        Args:
            task: Task containing conversation context and questions.
            
        Returns:
            Dictionary containing conversation response.
        """
        question = task.get("question", "")
        context = task.get("context", {})
        
        # Placeholder conversation handling
        # In a real implementation, this would use the LLM to generate
        # intelligent responses and follow-up questions
        
        response = {
            "answer": f"I understand you're asking about: {question}",
            "follow_up_questions": [
                "Could you provide more details about the experimental setup?",
                "What type of recording equipment was used?"
            ],
            "metadata_suggestions": {
                "session_description": "Please describe the experimental session",
                "experimenter": "Who conducted this experiment?"
            }
        }
        
        return {
            "status": "success",
            "result": response,
            "agent_id": self.agent_id
        }
    
    def clear_cache(self) -> None:
        """Clear the analysis cache."""
        self.analysis_cache.clear()
        self.update_metadata({"cache_size": 0})
        logger.info(f"Cleared analysis cache for agent {self.agent_id}")
    
    async def shutdown(self) -> None:
        """Shutdown the conversation agent."""
        self.clear_cache()
        
        if self.llm_client:
            # In a real implementation, this would properly close LLM client connections
            self.llm_client = None
        
        await super().shutdown()
        logger.info(f"ConversationAgent {self.agent_id} shutdown completed")