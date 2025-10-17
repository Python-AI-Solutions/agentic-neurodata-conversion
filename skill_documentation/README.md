# Agent Skills Documentation

This directory contains **Agent Skills** documentation for the Agentic Neurodata Conversion system, following Anthropic's [Agent Skills framework](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills).

## What Are Agent Skills?

Agent Skills are **modular, standardized capability packages** that define what an AI agent can do. Each skill is documented in a `SKILL.md` file with:

- **Metadata** (YAML frontmatter): Version, dependencies, tags, etc.
- **Purpose**: What the skill does
- **When to Use**: Triggers and use cases
- **Capabilities**: Specific features and operations
- **Integration**: How it works with other skills
- **Examples**: Usage patterns and scenarios

## Why This Matters

**Before** (Scattered Documentation):
- Capabilities documented across code, comments, README
- Hard to understand what each agent does
- Difficult to share or reuse components
- No version tracking for features

**After** (Agent Skills):
- ✅ **Single source of truth** for each agent's capabilities
- ✅ **Easy onboarding** for new developers
- ✅ **Version tracking** with semantic versioning
- ✅ **Standardized format** recognized by AI systems
- ✅ **Shareable** with neuroscience community

## Available Skills

### 1. [nwb_conversion](./nwb_conversion/SKILL.md)
**Converts neurophysiology data to NWB format**

- **Category**: Data Conversion
- **Version**: 0.1.0
- **Key Features**:
  - LLM-first format detection (SpikeGLX, OpenEphys, Neuropixels, etc.)
  - Automatic metadata mapping (flat → nested NWB structure)
  - Progress tracking with LLM narration
  - Error explanation and recovery
  - File versioning during reconversions

**When to Use**: When converting raw neurophysiology recordings to NWB standard format.

**Depends On**: NeuroConv, PyNWB, SpikeInterface

---

### 2. [orchestration](./orchestration/SKILL.md)
**Orchestrates the complete conversion workflow**

- **Category**: Workflow Management
- **Version**: 0.1.0
- **Key Features**:
  - Natural language conversation with users
  - Pre-conversion metadata collection
  - Correction loop management (unlimited retries)
  - No-progress detection and escape options
  - Accept-as-is for files with minor issues

**When to Use**: For all user-facing interactions and workflow coordination.

**Depends On**: nwb_conversion skill, nwb_validation skill

---

### 3. [nwb_validation](./nwb_validation/SKILL.md)
**Validates NWB files using NWB Inspector**

- **Category**: Validation
- **Version**: 0.1.0
- **Key Features**:
  - NWB Inspector integration (official validation tool)
  - LLM-powered issue prioritization and explanation
  - Auto-fix vs needs-user-input categorization
  - Three-tier status: PASSED / PASSED_WITH_ISSUES / FAILED
  - Correction recommendation generation

**When to Use**: After conversion completes or when validating existing NWB files.

**Depends On**: NWB Inspector, PyNWB

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                         User                             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Orchestration Skill                     │
│  • User interaction                                      │
│  • Workflow coordination                                 │
│  • Metadata collection                                   │
│  • Correction loop management                            │
└─────────────────────────────────────────────────────────┘
              │                        │
              ▼                        ▼
┌───────────────────────┐    ┌───────────────────────┐
│  NWB Conversion Skill │    │ NWB Validation Skill  │
│  • Format detection   │    │  • NWB Inspector      │
│  • Data conversion    │    │  • Issue analysis     │
│  • Error handling     │    │  • Corrections        │
│  • File versioning    │    │  • Quality check      │
└───────────────────────┘    └───────────────────────┘
```

## Workflow Example

1. **User**: "I want to convert my SpikeGLX data to NWB"
   - **Orchestration Skill** receives request

2. **Orchestration** → **NWB Conversion**: "Detect format"
   - **NWB Conversion Skill** detects SpikeGLX

3. **Orchestration** asks user for metadata
   - User provides: experimenter, institution, description, subject details

4. **Orchestration** → **NWB Conversion**: "Run conversion"
   - **NWB Conversion Skill** converts to NWB format

5. **Orchestration** → **NWB Validation**: "Validate file"
   - **NWB Validation Skill** runs NWB Inspector

6. **IF validation fails**:
   - **NWB Validation** → **Orchestration**: Issues + corrections
   - **Orchestration** asks user for fixes
   - **Orchestration** → **NWB Conversion**: "Apply corrections"
   - Loop back to step 5

7. **IF validation passes**:
   - **Orchestration** reports success to user

## Skill Metadata Examples

### YAML Frontmatter (from SKILL.md)

```yaml
---
name: nwb_conversion
version: 0.1.0
description: Converts neurophysiology data to NWB format
category: data_conversion
tags:
  - neuroscience
  - nwb
  - spikeglx
dependencies:
  neuroconv: ">=0.6.3"
  pynwb: ">=2.8.2"
supported_formats:
  - SpikeGLX
  - OpenEphys
  - Neuropixels
