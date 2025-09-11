"""
Conversion agent for generating and executing NeuroConv conversion scripts.

This agent handles the generation of NeuroConv conversion scripts based on
analyzed metadata and file mappings, and can execute the conversion process.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import tempfile
import subprocess

from .base import BaseAgent, AgentCapability, AgentStatus

logger = logging.getLogger(__name__)


class ConversionAgent(BaseAgent):
    """
    Agent responsible for generating and executing NeuroConv conversion scripts.
    
    This agent takes normalized metadata and file mappings to generate
    appropriate NeuroConv conversion scripts and can execute the conversion
    process to produce NWB files.
    """
    
    def __init__(self, config: Optional[Any] = None, agent_id: Optional[str] = None):
        """
        Initialize the conversion agent.
        
        Args:
            config: Agent configuration containing conversion settings and timeouts.
            agent_id: Optional agent identifier.
        """
        self.script_templates: Dict[str, str] = {}
        self.conversion_cache: Dict[str, Any] = {}
        self.active_conversions: Dict[str, Any] = {}
        self.conversion_timeout = 300  # Default 5 minutes
        
        super().__init__(config, agent_id)
    
    def _initialize(self) -> None:
        """Initialize conversion agent specific components."""
        # Register capabilities
        self.add_capability(AgentCapability.SCRIPT_GENERATION)
        self.add_capability(AgentCapability.CONVERSION_EXECUTION)
        
        # Load configuration
        if self.config:
            self.conversion_timeout = getattr(self.config, 'conversion_timeout', 300)
        
        # Initialize script templates
        self._initialize_script_templates()
        
        # Update metadata
        self.update_metadata({
            "conversion_timeout": self.conversion_timeout,
            "templates_loaded": len(self.script_templates),
            "active_conversions": 0,
            "cache_size": 0
        })
        
        logger.info(f"ConversionAgent {self.agent_id} initialized with {len(self.script_templates)} templates")
    
    def _initialize_script_templates(self) -> None:
        """Initialize NeuroConv script templates for different data formats."""
        
        # Template for Open Ephys conversion
        self.script_templates["open_ephys"] = '''
import os
from pathlib import Path
from neuroconv.converters import OpenEphysRecordingInterfaceConverter
from pynwb import NWBHDF5IO

def convert_open_ephys_to_nwb(data_dir, output_path, metadata):
    """Convert Open Ephys data to NWB format."""
    
    # Initialize converter
    converter = OpenEphysRecordingInterfaceConverter(folder_path=data_dir)
    
    # Update metadata
    converter.get_metadata().update(metadata)
    
    # Run conversion
    converter.run_conversion(
        nwbfile_path=output_path,
        overwrite=True
    )
    
    return output_path

if __name__ == "__main__":
    data_dir = "{data_dir}"
    output_path = "{output_path}"
    metadata = {metadata}
    
    result_path = convert_open_ephys_to_nwb(data_dir, output_path, metadata)
    print(f"Conversion completed: {{result_path}}")
'''
        
        # Template for SpikeGLX conversion
        self.script_templates["spikeglx"] = '''
import os
from pathlib import Path
from neuroconv.converters import SpikeGLXRecordingInterfaceConverter
from pynwb import NWBHDF5IO

def convert_spikeglx_to_nwb(file_path, output_path, metadata):
    """Convert SpikeGLX data to NWB format."""
    
    # Initialize converter
    converter = SpikeGLXRecordingInterfaceConverter(file_path=file_path)
    
    # Update metadata
    converter.get_metadata().update(metadata)
    
    # Run conversion
    converter.run_conversion(
        nwbfile_path=output_path,
        overwrite=True
    )
    
    return output_path

if __name__ == "__main__":
    file_path = "{file_path}"
    output_path = "{output_path}"
    metadata = {metadata}
    
    result_path = convert_spikeglx_to_nwb(file_path, output_path, metadata)
    print(f"Conversion completed: {{result_path}}")
'''
        
        # Generic template for other formats
        self.script_templates["generic"] = '''
import os
from pathlib import Path
from neuroconv import NWBConverter
from pynwb import NWBHDF5IO

class CustomNWBConverter(NWBConverter):
    """Custom converter for {format_name} data."""
    
    data_interface_classes = {{
        # Add appropriate data interfaces here
    }}

def convert_to_nwb(source_data, output_path, metadata):
    """Convert data to NWB format."""
    
    # Initialize converter with source data
    converter = CustomNWBConverter(source_data=source_data)
    
    # Update metadata
    converter.get_metadata().update(metadata)
    
    # Run conversion
    converter.run_conversion(
        nwbfile_path=output_path,
        overwrite=True
    )
    
    return output_path

if __name__ == "__main__":
    source_data = {source_data}
    output_path = "{output_path}"
    metadata = {metadata}
    
    result_path = convert_to_nwb(source_data, output_path, metadata)
    print(f"Conversion completed: {{result_path}}")
'''
        
        logger.info(f"Loaded {len(self.script_templates)} script templates")
    
    def get_capabilities(self) -> Set[AgentCapability]:
        """Get the capabilities provided by this agent."""
        return {
            AgentCapability.SCRIPT_GENERATION,
            AgentCapability.CONVERSION_EXECUTION
        }
    
    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task assigned to the conversion agent.
        
        Args:
            task: Task dictionary containing task type and parameters.
            
        Returns:
            Dictionary containing the processing result.
        """
        task_type = task.get("type")
        
        if task_type == "script_generation":
            return await self._generate_script(task)
        elif task_type == "conversion_execution":
            return await self._execute_conversion(task)
        else:
            raise NotImplementedError(f"Task type '{task_type}' not supported by ConversionAgent")
    
    async def _generate_script(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a NeuroConv conversion script based on metadata and file mappings.
        
        Args:
            task: Task containing metadata, files_map, and optional parameters.
            
        Returns:
            Dictionary containing the generated script and metadata.
        """
        metadata = task.get("metadata", {})
        files_map = task.get("files_map", {})
        output_path = task.get("output_path")
        detected_format = task.get("format", "generic")
        
        if not metadata:
            raise ValueError("Metadata is required for script generation")
        
        if not files_map:
            raise ValueError("Files map is required for script generation")
        
        try:
            # Generate output path if not provided
            if not output_path:
                output_path = self._generate_output_path(metadata, files_map)
            
            # Select appropriate template
            template = self._select_template(detected_format, files_map)
            
            # Generate script content
            script_content = self._populate_template(
                template, metadata, files_map, output_path, detected_format
            )
            
            # Create temporary script file
            script_path = self._create_script_file(script_content)
            
            result = {
                "script_path": str(script_path),
                "script_content": script_content,
                "output_path": output_path,
                "format": detected_format,
                "metadata_used": metadata,
                "files_mapped": files_map
            }
            
            # Cache the result
            cache_key = self._generate_cache_key(metadata, files_map)
            self.conversion_cache[cache_key] = result
            self.update_metadata({"cache_size": len(self.conversion_cache)})
            
            return {
                "status": "success",
                "result": result,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "agent_id": self.agent_id
            }
    
    def _select_template(self, detected_format: str, files_map: Dict[str, str]) -> str:
        """
        Select the appropriate script template based on detected format.
        
        Args:
            detected_format: The detected data format.
            files_map: Mapping of file types to file paths.
            
        Returns:
            Template string for the conversion script.
        """
        # Normalize format name
        format_key = detected_format.lower()
        
        # Check if we have a specific template for this format
        if format_key in self.script_templates:
            return self.script_templates[format_key]
        
        # Fall back to generic template
        return self.script_templates["generic"]
    
    def _populate_template(self, template: str, metadata: Dict[str, Any], 
                          files_map: Dict[str, str], output_path: str, 
                          detected_format: str) -> str:
        """
        Populate a template with actual values.
        
        Args:
            template: Template string to populate.
            metadata: Metadata dictionary.
            files_map: File mappings.
            output_path: Output NWB file path.
            detected_format: Detected data format.
            
        Returns:
            Populated script content.
        """
        # Prepare template variables
        template_vars = {
            "metadata": repr(metadata),
            "output_path": output_path,
            "format_name": detected_format
        }
        
        # Add format-specific variables
        if detected_format.lower() == "open_ephys":
            template_vars["data_dir"] = files_map.get("data_dir", "")
        elif detected_format.lower() == "spikeglx":
            template_vars["file_path"] = files_map.get("recording", "")
        else:
            template_vars["source_data"] = repr(files_map)
        
        # Populate template
        try:
            populated_script = template.format(**template_vars)
        except KeyError as e:
            logger.warning(f"Template variable missing: {e}")
            # Use safe substitution for missing variables
            import string
            template_obj = string.Template(template)
            populated_script = template_obj.safe_substitute(**template_vars)
        
        return populated_script
    
    def _generate_output_path(self, metadata: Dict[str, Any], files_map: Dict[str, str]) -> str:
        """
        Generate an appropriate output path for the NWB file.
        
        Args:
            metadata: Metadata dictionary.
            files_map: File mappings.
            
        Returns:
            Generated output file path.
        """
        # Extract session identifier from metadata
        session_id = metadata.get("session_id", "unknown_session")
        subject_id = metadata.get("subject_id", "unknown_subject")
        
        # Create filename
        filename = f"{subject_id}_{session_id}.nwb"
        
        # Use output directory from config or default
        output_dir = "outputs"
        if self.config and hasattr(self.config, 'output_dir'):
            output_dir = self.config.output_dir
        
        output_path = Path(output_dir) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return str(output_path)
    
    def _create_script_file(self, script_content: str) -> Path:
        """
        Create a temporary script file with the generated content.
        
        Args:
            script_content: The script content to write.
            
        Returns:
            Path to the created script file.
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            prefix='neuroconv_script_',
            delete=False
        ) as f:
            f.write(script_content)
            script_path = Path(f.name)
        
        logger.info(f"Created conversion script: {script_path}")
        return script_path
    
    def _generate_cache_key(self, metadata: Dict[str, Any], files_map: Dict[str, str]) -> str:
        """
        Generate a cache key for the conversion parameters.
        
        Args:
            metadata: Metadata dictionary.
            files_map: File mappings.
            
        Returns:
            Cache key string.
        """
        import hashlib
        import json
        
        # Create a deterministic representation
        cache_data = {
            "metadata": metadata,
            "files_map": files_map
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    async def _execute_conversion(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a conversion script to generate an NWB file.
        
        Args:
            task: Task containing script_path and execution parameters.
            
        Returns:
            Dictionary containing execution results.
        """
        script_path = task.get("script_path")
        timeout = task.get("timeout", self.conversion_timeout)
        
        if not script_path:
            raise ValueError("script_path is required for conversion execution")
        
        script_file = Path(script_path)
        if not script_file.exists():
            raise FileNotFoundError(f"Conversion script not found: {script_path}")
        
        # Generate execution ID
        execution_id = f"conv_{len(self.active_conversions)}_{self.agent_id[:8]}"
        
        try:
            # Track active conversion
            self.active_conversions[execution_id] = {
                "script_path": script_path,
                "start_time": asyncio.get_event_loop().time(),
                "status": "running"
            }
            
            self.update_metadata({"active_conversions": len(self.active_conversions)})
            
            # Execute the conversion script
            result = await self._run_conversion_script(script_file, timeout)
            
            # Update conversion status
            self.active_conversions[execution_id]["status"] = "completed"
            self.active_conversions[execution_id]["end_time"] = asyncio.get_event_loop().time()
            
            return {
                "status": "success",
                "result": result,
                "execution_id": execution_id,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            # Update conversion status
            if execution_id in self.active_conversions:
                self.active_conversions[execution_id]["status"] = "failed"
                self.active_conversions[execution_id]["error"] = str(e)
            
            logger.error(f"Conversion execution failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "execution_id": execution_id,
                "agent_id": self.agent_id
            }
        
        finally:
            # Clean up completed conversion from active list
            if execution_id in self.active_conversions:
                # Move to completed conversions or remove after some time
                pass
            
            self.update_metadata({"active_conversions": len(self.active_conversions)})
    
    async def _run_conversion_script(self, script_path: Path, timeout: int) -> Dict[str, Any]:
        """
        Run the conversion script as a subprocess.
        
        Args:
            script_path: Path to the conversion script.
            timeout: Execution timeout in seconds.
            
        Returns:
            Dictionary containing execution results.
        """
        try:
            # Run the script
            process = await asyncio.create_subprocess_exec(
                "python", str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            # Check return code
            if process.returncode != 0:
                raise RuntimeError(f"Conversion script failed with code {process.returncode}: {stderr.decode()}")
            
            # Parse output
            output = stdout.decode().strip()
            
            # Extract output path from script output
            output_path = None
            for line in output.split('\n'):
                if "Conversion completed:" in line:
                    output_path = line.split("Conversion completed:")[-1].strip()
                    break
            
            result = {
                "output_path": output_path,
                "stdout": output,
                "stderr": stderr.decode(),
                "return_code": process.returncode,
                "script_path": str(script_path)
            }
            
            # Verify output file exists
            if output_path and Path(output_path).exists():
                result["output_file_size"] = Path(output_path).stat().st_size
                result["conversion_successful"] = True
            else:
                result["conversion_successful"] = False
                result["error"] = "Output NWB file not found"
            
            logger.info(f"Conversion script executed successfully: {output_path}")
            return result
            
        except asyncio.TimeoutError:
            # Kill the process if it's still running
            if process.returncode is None:
                process.kill()
                await process.wait()
            
            raise RuntimeError(f"Conversion script timed out after {timeout} seconds")
        
        except Exception as e:
            logger.error(f"Error running conversion script: {e}")
            raise
    
    def get_active_conversions(self) -> Dict[str, Any]:
        """
        Get information about currently active conversions.
        
        Returns:
            Dictionary of active conversions.
        """
        return self.active_conversions.copy()
    
    def cancel_conversion(self, execution_id: str) -> bool:
        """
        Cancel an active conversion.
        
        Args:
            execution_id: ID of the conversion to cancel.
            
        Returns:
            True if cancellation was successful, False otherwise.
        """
        if execution_id in self.active_conversions:
            # In a real implementation, this would terminate the subprocess
            self.active_conversions[execution_id]["status"] = "cancelled"
            logger.info(f"Cancelled conversion {execution_id}")
            return True
        
        return False
    
    def clear_cache(self) -> None:
        """Clear the conversion cache."""
        self.conversion_cache.clear()
        self.update_metadata({"cache_size": 0})
        logger.info(f"Cleared conversion cache for agent {self.agent_id}")
    
    async def shutdown(self) -> None:
        """Shutdown the conversion agent."""
        # Cancel any active conversions
        for execution_id in list(self.active_conversions.keys()):
            self.cancel_conversion(execution_id)
        
        self.clear_cache()
        
        await super().shutdown()
        logger.info(f"ConversionAgent {self.agent_id} shutdown completed")