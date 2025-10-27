# NWB Validation Report Generation - Complete Documentation

## Overview

This document provides a comprehensive guide to how reports are generated after NWB conversion, including all sections, formats, and contents.

## Report Generation Workflow

```
User uploads data
    ↓
Format Detection (SpikeGLX/OpenEphys/Neuropixels)
    ↓
NWB Conversion (with metadata)
    ↓
NWB Validation (nwbinspector)
    ↓
Report Generation (3 formats)
    ├─ PDF Report (human-readable)
    ├─ JSON Report (machine-readable)
    └─ Text Report (simple summary)
```

## Report Formats

### 1. PDF Report (`validation_report_YYYYMMDD_HHMMSS.pdf`)

**Purpose**: Human-readable, publication-quality report for documentation and sharing.

**Sections Included:**

#### **Header Section**
- **Title**: "NWB File Validation Report"
- **Date/Time**: Report generation timestamp
- **File Information**:
  - Input file path
  - Output NWB file path
  - File size
  - Creation date

#### **Executive Summary**
- **Validation Status**:
  - ✅ PASSED (no critical issues)
  - ⚠️ PASSED_WITH_WARNINGS (best practice suggestions)
  - ❌ FAILED (critical issues found)
- **Overall Assessment**: Brief summary of validation outcome
- **Key Statistics**:
  - Total issues found
  - Critical issues count
  - Warnings count
  - Best practice suggestions count

#### **Metadata Section**
- **Experiment Information**:
  - Experimenter(s)
  - Institution
  - Lab
  - Experiment description
  - Session description
  - Session start time
  - Keywords
- **Subject Information**:
  - Subject ID
  - Species (scientific + common name)
  - Sex (expanded from code)
  - Age (ISO 8601 format)
  - Weight
  - Description

#### **Validation Results Section**
- **Issues Grouped by Severity**:
  - **CRITICAL**: Must be fixed for DANDI submission
  - **BEST_PRACTICE_VIOLATION**: Should be fixed
  - **BEST_PRACTICE_SUGGESTION**: Recommended improvements

For each issue:
- **Message**: What the issue is
- **Location**: Where in the NWB file (HDF5 path)
- **Check Function**: Which validation rule detected it
- **Importance**: Why it matters
- **Suggested Fix**: How to resolve it (if available)

#### **Workflow Trace Section** (NEW!)
- **Complete Conversion Process**:
  - Input format detected
  - Conversion start/end time
  - Duration in seconds
- **Technologies Used**:
  - NeuroConv version
  - SpikeInterface version
  - PyNWB version
  - NWBInspector version
  - Python version
- **Data Provenance**:
  - Original file paths
  - Metadata sources
  - Processing steps
- **Scientific Transparency**:
  - Parameters used
  - Compression settings
  - Stream information (for electrophysiology)

#### **Recommendations Section**
- Prioritized action items
- Next steps for DANDI submission
- Best practice suggestions

#### **Footer**
- Report generation tool information
- Contact/support information

---

### 2. JSON Report (`validation_report_YYYYMMDD_HHMMSS.json`)

**Purpose**: Machine-readable format for automation, analysis, and integration.

**Complete Structure:**

