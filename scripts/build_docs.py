#!/usr/bin/env python
"""
Build comprehensive documentation for the agentic neurodata conversion project.

This script:
1. Generates API documentation from code
2. Validates all documentation files
3. Creates a documentation index
4. Checks for broken links and references
"""

from datetime import datetime
from pathlib import Path
import re
import subprocess
import sys


def validate_markdown_files(docs_dir: Path) -> dict[str, list[str]]:
    """Validate markdown files for common issues."""
    issues = {}

    for md_file in docs_dir.rglob("*.md"):
        file_issues = []

        try:
            content = md_file.read_text(encoding="utf-8")

            # Check for empty files
            if not content.strip():
                file_issues.append("File is empty")
                continue

            # Check for missing title (should start with # )
            lines = content.split("\n")
            if not any(line.strip().startswith("# ") for line in lines[:5]):
                file_issues.append("Missing main title (# Title)")

            # Check for broken internal links
            internal_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
            for _link_text, link_url in internal_links:
                if link_url.startswith(("http://", "https://")):
                    continue  # Skip external links

                # Check if internal file exists
                if link_url.startswith("/"):
                    # Absolute path from docs root
                    target_path = docs_dir / link_url.lstrip("/")
                else:
                    # Relative path
                    target_path = md_file.parent / link_url

                # Remove anchor if present
                if "#" in link_url:
                    target_path = Path(str(target_path).split("#")[0])

                if not target_path.exists():
                    file_issues.append(f"Broken link: {link_url}")

            # Check for TODO/FIXME comments
            todo_pattern = r"(?i)(TODO|FIXME|XXX):"
            todos = re.findall(todo_pattern, content)
            if todos:
                file_issues.append(f"Contains {len(todos)} TODO/FIXME items")

            # Check for code blocks without language specification
            code_blocks = re.findall(r"```(\w*)\n", content)
            unspecified_blocks = [block for block in code_blocks if not block]
            if unspecified_blocks:
                file_issues.append(
                    f"{len(unspecified_blocks)} code blocks without language specification"
                )

        except Exception as e:
            file_issues.append(f"Error reading file: {e}")

        if file_issues:
            issues[str(md_file.relative_to(docs_dir))] = file_issues

    return issues


def check_documentation_coverage() -> dict[str, bool]:
    """Check if all required documentation exists."""
    docs_dir = Path("docs")
    required_docs = {
        "README.md": docs_dir / "README.md",
        "API Overview": docs_dir / "api" / "README.md",
        "Architecture Overview": docs_dir / "architecture" / "README.md",
        "Development Setup": docs_dir / "development" / "setup.md",
        "MCP Tools Guide": docs_dir / "development" / "mcp-tools.md",
        "Testing Guide": docs_dir / "development" / "testing.md",
        "Contributing Guide": docs_dir / "development" / "contributing.md",
        "Troubleshooting": docs_dir / "development" / "troubleshooting.md",
        "Client Integration Examples": docs_dir / "examples" / "client-integration.md",
        "MCP Tool Examples": docs_dir / "examples" / "mcp-tool-examples.md",
    }

    coverage = {}
    for doc_name, doc_path in required_docs.items():
        coverage[doc_name] = doc_path.exists()

    return coverage


