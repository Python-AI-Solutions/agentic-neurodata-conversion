# ANTHROPIC AGENT SKILLS - STUDY & APPLICATION ANALYSIS
# Comparison with Agentic Neurodata Conversion System

**Study Date**: 2025-10-17
**Source**: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
**Purpose**: Analyze Anthropic's Agent Skills framework and compare with current implementation

---

## EXECUTIVE SUMMARY

Anthropic's **Agent Skills** framework provides a modular, composable approach to building specialized AI agent capabilities. This study analyzes the framework and compares it with your current three-agent architecture.

**Key Finding**: Your system **already implements many Agent Skills principles** through its three-agent architecture, but could benefit from the **progressive disclosure** pattern and **SKILL.md** standardization approach.

---

## TABLE OF CONTENTS

1. [Anthropic Agent Skills Overview](#1-anthropic-agent-skills-overview)
2. [Core Concepts](#2-core-concepts)
3. [Technical Architecture](#3-technical-architecture)
4. [Implementation Patterns](#4-implementation-patterns)
5. [Comparison with Your System](#5-comparison-with-your-system)
6. [Opportunities for Enhancement](#6-opportunities-for-enhancement)
7. [Recommendations](#7-recommendations)

---

## 1. ANTHROPIC AGENT SKILLS OVERVIEW

### **What Are Agent Skills?**

**Definition**: Modular, composable capabilities that transform general-purpose AI agents into specialized tools for specific domains or tasks.

**Core Idea**: Instead of one giant prompt, break down agent capabilities into:
- **Discoverable modules** (skills)
- **Progressive context loading** (load only what's needed)
- **Reusable capabilities** (share across agents)
- **Standardized structure** (SKILL.md files)

### **Key Benefits**

1. **Modularity**: Each skill is self-contained
2. **Scalability**: Add capabilities without bloating context
3. **Reusability**: Skills work across different agents
4. **Context Efficiency**: Load only relevant information
5. **Maintainability**: Update skills independently

---

## 2. CORE CONCEPTS

### **2.1 Progressive Disclosure of Context**

**Problem**: Putting all information in system prompt causes:
- Context window exhaustion
- Information overload
- Reduced performance
- Higher costs

**Solution**: Three-level information hierarchy

```
Level 1: Metadata (Always Loaded)
├─ Skill name
├─ Brief description
└─ When to use this skill

Level 2: Core Instructions (Loaded on demand)
├─ Detailed task instructions
├─ Step-by-step procedures
└─ Decision trees

Level 3: Contextual Files (Loaded when needed)
├─ Code examples
├─ Reference documentation
└─ Helper scripts
```

**Example Flow**:
```
1. Agent sees: "PDF_EXTRACTION skill available for form processing"
2. Agent decides: "This task needs PDF extraction"
3. Agent loads: Full PDF_EXTRACTION skill instructions
4. Agent executes: Uses skill to complete task
```

### **2.2 SKILL.md Structure**

**Standardized Format**:

```markdown
---
name: skill_name
description: Brief one-line description
category: domain_category
version: 1.0.0
---

# Skill: [Name]

## When to Use
- Trigger condition 1
- Trigger condition 2

## Prerequisites
- Required tool 1
- Required tool 2

## Instructions
1. Step-by-step procedure
2. Decision points
3. Error handling

## Examples
[Concrete usage examples]

## Notes
[Additional context]
```

### **2.3 Modular Skill Directories**

**File Structure**:
```
skills/
├── pdf_extraction/
│   ├── SKILL.md              # Core skill definition
│   ├── extract_forms.py      # Helper script
│   └── examples/
│       └── sample_form.pdf
├── code_review/
│   ├── SKILL.md
│   └── checklist.md
└── data_analysis/
    ├── SKILL.md
    └── templates/
        └── analysis_template.py
```

---

## 3. TECHNICAL ARCHITECTURE

### **3.1 How Agent Skills Work**

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REQUEST                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  AGENT RECEIVES TASK                                         │
│  • Analyzes request                                          │
│  • Reviews available skills (metadata only)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  SKILL SELECTION                                             │
│  • Matches request to skill descriptions                     │
│  • Identifies relevant skills                                │
│  Example: "Extract data from PDF form" → PDF_EXTRACTION      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  PROGRESSIVE LOADING                                         │
│  1. Load SKILL.md core instructions                          │
│  2. Load referenced helper scripts (if needed)               │
│  3. Load example files (if needed)                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  SKILL EXECUTION                                             │
│  • Follow skill instructions                                 │
│  • Use helper tools/scripts                                  │
│  • Apply domain-specific logic                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  RETURN RESULTS                                              │
│  • Structured output                                         │
│  • Success/failure status                                    │
└─────────────────────────────────────────────────────────────┘
```

### **3.2 Key Technical Patterns**

#### **Pattern 1: Lazy Loading**

```python
# Don't load everything upfront
system_prompt = """
Available skills:
- pdf_extraction: Extract form fields from PDF documents
- code_review: Review code for quality and security
- data_analysis: Analyze datasets and generate insights

Load skills on-demand using load_skill(skill_name).
"""

# Load only when needed
if task_requires_pdf_processing:
    skill_content = load_skill("pdf_extraction")
    # Now execute with full context
```

#### **Pattern 2: Skill Composition**

```python
# Skills can call other skills
# SKILL.md for "document_processing"
---
When processing a document:
1. Use pdf_extraction skill to extract text
2. Use data_analysis skill to analyze content
3. Use report_generation skill to format output
---
```

#### **Pattern 3: Tool Integration**

```python
# Skills reference executable tools
# SKILL.md
---
Prerequisites:
- filesystem_tool: For reading PDF files
- code_execution_tool: For running extract_forms.py

Instructions:
1. Read PDF file using filesystem_tool
2. Execute extract_forms.py with code_execution_tool
3. Return structured data
---
```

---

## 4. IMPLEMENTATION PATTERNS

### **4.1 Example: PDF Form Extraction Skill**

**SKILL.md**:
```markdown
---
name: pdf_form_extraction
description: Extract form field data from PDF documents
category: document_processing
version: 1.0.0
tools_required:
  - filesystem
  - code_execution
---

# Skill: PDF Form Extraction

## When to Use
- User provides PDF form document
- Task requires extracting structured data from forms
- Need to process government forms, tax documents, etc.

## Prerequisites
- PDF file path available
- Python with PyPDF2 installed
- extract_forms.py helper script in skill directory

## Instructions

1. **Validate Input**
   - Check PDF file exists and is readable
   - Verify file is actually a PDF (not corrupted)

2. **Run Extraction**
   - Execute: `python extract_forms.py <pdf_path>`
   - Script returns JSON with form field data

3. **Process Results**
   - Parse JSON output
   - Validate required fields are present
   - Handle missing or malformed data

4. **Error Handling**
   - If extraction fails: Report specific error
   - If fields missing: Ask user for manual input
   - If PDF corrupted: Request new file

## Output Format
```json
{
  "form_type": "W-9",
  "fields": {
    "name": "John Doe",
    "ssn": "***-**-1234",
    "address": "123 Main St"
  },
  "confidence": 0.95
}
```

## Examples

Example 1: Tax Form
- Input: W-9_form.pdf
- Output: Extracted taxpayer information

Example 2: Survey Form
- Input: survey_response.pdf
- Output: Structured survey answers
```

**Helper Script (extract_forms.py)**:
```python
#!/usr/bin/env python3
"""
PDF form field extraction helper.
"""
import sys
import json
from PyPDF2 import PdfReader

def extract_form_fields(pdf_path):
    """Extract form fields from PDF."""
    reader = PdfReader(pdf_path)

    # Get form fields
    fields = {}
    if "/AcroForm" in reader.trailer["/Root"]:
        form = reader.trailer["/Root"]["/AcroForm"]
        # Extract field data...
        fields = process_acro_form(form)

    return {
        "form_type": detect_form_type(fields),
        "fields": fields,
        "confidence": calculate_confidence(fields)
    }

if __name__ == "__main__":
    pdf_path = sys.argv[1]
    result = extract_form_fields(pdf_path)
    print(json.dumps(result, indent=2))
```

### **4.2 Best Practices from Article**

#### **Practice 1: Start with Capability Gaps**

```
1. Identify what your agent struggles with
2. Create skill to fill that gap
3. Test with real scenarios
4. Iterate based on performance
```

#### **Practice 2: Design from Claude's Perspective**

```
Think: "What information would help me complete this task?"

Good Skill:
- Clear trigger conditions
- Step-by-step instructions
- Concrete examples
- Error handling guidance

Bad Skill:
- Vague descriptions
- Missing prerequisites
- No examples
- Unclear success criteria
```

#### **Practice 3: Collaborative Development**

```
1. Write initial skill draft
2. Test with Claude
3. Observe where Claude gets confused
4. Refine instructions
5. Repeat until robust
```

#### **Practice 4: Audit Untrusted Skills**

```
If loading skills from external sources:
- Review SKILL.md for malicious instructions
- Inspect helper scripts for security issues
- Verify tool usage is appropriate
- Test in sandboxed environment first
```

---

## 5. COMPARISON WITH YOUR SYSTEM

### **5.1 What You Already Have** ✅

Your three-agent architecture **already implements core Agent Skills principles**:

#### **✅ Modular Capabilities**

**Your Implementation**:
```
agents/
├── conversation_agent.py    # Skill: User Interaction & Orchestration
├── conversion_agent.py      # Skill: Format Detection & NWB Conversion
└── evaluation_agent.py      # Skill: NWB Validation & Reporting
```

**Agent Skills Equivalent**:
```
skills/
├── user_interaction/
│   └── SKILL.md
├── nwb_conversion/
│   └── SKILL.md
└── nwb_validation/
    └── SKILL.md
```

**Comparison**: ✅ **You have modular capabilities** - Your three agents are essentially three major skills

#### **✅ Specialized Domain Logic**

**Your Conversion Agent**:
```python
# Format detection - specialized skill
async def handle_detect_format(self, message, state):
    """Detect neurodata format - domain-specific capability."""
    # LLM detection first
    if self._llm_service:
        llm_result = await self._detect_format_with_llm(...)
    # Fallback to pattern matching
    return detected_format
```

**Agent Skills Pattern**: ✅ **Domain expertise encapsulated** - Your agents contain neuroscience-specific knowledge

#### **✅ Tool Integration**

**Your Implementation**:
```python
# Uses NeuroConv tool
from neuroconv import get_format_summaries

# Uses NWB Inspector tool
from nwbinspector import inspect_nwbfile
```

**Agent Skills Pattern**: ✅ **External tools integrated** - Your agents use specialized neuroscience tools

#### **✅ Composability**

**Your Message Flow**:
```
Conversation Agent (orchestrator)
    ↓ delegates to
Conversion Agent (executor)
    ↓ produces
NWB file
    ↓ passes to
Evaluation Agent (validator)
    ↓ returns to
Conversation Agent (reports to user)
```

**Agent Skills Pattern**: ✅ **Skills compose together** - Your agents work in sequence like composed skills

### **5.2 What You Don't Have** ⚠️

#### **⚠️ Progressive Disclosure**

**Current Approach**:
```python
# All agent logic loaded upfront
from agents import (
    register_conversation_agent,
    register_conversion_agent,
    register_evaluation_agent,
)

# Everything in memory all the time
```

**Agent Skills Approach**:
```python
# Load metadata only
available_agents = {
    "conversation": "Handles user interaction and orchestration",
    "conversion": "Converts neurodata to NWB format",
    "evaluation": "Validates NWB files"
}

# Load full logic only when needed
if task_requires_conversion:
    agent = load_agent("conversion")  # Load on demand
```

**Impact**: Your system loads all three agents always, even if only one is needed. For your MVP this is fine, but at scale this could be optimized.

#### **⚠️ Standardized Skill Metadata**

**Current Approach**:
```python
# No standardized metadata format
# Agent capabilities described in code docstrings
"""
Conversion Agent implementation.

Responsible for:
- Format detection
- NWB conversion using NeuroConv
- Pure technical conversion logic
"""
```

**Agent Skills Approach**:
```markdown
# agents/conversion_agent/SKILL.md
---
name: nwb_conversion
description: Convert neurodata formats to NWB using NeuroConv
category: data_conversion
version: 0.1.0
tools_required:
  - neuroconv
  - pynwb
---

## When to Use
- User has uploaded SpikeGLX, OpenEphys, or Neuropixels data
- Task requires NWB format conversion
- Format detection needed

## Instructions
[Step-by-step conversion procedure]
```

**Impact**: Harder for other developers or AI agents to discover your agent capabilities programmatically.

#### **⚠️ Skill Discovery Mechanism**

**Current Approach**:
```python
# Agents registered manually at startup
mcp_server = get_mcp_server()
register_conversation_agent(mcp_server)
register_conversion_agent(mcp_server)
register_evaluation_agent(mcp_server)
```

**Agent Skills Approach**:
```python
# Automatic skill discovery
skill_registry = SkillRegistry("./skills")
available_skills = skill_registry.discover()
# Returns: {"nwb_conversion": {...}, "nwb_validation": {...}}
```

**Impact**: Adding new agent capabilities requires code changes. Skills approach allows dropping in new SKILL.md files.

---

## 6. OPPORTUNITIES FOR ENHANCEMENT

### **6.1 Add SKILL.md Files for Documentation**

**Benefit**: Standardized documentation that both humans and AI can read

**Implementation**:

```bash
# Create skill metadata files
backend/src/agents/conversation_agent/SKILL.md
backend/src/agents/conversion_agent/SKILL.md
backend/src/agents/evaluation_agent/SKILL.md
```

**Example: conversion_agent/SKILL.md**:
```markdown
---
name: nwb_conversion
description: Convert neurophysiology data to NWB format
category: data_conversion
version: 0.1.0
author: Aditya Patane
tools_required:
  - neuroconv >= 0.6.3
  - pynwb >= 2.8.2
  - spikeinterface >= 0.101.0
supported_formats:
  - SpikeGLX
  - OpenEphys
  - Neuropixels
---

# Skill: NWB Conversion

## When to Use
- User has uploaded neurophysiology data files
- Task requires conversion to NWB (Neurodata Without Borders) format
- Format detection is needed before conversion
- Metadata mapping from flat to nested structure

## Prerequisites
- Input file or directory path
- Optional: User-provided metadata (experimenter, institution, etc.)
- NeuroConv installed with appropriate data interfaces

## Instructions

### Step 1: Format Detection
1. Analyze file structure and naming patterns
2. Try LLM-based detection first (if available, confidence > 70%)
3. Fallback to pattern matching:
   - SpikeGLX: *.ap.bin, *.lf.bin with *.meta files
   - OpenEphys: structure.oebin or settings.xml
   - Neuropixels: *.nidq.bin or imec probe files
4. Return detected format or request user selection

### Step 2: Metadata Mapping
1. Collect user-provided metadata (flat dictionary)
2. Map to NWB nested structure:
   - experimenter → NWBFile.experimenter (convert to list)
   - subject_id → Subject.subject_id
   - institution → NWBFile.institution
3. Merge with auto-extracted metadata from file

### Step 3: Conversion Execution
1. Initialize NeuroConv data interface for detected format
2. Extract metadata from data file
3. Merge user + extracted metadata
4. Execute run_conversion() with NWB output path
5. Compute SHA256 checksum of output file

### Step 4: Error Handling
- File not found: Report clear error with expected location
- Format detection failed: Request user to select format
- Conversion failed: Explain error in user-friendly terms (use LLM if available)
- Metadata missing: Report which fields are required

## Output Format
Returns NWB file path and checksum:
```json
{
  "output_path": "/path/to/output.nwb",
  "checksum": "sha256:abc123...",
  "format": "SpikeGLX",
  "metadata": {...}
}
```

## Examples

### Example 1: SpikeGLX Conversion
**Input**: Directory with `data_g0_t0.imec0.ap.bin` and `.meta` files
**Output**: `data_g0_t0.nwb` with neural recording data

### Example 2: Ambiguous Format
**Input**: Generic `.bin` file without clear naming
**Output**: Request user format selection from supported list

## Helper Scripts
- `_detect_format()`: Multi-strategy format detection
- `_map_flat_to_nested_metadata()`: Metadata transformation
- `_run_neuroconv_conversion()`: NeuroConv execution wrapper

## Notes
- Supports LLM-enhanced format detection (optional, graceful degradation)
- File versioning: Previous outputs preserved as `_v2`, `_v3`, etc.
- Progress tracking: Updates GlobalState with 0-100% progress
- Checksums: SHA256 for data integrity verification
```

**Benefits**:
- ✅ Developers understand capabilities instantly
- ✅ AI assistants can read and use agent capabilities
- ✅ Onboarding new team members faster
- ✅ Documentation stays in sync with code

### **6.2 Implement Progressive Loading (Optional)**

**Current Cost**: All agents loaded = ~8,515 lines in memory

**Optimized Cost**: Load on demand = ~2,000 lines average per request

**Implementation** (if scaling beyond single session):

```python
# services/agent_loader.py
class AgentLoader:
    """Progressive agent loading."""

    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self._metadata_cache = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Dict]:
        """Load only SKILL.md frontmatter."""
        metadata = {}
        for skill_dir in self.agents_dir.glob("*/"):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                # Parse YAML frontmatter only
                meta = self._parse_frontmatter(skill_md)
                metadata[meta["name"]] = meta
        return metadata

    def get_available_agents(self) -> List[Dict]:
        """Return lightweight agent metadata."""
        return [
            {
                "name": meta["name"],
                "description": meta["description"],
                "when_to_use": meta.get("when_to_use", [])
            }
            for meta in self._metadata_cache.values()
        ]

    def load_agent(self, agent_name: str):
        """Load full agent implementation on demand."""
        if agent_name == "conversation":
            from agents.conversation_agent import ConversationAgent
            return ConversationAgent()
        elif agent_name == "conversion":
            from agents.conversion_agent import ConversionAgent
            return ConversionAgent()
        elif agent_name == "evaluation":
            from agents.evaluation_agent import EvaluationAgent
            return EvaluationAgent()
        else:
            raise ValueError(f"Unknown agent: {agent_name}")
```

**Usage**:
```python
# Load metadata only at startup (fast)
loader = AgentLoader("backend/src/agents")
available = loader.get_available_agents()

# Load full agent only when needed (lazy)
if task_requires_conversion:
    agent = loader.load_agent("conversion")
    result = await agent.handle_run_conversion(...)
```

**When Needed**: Multi-session support with 100+ concurrent users

### **6.3 Create Sub-Skills for Complex Agents**

**Current**: Conversation Agent = 1,978 lines (monolithic)

**Opportunity**: Break into sub-skills

```
agents/
└── conversation_agent/
    ├── SKILL.md                      # Main orchestration skill
    ├── skills/
    │   ├── metadata_collection/
    │   │   ├── SKILL.md
    │   │   └── metadata_strategy.py
    │   ├── retry_management/
    │   │   └── SKILL.md
    │   ├── user_interaction/
    │   │   ├── SKILL.md
    │   │   └── conversational_handler.py
    │   └── workflow_orchestration/
    │       └── SKILL.md
    └── conversation_agent.py         # Delegates to sub-skills
```

**Benefit**: Conversation Agent can load only relevant sub-skill for current task

**Example Sub-Skill: metadata_collection/SKILL.md**:
```markdown
---
name: dandi_metadata_collection
description: Collect DANDI-required metadata from users
parent_skill: conversation
category: user_interaction
---

# Sub-Skill: DANDI Metadata Collection

## When to Use
- Before NWB conversion starts
- User hasn't provided required DANDI fields
- metadata_requests_count < 2 (prevent infinite loops)
- user_wants_minimal = False

## Required Fields
1. experimenter (scientist name)
2. institution (lab/university)
3. experiment_description or session_description

## Instructions
[Detailed metadata collection procedure]
```

**When Needed**: When conversation agent grows beyond 3,000 lines

---

## 7. RECOMMENDATIONS

### **7.1 Immediate Actions (Low Effort, High Value)** ⭐⭐⭐

#### **Action 1: Add SKILL.md Documentation**

**Effort**: 2-3 hours
**Benefit**: Better documentation, AI-readable agent capabilities

**Steps**:
1. Create `backend/src/agents/conversation_agent/SKILL.md`
2. Create `backend/src/agents/conversion_agent/SKILL.md`
3. Create `backend/src/agents/evaluation_agent/SKILL.md`
4. Follow template above with YAML frontmatter

**Result**: Developers and AI can understand agent capabilities at a glance

#### **Action 2: Document Agent Selection Logic**

**Effort**: 1 hour
**Benefit**: Clear decision tree for when to use each agent

**Create**: `backend/src/agents/README.md`
```markdown
# Agent Selection Guide

## When to Use Each Agent

### Conversation Agent
Use when:
- User interaction required
- Workflow orchestration needed
- Retry decision pending
- Metadata collection needed

### Conversion Agent
Use when:
- Format detection needed
- NWB conversion required
- Metadata mapping needed
- File versioning needed

### Evaluation Agent
Use when:
- NWB validation needed
- Quality assessment required
- Report generation needed
- Issue prioritization needed
```

### **7.2 Future Enhancements (When Scaling)** ⭐⭐

#### **Enhancement 1: Progressive Agent Loading**

**When**: Multi-session support with 50+ concurrent users
**Benefit**: Reduced memory usage per session
**Effort**: 1-2 days
**Implementation**: See section 6.2 above

#### **Enhancement 2: Sub-Skill Decomposition**

**When**: Agent files exceed 3,000 lines
**Benefit**: Better modularity, easier maintenance
**Effort**: 3-5 days
**Implementation**: See section 6.3 above

#### **Enhancement 3: Skill Marketplace/Plugin System**

**When**: External contributors want to add capabilities
**Benefit**: Ecosystem growth, community contributions
**Effort**: 1-2 weeks

**Vision**:
```
community_skills/
├── calcium_imaging_conversion/
│   └── SKILL.md
├── patch_clamp_analysis/
│   └── SKILL.md
└── miniscope_processing/
    └── SKILL.md
```

### **7.3 What NOT to Do** ❌

#### **Don't: Premature Optimization**

Your current architecture is **excellent for your use case**. Don't refactor to Agent Skills pattern unless:
- ❌ You have 100+ concurrent sessions
- ❌ Context windows are a bottleneck
- ❌ Memory usage is problematic
- ❌ Agent loading time is noticeable

#### **Don't: Over-Engineer**

Agent Skills are powerful but add complexity. Your three-agent architecture is:
- ✅ Clean and understandable
- ✅ Well-tested (267 tests)
- ✅ Production-ready
- ✅ Sufficient for MVP and beyond

**Recommendation**: Add SKILL.md files for documentation, but keep current architecture.

---

## CONCLUSION

### **Key Takeaways**

1. **Your System Already Follows Core Principles** ✅
   - Modular capabilities (three agents)
   - Specialized domain logic (neuroscience)
   - Tool integration (NeuroConv, NWB Inspector)
   - Composable workflow (agents collaborate)

2. **Anthropic's Pattern Adds Value For** ⭐
   - Documentation standardization (SKILL.md)
   - Progressive context loading (when scaling)
   - Skill discovery (programmatic capability detection)
   - Community contributions (plugin system)

3. **Immediate Action: Documentation** 📝
   - Add SKILL.md files (2-3 hours)
   - Document agent selection logic (1 hour)
   - Benefit: Better onboarding, AI-readable capabilities

4. **Future Consideration: Progressive Loading** 🔮
   - When: 50+ concurrent sessions
   - Benefit: Memory optimization, faster loading
   - Effort: 1-2 days implementation

### **Final Recommendation**

✅ **Keep your current architecture** - It's excellent and production-ready

✅ **Add SKILL.md files** - Low effort, high documentation value

⚪ **Consider progressive loading** - Only when scaling beyond 50 users

❌ **Don't over-engineer** - Your three-agent pattern is clean and sufficient

---

**Your system demonstrates many of the same principles Anthropic advocates for in their Agent Skills framework, which validates your architectural decisions.** The main opportunity is better documentation through standardized SKILL.md files.

---

**Study Complete**
**Date**: 2025-10-17
**Recommendation**: Document current agents with SKILL.md files, keep architecture as-is
