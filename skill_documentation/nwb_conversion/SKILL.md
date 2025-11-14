---
name: nwb_conversion
version: 0.1.0
description: Converts neurophysiology data to NWB format with automatic format detection and intelligent error handling
category: data_conversion
author: Agentic Neurodata Conversion Team
tags:
  - neuroscience
  - nwb
  - data-conversion
  - neurophysiology
  - spikeglx
  - openephys
  - neuropixels
  - electrophysiology
dependencies:
  neuroconv: ">=0.6.3"
  pynwb: ">=2.8.2"
  hdmf: ">=3.14.5"
  numpy: "*"
  pydantic: ">=2.0.0"
  spikeinterface: "*"
  neo: "*"
supported_formats:
  - SpikeGLX
  - OpenEphys
  - OpenEphysBinary
  - Neuropixels
  - Blackrock
  - Axona
  - Neuralynx
  - Plexon
input_files:
  - "*.bin"
  - "*.dat"
  - "*.continuous"
  - "*.meta"
  - "*.xml"
  - "structure.oebin"
  - "settings.xml"
output_format: "*.nwb"
estimated_duration: "2-10 minutes per GB"
implementation: backend/src/agents/conversion_agent.py
---

# Skill: NWB Conversion

## Purpose
Automatically detect neurophysiology data formats and convert them to NWB (Neurodata Without Borders) standard format, ensuring FAIR data principles (Findable, Accessible, Interoperable, Reusable). This skill is the technical core of the conversion system, handling all format-specific operations.

## When to Use This Skill

### ✅ USE When:
- User has uploaded neurophysiology recording files (.bin, .dat, .continuous)
- User mentions formats: "SpikeGLX", "OpenEphys", "Neuropixels", "Intan"
- Task involves: "convert to NWB", "standardize data", "prepare for sharing"
- User needs: DANDI archive submission, lab data sharing, long-term archival
- Metadata has been collected and conversion should proceed
- Re-conversion is needed after corrections

### ❌ DON'T USE When:
- Files are already in NWB format (`.nwb` extension)
- User wants data analysis, not conversion
- Data is not neurophysiology (e.g., behavioral videos, CSV tables)
- User only wants file inspection/preview (use inspection tools instead)
- Metadata collection is incomplete (conversation agent handles this)
- Validation is needed (evaluation agent handles this)

## Capabilities

### 1. Format Detection
- **LLM-First Detection**: Uses AI to intelligently analyze file structures
- **Pattern Matching Fallback**: Fast hardcoded detection for common formats
- **Confidence Scoring**: Returns confidence level (high/ambiguous)
- **Multi-format Support**: Detects SpikeGLX, OpenEphys, Neuropixels, and more

**Detection Logic**:
```
1. Try LLM-based detection (if available)
   → Analyzes file names, directory structure, content patterns
   → Returns confidence score (0-100%)
   → Accepts if confidence > 70%

2. Fallback to pattern matching
   → SpikeGLX: *.ap.bin, *.lf.bin, *.nidq.bin + *.meta files
   → OpenEphys: structure.oebin or settings.xml + continuous/ folder
   → Neuropixels: *.imec*.bin or *.nidq.bin files

3. Return result
   → format: "SpikeGLX" (if detected)
   → confidence: "high" or "ambiguous"
   → supported_formats: List of all supported formats
```

### 2. NWB Conversion
- **NeuroConv Integration**: Uses NeuroConv library for standardized conversion
- **Metadata Mapping**: Converts flat user metadata to NWB nested structure
- **Progress Tracking**: Reports progress at 10%, 20%, 30%, ..., 100%
- **LLM Narration**: Provides friendly progress updates during conversion
- **Parameter Optimization**: LLM suggests optimal compression settings
- **Stream Detection**: Automatically selects best data stream (for SpikeGLX)
- **File Versioning**: Creates versioned backups during reconversions

**Conversion Workflow**:
```
1. Initialize (10%) - Load format-specific interface
2. Analyze (20%) - Examine file size and characteristics
3. Optimize (30%) - LLM suggests compression parameters
4. Process (50-80%) - Run NeuroConv conversion
5. Verify (95%) - Check NWB file integrity
6. Checksum (98%) - Calculate SHA256 hash
7. Complete (100%) - Return output path and checksum
```

### 3. Error Handling
- **LLM Error Explanation**: Converts technical errors to user-friendly messages
- **Automatic Cleanup**: Removes partial/corrupt files on conversion failure
- **Detailed Logging**: Records all steps for debugging
- **Recovery Suggestions**: Provides actionable fix recommendations

