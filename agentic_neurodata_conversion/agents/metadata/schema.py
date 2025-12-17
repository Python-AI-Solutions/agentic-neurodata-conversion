"""NWB and DANDI Schema Definitions.

This module provides comprehensive schema definitions for all required and recommended
fields in NWB files and DANDI archive compliance.

This replaces hardcoded field lists with a dynamic, schema-driven approach.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldRequirementLevel(str, Enum):
    """Requirement level for metadata fields."""

    REQUIRED = "required"  # Must have for valid NWB
    RECOMMENDED = "recommended"  # Should have for DANDI compliance
    OPTIONAL = "optional"  # Nice to have


class FieldType(str, Enum):
    """Data type for metadata fields."""

    STRING = "string"
    LIST = "list"
    DATE = "date"
    DURATION = "duration"
    NUMBER = "number"
    ENUM = "enum"
    NESTED = "nested"


class MetadataFieldSchema(BaseModel):
    """Schema definition for a metadata field."""

    name: str = Field(description="Field name in NWB/DANDI")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(description="What this field represents")
    field_type: FieldType = Field(description="Data type")
    requirement_level: FieldRequirementLevel = Field(description="How critical this field is")

    # Validation and normalization
    allowed_values: list[str] | None = Field(default=None, description="Enum values if applicable")
    format: str | None = Field(default=None, description="Format string (e.g., ISO 8601)")
    example: str = Field(description="Example value")

    # Extraction hints for LLM
    extraction_patterns: list[str] = Field(description="Patterns to look for in user text")
    synonyms: list[str] = Field(default_factory=list, description="Alternative names/terms")
    normalization_rules: dict[str, str] = Field(default_factory=dict, description="Value mappings")

    # Context
    nwb_path: str | None = Field(default=None, description="Path in NWB file structure")
    dandi_field: str | None = Field(default=None, description="Corresponding DANDI field")
    why_needed: str = Field(description="Explanation for users")


class NWBDANDISchema:
    """Comprehensive schema for NWB and DANDI metadata fields.

    This provides a single source of truth for all required fields,
    eliminating hardcoding throughout the codebase.
    """

    @staticmethod
    def get_all_fields() -> list[MetadataFieldSchema]:
        """Get complete list of all metadata fields."""
        return [
            # ============================================================
            # GENERAL METADATA (NWB Core)
            # ============================================================
            MetadataFieldSchema(
                name="experimenter",
                display_name="Experimenter(s)",
                description="Person(s) who performed the experiment",
                field_type=FieldType.LIST,
                requirement_level=FieldRequirementLevel.REQUIRED,
                format="DANDI format: 'LastName, FirstName' or 'LastName, FirstName MiddleInitial.'",
                example='["Smith, Jane", "Doe, John M."]',
                extraction_patterns=[
                    "experimenter",
                    "researcher",
                    "scientist",
                    "performed by",
                    "recorded by",
                    "collected by",
                    "my name is",
                    "I am",
                ],
                synonyms=["researcher", "scientist", "investigator", "PI"],
                normalization_rules={
                    "Dr. Jane Smith": "Smith, Jane",
                    "Jane Smith": "Smith, Jane",
                    "J. Smith": "Smith, J.",
                },
                nwb_path="/general/experimenter",
                dandi_field="contributor",
                why_needed="Required to credit data creators and enable contact for questions",
            ),
            MetadataFieldSchema(
                name="institution",
                display_name="Institution",
                description="Institution where experiment was performed",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.REQUIRED,
                example="University of California, Berkeley",
                extraction_patterns=[
                    "institution",
                    "university",
                    "lab",
                    "at",
                    "from",
                    "institute",
                    "college",
                    "hospital",
                    "center",
                ],
                synonyms=["university", "lab", "research center", "facility"],
                normalization_rules={
                    "MIT": "Massachusetts Institute of Technology",
                    "UCB": "University of California, Berkeley",
                    "Stanford": "Stanford University",
                    "Harvard": "Harvard University",
                    "UCSF": "University of California, San Francisco",
                    "Janelia": "Janelia Research Campus",
                    "Allen": "Allen Institute",
                },
                nwb_path="/general/institution",
                dandi_field="affiliation",
                why_needed="Required for institutional affiliation and data provenance",
            ),
            MetadataFieldSchema(
                name="lab",
                display_name="Lab Name",
                description="Laboratory where experiment was performed",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.RECOMMENDED,
                example="Svoboda Lab",
                extraction_patterns=["lab", "laboratory", "group", "team"],
                synonyms=["laboratory", "research group"],
                normalization_rules={},
                nwb_path="/general/lab",
                dandi_field="lab",
                why_needed="Helps identify specific research group within institution",
            ),
            MetadataFieldSchema(
                name="experiment_description",
                display_name="Experiment Description",
                description="Brief description of the experiment purpose and methods",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.REQUIRED,
                example="Extracellular electrophysiology recording from mouse primary visual cortex using Neuropixels probes during visual stimulation",
                extraction_patterns=[
                    "experiment",
                    "study",
                    "recording",
                    "measurement",
                    "we recorded",
                    "we measured",
                    "data from",
                    "investigating",
                ],
                synonyms=["study description", "experimental design", "methods"],
                normalization_rules={},
                nwb_path="/general/experiment_description",
                dandi_field="description",
                why_needed="Required to understand what the experiment is about",
            ),
            MetadataFieldSchema(
                name="session_description",
                display_name="Session Description",
                description="Description of this specific recording session",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.REQUIRED,
                example="Mouse performing visual discrimination task with drifting gratings",
                extraction_patterns=[
                    "session",
                    "recording",
                    "trial",
                    "run",
                    "during",
                    "performing",
                    "task",
                    "condition",
                ],
                synonyms=["recording session", "trial description"],
                normalization_rules={},
                nwb_path="/general/session_description",
                dandi_field="session_description",
                why_needed="Required to describe what happened in this particular session",
            ),
            MetadataFieldSchema(
                name="session_start_time",
                display_name="Session Start Time",
                description="When the recording session started",
                field_type=FieldType.DATE,
                requirement_level=FieldRequirementLevel.REQUIRED,
                format="ISO 8601: YYYY-MM-DDTHH:MM:SS±HH:MM",
                example="2024-01-15T14:30:00-08:00",
                extraction_patterns=["date", "time", "started", "began", "on", "at", "recorded on", "session date"],
                synonyms=["recording date", "session date", "start time"],
                normalization_rules={},
                nwb_path="/session_start_time",
                dandi_field="session_start_time",
                why_needed="Required for temporal organization and data provenance",
            ),
            MetadataFieldSchema(
                name="keywords",
                display_name="Keywords",
                description="Searchable keywords describing the experiment",
                field_type=FieldType.LIST,
                requirement_level=FieldRequirementLevel.RECOMMENDED,
                example='["electrophysiology", "visual cortex", "neuropixels", "mouse", "V1"]',
                extraction_patterns=[
                    "keywords",
                    "tags",
                    "topics",
                    "related to",
                    # Inferred from context
                ],
                synonyms=["tags", "topics", "categories"],
                normalization_rules={
                    "ephys": "electrophysiology",
                    "2P": "two-photon imaging",
                    "Ca imaging": "calcium imaging",
                },
                nwb_path="/general/keywords",
                dandi_field="keywords",
                why_needed="Improves data discoverability in DANDI archive",
            ),
            # ============================================================
            # SUBJECT METADATA (NWB Core)
            # ============================================================
            MetadataFieldSchema(
                name="subject_id",
                display_name="Subject ID",
                description="Unique identifier for the experimental subject",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.REQUIRED,
                example="mouse_001",
                extraction_patterns=["subject", "animal", "ID", "identifier", "number", "mouse", "rat", "participant"],
                synonyms=["animal ID", "subject number", "participant ID"],
                normalization_rules={},
                nwb_path="/general/subject/subject_id",
                dandi_field="subject_id",
                why_needed="Required to identify individual subject in dataset",
            ),
            MetadataFieldSchema(
                name="species",
                display_name="Species",
                description="Species of the experimental subject",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.REQUIRED,
                format="Use scientific name (binomial nomenclature)",
                example="Mus musculus",
                extraction_patterns=["species", "mouse", "rat", "monkey", "human", "animal", "organism"],
                synonyms=["organism", "animal species"],
                normalization_rules={
                    "mouse": "Mus musculus",
                    "mice": "Mus musculus",
                    "rat": "Rattus norvegicus",
                    "rats": "Rattus norvegicus",
                    "rhesus": "Macaca mulatta",
                    "macaque": "Macaca mulatta",
                    "human": "Homo sapiens",
                    "C elegans": "Caenorhabditis elegans",
                    "fly": "Drosophila melanogaster",
                    "zebrafish": "Danio rerio",
                },
                nwb_path="/general/subject/species",
                dandi_field="species",
                why_needed="Required to identify experimental organism",
            ),
            MetadataFieldSchema(
                name="sex",
                display_name="Sex",
                description="Biological sex of the subject",
                field_type=FieldType.ENUM,
                requirement_level=FieldRequirementLevel.REQUIRED,
                allowed_values=["M", "F", "U", "O"],
                example="M",
                extraction_patterns=["sex", "gender", "male", "female", "M", "F"],
                synonyms=["gender"],
                normalization_rules={
                    "male": "M",
                    "Male": "M",
                    "m": "M",
                    "♂": "M",
                    "female": "F",
                    "Female": "F",
                    "f": "F",
                    "♀": "F",
                    "unknown": "U",
                    "Unknown": "U",
                    "other": "O",
                },
                nwb_path="/general/subject/sex",
                dandi_field="sex",
                why_needed="Required NWB field when subject info is provided",
            ),
            MetadataFieldSchema(
                name="age",
                display_name="Age",
                description="Age of the subject at time of experiment",
                field_type=FieldType.DURATION,
                requirement_level=FieldRequirementLevel.RECOMMENDED,
                format="ISO 8601 duration (e.g., P90D for 90 days, P12W for 12 weeks)",
                example="P60D",
                extraction_patterns=["age", "old", "days", "weeks", "months", "years", "P", "postnatal day"],
                synonyms=["age at recording"],
                normalization_rules={
                    "60 days": "P60D",
                    "P60": "P60D",
                    "8 weeks": "P56D",
                    "2 months": "P60D",
                    "adult": "P90D",
                },
                nwb_path="/general/subject/age",
                dandi_field="age",
                why_needed="Important for developmental studies and data interpretation",
            ),
            MetadataFieldSchema(
                name="strain",
                display_name="Strain/Genotype",
                description="Genetic strain or genotype of the subject",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.RECOMMENDED,
                example="C57BL/6J",
                extraction_patterns=["strain", "genotype", "genetic", "line", "C57", "transgenic", "knockout"],
                synonyms=["genetic background", "mouse line"],
                normalization_rules={
                    "C57": "C57BL/6J",
                    "wild type": "wild-type",
                    "WT": "wild-type",
                },
                nwb_path="/general/subject/genotype",
                dandi_field="genotype",
                why_needed="Critical for genetic studies and reproducibility",
            ),
            MetadataFieldSchema(
                name="date_of_birth",
                display_name="Date of Birth",
                description="Birth date of the subject",
                field_type=FieldType.DATE,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                format="ISO 8601: YYYY-MM-DD",
                example="2023-11-15",
                extraction_patterns=["birth", "born", "DOB", "date of birth"],
                synonyms=["DOB", "birth date"],
                normalization_rules={},
                nwb_path="/general/subject/date_of_birth",
                dandi_field="date_of_birth",
                why_needed="Useful for calculating exact age at recording",
            ),
            MetadataFieldSchema(
                name="weight",
                display_name="Weight",
                description="Weight of the subject (with units)",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                example="25g",
                extraction_patterns=["weight", "mass", "grams", "kg", "g"],
                synonyms=["body weight", "mass"],
                normalization_rules={},
                nwb_path="/general/subject/weight",
                dandi_field="weight",
                why_needed="Useful for dosing calculations and health monitoring",
            ),
            MetadataFieldSchema(
                name="description",
                display_name="Subject Description",
                description="Additional information about the subject",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                example="Healthy adult mouse, housed in standard conditions",
                extraction_patterns=["subject", "animal", "condition", "health"],
                synonyms=["subject notes"],
                normalization_rules={},
                nwb_path="/general/subject/description",
                dandi_field="subject_description",
                why_needed="Provides additional context about subject condition",
            ),
            # ============================================================
            # DANDI-SPECIFIC FIELDS
            # ============================================================
            MetadataFieldSchema(
                name="related_publications",
                display_name="Related Publications",
                description="DOIs or URLs of related publications",
                field_type=FieldType.LIST,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                example='["10.1038/s41593-020-0604-z"]',
                extraction_patterns=["publication", "paper", "DOI", "published", "article"],
                synonyms=["papers", "articles", "references"],
                normalization_rules={},
                nwb_path="/general/related_publications",
                dandi_field="relatedResource",
                why_needed="Links data to published research",
            ),
            MetadataFieldSchema(
                name="protocol",
                display_name="Protocol",
                description="Experimental protocol or IRB/IACUC number",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.RECOMMENDED,
                example="IACUC-2024-001",
                extraction_patterns=["protocol", "IACUC", "IRB", "approval", "ethics"],
                synonyms=["ethics approval", "animal protocol"],
                normalization_rules={},
                nwb_path="/general/protocol",
                dandi_field="protocol",
                why_needed="Required for ethical compliance documentation",
            ),
            MetadataFieldSchema(
                name="data_collection",
                display_name="Data Collection Notes",
                description="Notes about data collection methods",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                example="Recorded using Neuropixels 2.0 probes, 30kHz sampling",
                extraction_patterns=["collected", "recorded", "sampled", "acquired"],
                synonyms=["acquisition notes", "recording notes"],
                normalization_rules={},
                nwb_path="/general/data_collection",
                dandi_field="approach",
                why_needed="Documents data collection methodology",
            ),
            MetadataFieldSchema(
                name="surgery",
                display_name="Surgery Details",
                description="Description of surgical procedures",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                example="Craniotomy over V1, dura removed",
                extraction_patterns=["surgery", "surgical", "craniotomy", "implant"],
                synonyms=["surgical procedure", "operation"],
                normalization_rules={},
                nwb_path="/general/surgery",
                dandi_field="surgery",
                why_needed="Important for understanding data quality and interpretation",
            ),
            MetadataFieldSchema(
                name="virus",
                display_name="Virus/Injection Details",
                description="Details about viral injections or optogenetic constructs",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                example="AAV9-hSyn-ChR2-EYFP injected in V1, 200nL",
                extraction_patterns=["virus", "AAV", "injection", "transfection", "optogenetic"],
                synonyms=["viral vector", "construct"],
                normalization_rules={},
                nwb_path="/general/virus",
                dandi_field="virus",
                why_needed="Critical for optogenetic and imaging experiments",
            ),
            MetadataFieldSchema(
                name="pharmacology",
                display_name="Pharmacology",
                description="Drugs or pharmacological agents used",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                example="Isoflurane anesthesia, 1-2%",
                extraction_patterns=["drug", "pharmacology", "anesthesia", "injected", "administered"],
                synonyms=["drugs", "pharmaceuticals"],
                normalization_rules={},
                nwb_path="/general/pharmacology",
                dandi_field="pharmacology",
                why_needed="Important for understanding experimental conditions",
            ),
            MetadataFieldSchema(
                name="stimulus_notes",
                display_name="Stimulus Notes",
                description="Description of experimental stimuli",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                example="Drifting gratings, 8 orientations, 2 Hz temporal frequency",
                extraction_patterns=["stimulus", "stimuli", "presented", "visual", "auditory"],
                synonyms=["stimulation", "sensory stimuli"],
                normalization_rules={},
                nwb_path="/general/stimulus",
                dandi_field="stimulusType",
                why_needed="Describes experimental manipulations",
            ),
            # ============================================================
            # ELECTROPHYSIOLOGY METADATA (Anatomical Location)
            # ============================================================
            MetadataFieldSchema(
                name="brain_region",
                display_name="Brain Region",
                description="Anatomical brain region where recording was made",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.RECOMMENDED,
                example="hippocampus",
                extraction_patterns=[
                    "brain_region",
                    "brain region",
                    "location",
                    "anatomy",
                    "region",
                    "hippocampus",
                    "cortex",
                    "amygdala",
                    "striatum",
                    "thalamus",
                    "cerebellum",
                    "V1",
                    "CA1",
                    "Ammon",
                ],
                synonyms=["anatomical location", "recording location", "electrode location", "recording site"],
                normalization_rules={
                    "hc": "hippocampus",
                    "ctx": "cortex",
                    "hippo": "hippocampus",
                    "visual cortex": "primary visual cortex",
                    "V1": "primary visual cortex",
                },
                nwb_path="/general/extracellular_ephys/electrodes/location",
                dandi_field="anatomy",
                why_needed="Critical for understanding where neural recordings were obtained",
            ),
            MetadataFieldSchema(
                name="electrode_location",
                display_name="Electrode Location",
                description="Specific location of electrode placement",
                field_type=FieldType.STRING,
                requirement_level=FieldRequirementLevel.OPTIONAL,
                example="CA1 region of hippocampus",
                extraction_patterns=[
                    "electrode",
                    "probe",
                    "placement",
                    "electrode location",
                    "probe location",
                    "implant",
                ],
                synonyms=["probe location", "electrode placement", "implant location"],
                normalization_rules={},
                nwb_path="/general/extracellular_ephys/electrodes/location",
                dandi_field="anatomy",
                why_needed="Precise anatomical localization for electrophysiology data",
            ),
        ]

    @staticmethod
    def get_required_fields() -> list[MetadataFieldSchema]:
        """Get only required fields."""
        return [
            field
            for field in NWBDANDISchema.get_all_fields()
            if field.requirement_level == FieldRequirementLevel.REQUIRED
        ]

    @staticmethod
    def get_recommended_fields() -> list[MetadataFieldSchema]:
        """Get recommended fields for DANDI compliance."""
        return [
            field
            for field in NWBDANDISchema.get_all_fields()
            if field.requirement_level in [FieldRequirementLevel.REQUIRED, FieldRequirementLevel.RECOMMENDED]
        ]

    @staticmethod
    def get_field_by_name(field_name: str) -> MetadataFieldSchema | None:
        """Get field schema by name."""
        for field in NWBDANDISchema.get_all_fields():
            if field.name == field_name:
                return field
        return None

    @staticmethod
    def generate_llm_extraction_prompt() -> str:
        """Generate comprehensive LLM prompt for metadata extraction.

        This dynamically creates the prompt from the schema,
        eliminating hardcoded field lists.
        """
        all_fields = NWBDANDISchema.get_all_fields()

        # Group by requirement level
        required = [f for f in all_fields if f.requirement_level == FieldRequirementLevel.REQUIRED]
        recommended = [f for f in all_fields if f.requirement_level == FieldRequirementLevel.RECOMMENDED]
        optional = [f for f in all_fields if f.requirement_level == FieldRequirementLevel.OPTIONAL]

        prompt = """You are an expert at extracting structured metadata from natural language for neuroscience data.

