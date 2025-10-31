# Flexible Metadata Workflow Implementation

## Overview
This document describes the implementation of a more flexible and user-friendly metadata collection workflow that:
1. Makes all metadata fields optional (not blocking conversion)
2. Adds a metadata review step before conversion
3. Handles errors gracefully by asking for corrections instead of failing

## Key Changes

### 1. Non-Blocking Metadata Validation
**File:** [backend/src/agents/conversation_agent.py](backend/src/agents/conversation_agent.py)

#### Before (Lines 1583-1615):
```python
# Would block conversion if metadata was missing
if not is_valid:
    return MCPResponse.error_response(
        error_code="MISSING_REQUIRED_METADATA",
        error_message=explanation,
    )
```

#### After (Lines 1605-1622):
```python
# Now just warns but proceeds with conversion
if not is_valid:
    state.add_log(
        LogLevel.WARNING,
        f"Some recommended NWB metadata fields are missing: {missing_fields}"
    )
    # Store warning but DO NOT block conversion
    state.metadata['_missing_fields_warning'] = {
        'fields': missing_fields,
        'message': f"Note: Some recommended fields are missing...",
        'timestamp': datetime.now().isoformat()
    }
    # Conversion continues...
```

**Benefits:**
- Users can convert with minimal metadata
- System gracefully handles missing fields
- Warnings are logged but don't prevent conversion

### 2. Metadata Review Step
**File:** [backend/src/agents/conversation_agent.py](backend/src/agents/conversation_agent.py)

#### New Review Step (Lines 740-761):
```python
# Before starting conversion, show metadata review
if not state.metadata.get('_metadata_review_shown', False):
    state.metadata['_metadata_review_shown'] = True
    state.conversation_type = "metadata_review"

    # Generate review message showing all collected metadata
    review_message = await self._generate_metadata_review_message(
        metadata,
        detected_format,
        state
    )

    return MCPResponse.success_response(
        result={
            "status": "metadata_review",
            "message": review_message,
            "conversation_type": "metadata_review",
            "metadata": metadata,
        },
    )
```

#### Review Message Generator (Lines 1313-1414):
The `_generate_metadata_review_message` method:
- Shows all collected metadata
- Notes any missing recommended fields (without blocking)
- Asks if user wants to add more metadata
- Makes it clear they can proceed as-is

#### Handling Review Response (Lines 2764-2851):
```python
if state.conversation_type == "metadata_review":
    if user_message.lower() in ["no", "proceed", "continue", "skip", "start"]:
        # Proceed with conversion
        return await self._run_conversion(...)
    else:
        # Parse additional metadata from user input
        additional_metadata = {}
        # ... parsing logic ...
        if additional_metadata:
            state.metadata.update(additional_metadata)
            # Track provenance
            for field, value in additional_metadata.items():
                self._track_user_provided_metadata(...)
```

### 3. Graceful Error Handling
**File:** [backend/src/agents/conversation_agent.py](backend/src/agents/conversation_agent.py)

#### Validation Error Handling (Lines 2943-2999):
```python
# Instead of failing on validation errors, ask for corrections
if skip_type == "none":  # User is providing metadata
    try:
        extracted_metadata = await self._extract_metadata_from_message(
            user_message, state
        )

        # Validate extracted metadata
        validation_errors = self._validate_metadata_format(extracted_metadata)

        if validation_errors:
            # Ask user to correct instead of failing
            error_message = "I noticed some issues with the metadata format:\n\n"
            for field, error in validation_errors.items():
                error_message += f"• **{field}**: {error}\n"

            error_message += "\nCould you please provide the corrected information?"

            return MCPResponse.success_response(
                result={
                    "status": "awaiting_user_input",
                    "message": error_message,
                    "validation_errors": validation_errors,
                },
            )
    except Exception as e:
        # Handle parsing errors gracefully
        clarification_message = (
            "I had trouble understanding that. Could you please provide "
            "the metadata in one of these formats:\n\n"
            "• Natural language: 'The experiment was done by Dr. Smith at MIT...'\n"
            "• Field format: 'experimenter: Smith, John'\n"
            "• Or simply say 'skip' to proceed without this information"
        )
        return MCPResponse.success_response(...)
```