### 4. Correction & Reconversion
- **Apply Corrections**: Merges automatic fixes and user input
- **Version Previous Files**: Preserves previous attempts with checksums
- **Unlimited Retries**: No limit on correction attempts
- **Progress Tracking**: Tracks correction attempt number

## MCP Message Handlers

This skill responds to three MCP actions:

### 1. `detect_format`
**Input**:
```json
{
  "target_agent": "conversion",
  "action": "detect_format",
  "context": {
    "input_path": "/tmp/uploads/recording.bin"
  }
}
```

**Output (Success)**:
```json
{
  "success": true,
  "result": {
    "format": "SpikeGLX",
    "confidence": "high",
    "supported_formats": ["SpikeGLX", "OpenEphys", ...]
  }
}
```

**Output (Ambiguous)**:
```json
{
  "success": true,
  "result": {
    "format": null,
    "confidence": "ambiguous",
    "message": "Format detection ambiguous - user input required",
    "supported_formats": ["SpikeGLX", "OpenEphys", ...]
  }
}
```

### 2. `run_conversion`
**Input**:
```json
{
  "target_agent": "conversion",
  "action": "run_conversion",
  "context": {
    "input_path": "/tmp/uploads/recording.bin",
    "output_path": "/tmp/outputs/session.nwb",
    "format": "SpikeGLX",
    "metadata": {
      "session_description": "Example recording",
      "experimenter": "Dr. Smith",
      "institution": "MIT",
      "subject_id": "mouse001",
      "species": "Mus musculus",
      "age": "P90D",
      "sex": "M"
    }
  }
}
```

**Output (Success)**:
```json
{
  "success": true,
  "result": {
    "output_path": "/tmp/outputs/session.nwb",
    "checksum": "a1b2c3d4...",
    "message": "Conversion completed successfully"
  }
}
```

**Output (Error)**:
```json
{
  "success": false,
  "error": {
    "code": "CONVERSION_FAILED",
    "message": "The session start time format wasn't recognized. Try using ISO 8601 format like '2024-03-15T14:30:00-05:00'",
    "context": {
      "exception": "ValueError: Invalid datetime format",
      "technical_details": "Conversion failed: ..."
    }
  }
}
```

### 3. `apply_corrections`
**Input**:
```json
{
  "target_agent": "conversion",
  "action": "apply_corrections",
  "context": {
    "correction_context": {...},
    "auto_fixes": {
      "session_description": "Corrected description"
    },
    "user_input": {
      "session_start_time": "2024-03-15T14:30:00"
    }
  }
}
```

**Output (Success)**:
```json
{
  "success": true,
  "result": {
    "status": "reconversion_successful",
    "output_path": "/tmp/outputs/session.nwb",
    "attempt": 2,
    "checksum": "e5f6g7h8..."
  }
}
```

## Metadata Structure

### Input: Flat Metadata (from user)
```json
{
  "experimenter": "Dr. Smith",
  "institution": "MIT",
  "lab": "Smith Lab",
  "session_description": "Recording session",
  "subject_id": "mouse001",
  "species": "Mus musculus",
  "age": "P90D",
  "sex": "M"
}
```

### Output: Nested NWB Metadata (internal)
```json
{
  "NWBFile": {
    "experimenter": ["Dr. Smith"],
    "institution": "MIT",
    "lab": "Smith Lab",
    "session_description": "Recording session"
  },
  "Subject": {
    "subject_id": "mouse001",
    "species": "Mus musculus",
    "age": "P90D",
    "sex": "M"
  }
}
```

**Mapping Rules**:
- **NWBFile fields**: experimenter, institution, session_description, experiment_description, keywords, related_publications, session_id, lab, protocol, notes
- **Subject fields**: subject_id, species, age, sex, description, weight, strain, genotype
- **List conversion**: experimenter, keywords, related_publications auto-convert string → list
- **Fallback**: Unknown fields go to NWBFile

## Format-Specific Details

### SpikeGLX Format
**Files Required**:
- Data: `*.ap.bin` (action potential band) or `*.lf.bin` (local field) or `*.nidq.bin` (NIDAQ)
- Metadata: `*.meta` (companion metadata file)

**Detection Pattern**:
- File has `.bin` extension
- Name contains `.ap.`, `.lf.`, or `.nidq.`
- Corresponding `.meta` file exists

**Interface**: `SpikeGLXRecordingInterface(folder_path, stream_id)`

**Stream Selection**: Automatically selects first non-SYNC stream (typically `imec0.ap`)

### OpenEphys Format
**Files Required**:
- New format (>=0.4.0): `structure.oebin` file
- Old format (<0.4.0): `settings.xml` file
- Binary format: `continuous/` folder with `.dat` or `.continuous` files