Your task: Extract ALL relevant metadata fields from the user's message, following NWB and DANDI standards.

"""

        # Add field extraction rules
        prompt += "## REQUIRED FIELDS (Must extract if mentioned):\n\n"
        for field in required:
            prompt += f"**{field.display_name} ({field.name}):**\n"
            prompt += f"- What: {field.description}\n"
            prompt += f"- Example: {field.example}\n"
            prompt += f"- Look for: {', '.join(field.extraction_patterns[:5])}\n"
            if field.normalization_rules:
                rules_sample = list(field.normalization_rules.items())[:3]
                prompt += f"- Normalize: {', '.join([f'{k}→{v}' for k, v in rules_sample])}\n"
            prompt += f"- Why needed: {field.why_needed}\n\n"

        prompt += "\n## RECOMMENDED FIELDS (Extract if available):\n\n"
        for field in recommended[:5]:  # Show top 5
            prompt += f"**{field.display_name}:** {field.description} (e.g., {field.example})\n"

        prompt += f"\n... and {len(recommended) - 5} more recommended fields.\n\n"

        prompt += "## OPTIONAL FIELDS:\n"
        prompt += f"Extract any of: {', '.join([f.display_name for f in optional[:10]])}, etc.\n\n"

        prompt += """
## Extraction Strategy:

