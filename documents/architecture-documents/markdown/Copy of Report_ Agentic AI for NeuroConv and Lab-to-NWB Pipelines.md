# <a name="_7dgwltq1cf03"></a>**Agentic AI for NeuroConv and Lab-to-NWB Pipelines**

## <a name="_49e22eqi4bh3"></a>**1. Background**

### <a name="_mhouat65mjaz"></a>**Neurodata Without Borders (NWB)**

- NWB is a standardized file format for storing and sharing neurophysiology
  data.
- It unifies raw data, metadata, and analysis results into a single structure.
- Goal: make datasets comparable across labs, reproducible, and FAIR (Findable,
  Accessible, Interoperable, Reusable).

### <a name="_4cs85pk2n8ea"></a>**NeuroConv**

- Python package developed to facilitate conversions from various proprietary
  data formats into NWB.
- Provides **interfaces** (e.g., for SpikeGLX, NeuroExplorer, SLEAP, DeepLabCut,
  etc.).
- Handles raw data extraction, metadata mapping, and file writing.
- Flexible: can support multiple modalities (electrophysiology, imaging,
  behavior).

### <a name="_701sqko3wlwu"></a>**CatalystNeuro**

- A company that collaborates with labs to standardize their data pipelines.
- Goes beyond NeuroConv by building **lab-to-NWB repositories**:
  - Examples: mease-lab-to-nwb, stavisky-lab-to-nwb, churchland-lab-to-nwb.
  - Each repo is an **end-to-end pipeline** customized for a lab’s workflow.

---

## <a name="_np7uhsm5sgbv"></a>**2. What Lab-to-NWB Repos Contain**

CatalystNeuro builds these repos to adapt NeuroConv to each lab’s unique data
environment.\
``Key components:

1. **Conversion Interfaces Config**\
   1. Which NeuroConv interfaces to load.
   1. Example: SpikeGLX (electrophysiology) + DeepLabCut (behavior).

1. **Metadata Templates**\
   1. Lab-specific JSON/YAML schemas.
   1. Pre-filled fields for experiment type, rig info, subject species,
      electrode maps.

1. **Preprocessing Steps**\
   1. Clock synchronization between devices.
   1. Renaming/relabeling channels.
   1. Data cleaning or trial segmentation.

1. **Main Entry Script**\
   1. CLI or Python script: python convert_session.py --session 2023-07-14.
   1. Automates batch conversion.

1. **Validation**\
   1. Runs NWB schema validation.
   1. Ensures output is FAIR-compliant.

---

## <a name="_lppzgbqimkgm"></a>**3. The Agentic AI Vision**

We want to build an **agentic AI system** that can **replicate CatalystNeuro’s
lab-to-NWB creation process**:

- **Step 1: Input raw data**\
  - AI receives files with no prior knowledge of the lab.

- **Step 2: Detect and classify data formats**\
  - Use NeuroConv interfaces (format-aware tools).
  - Example: detect SpikeGLX files → use SpikeGLXRecordingInterface.

- **Step 3: Construct metadata schema**\
  - Propose templates (species, task, rig configuration).
  - Allow user to fill missing fields interactively.

- **Step 4: Generate a conversion pipeline (lab-to-NWB repo)**\
  - Create repo with:
    - Interface loading script.
    - Metadata YAML.
    - Main conversion CLI.
    - Validation hooks.

- **Step 5: Execution & Reuse**\
  - Repo can be run repeatedly on future datasets.
  - Mimics CatalystNeuro’s deliverable to labs.

---

## <a name="_q4h0l3lckcqh"></a>**4. Giving Context to the Agent**

To teach the agent **how to build lab-to-NWB repos automatically**, we need to
provide context:

1. **Knowledge Base**\
   1. Summaries of existing CatalystNeuro lab-to-NWB repos.
   1. Show typical structures: src/, metadata/, convert_session.py.

1. **NeuroConv Documentation**\
   1. Explain how to use interfaces (.run_conversion(), metadata injection).

1. **Design Patterns**\
   1. Hooks for preprocessing (clock alignment, channel mapping).
   1. YAML-driven configs.
   1. Script scaffolds for reproducibility.

1. **Few-shot Examples**\
   1. Example repo scaffolds the agent can copy/adapt.

---

## <a name="_zb5aznyn8tpr"></a>**5. Proposed Workflow for Research**

1. Collect and summarize 40+ CatalystNeuro lab-to-NWB repos.
1. Build a **meta-schema**: what common elements appear across repos.
1. Train the agent to:
   1. Identify formats.
   1. Assemble interfaces.
   1. Propose metadata.
   1. Write scaffold code.
1. Validate output using NWB tools.

---

## <a name="_4c4xomhcvd0v"></a>**6. Expected Outcome**

- An **agentic AI assistant** that can:
  - Take any new lab’s raw data.
  - Build a custom lab-to-NWB repo automatically.
  - Follow CatalystNeuro’s methodology (interfaces + metadata + preprocessing +
    validation).
- Long-term: reduce time/cost for labs to adopt NWB.
