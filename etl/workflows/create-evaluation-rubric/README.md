# Create Evaluation Rubric

This workflow defines evaluation criteria and metrics for the agentic converter.

## Purpose

- Define success metrics for conversion quality
- Create scoring rubrics for different aspects
- Establish validation criteria
- Enable systematic evaluation of LLM performance

## Evaluation Dimensions

### 1. Correctness Metrics

- Schema compliance (NWB validation)
- Data integrity (no data loss)
- Metadata completeness
- Unit conversions accuracy

### 2. Completeness Metrics

- Required fields populated
- Optional metadata extracted
- Relationships preserved
- Provenance information retained

### 3. Efficiency Metrics

- Number of user interactions required
- Token usage per conversion
- Time to completion
- Error recovery attempts

### 4. Usability Metrics

- Quality of LLM questions
- Clarity of error messages
- Helpfulness of suggestions
- User effort reduction

## Rubric Components

1. **Binary Checks** - Pass/fail validation criteria
2. **Scaled Scores** - 0-100 rating for quality aspects
3. **Comparative Metrics** - Performance vs. baseline
4. **User Feedback** - Subjective quality measures

## Output Files

- `evaluation_rubric.yaml` - Complete rubric definition
- `scoring_functions.py` - Python scoring implementations
- `validation_criteria.json` - JSON schema for validation
- `metrics_weights.yaml` - Weights for composite scores

## Usage

```bash
pixi run python create_rubric.py
```

## Integration

The rubric is used by:

- `tests/evaluation-tests/` - Automated evaluation
- `agentic-converter/` - Runtime validation
- Benchmarking scripts for model comparison
