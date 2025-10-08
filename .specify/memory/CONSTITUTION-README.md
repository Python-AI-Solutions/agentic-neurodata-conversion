# Constitution Versions

This directory contains multiple formats and versions of the project constitution.

## Current Version: 3.0.0

### Available Formats (v3.0.0)

### 1. constitution.md (Current/Active - Detailed Format)
- **Lines**: 1,099
- **Size**: 67KB
- **Format**: Detailed, narrative format with expanded explanations
- **Best For**: Deep understanding, comprehensive reference, detailed rationale
- **Content**: Full explanations for each principle, complete technical standards, extensive examples

**Use When**:
- Reading for comprehensive understanding
- Looking for detailed rationale behind decisions
- Need full context for governance decisions
- First-time reading of the constitution

### 2. constitution-v3.0.0-detailed.md (Backup)
- **Lines**: 1,099
- **Size**: 67KB
- **Format**: Same as constitution.md (backup copy)
- **Best For**: Version preservation
- **Content**: Identical to constitution.md

**Use When**:
- Need original detailed version for reference
- Comparing changes if constitution.md is updated

### 3. constitution-v3.0.0-hierarchical.md (Quick Reference)
- **Lines**: 1,430
- **Size**: 56KB
- **Format**: Hierarchical structure with requirement numbering (REQ-XXX-NNN)
- **Best For**: Quick navigation, finding specific requirements, cross-referencing
- **Content**: Same requirements but organized with:
  - Clear requirement IDs (REQ-MCP-001, REQ-AGENT-CONV-001, etc.)
  - Table of contents with anchor links
  - Cross-references between related requirements
  - Grouped by theme for easier scanning
  - Summary sections for technical standards
  - Condensed explanations with focus on actionable requirements

**Use When**:
- Need to find specific requirements quickly
- Cross-referencing between principles
- Citing specific requirements in PRs or discussions
- Building compliance checklists
- Creating traceability matrices

## Historical Versions

### 4. constitution-v1.0.0-original.md (Original from Git)
- **Lines**: 139
- **Size**: ~8KB
- **Version**: 1.0.0
- **Date**: Original commit (3646df6)
- **Format**: Simple, concise original constitution
- **Content**: 6 core principles (MCP-Centric, Agent Specialization, TDD, Data Integrity, Metadata Completeness, Reproducibility)

**Use When**:
- Understanding project origins
- Comparing evolution from v1.0.0 to v3.0.0
- Historical reference
- Tracing how principles evolved

## Version History

**Version 3.0.0** (2025-10-08)
- Complete rebuild from all 10 requirements.md files (1,389 lines)
- No compression - all requirements fully incorporated
- Expanded from 400 to 1,099 lines (2.7x increase)
- Detailed specifications for all 8 core principles
- Comprehensive technical standards (6 sections)
- Complete development workflow requirements
- Formal governance with enforcement mechanisms

**Version 2.0.1** (2025-10-08)
- Clarified modular architecture (10 system modules + 8 validation sub-modules)
- PATCH update to v2.0.0

**Version 2.0.0** (2025-10-08)
- First consolidation from multiple PR-specific constitutions
- MAJOR version - unified disparate constitutions

**Version 1.1.0** (Earlier)
- Expanded version from single PR
- Added additional principles

**Version 1.0.0** (Original - commit 3646df6)
- Initial constitution with 6 core principles
- 139 lines, simple and concise
- **Available as**: `constitution-v1.0.0-original.md`

## Which Format to Use?

| Task | Recommended Format |
|------|-------------------|
| Understanding principles deeply | constitution.md (Detailed) |
| Quick requirement lookup | constitution-v3.0.0-hierarchical.md |
| Citing specific requirements | constitution-v3.0.0-hierarchical.md (use REQ-IDs) |
| PR compliance review | constitution-v3.0.0-hierarchical.md (scan checklist) |
| Learning project governance | constitution.md (Detailed) |
| Building traceability matrix | constitution-v3.0.0-hierarchical.md (REQ-IDs) |
| Creating test plans | constitution-v3.0.0-hierarchical.md (Principle III) |
| Architecture discussions | Either (both have full content) |
| Understanding project evolution | constitution-v1.0.0-original.md (compare with current) |
| Historical reference | constitution-v1.0.0-original.md |

## Requirement ID System

The hierarchical format uses a systematic requirement ID system:

**Format**: `REQ-[DOMAIN]-[NUMBER]`

**Examples**:
- `REQ-MCP-001` to `REQ-MCP-009`: MCP-Centric Architecture requirements
- `REQ-AGENT-CONV-001` to `REQ-AGENT-CONV-008`: Conversation Agent requirements
- `REQ-AGENT-CONVERT-001` to `REQ-AGENT-CONVERT-008`: Conversion Agent requirements
- `REQ-TDD-001` to `REQ-TDD-009`: TDD Workflow and Quality Gates
- `REQ-TEST-MCP-001` to `REQ-TEST-MCP-006`: MCP Server Testing
- `REQ-TEST-AGENT-001` to `REQ-TEST-AGENT-006`: Agent Testing
- `REQ-TEST-E2E-001` to `REQ-TEST-E2E-006`: End-to-End Testing
- `REQ-SCHEMA-001` to `REQ-SCHEMA-005`: Schema Workflow
- `REQ-KG-001` to `REQ-KG-009`: Knowledge Graph requirements
- `REQ-VAL-001` to `REQ-VAL-019`: Validation system requirements
- `REQ-DL-001` to `REQ-DL-007`: DataLad requirements
- `REQ-PROV-001` to `REQ-PROV-003`: Provenance tracking
- `REQ-QUAL-001` to `REQ-QUAL-006`: Quality assessment
- `REQ-LOG-001` to `REQ-LOG-008`: Logging requirements
- `REQ-MON-001` to `REQ-MON-003`: Monitoring requirements

Total: **100+ numbered requirements** across all principles.

## Cross-References

Both formats are semantically identical. The hierarchical format adds:
- Requirement IDs for citation
- Cross-reference links (e.g., "See [Principle III](#iii-test-driven-development)")
- Table of contents with anchor links
- Summary sections for quicker scanning

## Maintenance

When updating the constitution:
1. Update `constitution.md` (the active detailed version)
2. Follow the amendment process in Governance section
3. Increment version per semantic versioning policy
4. Consider creating new hierarchical version if requirements change significantly
5. Update this README with new version info

## Source

All versions generated from comprehensive requirements across 10 specification files (1,389 lines total):
1. agent-implementations/requirements.md (161 lines)
2. client-libraries-integrations/requirements.md (105 lines)
3. core-project-organization/requirements.md (164 lines)
4. data-management-provenance/requirements.md (121 lines)
5. evaluation-reporting/requirements.md (67 lines)
6. knowledge-graph-systems/requirements.md (103 lines)
7. mcp-server-architecture/requirements.md (150 lines)
8. test-verbosity-optimization/requirements.md (duplicate)
9. testing-quality-assurance/requirements.md (151 lines)
10. validation-quality-assurance/requirements.md (246 lines)
