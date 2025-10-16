# Report Generation Bugs Analysis

## Issue Report

**Problem:** NWB evaluation PDF reports show "N/A" for metadata fields that actually exist in the NWB file.

**Example from User's Report:**
```
Experimenter: N/A
Institution: N/A
Species: N/A
```

But on page 2, validation shows:
```
2. [ValidationSeverity.INFO] The name of experimenter 'Aditya' does not match...
```

This proves the experimenter field EXISTS in the NWB file (value: "Aditya"), but the report shows "N/A".

---

## Root Cause Analysis

### Bug Location
**File:** [backend/src/agents/evaluation_agent.py:298-372](backend/src/agents/evaluation_agent.py#L298-L372)
**Function:** `_extract_file_info()`

### The Problem

The `_extract_file_info()` function is **incomplete**. It only extracts:
- ✅ `nwb_version`
- ✅ `file_size_bytes`
- ✅ `creation_date`
- ✅ `identifier`
- ✅ `session_description`
- ✅ `subject_id`

But it's **missing**:
- ❌ `experimenter`
- ❌ `institution`
- ❌ `lab`
- ❌ `species`
- ❌ `sex`
- ❌ `age` / `date_of_birth`
- ❌ `description` (subject description)

### Why This Matters for Scientific Community

1. **Scientific Reproducibility**
   - Missing experimenter info makes it hard to contact data originators
   - Missing institution/lab reduces provenance tracking
   - Missing species/subject info reduces data discoverability

2. **DANDI Archive Requirements**
   - DANDI requires properly formatted experimenter names
   - Species and subject metadata are critical for neuroscience data sharing
   - Institution info is needed for data provenance

3. **Report Credibility**
   - Reports showing "N/A" when data exists undermines trust
   - Scientists rely on these reports for quality assessment
   - Incorrect reports could lead to rejecting valid data or accepting invalid data

---

## NWB File Structure Reference

NWB files (HDF5 format) store metadata in specific locations:

### Top-Level Attributes
```python
file.attrs['identifier']              # Unique file ID
file.attrs['session_description']     # Session description
file.attrs['session_start_time']      # ISO 8601 timestamp
file.attrs['nwb_version']             # NWB format version
```

### General Group (`/general/`)
```python
file['general'].attrs['experimenter']  # List of experimenters (can be string or array)
file['general'].attrs['institution']   # Institution name
file['general'].attrs['lab']           # Lab name
file['general'].attrs['session_id']    # Session identifier
file['general'].attrs['experiment_description']  # Experiment details
```

### Subject Group (`/general/subject/`)
```python
subject = file['general']['subject']
subject.attrs['subject_id']      # Subject identifier
subject.attrs['species']         # e.g., "Mus musculus", "Rattus norvegicus", "Homo sapiens"
subject.attrs['sex']             # M, F, U, or O
subject.attrs['age']             # ISO 8601 duration (e.g., "P90D" for 90 days)
subject.attrs['date_of_birth']   # ISO 8601 datetime
subject.attrs['description']     # Free-text description
subject.attrs['genotype']        # Genetic information
subject.attrs['strain']          # e.g., "C57BL/6J"
```

---

## Required Fixes

### Fix #1: Complete `_extract_file_info()` Function

**Current Code** (lines 311-372):
```python
file_info = {
    'nwb_version': 'Unknown',
    'file_size_bytes': 0,
    'creation_date': 'Unknown',
    'identifier': 'Unknown',
    'session_description': 'N/A',
    'subject_id': 'N/A',
}
```

**Should Be:**
```python
file_info = {
    # File-level
    'nwb_version': 'Unknown',
    'file_size_bytes': 0,
    'creation_date': 'Unknown',
    'identifier': 'Unknown',
    'session_description': 'N/A',
    'session_start_time': 'N/A',

    # General metadata
    'experimenter': [],  # List of experimenters
    'institution': 'N/A',
    'lab': 'N/A',
    'experiment_description': 'N/A',
    'session_id': 'N/A',

    # Subject metadata
    'subject_id': 'N/A',
    'species': 'N/A',
    'sex': 'N/A',
    'age': 'N/A',
    'date_of_birth': 'N/A',
    'description': 'N/A',  # Subject description
    'genotype': 'N/A',
    'strain': 'N/A',
}
```

### Fix #2: Extract General Metadata

Add code to extract from `/general/` group:

```python
# Extract general metadata
if 'general' in f:
    general = f['general']

    # Experimenter (can be string or array)
    if 'experimenter' in general.attrs:
        exp_value = general.attrs['experimenter']
        if isinstance(exp_value, bytes):
            file_info['experimenter'] = [exp_value.decode('utf-8')]
        elif isinstance(exp_value, str):
            file_info['experimenter'] = [exp_value]
        elif isinstance(exp_value, (list, tuple)):
            file_info['experimenter'] = [
                e.decode('utf-8') if isinstance(e, bytes) else str(e)
                for e in exp_value
            ]
        else:
            file_info['experimenter'] = [str(exp_value)]

    # Institution
    if 'institution' in general.attrs:
        inst_value = general.attrs['institution']
        file_info['institution'] = inst_value.decode('utf-8') if isinstance(inst_value, bytes) else str(inst_value)

    # Lab
    if 'lab' in general.attrs:
        lab_value = general.attrs['lab']
        file_info['lab'] = lab_value.decode('utf-8') if isinstance(lab_value, bytes) else str(lab_value)

    # Experiment description
    if 'experiment_description' in general.attrs:
        desc_value = general.attrs['experiment_description']
        file_info['experiment_description'] = desc_value.decode('utf-8') if isinstance(desc_value, bytes) else str(desc_value)

    # Session ID
    if 'session_id' in general.attrs:
        sid_value = general.attrs['session_id']
        file_info['session_id'] = sid_value.decode('utf-8') if isinstance(sid_value, bytes) else str(sid_value)
```

### Fix #3: Extract Subject Metadata

Enhance the existing subject extraction (lines 350-353):

```python
# Get subject metadata
if 'general' in f and 'subject' in f['general']:
    subject_group = f['general']['subject']

    # Subject ID (already exists, but improve it)
    if 'subject_id' in subject_group.attrs:
        file_info['subject_id'] = subject_group.attrs['subject_id'].decode() if isinstance(subject_group.attrs['subject_id'], bytes) else str(subject_group.attrs['subject_id'])

    # Species
    if 'species' in subject_group.attrs:
        species_value = subject_group.attrs['species']
        file_info['species'] = species_value.decode('utf-8') if isinstance(species_value, bytes) else str(species_value)

    # Sex
    if 'sex' in subject_group.attrs:
        sex_value = subject_group.attrs['sex']
        file_info['sex'] = sex_value.decode('utf-8') if isinstance(sex_value, bytes) else str(sex_value)

    # Age
    if 'age' in subject_group.attrs:
        age_value = subject_group.attrs['age']
        file_info['age'] = age_value.decode('utf-8') if isinstance(age_value, bytes) else str(age_value)

    # Date of birth
    if 'date_of_birth' in subject_group.attrs:
        dob_value = subject_group.attrs['date_of_birth']
        file_info['date_of_birth'] = dob_value.decode('utf-8') if isinstance(dob_value, bytes) else str(dob_value)

    # Description
    if 'description' in subject_group.attrs:
        desc_value = subject_group.attrs['description']
        file_info['description'] = desc_value.decode('utf-8') if isinstance(desc_value, bytes) else str(desc_value)

    # Genotype
    if 'genotype' in subject_group.attrs:
        geno_value = subject_group.attrs['genotype']
        file_info['genotype'] = geno_value.decode('utf-8') if isinstance(geno_value, bytes) else str(geno_value)

    # Strain
    if 'strain' in subject_group.attrs:
        strain_value = subject_group.attrs['strain']
        file_info['strain'] = strain_value.decode('utf-8') if isinstance(strain_value, bytes) else str(strain_value)
```

### Fix #4: Update PyNWB Fallback

Update the PyNWB fallback (lines 357-367) to also extract these fields:

```python
from pynwb import NWBHDF5IO
with NWBHDF5IO(nwb_path, 'r') as io:
    nwbfile = io.read()

    # File-level
    file_info['nwb_version'] = str(getattr(nwbfile, 'nwb_version', 'Unknown'))
    file_info['identifier'] = str(getattr(nwbfile, 'identifier', 'Unknown'))
    file_info['session_description'] = str(getattr(nwbfile, 'session_description', 'N/A'))
    file_info['session_start_time'] = str(getattr(nwbfile, 'session_start_time', 'N/A'))

    # General metadata
    file_info['experimenter'] = list(getattr(nwbfile, 'experimenter', []))
    file_info['institution'] = str(getattr(nwbfile, 'institution', 'N/A'))
    file_info['lab'] = str(getattr(nwbfile, 'lab', 'N/A'))
    file_info['experiment_description'] = str(getattr(nwbfile, 'experiment_description', 'N/A'))
    file_info['session_id'] = str(getattr(nwbfile, 'session_id', 'N/A'))

    # Subject metadata
    if nwbfile.subject:
        file_info['subject_id'] = str(getattr(nwbfile.subject, 'subject_id', 'N/A'))
        file_info['species'] = str(getattr(nwbfile.subject, 'species', 'N/A'))
        file_info['sex'] = str(getattr(nwbfile.subject, 'sex', 'N/A'))
        file_info['age'] = str(getattr(nwbfile.subject, 'age', 'N/A'))
        file_info['date_of_birth'] = str(getattr(nwbfile.subject, 'date_of_birth', 'N/A'))
        file_info['description'] = str(getattr(nwbfile.subject, 'description', 'N/A'))
        file_info['genotype'] = str(getattr(nwbfile.subject, 'genotype', 'N/A'))
        file_info['strain'] = str(getattr(nwbfile.subject, 'strain', 'N/A'))
```

---

## Fix #5: Update Report Service

**File:** [backend/src/services/report_service.py:137-147](backend/src/services/report_service.py#L137-L147)

Update the PDF report generation to include all fields:

```python
file_data = [
    ['NWB Version:', file_info.get('nwb_version', 'N/A')],
    ['File Size:', self._format_filesize(file_info.get('file_size_bytes', 0))],
    ['Creation Date:', file_info.get('creation_date', 'N/A')],
    ['Session Start:', file_info.get('session_start_time', 'N/A')],
    ['Identifier:', file_info.get('identifier', 'Unknown')],
    ['Session Description:', file_info.get('session_description', 'N/A')],
    ['', ''],  # Spacer
    ['Experimenter:', ', '.join(file_info.get('experimenter', [])) or 'N/A'],
    ['Institution:', file_info.get('institution', 'N/A')],
    ['Lab:', file_info.get('lab', 'N/A')],
    ['', ''],  # Spacer
    ['Subject ID:', file_info.get('subject_id', 'N/A')],
    ['Species:', file_info.get('species', 'N/A')],
    ['Sex:', file_info.get('sex', 'N/A')],
    ['Age:', file_info.get('age', 'N/A')],
    ['Description:', file_info.get('description', 'N/A')],
]
```

---

## Additional Improvements for Scientific Community

### 1. Human-Readable Age Format
Instead of showing "P90D" (ISO 8601 duration), convert to "90 days" or "3 months":

```python
def _format_age(iso_age: str) -> str:
    """Convert ISO 8601 duration to human-readable format."""
    if not iso_age or iso_age == 'N/A':
        return 'N/A'

    import re
    # Match P90D, P3M, P2Y formats
    match = re.match(r'P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?', iso_age)
    if match:
        years, months, days = match.groups()
        parts = []
        if years:
            parts.append(f"{years} year{'s' if int(years) != 1 else ''}")
        if months:
            parts.append(f"{months} month{'s' if int(months) != 1 else ''}")
        if days:
            parts.append(f"{days} day{'s' if int(days) != 1 else ''}")
        return ', '.join(parts) if parts else iso_age
    return iso_age
```

### 2. Species Scientific Name Enhancement
Show both scientific and common names:

```python
SPECIES_COMMON_NAMES = {
    'Mus musculus': 'House mouse',
    'Rattus norvegicus': 'Norway rat',
    'Homo sapiens': 'Human',
    'Macaca mulatta': 'Rhesus macaque',
    'Danio rerio': 'Zebrafish',
    'Drosophila melanogaster': 'Fruit fly',
    'Caenorhabditis elegans': 'Roundworm',
}

def _format_species(species: str) -> str:
    """Format species with common name if known."""
    if species == 'N/A' or not species:
        return 'N/A'

    common_name = SPECIES_COMMON_NAMES.get(species)
    if common_name:
        return f"{species} ({common_name})"
    return species
```

### 3. Sex Code Expansion
Expand sex codes to full words:

```python
SEX_CODES = {
    'M': 'Male',
    'F': 'Female',
    'U': 'Unknown',
    'O': 'Other',
}

def _format_sex(sex_code: str) -> str:
    """Expand sex code to full word."""
    if not sex_code or sex_code == 'N/A':
        return 'N/A'
    return SEX_CODES.get(sex_code.upper(), sex_code)
```

### 4. Add Metadata Completeness Score

Add a "Metadata Completeness" section to the report:

```python
def _calculate_metadata_completeness(file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate metadata completeness score."""
    required_fields = [
        'identifier', 'session_description', 'session_start_time',
        'experimenter', 'institution', 'subject_id', 'species'
    ]

    recommended_fields = [
        'lab', 'experiment_description', 'sex', 'age', 'description'
    ]

    required_present = sum(
        1 for field in required_fields
        if file_info.get(field) not in [None, 'N/A', 'Unknown', []]
    )

    recommended_present = sum(
        1 for field in recommended_fields
        if file_info.get(field) not in [None, 'N/A', 'Unknown', []]
    )

    required_score = (required_present / len(required_fields)) * 100
    recommended_score = (recommended_present / len(recommended_fields)) * 100
    overall_score = (required_score * 0.7) + (recommended_score * 0.3)

    return {
        'overall_score': round(overall_score, 1),
        'required_fields_complete': f"{required_present}/{len(required_fields)}",
        'recommended_fields_complete': f"{recommended_present}/{len(recommended_fields)}",
        'grade': 'A' if overall_score >= 90 else 'B' if overall_score >= 80 else 'C' if overall_score >= 70 else 'D' if overall_score >= 60 else 'F',
    }
```

---

## Testing Plan

### Test Data
Create test NWB files with:
1. **Complete metadata** - All fields populated
2. **Minimal metadata** - Only required fields
3. **Edge cases** - Empty strings, special characters, unicode
4. **Array experimenters** - Multiple experimenters
5. **Real-world file** - User's actual file with "Aditya" experimenter

### Validation
For each test file:
1. Generate PDF report
2. Verify all present fields show correct values (not "N/A")
3. Verify absent fields show "N/A"
4. Verify formatting is scientific-quality
5. Compare with NWB Inspector output

---

## Impact on Scientific Quality

### Before Fix
```
Experimenter: N/A
Institution: N/A
Species: N/A
Sex: N/A
Age: N/A
Description: N/A
```
**Result:** Report looks incomplete, undermines trust, cannot use for publication/DANDI submission

### After Fix
```
Experimenter: Aditya
Institution: MIT
Lab: Smith Lab
Species: Mus musculus (House mouse)
Sex: Male
Age: P60D (60 days, ~2 months postnatal)
Description: C57BL/6J wildtype mouse
Strain: C57BL/6J
```
**Result:** Complete, professional, publication-ready report

---

## Files to Modify

1. **backend/src/agents/evaluation_agent.py**
   - Function: `_extract_file_info()` (lines 298-372)
   - Add: Complete metadata extraction logic
   - Add: Helper functions for formatting

2. **backend/src/services/report_service.py**
   - Function: `generate_pdf_report()` (lines 86-258)
   - Update: File information table
   - Add: Metadata completeness section
   - Add: Formatting helper functions

---

## Priority

**P0 - CRITICAL**

This bug affects:
- ✗ All generated PDF reports
- ✗ Scientific credibility of the system
- ✗ DANDI submission readiness assessment
- ✗ User trust in the AI system
- ✗ Publication-quality output

**Must be fixed before:**
- Any production use
- Any scientific publication
- Any DANDI submissions
- Any demos to neuroscience community

---

**Report Date:** October 21, 2025
**Status:** Identified, Solution Designed, Ready for Implementation