implementation: backend/src/agents/conversion_agent.py
---
```

**This structured metadata enables**:
- Version compatibility checking
- Dependency resolution
- Format discovery (which skill handles SpikeGLX?)
- Implementation linking (where's the code?)

## Benefits of This Documentation

### For Developers:
- **Fast Onboarding**: Read SKILL.md files to understand system
- **Clear Responsibilities**: Each skill has single, well-defined purpose
- **Easy Debugging**: Know which skill handles what operation
- **Version Tracking**: See capability changes over time

### For Users:
- **Transparency**: Understand what the system can/can't do
- **Troubleshooting**: Match errors to specific skills
- **Feature Requests**: Know where new capabilities would fit

### For Research Community:
- **Shareability**: Package skills for other labs
- **Reproducibility**: Document exact versions used
- **Collaboration**: Contribute new skills or improvements

## How to Use These Docs

### As a Developer:

**Starting a new feature?**
1. Determine which skill it belongs to
2. Read that skill's SKILL.md
3. Update SKILL.md if adding new capabilities
4. Increment version if making breaking changes

**Debugging an issue?**
1. Identify which skill is involved
2. Check SKILL.md for common errors section
3. Follow troubleshooting steps
4. Check implementation code link

**Onboarding to project?**
1. Read this README first
2. Read orchestration/SKILL.md (workflow overview)
3. Read nwb_conversion/SKILL.md and nwb_validation/SKILL.md
4. You now understand the entire system!

### As a User:

**Want to know what the system can do?**
- Read the "Capabilities" section of each SKILL.md

**Encountering errors?**
- Check "Common Errors" sections for solutions

**Want to contribute a new format?**
- Read nwb_conversion/SKILL.md to understand format detection
- Follow "Supported Formats" section for examples

## Future Enhancements

### Phase 1: Documentation Only (✅ Complete)
- Created SKILL.md files for all agents
- Standardized metadata format
- Documented capabilities, workflows, and integration

### Phase 2: Metadata Integration (Future)
If we decide to implement progressive loading:
- Load skills from SKILL.md at runtime
- Use metadata for skill discovery and routing
- Implement version checking

### Phase 3: Progressive Loading (Future - If Scaling >50 Users)
If context usage becomes an issue:
- Load only needed skill at execution time
- Cache loaded skills per session
- Reduce context window usage by 40-60%

### Phase 4: Community Sharing (Future - If Proven in Production)
If system is successful and community wants it:
- Package skills as standalone distributions
- Publish to PyPI or GitHub
- Enable skill marketplace for neuroscience community

## Comparison: Agent Skills vs Traditional Documentation

| Aspect | Traditional Docs | Agent Skills |
|--------|-----------------|--------------|
| **Location** | Scattered (code, README, wiki) | Centralized (SKILL.md) |
| **Format** | Unstructured text | Structured (YAML + Markdown) |
| **Versioning** | Implicit (git history) | Explicit (semantic versions) |
| **Dependencies** | Documented separately | Embedded in metadata |
| **Discovery** | Manual search | Metadata queries |
| **Machine-Readable** | No | Yes (YAML frontmatter) |
| **Shareability** | Hard (tightly coupled) | Easy (self-contained) |
| **Maintenance** | Often outdated | Single source of truth |

## Related Resources

### Anthropic Resources:
- [Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

### Project Resources:
- [AGENT_SKILLS_STUDY_AND_APPLICATION.md](../AGENT_SKILLS_STUDY_AND_APPLICATION.md) - Detailed analysis of Agent Skills framework
- [COMPLETE_WORKFLOW_AND_LOGIC_BUG_ANALYSIS.md](../COMPLETE_WORKFLOW_AND_LOGIC_BUG_ANALYSIS.md) - System verification report
- [Requirements Specification](../specs/requirements.md) - Complete requirements

### Neuroscience Resources:
- [NWB Format Specification](https://nwb-schema.readthedocs.io/)
- [NeuroConv Documentation](https://neuroconv.readthedocs.io/)
- [DANDI Archive](https://www.dandiarchive.org/)

## Contributing

### Adding a New Skill

1. **Create directory**: `skill_documentation/new_skill/`
2. **Create SKILL.md**: Follow template from existing skills
3. **Required sections**:
   - YAML frontmatter with metadata
   - Purpose and "When to Use"
   - Capabilities and workflow
   - Integration with other skills
   - Common errors and troubleshooting
4. **Update this README**: Add skill to "Available Skills" section
5. **Test**: Ensure examples are accurate and runnable

### Updating an Existing Skill

1. **Read current SKILL.md**: Understand existing capabilities
2. **Make changes**: Update relevant sections
3. **Version bump**:
   - Patch (0.1.0 → 0.1.1): Bug fixes, clarifications
   - Minor (0.1.0 → 0.2.0): New capabilities, non-breaking changes
   - Major (0.1.0 → 1.0.0): Breaking changes, API redesign
4. **Update history**: Add entry to "Version History" section
5. **Test**: Verify documentation matches implementation

## Questions?

- **Technical Issues**: [GitHub Issues](https://github.com/yourteam/agentic-neurodata-conversion/issues)
- **Skill Clarifications**: Read the relevant SKILL.md file
- **General Questions**: Contact the maintainer team

---

**Last Updated**: 2025-10-17
**Status**: Phase 1 Complete (Documentation Only)
**Next Step**: Use these docs for development and onboarding
**Maintained By**: Agentic Neurodata Conversion Team