**Detection Pattern**:
- Directory contains `structure.oebin` OR
- Directory contains `settings.xml` OR
- Directory contains `continuous/` subfolder with data files

**Interface**: `OpenEphysRecordingInterface(folder_path)`

### Neuropixels Format
**Files Required**:
- Probe data: `*.imec*.bin` files (e.g., `recording.imec0.ap.bin`)
- NIDAQ data: `*.nidq.bin` files
- Metadata: Corresponding `*.meta` files

**Detection Pattern**:
- File name contains `.imec` AND `.bin` OR
- File name contains `.nidq.`

**Interface**: Uses `SpikeGLXRecordingInterface` (Neuropixels uses SpikeGLX format)

## Performance Characteristics

| File Size | Expected Duration | RAM Usage | Disk Space Required |
|-----------|------------------|-----------|---------------------|
| 100 MB    | 20-40 seconds    | 500 MB    | 130 MB (1.3x)       |
| 1 GB      | 2-4 minutes      | 2 GB      | 1.3 GB (1.3x)       |
| 10 GB     | 10-20 minutes    | 8 GB      | 13 GB (1.3x)        |
| 50 GB     | 45-90 minutes    | 16 GB     | 65 GB (1.3x)        |

**Notes**:
- Conversion time depends on I/O speed and CPU
- RAM usage scales with file size (buffering)
- Output typically 1.1-1.3x input size (with compression)
- LLM operations add minimal overhead (~1-2 seconds total)

## Common Errors and Solutions

### Error 1: "Format detection ambiguous - user input required"
**Cause**: File structure doesn't match known patterns clearly

**Solution**:
1. Agent should ask user: "What format is this data in?"
2. Show list of supported formats
3. User selects format manually
4. Proceed with selected format

### Error 2: "Missing input_path in detect_format request"
**Cause**: MCP message missing required field

**Solution**: Ensure `context.input_path` is set in MCP message

### Error 3: "Unsupported format: XYZ"
**Cause**: Format not in supported list or typo

**Solution**:
1. Check format name spelling (case-sensitive)
2. Verify format is in supported list
3. If format should be supported, update format_map in code

### Error 4: "Cannot parse filename" (SpikeGLX)
**Cause**: SpikeGLX files don't follow expected naming convention

**Expected Format**: `<name>_g<gate>_t<trigger>.imec<probe>.ap.bin`

**Solution**:
1. Rename files to match SpikeGLX naming convention
2. Ensure `.meta` file has matching name
3. If files are valid, may need to update parser

### Error 5: "Failed to initialize OpenEphys interface"
**Cause**: Missing `structure.oebin` or `settings.xml`

**Solution**:
1. Verify file is complete OpenEphys dataset
2. Check for `structure.oebin` (new format) or `settings.xml` (old format)
3. Ensure `continuous/` folder exists with data files

### Error 6: "Conversion failed" (generic)
**Cause**: Various possible issues (metadata, file corruption, disk space)

**Solution**:
1. Check LLM-generated error explanation (user-friendly message)
2. Review technical_details in error context
3. Common fixes:
   - Fix metadata format (e.g., session_start_time)
   - Free up disk space
   - Re-upload data if corrupt
   - Simplify metadata values

### Error 7: Partial/corrupt NWB file remains after error
**Note**: This is automatically handled!

**Automatic Fix**:
- System detects conversion failure
- Deletes partial `.nwb` file automatically
- Logs cleanup action
- User doesn't see corrupt file

## Integration with Other Skills

### Upstream Skills (Called Before):
- **Orchestration Skill**: Routes conversion requests, manages workflow
- **File Upload**: Provides input_path
- **Metadata Collection**: Provides required metadata

### Downstream Skills (Called After):
- **NWB Validation Skill**: Validates conversion output
- **Report Generation**: Creates human-readable summary

### Parallel Skills (Used Concurrently):
- **Progress Tracking**: Updates progress bar during conversion
- **Logging Service**: Records detailed logs

## Workflow Example

### Scenario: Convert SpikeGLX Recording

**Step 1: Format Detection**
```
Conversation Agent → Conversion Agent: detect_format
Input: /uploads/recording.ap.bin

Conversion Agent:
1. Tries LLM detection → 85% confidence "SpikeGLX"
2. Accepts (>70% threshold)
3. Returns: format="SpikeGLX", confidence="high"
```

**Step 2: Metadata Collection**
```
(Handled by Conversation Agent - not this skill)
Collects: experimenter, institution, subject_id, species, age, sex, etc.
```

