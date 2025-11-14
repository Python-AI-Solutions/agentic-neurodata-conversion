"""Prompt Service for loading and rendering YAML prompt templates.

Implements Task T018: PromptService with YAML loading and Jinja2 rendering.
"""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, Template


class PromptService:
    """Service for managing LLM prompt templates.

    Loads YAML prompt templates and renders them with Jinja2.
    """

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize prompt service.

        Args:
            prompts_dir: Directory containing prompt YAML files.
                        Defaults to backend/src/prompts/
        """
        if prompts_dir is None:
            # Default to prompts directory relative to this file
            prompts_dir = Path(__file__).parent.parent / "prompts"

        self.prompts_dir = Path(prompts_dir)
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")

        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=False,  # nosec B701 - safe: generating LLM prompts, not HTML - no XSS risk
        )

        # Add custom filters
        self.jinja_env.filters["filesizeformat"] = self._filesizeformat

    def _filesizeformat(self, bytes_value: int) -> str:
        """Custom Jinja2 filter for formatting file sizes."""
        size = float(bytes_value)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def load_template(self, template_name: str) -> dict[str, Any]:
        """Load a YAML prompt template.

        Args:
            template_name: Name of template file (with or without .yaml extension)

        Returns:
            Dictionary containing template data

        Raises:
            FileNotFoundError: If template doesn't exist
            yaml.YAMLError: If template is invalid YAML
        """
        # Ensure .yaml extension
        if not template_name.endswith(".yaml"):
            template_name = f"{template_name}.yaml"

        template_path = self.prompts_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path) as f:
            template_data = yaml.safe_load(f)

        return dict(template_data) if template_data else {}  # Cast Any to dict

    def render_prompt(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a prompt template with context data.

        Args:
            template_name: Name of template file
            context: Dictionary of variables to render in template

        Returns:
            Rendered prompt string

        Raises:
            FileNotFoundError: If template doesn't exist
            jinja2.TemplateError: If rendering fails
        """
        template_data = self.load_template(template_name)

        # Get the template string
        template_str = template_data.get("template", "")

        # Create Jinja2 template
        template = Template(template_str)

        # Render with context
        rendered = template.render(**context)

        return str(rendered).strip()  # Cast Any to str

    def get_system_role(self, template_name: str) -> str:
        """Get system role from template.

        Args:
            template_name: Name of template file

        Returns:
            System role string
        """
        template_data = self.load_template(template_name)
        return str(template_data.get("system_role", "")).strip()  # Cast Any to str

    def get_output_schema(self, template_name: str) -> dict[str, Any] | None:
        """Get output schema from template.

        Args:
            template_name: Name of template file

        Returns:
            Output schema dictionary or None
        """
        template_data = self.load_template(template_name)
        schema = template_data.get("output_schema")
        return dict(schema) if schema else None  # Cast Any to dict or None

    def create_llm_prompt(self, template_name: str, context: dict[str, Any]) -> dict[str, Any]:
        """Create complete LLM prompt with system role, rendered template, and schema.

        Args:
            template_name: Name of template file
            context: Dictionary of variables to render

        Returns:
            Dictionary with 'system_role', 'prompt', and 'output_schema'
        """
        return {
            "system_role": self.get_system_role(template_name),
            "prompt": self.render_prompt(template_name, context),
            "output_schema": self.get_output_schema(template_name),
        }
