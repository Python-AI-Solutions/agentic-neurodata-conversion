# Condense NWB Specification

This workflow condenses the NWB specification for use in LLM prompts.

## Purpose

- Extract essential NWB schema components
- Reduce token usage for LLM context
- Focus on commonly used NWB types

## Workflow Steps

1. Download NWB core schema
2. Parse YAML specification files
3. Extract core types and their relationships
4. Generate condensed specification

## Output

Condensed specification saved to: `etl/prompt-input-data/condensed-nwb-spec/`

## Usage

```bash
pixi run python condense_nwb_spec.py
```

## Dependencies

- pynwb
- pyyaml
- hdmf
