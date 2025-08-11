"""
Pythonic interface for the LLM-guided NWB conversion tool.

This module provides a Python API for programmatic access to the conversion functionality.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path


class LLMConversionTool:
    """
    Main interface for LLM-guided NWB conversion.
    
    Example:
        >>> tool = LLMConversionTool()
        >>> result = tool.convert(
        ...     input_path="data/messy_data.mat",
        ...     output_path="data/clean.nwb",
        ...     interactive=True
        ... )
    """
    
    def __init__(
        self,
        model: str = "claude-3-opus",
        prompt_template: Optional[Path] = None,
        validation_level: str = "strict"
    ):
        """
        Initialize the conversion tool.
        
        Args:
            model: LLM model to use
            prompt_template: Custom prompt template path
            validation_level: Validation strictness ("strict", "normal", "lenient")
        """
        self.model = model
        self.prompt_template = prompt_template
        self.validation_level = validation_level
    
    def convert(
        self,
        input_path: Path,
        output_path: Path,
        metadata: Optional[Dict[str, Any]] = None,
        interactive: bool = True
    ) -> Dict[str, Any]:
        """
        Convert data to NWB format.
        
        Args:
            input_path: Path to input data
            output_path: Path for output NWB file
            metadata: Additional metadata to include
            interactive: Whether to ask user for missing metadata
            
        Returns:
            Conversion result with status and validation report
        """
        # Implementation will be added
        raise NotImplementedError("Conversion implementation pending")
    
    def validate(self, nwb_path: Path) -> Dict[str, Any]:
        """
        Validate an NWB file.
        
        Args:
            nwb_path: Path to NWB file
            
        Returns:
            Validation report
        """
        # Implementation will be added
        raise NotImplementedError("Validation implementation pending")
    
    def analyze_data(self, data_path: Path) -> Dict[str, Any]:
        """
        Analyze data structure and suggest NWB mapping.
        
        Args:
            data_path: Path to data
            
        Returns:
            Analysis report with suggested mappings
        """
        # Implementation will be added
        raise NotImplementedError("Analysis implementation pending")


__all__ = ["LLMConversionTool"]