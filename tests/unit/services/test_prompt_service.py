"""Unit tests for PromptService.

Tests YAML prompt loading, Jinja2 rendering, and template management
with focus on uncovered lines 26->30, 32, 45-50, 66->69, 72.
"""

import pytest
import yaml

from agentic_neurodata_conversion.services.prompt_service import PromptService


@pytest.fixture
def sample_prompts_dir(tmp_path):
    """Create a temporary prompts directory with sample YAML files."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Create sample prompt template
    sample_prompt = {
        "system_role": "You are a helpful assistant",
        "template": "Hello {{ name }}! You have {{ count }} messages.",
        "output_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
            },
        },
    }
    with open(prompts_dir / "sample.yaml", "w") as f:
        yaml.dump(sample_prompt, f)

    # Create prompt without extension (for testing auto-extension)
    simple_prompt = {
        "system_role": "Simple assistant",
        "template": "Simple template",
    }
    with open(prompts_dir / "simple.yaml", "w") as f:
        yaml.dump(simple_prompt, f)

    return prompts_dir


@pytest.mark.unit
@pytest.mark.service
class TestPromptServiceInitialization:
    """Test PromptService initialization and directory handling."""

    def test_init_with_explicit_directory(self, sample_prompts_dir):
        """Test initialization with explicit prompts directory."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        assert service.prompts_dir == sample_prompts_dir
        assert service.jinja_env is not None

    def test_init_with_default_directory(self):
        """Test initialization with default prompts directory (lines 26->30).

        Tests the default path resolution:
        prompts_dir = Path(__file__).parent.parent / "prompts"
        """
        # Use the actual default directory since it exists in the repo
        service = PromptService(prompts_dir=None)

        # Verify the default path was used and points to the prompts directory
        assert service.prompts_dir.exists()
        assert service.prompts_dir.name == "prompts"

    def test_init_with_nonexistent_directory_raises_error(self, tmp_path):
        """Test initialization with non-existent directory raises FileNotFoundError (line 32)."""
        nonexistent_dir = tmp_path / "does_not_exist"

        with pytest.raises(FileNotFoundError) as exc_info:
            PromptService(prompts_dir=nonexistent_dir)

        assert "Prompts directory not found" in str(exc_info.value)
        assert str(nonexistent_dir) in str(exc_info.value)

    def test_init_sets_up_jinja_environment(self, sample_prompts_dir):
        """Test that initialization sets up Jinja2 environment correctly."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        # Verify Jinja2 environment is configured
        assert service.jinja_env is not None
        assert service.jinja_env.autoescape is False  # Line 37

    def test_init_registers_custom_filters(self, sample_prompts_dir):
        """Test that custom filters are registered (line 41)."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        # Verify filesizeformat filter is registered
        assert "filesizeformat" in service.jinja_env.filters


@pytest.mark.unit
@pytest.mark.service
class TestFilesizeformatFilter:
    """Test _filesizeformat custom Jinja2 filter (lines 45-50)."""

    def test_filesizeformat_bytes(self, sample_prompts_dir):
        """Test file size formatting for bytes (line 47-48)."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        result = service._filesizeformat(512)
        assert result == "512.0 B"

    def test_filesizeformat_kilobytes(self, sample_prompts_dir):
        """Test file size formatting for kilobytes (line 49)."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        result = service._filesizeformat(1024)
        assert result == "1.0 KB"

        result = service._filesizeformat(2048)
        assert result == "2.0 KB"

    def test_filesizeformat_megabytes(self, sample_prompts_dir):
        """Test file size formatting for megabytes (line 49)."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        result = service._filesizeformat(1024 * 1024)
        assert result == "1.0 MB"

        result = service._filesizeformat(5 * 1024 * 1024)
        assert result == "5.0 MB"

    def test_filesizeformat_gigabytes(self, sample_prompts_dir):
        """Test file size formatting for gigabytes (line 46-49 loop)."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        result = service._filesizeformat(1024 * 1024 * 1024)
        assert result == "1.0 GB"

        result = service._filesizeformat(3 * 1024 * 1024 * 1024)
        assert result == "3.0 GB"

    def test_filesizeformat_terabytes(self, sample_prompts_dir):
        """Test file size formatting for terabytes (line 50)."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        result = service._filesizeformat(1024 * 1024 * 1024 * 1024)
        assert result == "1.0 TB"

        result = service._filesizeformat(2.5 * 1024 * 1024 * 1024 * 1024)
        assert result == "2.5 TB"

    def test_filesizeformat_zero(self, sample_prompts_dir):
        """Test file size formatting for zero bytes."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        result = service._filesizeformat(0)
        assert result == "0.0 B"

    def test_filesizeformat_fractional_kb(self, sample_prompts_dir):
        """Test file size formatting with fractional values."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        result = service._filesizeformat(1536)  # 1.5 KB
        assert result == "1.5 KB"


@pytest.mark.unit
@pytest.mark.service
class TestLoadTemplate:
    """Test load_template method."""

    def test_load_template_basic(self, sample_prompts_dir):
        """Test loading a basic template."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        template = service.load_template("sample.yaml")

        assert template["system_role"] == "You are a helpful assistant"
        assert "Hello {{ name }}!" in template["template"]
        assert "output_schema" in template

    def test_load_template_without_extension(self, sample_prompts_dir):
        """Test loading template without .yaml extension (lines 66->69).

        Tests automatic .yaml extension addition when not provided.
        """
        service = PromptService(prompts_dir=sample_prompts_dir)

        # Load without .yaml extension
        template = service.load_template("simple")

        assert template["system_role"] == "Simple assistant"
        assert template["template"] == "Simple template"

    def test_load_template_with_extension(self, sample_prompts_dir):
        """Test loading template with .yaml extension (line 66-67)."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        # Load with .yaml extension
        template = service.load_template("simple.yaml")

        assert template["system_role"] == "Simple assistant"

    def test_load_template_nonexistent_raises_error(self, sample_prompts_dir):
        """Test loading non-existent template raises FileNotFoundError (line 72)."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        with pytest.raises(FileNotFoundError) as exc_info:
            service.load_template("nonexistent.yaml")

        assert "Template not found" in str(exc_info.value)

    def test_load_template_empty_file(self, tmp_path):
        """Test loading empty YAML file returns empty dict (line 77)."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create empty YAML file
        empty_file = prompts_dir / "empty.yaml"
        empty_file.write_text("")

        service = PromptService(prompts_dir=prompts_dir)
        template = service.load_template("empty.yaml")

        assert template == {}

    def test_load_template_none_content(self, tmp_path):
        """Test loading YAML with null content returns empty dict (line 77)."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create YAML file with null content
        null_file = prompts_dir / "null.yaml"
        null_file.write_text("null\n")

        service = PromptService(prompts_dir=prompts_dir)
        template = service.load_template("null.yaml")

        assert template == {}