```json
{
  "report_metadata": {
    "generated_at": "2025-10-27T14:30:15.123456",
    "report_version": "1.0",
    "tool": "Agentic Neurodata Conversion",
    "nwbinspector_version": "0.4.36"
  },

  "nwb_file": "/path/to/output.nwb",
  "nwb_file_size_mb": 45.67,
  "input_file": "/path/to/input/Noise4Sam_g0_t0.imec0.ap.bin",

  "validation_status": "PASSED_WITH_WARNINGS",
  "validation_timestamp": "2025-10-27T14:30:10.000000",

  "summary": {
    "total_issues": 8,
    "critical": 0,
    "best_practice_violation": 2,
    "best_practice_suggestion": 6
  },

  "issues_by_severity": {
    "CRITICAL": 0,
    "BEST_PRACTICE_VIOLATION": 2,
    "BEST_PRACTICE_SUGGESTION": 6
  },

  "issues": [
    {
      "message": "Subject object should have age specified",
      "severity": "BEST_PRACTICE_VIOLATION",
      "location": "/general/subject",
      "check_function_name": "check_subject_age",
      "importance": "HIGH",
      "file_path": "/path/to/output.nwb",
      "suggested_fix": "Add age field to Subject object using ISO 8601 duration format (e.g., 'P90D' for 90 days)",
      "object_type": "Subject",
      "object_name": "subject"
    },
    {
      "message": "Missing experimenter field in general metadata",
      "severity": "BEST_PRACTICE_SUGGESTION",
      "location": "/general/experimenter",
      "check_function_name": "check_experimenter_exists",
      "importance": "MEDIUM",
      "file_path": "/path/to/output.nwb"
    }
    // ... more issues
  ],

  "metadata": {
    "experiment": {
      "experimenter": ["Smith, Jane", "Doe, John"],
      "institution": "Massachusetts Institute of Technology",
      "lab": "Neuroscience Lab",
      "experiment_description": "Extracellular electrophysiology...",
      "session_description": "Recording session...",
      "session_start_time": "2025-10-27T10:00:00",
      "keywords": ["electrophysiology", "SpikeGLX", "neuropixels"]
    },
    "subject": {
      "subject_id": "mouse001",
      "species": "Mus musculus",
      "sex": "M",
      "age": "P90D",
      "weight": "25g",
      "description": "Adult male mouse"
    }
  },

  "workflow_trace": {
    "input_format": "SpikeGLX",
    "input_file_path": "/path/to/input/Noise4Sam_g0_t0.imec0.ap.bin",
    "conversion_start_time": "2025-10-27T14:29:45.000000",
    "conversion_end_time": "2025-10-27T14:30:08.000000",
    "conversion_duration_seconds": 23.45,

    "technologies_used": [
      "NeuroConv v0.6.3 - High-level conversion framework",
      "SpikeInterface v0.101.0 - Electrophysiology data reading",
      "PyNWB v2.8.2 - NWB file writing",
      "NWBInspector v0.4.36 - Validation",
      "Python 3.13.0"
    ],

    "data_streams": [
      {
        "stream_id": "imec0.ap",
        "stream_type": "Action Potentials (AP band)",
        "sampling_rate_hz": 30000.0,
        "num_channels": 384,
        "duration_seconds": 1.0,
        "data_shape": [30000, 384]
      }
    ],

    "conversion_parameters": {
      "compression": "gzip",
      "compression_level": 4,
      "chunking": "auto",
      "electrode_group": "Neuropixels2.0"
    },

    "metadata_sources": [
      "User-provided via API",
      "Auto-extracted from .meta file",
      "Inferred from file structure"
    ],

    "processing_steps": [
      "1. Detected SpikeGLX format from .bin/.meta file pair",
      "2. Extracted metadata from .meta file (sampling rate, channel count, probe type)",
      "3. Created SpikeGLXRecordingInterface with stream 'imec0.ap'",
      "4. Mapped user metadata to NWB schema",
      "5. Converted raw binary data to NWB ElectricalSeries",
      "6. Added electrode table with 384 channels",
      "7. Validated with NWBInspector",
      "8. Generated validation reports"
    ],

    "data_provenance": {
      "original_format": "SpikeGLX",
      "recording_device": "Neuropixels 2.0",
      "probe_serial_number": "extracted_from_meta",
      "acquisition_software": "SpikeGLX",
      "conversion_tool": "Agentic Neurodata Conversion v1.0"
    }
  },

  "statistics": {
    "total_validation_time_seconds": 2.34,
    "nwb_file_compressed": true,
    "compression_ratio": 2.3,
    "estimated_dandi_upload_time_minutes": 15
  },

  "recommendations": [
    {
      "priority": "HIGH",
      "recommendation": "Add subject age for DANDI compliance",
      "action": "Update metadata with age field in ISO 8601 format"
    },
    {
      "priority": "MEDIUM",
      "recommendation": "Add experimenter information",
      "action": "Provide experimenter name(s) in 'LastName, FirstName' format"
    }
  ],

  "dandi_readiness": {
    "ready_for_submission": false,
    "blocking_issues": ["Missing subject age", "Missing experimenter"],
    "compliance_score": 75,
    "estimated_fixes_required": 2
  }
}
```

---

### 3. Text Report (`validation_report_YYYYMMDD_HHMMSS.txt`)

**Purpose**: Simple, plain-text summary for quick viewing in terminal or logs.

**Example Content:**

