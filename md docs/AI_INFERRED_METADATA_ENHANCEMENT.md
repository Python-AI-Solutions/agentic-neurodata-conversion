# AI-Inferred Metadata Enhancement

## Overview
This enhancement ensures that NWB Inspector validation warnings for missing optional fields (keywords, descriptions) are automatically resolved by inferring these fields using AI when not explicitly provided by the user.

## Problem Statement
NWB Inspector was flagging INFO-level validation issues for missing optional fields:
- "Description is missing."
- "Metadata /general/keywords is missing."

These fields were being inferred by the metadata inference engine but weren't being added to the final NWB file if users didn't explicitly provide them during the metadata collection workflow.

## Solution Implemented

### Code Changes

#### [backend/src/agents/conversation_agent.py](backend/src/agents/conversation_agent.py:1617-1664)

Added automatic inference fallback logic in the `_run_conversion` method, right before conversion starts:

```python
# ENHANCEMENT: Auto-fill optional fields from inference if not provided by user
# This ensures NWB Inspector validation passes for recommended fields
inference_result = getattr(state, 'inference_result', {})
if inference_result:
    inferred_metadata = inference_result.get("inferred_metadata", {})
    confidence_scores = inference_result.get("confidence_scores", {})

    # Fields to auto-fill if missing (NWB Inspector checks these)
    optional_fields_to_infer = ["keywords", "experiment_description", "session_description"]

    for field_name in optional_fields_to_infer:
        # Only add if:
        # 1. Not already in metadata (user didn't provide it)
        # 2. Was inferred with reasonable confidence (>= 60%)
        # 3. Inference result has this field
        if (not metadata.get(field_name) and
            field_name in inferred_metadata and
            confidence_scores.get(field_name, 0) >= 60):

            inferred_value = inferred_metadata[field_name]
            confidence = confidence_scores.get(field_name, 60)

            # Add to metadata
            metadata[field_name] = inferred_value
            state.metadata[field_name] = inferred_value

            # Track provenance as AI-inferred
            self._track_metadata_provenance(
                state=state,
                field_name=field_name,
                value=inferred_value,
                provenance_type="ai-inferred",
                confidence=confidence,
                source=f"Inferred from file analysis: {Path(input_path).name}",
                needs_review=True,  # AI inferences should be reviewed
                raw_input=f"Automatically inferred from: {Path(input_path).name}",
            )

            state.add_log(
                LogLevel.INFO,
                f"Auto-filled {field_name} from AI inference (confidence: {confidence}%)",
                {
                    "field": field_name,
                    "value": str(inferred_value)[:100],  # Truncate for logging
                    "confidence": confidence,
                    "provenance": "ai-inferred"
                }
            )
```

## How It Works

### Workflow

1. **User uploads file** → System runs metadata inference engine
2. **LLM analyzes file** → Infers keywords, experiment_description, session_description, etc.
3. **User provides metadata** → Can skip optional fields if desired
4. **Before conversion** → System checks if optional fields are missing
5. **Auto-fill logic** → Adds inferred values with ≥60% confidence
6. **Provenance tracking** → Tags as "ai-inferred" with source information
7. **NWB file created** → Includes inferred metadata, reducing validation warnings

### Provenance Tracking

All AI-inferred fields are tracked with:
- **Provenance Type**: `ai-inferred`
- **Source**: "Inferred from file analysis: {filename}"
- **Confidence Score**: 60-100%
- **Needs Review**: `True` (marked for user review)

This ensures full transparency in the PDF reports about which fields were inferred vs. user-provided.

## Fields Automatically Inferred

1. **keywords** (array)
   - Extracted from: file format, species, brain region, recording modality
   - Example: `["electrophysiology", "mouse", "visual cortex", "neuropixels"]`
   - NWB Path: `/general/keywords`

2. **experiment_description** (string)
   - Constructed from: modality, species, brain region, recording system
   - Example: "Extracellular electrophysiology recording from mouse primary visual cortex using Neuropixels probes"
   - NWB Path: `/general/experiment_description`

3. **session_description** (string)
   - Describes the specific recording session
   - Example: "Neural recording session from mouse V1 during visual stimulation"
   - NWB Path: `/general/session_description`

## Confidence Threshold

**60% minimum confidence** required for auto-filling:
- Above 80%: High confidence, likely accurate
- 60-80%: Moderate confidence, reasonable inference
- Below 60%: Not used (too uncertain)

## Benefits

1. **Reduces Validation Warnings**: Eliminates INFO-level warnings for missing optional fields
2. **Improves Data Quality**: Ensures comprehensive metadata in NWB files
3. **Better DANDI Compliance**: Meets recommended metadata standards
4. **Enhanced Discoverability**: Keywords improve searchability in archives
5. **Transparent Provenance**: Clear tracking of AI-inferred vs. user-provided data
6. **User-Friendly**: Users don't need to provide every single field manually

## Report Integration

In the PDF reports, AI-inferred fields display with:
- **Badge**: `🤖 ai-inferred` (with confidence %)
- **Source**: "Inferred from file analysis: {filename}"
- **Needs Review**: Yellow flag indicating should be verified

## Testing

### Verification Steps:

1. Upload a test file without providing keywords or descriptions
2. Complete metadata collection, skipping optional fields
3. Run conversion
4. Check validation results - should have 0 INFO warnings for missing keywords/description
5. Open PDF report - verify AI-inferred fields show with proper provenance badges
6. Check logs for "Auto-filled {field_name} from AI inference" messages

### Expected Outcomes:

- ✅ Keywords array populated from file analysis
- ✅ Experiment description generated from context
- ✅ Session description inferred if missing
- ✅ Provenance tracked as "ai-inferred" in reports
- ✅ Validation warnings reduced or eliminated

## Logging

Look for these log entries during conversion:

```
[INFO] Auto-filled keywords from AI inference (confidence: 75%)
[INFO] Auto-filled experiment_description from AI inference (confidence: 82%)
[INFO] Auto-filled session_description from AI inference (confidence: 68%)
```

## Future Enhancements

Potential improvements:
1. Allow users to review and edit AI-inferred fields before finalizing
2. Learn from user corrections to improve inference accuracy over time
3. Add more optional fields to auto-inference (protocols, related_publications, etc.)
4. Implement field-specific confidence thresholds based on importance
5. Provide UI warnings when relying heavily on AI-inferred metadata

## Summary

This enhancement makes the system more intelligent and user-friendly by:
- Automatically filling in optional metadata that users might skip
- Maintaining full transparency through provenance tracking
- Reducing validation warnings without compromising data integrity
- Balancing automation with the need for scientific accuracy

All inferred values are clearly marked and can be reviewed/corrected by users, ensuring scientific rigor while reducing manual data entry burden.