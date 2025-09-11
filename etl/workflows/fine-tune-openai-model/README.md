# Fine-tune OpenAI Model (Stretch Goal)

This workflow contains scripts for fine-tuning OpenAI's model for NWB conversion
tasks.

## Status

⚠️ **STRETCH GOAL** - Not implemented in initial version

## Purpose

- Prepare training data from successful conversions
- Fine-tune GPT model on NWB conversion tasks
- Evaluate fine-tuned model performance
- Compare with base model and other approaches

## Planned Workflow

### 1. Data Preparation

- Collect successful conversion examples
- Format as conversation pairs (input → output)
- Create validation and test splits
- Ensure diverse coverage of data types

### 2. Fine-tuning Process

- Upload training data to OpenAI
- Configure fine-tuning parameters
- Monitor training progress
- Evaluate on validation set

### 3. Model Evaluation

- Test on synthetic messy datasets
- Compare with base model performance
- Measure improvement in specific areas
- Cost-benefit analysis

## Planned Output

- Fine-tuned model ID
- Performance metrics comparison
- Training logs and configuration
- Best practices documentation

## Future Implementation

```bash
# When implemented:
pixi run python prepare_training_data.py
pixi run python fine_tune_model.py
pixi run python evaluate_fine_tuned.py
```

## Dependencies (Future)

- openai
- tiktoken
- jsonlines
- scikit-learn

## Notes

This is a stretch goal for future enhancement. Initial implementation focuses on
prompt engineering with base models.