```
================================================================================
NWB FILE VALIDATION REPORT
================================================================================
Generated: 2025-10-27 14:30:15
Report Version: 1.0

FILE INFORMATION
--------------------------------------------------------------------------------
NWB File: /path/to/output.nwb
File Size: 45.67 MB
Input File: /path/to/input/Noise4Sam_g0_t0.imec0.ap.bin
Input Format: SpikeGLX

VALIDATION SUMMARY
--------------------------------------------------------------------------------
Status: PASSED WITH WARNINGS ⚠️
Total Issues: 8
  - Critical: 0
  - Best Practice Violations: 2
  - Best Practice Suggestions: 6

METADATA
--------------------------------------------------------------------------------
Experimenter(s): Smith, Jane; Doe, John
Institution: Massachusetts Institute of Technology
Lab: Neuroscience Lab
Experiment: Extracellular electrophysiology recording
Session: Recording session with visual stimulation
Start Time: 2025-10-27 10:00:00

Subject Information:
  ID: mouse001
  Species: Mus musculus (House mouse)
  Sex: Male
  Age: P90D (90 days / ~13 weeks)

VALIDATION ISSUES
--------------------------------------------------------------------------------

BEST PRACTICE VIOLATIONS (2):
----------------------------------------------
1. Subject object should have age specified
   Location: /general/subject
   Importance: HIGH
   Fix: Add age field using ISO 8601 duration format

2. Missing experimenter field in general metadata
   Location: /general/experimenter
   Importance: MEDIUM

BEST PRACTICE SUGGESTIONS (6):
----------------------------------------------
1. Consider adding keywords for better discoverability
2. Add lab information
3. Include related publications if available
4. Add protocol description
5. Include stimulus information
6. Add notes about experimental conditions

WORKFLOW TRACE
--------------------------------------------------------------------------------
Input Format: SpikeGLX
Conversion Duration: 23.45 seconds

Technologies Used:
  - NeuroConv v0.6.3 - High-level conversion framework
  - SpikeInterface v0.101.0 - Electrophysiology data reading
  - PyNWB v2.8.2 - NWB file writing
  - NWBInspector v0.4.36 - Validation
  - Python 3.13.0

Data Streams:
  - Stream: imec0.ap (Action Potentials)
  - Sampling Rate: 30000.0 Hz
  - Channels: 384
  - Duration: 1.0 seconds

Processing Steps:
  1. Detected SpikeGLX format from .bin/.meta file pair
  2. Extracted metadata from .meta file
  3. Created SpikeGLXRecordingInterface
  4. Mapped user metadata to NWB schema
  5. Converted raw data to NWB ElectricalSeries
  6. Added electrode table with 384 channels
  7. Validated with NWBInspector
  8. Generated validation reports

RECOMMENDATIONS
--------------------------------------------------------------------------------
Priority: HIGH
  → Add subject age for DANDI compliance

Priority: MEDIUM
  → Add experimenter information
  → Include experiment description

DANDI SUBMISSION READINESS
--------------------------------------------------------------------------------
Ready for Submission: NO ❌
Blocking Issues: 2
  - Missing subject age
  - Missing experimenter information

Estimated Fixes Required: 2
Compliance Score: 75%

================================================================================
END OF REPORT
================================================================================

For more details, see:
  - JSON Report: validation_report_20251027_143015.json
  - PDF Report: validation_report_20251027_143015.pdf

Generated by: Agentic Neurodata Conversion v1.0
```

---

## Report Generation Code Location

**File**: [`backend/src/services/report_service.py`](backend/src/services/report_service.py)

**Key Methods:**
- `generate_pdf_report()` - Creates PDF report
- `generate_json_report()` - Creates JSON report
- `generate_text_report()` - Creates text report
- `_build_workflow_trace()` - Extracts workflow information

**Invoked By**: [`backend/src/agents/evaluation_agent.py`](backend/src/agents/evaluation_agent.py) after validation

---

## Workflow Trace - New Feature

The **Workflow Trace** section was added to provide **scientific transparency** and **reproducibility**. It includes:

1. **Complete Process Documentation**: Every step from upload to report
2. **Technology Stack**: Exact versions of all libraries used
3. **Data Provenance**: Where data came from, how it was processed
4. **Parameters**: All conversion settings (compression, chunking, etc.)
5. **Timing**: Duration of each major step

### Why Workflow Trace Matters

- **Reproducibility**: Others can replicate your conversion
- **Transparency**: Scientific community can verify the process
- **Debugging**: If issues arise, you know exactly what was done
- **DANDI Compliance**: Demonstrates proper data handling
- **Publication**: Can be cited in methods sections

---

## Report Storage

**Default Location**:
```
backend/src/outputs/
├── output.nwb
├── validation_report_YYYYMMDD_HHMMSS.pdf
├── validation_report_YYYYMMDD_HHMMSS.json
├── validation_report_YYYYMMDD_HHMMSS.txt
└── validation_history/
    └── session_YYYYMMDD_HHMMSS.json
```

**File Naming Convention**:
- Timestamp format: `YYYYMMDD_HHMMSS`
- Example: `validation_report_20251027_143015.pdf`

---

## Using Reports

### For Scientists
- **PDF**: Share with collaborators, include in lab documentation
- **Text**: Quick terminal review with `cat report.txt`

### For Automation
- **JSON**: Parse programmatically, integrate with pipelines
- Use `validation_status` field to determine next steps
- Parse `issues` array for automated fixes

### For DANDI Submission
1. Review PDF report for blocking issues
2. Fix all CRITICAL issues
3. Address BEST_PRACTICE_VIOLATIONS
4. Re-run conversion
5. Submit when `dandi_readiness.ready_for_submission === true`

---

## Example API Response

When reports are generated, the API returns:

```json
{
  "status": "completed",
  "output_path": "/path/to/output.nwb",
  "validation_status": "PASSED_WITH_WARNINGS",
  "reports": {
    "pdf": "/path/to/validation_report_20251027_143015.pdf",
    "json": "/path/to/validation_report_20251027_143015.json",
    "text": "/path/to/validation_report_20251027_143015.txt"
  },
  "summary": {
    "total_issues": 8,
    "critical": 0,
    "warnings": 2,
    "suggestions": 6
  }
}
```

---

## Summary

The report generation system provides:

✅ **3 Report Formats** - PDF, JSON, Text for different use cases
✅ **Complete Validation Results** - All issues with locations and fixes
✅ **Workflow Transparency** - Full process documentation
✅ **Metadata Summary** - Quick view of experiment details
✅ **DANDI Readiness** - Clear guidance for submission
✅ **Scientific Rigor** - Technology versions, provenance, reproducibility

All reports are automatically generated after NWB validation and saved alongside the NWB file! 🎉