1. **Be Comprehensive**: Extract ALL fields mentioned or inferable
2. **Use Domain Knowledge**: Infer species from "mouse", modality from "neuropixels", etc.
3. **Normalize Values**: Use scientific names, standard formats, enum values
4. **Handle Variants**: Recognize synonyms and alternative phrasings
5. **Validate**: Check required fields before marking ready_to_proceed

## Response Format:
```json
{
    "extracted_metadata": {
        // Include ALL extracted fields by their field names
        "experimenter": ["LastName, FirstName"],
        "institution": "Full Institution Name",
        "species": "Scientific Name",
        "sex": "M" or "F" or "U",
        // ... all other extracted fields ...
    },
    "needs_more_info": true/false,
    "missing_required_fields": ["field1", "field2"],  // List any required fields not extracted
    "ready_to_proceed": true/false,
    "confidence": 0-100,
    "follow_up_message": "Conversational response"
}
```

## CRITICAL - ready_to_proceed Logic:

Set `ready_to_proceed: true` when ANY of these conditions are met:
1. **ALL required NWB fields** (experimenter, institution, experiment_description,
   session_start_time, subject_id, species, sex) are extracted
2. **Substantial metadata** provided (5+ fields extracted) even if some required fields missing
3. **User indicates lack of info with context**: "don't have experimenter", "not sure about species"
   (shows readiness to proceed with available data)