def generate_documentation_index() -> str:
    """Generate a comprehensive documentation index."""
    docs_dir = Path("docs")

    index_content = [
        "# Documentation Index",
        "",
        f"Generated on: {datetime.now().isoformat()}",
        "",
        "This is a comprehensive index of all documentation for the agentic neurodata conversion project.",
        "",
        "## Quick Start",
        "",
        "1. **Setup**: [Development Setup](development/setup.md)",
        "2. **Architecture**: [System Overview](architecture/README.md)",
        "3. **API**: [MCP Tools](api/README.md)",
        "4. **Examples**: [Client Integration](examples/README.md)",
        "",
        "## Documentation Structure",
        "",
    ]

    # Recursively build documentation tree
    def build_tree(directory: Path, level: int = 0) -> list[str]:
        items = []
        indent = "  " * level

        # Get all items and sort them
        all_items = list(directory.iterdir())
        directories = [item for item in all_items if item.is_dir()]
        files = [item for item in all_items if item.is_file() and item.suffix == ".md"]

        # Sort directories and files separately
        directories.sort(key=lambda x: x.name)
        files.sort(key=lambda x: x.name)

        # Add directories first
        for subdir in directories:
            if subdir.name.startswith("."):
                continue

            items.append(f"{indent}- **{subdir.name}/**")
            items.extend(build_tree(subdir, level + 1))

        # Add files
        for file in files:
            if file.name.startswith("."):
                continue

            # Get relative path from docs root
            rel_path = file.relative_to(docs_dir)

            # Try to get title from file
            title = file.stem.replace("_", " ").replace("-", " ").title()
            try:
                content = file.read_text(encoding="utf-8")
                # Look for first # title
                for line in content.split("\n")[:10]:
                    if line.strip().startswith("# "):
                        title = line.strip()[2:]
                        break
            except Exception:
                pass

            items.append(f"{indent}- [{title}]({rel_path})")

        return items

    tree_items = build_tree(docs_dir)
    index_content.extend(tree_items)

    # Add sections for different types of documentation
    index_content.extend(
        [
            "",
            "## By Category",
            "",
            "### Development",
            "- [Setup Guide](development/setup.md) - Environment setup and installation",
            "- [MCP Tools Development](development/mcp-tools.md) - Creating MCP tools and agents",
            "- [Testing Guidelines](development/testing.md) - Testing practices and commands",
            "- [Contributing](development/contributing.md) - Contribution workflow and standards",
            "- [Troubleshooting](development/troubleshooting.md) - Common issues and solutions",
            "",
            "### API Reference",
            "- [MCP Tools](api/mcp_tools.md) - All available MCP tools and parameters",
            "- [Agents](api/agents.md) - Internal agent interfaces",
            "- [HTTP API](api/http_api.md) - REST API endpoints",
            "- [Configuration](api/configuration.md) - Configuration options",
            "",
            "### Architecture",
            "- [System Overview](architecture/overview.md) - High-level system design",
            "- [MCP Server](architecture/mcp_server.md) - MCP server architecture",
            "",
            "### Examples",
            "- [Client Integration](examples/client-integration.md) - Integration patterns",
            "- [MCP Tool Examples](examples/mcp-tool-examples.md) - Tool implementation examples",
            "",
            "## External Resources",
            "",
            "- [NeuroConv Documentation](https://neuroconv.readthedocs.io/)",
            "- [NWB Format Specification](https://nwb-schema.readthedocs.io/)",
            "- [Model Context Protocol](https://modelcontextprotocol.io/)",
            "- [Pixi Package Manager](https://pixi.sh/)",
            "",
            "## Maintenance",
            "",
            "### Regenerating Documentation",
            "",
            "```bash",
            "# Generate API documentation",
            "pixi run python scripts/generate_api_docs.py",
            "",
            "# Build and validate all documentation",
            "pixi run python scripts/build_docs.py",
            "```",
            "",
            "### Documentation Standards",
            "",
            "- Use clear, descriptive titles",
            "- Include code examples where appropriate",
            "- Keep examples up-to-date with API changes",
            "- Use consistent formatting and structure",
            "- Include cross-references to related documentation",
        ]
    )

    return "\n".join(index_content)


def check_code_examples() -> dict[str, list[str]]:
    """Check that code examples in documentation are valid."""
    docs_dir = Path("docs")
    issues = {}

    for md_file in docs_dir.rglob("*.md"):
        file_issues = []

        try:
            content = md_file.read_text(encoding="utf-8")

            # Find Python code blocks
            python_blocks = re.findall(r"```python\n(.*?)\n```", content, re.DOTALL)

            for i, code_block in enumerate(python_blocks):
                # Basic syntax check
                try:
                    compile(code_block, f"{md_file}:block_{i}", "exec")
                except SyntaxError as e:
                    file_issues.append(
                        f"Python code block {i + 1} has syntax error: {e}"
                    )
                except Exception:
                    # Other compilation errors (like undefined names) are expected in examples
                    pass

            # Check for common issues in bash code blocks
            bash_blocks = re.findall(r"```(?:bash|sh)\n(.*?)\n```", content, re.DOTALL)

            for i, code_block in enumerate(bash_blocks):
                lines = code_block.strip().split("\n")
                for line_num, line in enumerate(lines):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Check for pixi usage
                    if (
                        "python" in line
                        and not line.startswith("pixi run")
                        and "pixi run python" not in line
                    ):
                        file_issues.append(
                            f"Bash block {i + 1}, line {line_num + 1}: Should use 'pixi run python' instead of 'python'"
                        )

        except Exception as e:
            file_issues.append(f"Error checking code examples: {e}")

        if file_issues:
            issues[str(md_file.relative_to(docs_dir))] = file_issues

    return issues