#### Metadata Format Validation (Lines 3994-4039):
```python
def _validate_metadata_format(self, metadata: Dict[str, Any]) -> Dict[str, str]:
    """Validate metadata format and return any errors."""
    errors = {}

    for field, value in metadata.items():
        field_schema = NWBDANDISchema.get_field_schema(field)

        # Field-specific validation
        if field_schema.field_type.value == "date":
            if not self._is_valid_date_format(value):
                errors[field] = "Please provide date in ISO format..."

        elif field == "sex" and value not in ["M", "F", "U"]:
            errors[field] = "Please use 'M' for male, 'F' for female..."

        elif field == "experimenter" and "," not in str(value):
            errors[field] = "Please use format 'LastName, FirstName'"

        # ... more validation rules

    return errors
```

## User Experience Flow

### 1. Upload File
User uploads their data file

### 2. Standard Metadata Collection (Optional)
System asks for standard NWB metadata but user can:
- Provide the metadata
- Skip individual fields
- Skip all remaining questions

### 3. Custom Metadata (Optional)
System asks if user wants to add custom metadata
- User can add any additional fields
- User can skip this step

### 4. **Metadata Review** (NEW)
System shows all collected metadata and asks:
```
## 📋 Metadata Review

**Format Detected:** SpikeGLX

**Metadata Collected:**
• Experimenter: Smith, Jane
• Institution: MIT
• Session Start Time: 2025-08-15T10:00:00
• Subject Id: mouse_001
• Species: Mus musculus
• Sex: M

**Note:** Some recommended fields are missing: experiment_description, session_description
These are not required but would improve DANDI compatibility.

**Would you like to add any additional metadata before conversion?**

Options:
• Type any additional metadata you want to add
• Say "add [field]: [value]" to add specific fields
• Say "proceed" or "no" to start conversion with current metadata
```

### 5. Conversion
System proceeds with whatever metadata was provided:
- Missing fields generate warnings (not errors)
- Conversion completes successfully
- Report shows what was missing

### 6. Error Handling
If user provides invalid metadata format:
```
I noticed some issues with the metadata format:

• **experimenter**: Please use format 'LastName, FirstName'
• **sex**: Please use 'M' for male, 'F' for female, or 'U' for unknown

Could you please provide the corrected information?
```

## Testing Instructions

### Test Case 1: Skip All Metadata
1. Upload a file
2. When asked for metadata, say "skip all"
3. **Expected**: System proceeds to metadata review
4. Say "proceed"
5. **Expected**: Conversion completes with warnings about missing fields

### Test Case 2: Partial Metadata with Review
1. Upload a file
2. Provide some metadata: "experimenter is Dr. Smith at MIT"
3. Skip remaining questions
4. At metadata review, add more: "subject_id: mouse_001, sex: M"
5. **Expected**: Conversion proceeds with combined metadata

### Test Case 3: Invalid Metadata Format
1. Upload a file
2. Provide invalid metadata: "sex is male" (should be "M")
3. **Expected**: System asks for correction with clear instructions
4. Provide corrected: "sex: M"
5. **Expected**: Metadata accepted and conversion proceeds

### Test Case 4: Natural Language to ISO Date
1. Upload a file
2. Provide: "session started on August 15th 2025 at 10am"
3. **Expected**: System converts to ISO format: 2025-08-15T10:00:00
4. Review shows the converted format
5. Conversion proceeds successfully

## Benefits

1. **User-Friendly**: No longer forces users to provide all metadata
2. **Flexible**: Users can add metadata at multiple points
3. **Transparent**: Review step shows exactly what will be used
4. **Graceful**: Errors result in helpful correction requests, not failures
5. **Progressive**: Can start with minimal metadata and add more as needed

## Implementation Details

### Key Components

1. **Non-blocking validation** - `_validate_required_nwb_metadata` (line 1560)
2. **Metadata review** - `_generate_metadata_review_message` (line 1313)
3. **Review response handler** - In `handle_conversational_response` (line 2764)
4. **Error correction flow** - `_validate_metadata_format` (line 3994)
5. **Metadata extraction** - `_extract_metadata_from_message` (line 3950)

### State Management

The system tracks:
- `_metadata_review_shown`: Whether review has been displayed
- `_missing_fields_warning`: Fields that are missing but not blocking
- `conversation_type`: Current conversation context (review, custom, etc.)
- `validation_errors`: Any format issues to correct

## Summary

This implementation makes the NWB conversion system significantly more user-friendly by:
1. Not forcing users to provide all metadata upfront
2. Showing a clear review of what will be used
3. Handling errors gracefully with correction requests
4. Allowing conversion to proceed with whatever metadata is available

The system maintains data quality through warnings and recommendations while respecting user autonomy to proceed with minimal metadata when needed.