4. **User provides metadata AND expresses readiness**: "here's the info, let's go" or
   "Dr. Smith MIT, ready to proceed"
5. **User confirms with positive affirmation**: "yes", "ok", "correct", "accept", "proceed", "go ahead", "looks good"
   EVEN if the current message contains no new metadata - the confirmation indicates they've already provided info

Set `ready_to_proceed: false` ONLY when:
- User asks clarifying questions: "what do you need?", "which fields?", "what does that mean?"
- User explicitly wants to edit: "let me change that", "wait, that's wrong", "I need to fix something"
- User explicitly declines: "skip", "don't have that", "I'll do this later"

**CRITICAL USER INTENT UNDERSTANDING**:
- If user says "yes", "ok", "correct", "proceed", "accept", "looks good" etc. → set ready_to_proceed=TRUE
- These affirmations mean "I'm satisfied with what I've already provided, let's continue"
- DO NOT interpret confirmation as "user hasn't provided data yet"
- The confirmation IS the signal to proceed, even if no NEW metadata is in the current message

**IMPORTANT**: If user says "ready" or "start" but provides NO actual metadata AND this is the FIRST interaction,
then ask for metadata. But if they're responding to a confirmation request, assume they've already provided data earlier.

Extract as much as possible from the user's message!
"""

        return prompt

    @staticmethod
    def validate_metadata(metadata: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate metadata against schema.

        Returns:
            (is_valid, list_of_missing_required_fields)
        """
        required_fields = NWBDANDISchema.get_required_fields()
        missing = []

        for field in required_fields:
            if field.name not in metadata or not metadata[field.name]:
                missing.append(field.name)

        return len(missing) == 0, missing

    @staticmethod
    def get_field_display_info(field_name: str) -> dict[str, str]:
        """Get user-friendly display information for a field."""
        field = NWBDANDISchema.get_field_by_name(field_name)
        if not field:
            return {"name": field_name, "description": "Unknown field"}

        return {
            "name": field.display_name,
            "description": field.description,
            "example": field.example,
            "why_needed": field.why_needed,
        }
