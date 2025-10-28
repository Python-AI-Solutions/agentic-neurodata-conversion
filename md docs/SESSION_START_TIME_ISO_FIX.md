# Session Start Time ISO 8601 Format Fix

## Issue
The conversion was failing with "Failed to start conversion: [object Object]" error when users provided natural language dates like "15th august 2025 around 10 am". The system wasn't converting these dates to the required ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`).

## Root Cause
The intelligent metadata parser wasn't properly converting natural language dates to ISO 8601 format, even though the NWB specification requires `session_start_time` to be in this exact format.

## Solution Implemented

### 1. Enhanced LLM Prompts
Added explicit instructions in [backend/src/agents/intelligent_metadata_parser.py](backend/src/agents/intelligent_metadata_parser.py):

```python
# In batch parsing prompt (lines 157-159):
- Session Start Time: ISO 8601 datetime format (e.g., "2025-08-15T10:00:00" for "August 15th, 2025 at 10:00 AM")
  IMPORTANT: For dates like "15th august 2025 around 10 am", convert to "2025-08-15T10:00:00"
  For dates without time, use 00:00:00 (e.g., "2025-08-15T00:00:00")

# In single field parsing prompt (lines 298-299):
{"CRITICAL: This is a datetime field. You MUST convert ANY date/time input to ISO 8601 format (YYYY-MM-DDTHH:MM:SS)." if field_schema.field_type.value == "date" else ""}
{"Examples: '15th august 2025 around 10 am' → '2025-08-15T10:00:00', 'January 1, 2024 3pm' → '2024-01-01T15:00:00'" if field_schema.field_type.value == "date" else ""}
```

### 2. Post-Processing Date Validation
Added `_post_process_date_field` method (lines 581-629) that:
- Checks if a field is a date type
- Validates if the value is already in ISO format
- Uses `dateutil.parser` to parse natural language dates
- Converts to ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`)
- Handles common phrases like "around", "approximately", "about"

### 3. Integration Points
- Applied post-processing in `parse_natural_language_batch` (lines 223-227)
- Applied post-processing in `parse_single_field` (lines 356-360)
- Both methods now ensure dates are properly formatted before returning

## Testing Instructions

### Test Case 1: Natural Language Date
1. Start the backend server: `pixi run dev`
2. Open the frontend at http://localhost:3000
3. Upload a test file (e.g., Noise4Sam_g0_t0.imec0.ap.bin)
4. When asked for metadata, provide:
   ```
   it was a mouse brain activity recording session conducted on 15th august 2025 around 10 am
   ```
5. Verify the system parses it to: `session_start_time: 2025-08-15T10:00:00`
6. Confirm metadata and proceed to conversion
7. **Expected Result**: Conversion should start successfully without "[object Object]" error

### Test Case 2: Various Date Formats
Test these inputs to ensure they all convert properly:
- "January 1st, 2024 at 3pm" → `2024-01-01T15:00:00`
- "March 15, 2025 10:30 AM" → `2025-03-15T10:30:00`
- "2025-08-15 around noon" → `2025-08-15T12:00:00`
- "yesterday at 2:30 PM" → (converts to actual date)

### Test Case 3: Pre-formatted ISO Date
1. Provide an already formatted date: `2025-08-15T10:00:00`
2. Verify it passes through unchanged
3. Conversion should work without issues

## Verification Points

### Backend Logs
Look for these log messages:
```
[INFO] Parsed session_start_time: '15th august 2025 around 10 am' → '2025-08-15T10:00:00' (confidence: XX%)
[INFO] Converted date '15th august 2025 around 10 am' to ISO format: 2025-08-15T10:00:00
```

### Frontend Display
The metadata confirmation should show:
```
✓ session_start_time = '2025-08-15T10:00:00' [AI badge]
   (from: "15th august 2025 around 10 am")
```

### API Response
The `/api/start-conversion` endpoint should return:
```json
{
  "success": true,
  "message": "Conversion started successfully"
}
```
Instead of the previous error response.

## Code Changes Summary

### Files Modified:
1. **backend/src/agents/intelligent_metadata_parser.py**
   - Added `from dateutil import parser as date_parser` import
   - Enhanced LLM prompts with explicit ISO 8601 conversion instructions
   - Added `_post_process_date_field` method for date validation/conversion
   - Integrated post-processing into both parsing methods

### Dependencies:
- `python-dateutil` library (should already be installed via pixi)

## Benefits

1. **User-Friendly**: Users can enter dates in natural language
2. **Robust Parsing**: Handles various date formats and phrases
3. **NWB Compliance**: Ensures dates meet ISO 8601 requirements
4. **Error Prevention**: Prevents conversion failures due to date format issues
5. **Transparent**: Shows both original input and converted value

## Future Enhancements

Consider adding:
1. Timezone detection based on user location
2. Support for relative dates ("last week", "2 days ago")
3. Date range validation (warn if date is in the future)
4. Custom date format preferences per user/lab

## Summary

This fix ensures that session_start_time and other date fields are properly converted from natural language to ISO 8601 format, preventing the "Failed to start conversion: [object Object]" error that occurred when users provided dates in formats like "15th august 2025 around 10 am".