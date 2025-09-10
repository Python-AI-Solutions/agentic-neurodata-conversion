**Electrophysiology Dataset Evaluation**

1\. **Chandravadia \- Human Memory Task (DANDI 000004\)**  
Brain region: Medical Temporal Lobe (MTL)  
Species: 59 human subjects  
Size: 5.8 GiB  
Sessions: Single recognition task per subject  
Data complexity: High \- combines single-unit recordings, behavioral synchronization, and clinical electrode data  
What makes it valuable: First human single-neuron dataset with memory task integration. Clinical electrode recordings provide direct human neural data during declarative memory formation and retrieval. Includes detailed spike sorting with waveform analysis.

Key Technical Features:   
Data structure: Well-organized NWB format with comprehensive metadata  
Processing level: Complete spike sorting and event synchronization included  
 

2\. **Kyzar \- Human Sternberg Working Memory (DANDI 000469\)**  
Brain region: Medial temporal lobe (amygdala and hippocampus) \+ medial frontal lobe  
Species: 21 human subjects  
Size: 9.1 GiB  
Sessions: 41 sessions across multiple patients  
Data complexity: Very high \- combines single-unit recordings, behavioral task data, and visual stimulus presentation with extensive microwire arrays  
What makes it valuable: Large-scale human single-neuron dataset during working memory task. Contains 1809 recorded single neurons with detailed spike sorting and waveform analysis. Includes visual stimulus presentation and behavioral response data for cognitive neuroscience applications.

Key Technical Features:   
Electrode coverage: 63+ microwires across multiple brain regions per patient  
Institution: Cedars-Sinai Medical Center (Rutishauser Lab)

3\. **Hires \- Somatosensory Touch Encoding (DANDI 000013\)**  
Brain region: Somatosensory cortex layer 4  
Species: 23 house mice  
Size: 10.6 GiB  
Sessions: 52 sessions across subjects  
Data complexity: Very high \- combines intracellular and extracellular electrophysiology with precise behavioral tracking and optogenetic stimulation  
What makes it valuable: Layer-specific cortical recordings during active touch behavior with millisecond precision tracking. Includes both patch-clamp and current-clamp recordings alongside behavioral measurements. Published dataset from Hires, Gutnisky et al. Elife 2015 provides established experimental validation.

4\. **Svoboda \- Mouse Motor Cortex Delay Response (DANDI 000006\)**  
Brain region: Anterior lateral motor cortex (ALM)  
Species: 12 house mice  
Size: 133.1 MiB  
Sessions: 53 sessions across subjects  
Data complexity: Medium \- combines extracellular electrophysiology with behavioral task timing and lick detection  
What makes it valuable: Motor cortex recordings during delay response task with two distinct neuron populations (pyramidal track upper and lower). Focused on movement execution timing with precise behavioral correlates. Compact dataset size makes it accessible while maintaining experimental depth.

Key Technical Features:   
Population analysis: Two characterized neuron populations with movement-related activity  
Institution: Janelia Research Campus (Svoboda Lab)

**5.Waade \- Entorhinal Grid Cells (DANDI 000582\)**  
Brain region: Medial entorhinal cortex (MEC)  
Species: 14 Norway rats  
Size: 1.7 GiB  
Sessions: Single spatial navigation session per rat  
Data complexity: Medium-high \- integrates spike times, position tracking, and LFP recordings with multi-electrode arrays  
What makes it valuable: Focused on grid cell spatial representation during 2D environment exploration. Contains both raw electrical signals and processed spike data with positional coordinates. 

Key Technical Features: Recording setup: Multi-electrode extracellular electrophysiology with behavioral tracking  
Data organization: 118 files with electrode depth metadata and hemisphere mapping included 

**Key findings**  
   
**4th dataset Svoboda**: Data appears **broken/incomplete**  via description \- 133 MiB across 53 sessions indicates missing neural recordings or corrupted files

**5th dataset Waade**: Data likely **heavily processed/stripped**

the first three datasets (Kyzar, Chandravadia, Hires) which provide complete electrophysiology data with proper neural signal depth. Avoid the two problematic datasets due to missing raw recordings and potential data integrity issues.

   
   
 