@pytest.mark.unit
@pytest.mark.service
class TestRenderPrompt:
    """Test render_prompt method."""

    def test_render_prompt_basic(self, sample_prompts_dir):
        """Test basic prompt rendering."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        rendered = service.render_prompt("sample", {"name": "Alice", "count": 3})

        assert "Hello Alice!" in rendered
        assert "You have 3 messages" in rendered

    def test_render_prompt_strips_whitespace(self, sample_prompts_dir):
        """Test that rendered prompt is stripped (line 104)."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        rendered = service.render_prompt("sample", {"name": "Bob", "count": 1})

        # Verify no leading/trailing whitespace
        assert rendered == rendered.strip()

    def test_render_prompt_without_extension(self, sample_prompts_dir):
        """Test rendering prompt without .yaml extension."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        rendered = service.render_prompt("simple", {})

        assert rendered == "Simple template"

    def test_render_prompt_with_missing_variables(self, sample_prompts_dir):
        """Test rendering with missing variables leaves placeholders."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        # Missing 'count' variable
        rendered = service.render_prompt("sample", {"name": "Charlie"})

        assert "Hello Charlie!" in rendered
        # Jinja2 replaces missing variables with empty string
        assert "You have  messages" in rendered

    def test_render_prompt_with_filesizeformat_filter(self, tmp_path):
        """Test rendering prompt using filesizeformat custom filter."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create template using filesizeformat filter
        filter_prompt = {"template": "File size: {{ size | filesizeformat }}"}
        with open(prompts_dir / "filter_test.yaml", "w") as f:
            yaml.dump(filter_prompt, f)

        service = PromptService(prompts_dir=prompts_dir)
        rendered = service.render_prompt("filter_test", {"size": 1024 * 1024})

        assert "File size: 1.0 MB" in rendered


@pytest.mark.unit
@pytest.mark.service
class TestGetSystemRole:
    """Test get_system_role method."""

    def test_get_system_role_basic(self, sample_prompts_dir):
        """Test getting system role from template."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        role = service.get_system_role("sample")

        assert role == "You are a helpful assistant"

    def test_get_system_role_strips_whitespace(self, tmp_path):
        """Test that system role is stripped (line 116)."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create template with whitespace in system_role
        whitespace_prompt = {"system_role": "  \n  Assistant with whitespace  \n  ", "template": "Test"}
        with open(prompts_dir / "whitespace.yaml", "w") as f:
            yaml.dump(whitespace_prompt, f)

        service = PromptService(prompts_dir=prompts_dir)
        role = service.get_system_role("whitespace")

        assert role == "Assistant with whitespace"
        assert role == role.strip()

    def test_get_system_role_missing_returns_empty(self, tmp_path):
        """Test getting system role when not in template returns empty string."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create template without system_role
        no_role_prompt = {"template": "No role here"}
        with open(prompts_dir / "no_role.yaml", "w") as f:
            yaml.dump(no_role_prompt, f)

        service = PromptService(prompts_dir=prompts_dir)
        role = service.get_system_role("no_role")

        assert role == ""


