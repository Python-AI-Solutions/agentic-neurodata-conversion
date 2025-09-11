# Condense NWB-LinkML Specification

This workflow condenses the NWB-LinkML specification for schema validation.

## Purpose

- Extract LinkML schema definitions from NWB
- Generate JSON Schema for validation
- Create Pydantic models for type checking
- Minimize token usage while preserving essential structure

## Workflow Steps

1. Load NWB-LinkML schemas
2. Extract core classes and slots
3. Generate JSON Schema from LinkML
4. Create Pydantic models for validation

## Output

- Condensed LinkML spec: `etl/prompt-input-data/condensed-nwb-linkml-spec/`
- JSON Schema: `etl/prompt-input-data/condensed-nwb-linkml-spec/json-schema/`
- Pydantic models: `etl/prompt-input-data/condensed-nwb-linkml-spec/pydantic/`

## Usage

```bash
pixi run python condense_linkml_spec.py
```

## Dependencies

- linkml
- linkml-runtime
- pydantic
- nwb-linkml