def main():
    """Main documentation build process."""
    print("🏗️  Building documentation...")

    docs_dir = Path("docs")

    # Step 1: Generate API documentation
    print("\n📚 Generating API documentation...")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/generate_api_docs.py"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.returncode == 0:
            print("✅ API documentation generated successfully")
        else:
            print("❌ API documentation generation failed:")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Error running API documentation generator: {e}")

    # Step 2: Check documentation coverage
    print("\n📋 Checking documentation coverage...")
    coverage = check_documentation_coverage()

    missing_docs = [name for name, exists in coverage.items() if not exists]
    if missing_docs:
        print("⚠️  Missing documentation files:")
        for doc in missing_docs:
            print(f"   - {doc}")
    else:
        print("✅ All required documentation files exist")

    # Step 3: Validate markdown files
    print("\n🔍 Validating markdown files...")
    validation_issues = validate_markdown_files(docs_dir)

    if validation_issues:
        print(f"⚠️  Found issues in {len(validation_issues)} files:")
        for file_path, issues in validation_issues.items():
            print(f"   📄 {file_path}:")
            for issue in issues:
                print(f"      - {issue}")
    else:
        print("✅ All markdown files are valid")

    # Step 4: Check code examples
    print("\n🧪 Checking code examples...")
    code_issues = check_code_examples()

    if code_issues:
        print(f"⚠️  Found code issues in {len(code_issues)} files:")
        for file_path, issues in code_issues.items():
            print(f"   📄 {file_path}:")
            for issue in issues:
                print(f"      - {issue}")
    else:
        print("✅ All code examples are valid")

    # Step 5: Generate documentation index
    print("\n📇 Generating documentation index...")
    try:
        index_content = generate_documentation_index()

        with open(docs_dir / "INDEX.md", "w") as f:
            f.write(index_content)

        print("✅ Documentation index generated")
    except Exception as e:
        print(f"❌ Error generating documentation index: {e}")

    # Step 6: Update main docs README
    print("\n📝 Updating main documentation README...")
    try:
        main_readme = f"""# Agentic Neurodata Conversion Documentation

Welcome to the comprehensive documentation for the agentic neurodata conversion project.

## Quick Navigation

- 🚀 **[Getting Started](development/setup.md)** - Set up your development environment
- 🏗️ **[Architecture](architecture/README.md)** - Understand the system design
- 🔧 **[API Reference](api/README.md)** - Explore available tools and endpoints
- 💡 **[Examples](examples/README.md)** - See integration patterns and usage examples
- 🤝 **[Contributing](development/contributing.md)** - Learn how to contribute

## Documentation Overview

This documentation is organized into several main sections:

### 🛠️ Development
Essential guides for developers working on the project:
- Environment setup and configuration
- MCP tools and agent development
- Testing guidelines and best practices
- Contribution workflow and standards
- Troubleshooting common issues

### 📖 API Reference
Comprehensive reference for all APIs:
- MCP tools and their parameters
- Internal agent interfaces
- HTTP API endpoints and responses
- Configuration options and environment variables

### 🏛️ Architecture
System design and architecture documentation:
- High-level system overview
- MCP server architecture details
- Component interactions and data flow

### 💻 Examples
Practical examples and integration patterns:
- Client integration examples (Python, JavaScript, CLI)
- MCP tool implementation examples
- Complete workflow demonstrations

## Key Features

- **MCP Server**: Central orchestration layer for dataset conversion
- **Multi-Agent System**: Specialized agents for different conversion tasks
- **NeuroConv Integration**: Automated script generation and execution
- **Quality Assurance**: Built-in validation and evaluation tools
- **Flexible APIs**: HTTP REST API and Python client libraries

## Documentation Standards

All documentation follows these standards:
- Clear, actionable instructions
- Working code examples
- Cross-references to related topics
- Regular updates with API changes

## Getting Help

- 📚 **Browse the full documentation**: [INDEX.md](INDEX.md)
- 🐛 **Report issues**: Use GitHub issues for bugs and feature requests
- 💬 **Ask questions**: Use GitHub discussions for general questions
- 🔄 **Stay updated**: Check the changelog for recent changes

---

*Last updated: {datetime.now().isoformat()}*

*Documentation built automatically from source code and maintained by the development team.*
"""

        with open(docs_dir / "README.md", "w") as f:
            f.write(main_readme)

        print("✅ Main documentation README updated")
    except Exception as e:
        print(f"❌ Error updating main README: {e}")

    # Summary
    print("\n📊 Documentation Build Summary:")
    print(f"   📁 Documentation directory: {docs_dir}")
    print(f"   📄 Total markdown files: {len(list(docs_dir.rglob('*.md')))}")
    print(
        f"   ✅ Coverage: {len([x for x in coverage.values() if x])}/{len(coverage)} required docs"
    )
    print(f"   ⚠️  Validation issues: {len(validation_issues)} files")
    print(f"   🧪 Code issues: {len(code_issues)} files")

    if not missing_docs and not validation_issues and not code_issues:
        print("\n🎉 Documentation build completed successfully!")
        return 0
    else:
        print(
            "\n⚠️  Documentation build completed with issues. Please review and fix the issues above."
        )
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