@pytest.mark.unit
@pytest.mark.service
class TestGetOutputSchema:
    """Test get_output_schema method."""

    def test_get_output_schema_basic(self, sample_prompts_dir):
        """Test getting output schema from template."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        schema = service.get_output_schema("sample")

        assert schema is not None
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_get_output_schema_missing_returns_none(self, tmp_path):
        """Test getting output schema when not in template returns None (line 129)."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create template without output_schema
        no_schema_prompt = {"system_role": "Assistant", "template": "No schema here"}
        with open(prompts_dir / "no_schema.yaml", "w") as f:
            yaml.dump(no_schema_prompt, f)

        service = PromptService(prompts_dir=prompts_dir)
        schema = service.get_output_schema("no_schema")

        assert schema is None

    def test_get_output_schema_empty_dict(self, tmp_path):
        """Test getting output schema when it's an empty dict (line 129).

        Empty dict is falsy, so it returns None per line 129: return dict(schema) if schema else None
        """
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create template with empty output_schema
        empty_schema_prompt = {"system_role": "Assistant", "template": "Template", "output_schema": {}}
        with open(prompts_dir / "empty_schema.yaml", "w") as f:
            yaml.dump(empty_schema_prompt, f)

        service = PromptService(prompts_dir=prompts_dir)
        schema = service.get_output_schema("empty_schema")

        # Empty dict is falsy, so returns None
        assert schema is None


@pytest.mark.unit
@pytest.mark.service
class TestCreateLLMPrompt:
    """Test create_llm_prompt method."""

    def test_create_llm_prompt_complete(self, sample_prompts_dir):
        """Test creating complete LLM prompt with all components."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        prompt_data = service.create_llm_prompt("sample", {"name": "Alice", "count": 5})

        assert "system_role" in prompt_data
        assert "prompt" in prompt_data
        assert "output_schema" in prompt_data

        assert prompt_data["system_role"] == "You are a helpful assistant"
        assert "Hello Alice!" in prompt_data["prompt"]
        assert "5 messages" in prompt_data["prompt"]
        assert prompt_data["output_schema"]["type"] == "object"

    def test_create_llm_prompt_without_schema(self, tmp_path):
        """Test creating LLM prompt when template has no schema."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        simple_prompt = {"system_role": "Simple", "template": "Hello {{ user }}"}
        with open(prompts_dir / "simple.yaml", "w") as f:
            yaml.dump(simple_prompt, f)

        service = PromptService(prompts_dir=prompts_dir)
        prompt_data = service.create_llm_prompt("simple", {"user": "Bob"})

        assert prompt_data["system_role"] == "Simple"
        assert prompt_data["prompt"] == "Hello Bob"
        assert prompt_data["output_schema"] is None

    def test_create_llm_prompt_integration(self, tmp_path):
        """Test create_llm_prompt integrates all methods correctly."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        complex_prompt = {
            "system_role": "File analyzer",
            "template": "Analyzing file of size: {{ size | filesizeformat }}",
            "output_schema": {"type": "object", "properties": {"analysis": {"type": "string"}}},
        }
        with open(prompts_dir / "complex.yaml", "w") as f:
            yaml.dump(complex_prompt, f)

        service = PromptService(prompts_dir=prompts_dir)
        # Use a size that will produce a clean MB value
        size_in_bytes = 512 * 1024 * 1024  # Exactly 512 MB
        prompt_data = service.create_llm_prompt("complex", {"size": size_in_bytes})

        assert prompt_data["system_role"] == "File analyzer"
        # Verify the file size is formatted (check for "MB" at minimum)
        assert " MB" in prompt_data["prompt"]
        assert "Analyzing file of size:" in prompt_data["prompt"]
        assert prompt_data["output_schema"]["properties"]["analysis"]["type"] == "string"


@pytest.mark.unit
@pytest.mark.service
class TestPromptServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_load_invalid_yaml_raises_error(self, tmp_path):
        """Test loading invalid YAML raises yaml.YAMLError."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create invalid YAML file
        invalid_file = prompts_dir / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: :")

        service = PromptService(prompts_dir=prompts_dir)

        with pytest.raises(yaml.YAMLError):
            service.load_template("invalid.yaml")

    def test_render_with_complex_jinja_logic(self, tmp_path):
        """Test rendering template with complex Jinja2 logic."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        complex_template = {
            "template": """
{% if items %}
Items:
{% for item in items %}
  - {{ item }}
{% endfor %}
{% else %}
No items
{% endif %}
            """
        }
        with open(prompts_dir / "complex.yaml", "w") as f:
            yaml.dump(complex_template, f)

        service = PromptService(prompts_dir=prompts_dir)

        # Test with items
        rendered = service.render_prompt("complex", {"items": ["apple", "banana"]})
        assert "Items:" in rendered
        assert "apple" in rendered
        assert "banana" in rendered

        # Test without items
        rendered = service.render_prompt("complex", {"items": []})
        assert "No items" in rendered

    def test_multiple_templates_in_same_service(self, sample_prompts_dir):
        """Test loading multiple templates from the same service instance."""
        service = PromptService(prompts_dir=sample_prompts_dir)

        template1 = service.load_template("sample")
        template2 = service.load_template("simple")

        assert template1["system_role"] == "You are a helpful assistant"
        assert template2["system_role"] == "Simple assistant"

        # Verify templates are independent
        assert template1 != template2