**Step 3: Conversion**
```
Conversation Agent → Conversion Agent: run_conversion
Input:
  - input_path: /uploads/recording.ap.bin
  - output_path: /outputs/session.nwb
  - format: SpikeGLX
  - metadata: {experimenter: "Dr. Smith", ...}

Conversion Agent:
1. Initialize SpikeGLXRecordingInterface
2. Detect streams → select "imec0.ap"
3. LLM suggests: "Use gzip compression for 1.5GB file"
4. Map flat metadata → nested NWB structure
5. Run NeuroConv conversion
6. Calculate SHA256 checksum
7. Return: output_path + checksum
```

**Step 4: Validation**
```
(Handled by Evaluation Agent - not this skill)
Runs NWB Inspector on output file
```

## LLM-Enhanced Features

### Feature 1: Intelligent Format Detection
**When**: Format is ambiguous from file patterns
**How**: LLM analyzes file structure, naming, content
**Benefit**: Handles edge cases, non-standard naming, novel formats

### Feature 2: Progress Narration
**When**: During conversion (starting, processing, finalizing, complete)
**How**: LLM generates friendly progress messages
**Benefit**: Better user experience vs generic messages

### Feature 3: Error Explanation
**When**: Conversion fails with technical error
**How**: LLM translates exception to user-friendly explanation
**Benefit**: Users understand what went wrong + how to fix

### Feature 4: Parameter Optimization
**When**: Before conversion starts
**How**: LLM suggests compression settings based on file size/format
**Benefit**: Optimized output for DANDI submission

**Graceful Degradation**: All LLM features have fallbacks if LLM unavailable

## State Management

### GlobalState Fields Used:
- **input_path**: Source data path (read)
- **output_path**: NWB file path (write)
- **metadata**: Flat user metadata (read)
- **current_phase**: Conversion status (write)
- **progress**: Current progress % (write)
- **checksums**: SHA256 hashes (write)
- **correction_attempt**: Retry count (read/write)
- **logs**: Detailed activity log (write)

### Status Updates:
- `DETECTING_FORMAT`: During format detection
- `CONVERTING`: During NWB conversion
- Updates via `state.update_status()` and `state.update_progress()`

## Testing Checklist

- [ ] Format detection works for all supported formats
- [ ] Ambiguous detection returns correct response
- [ ] Conversion succeeds with valid metadata
- [ ] Conversion fails gracefully with invalid metadata
- [ ] LLM error explanation generates helpful messages
- [ ] LLM format detection has reasonable confidence scores
- [ ] Progress updates from 0% to 100%
- [ ] Checksums calculated correctly
- [ ] Partial files cleaned up on error
- [ ] Versioning works during reconversions
- [ ] Metadata mapping (flat → nested) correct
- [ ] Stream detection works for SpikeGLX
- [ ] All MCP handlers respond correctly

## Version History

### v0.1.0 (2025-10-17)
- Initial skill documentation
- Support for SpikeGLX, OpenEphys, Neuropixels
- LLM-first format detection
- Intelligent error handling
- Progress narration
- Parameter optimization
- Automatic file cleanup on errors
- Unlimited correction attempts

### Planned Features (v0.2.0):
- Batch conversion support (multiple files)
- Streaming conversion (low-memory mode)
- Custom metadata templates (save/load)
- More format support (Intan, Neuralynx, Plexon)
- Real-time preview during conversion

## References

- [NWB Format Specification](https://nwb-schema.readthedocs.io/)
- [NeuroConv Documentation](https://neuroconv.readthedocs.io/)
- [SpikeGLX Documentation](https://billkarsh.github.io/SpikeGLX/)
- [OpenEphys Documentation](https://open-ephys.org/)
- [DANDI Archive Guidelines](https://www.dandiarchive.org/)
- [Implementation Code](backend/src/agents/conversion_agent.py)

## Security Notes

### File System Access:
- **Read**: User-uploaded files in `/tmp/uploads/`
- **Write**: NWB output files in `/tmp/outputs/`
- **No network access** during conversion (all local processing)

### Data Privacy:
- No data sent to external APIs during conversion
- LLM features use local/private LLM service only
- All processing happens on local server
- Temporary files managed securely

### Sandboxing Recommendations:
- Run conversion in isolated environment (Docker container)
- Limit file system access to specific directories
- Set resource limits (memory: 16GB, CPU: 80%, disk: depends on data)
- Monitor for suspicious file operations

---

**Last Updated**: 2025-10-17
**Maintainer**: Agentic Neurodata Conversion Team
**License**: MIT
**Support**: GitHub Issues
