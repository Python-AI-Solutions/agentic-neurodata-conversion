

Dataset Comparison

1\. Peyrache \- Head Direction Cells

Brain region: Thalamus \+ post-subiculum  
Species: 7 house mice  
Size: 193.5 GB  
Sessions: Multiple per mouse (9 sessions for Mouse17 over 10 days)  
Data complexity: High \- combines neural recordings, behavioral tracking, sleep states, and optogenetics signals  
What makes it useful: Shows how to sync multiple data types in one file. Good example of preserving detailed electrode metadata and experimental protocols.

2\. Senzai \- Hippocampal Granule Cells

Brain region: Hippocampus  
Species: 16 house mice  
Size: 2.3 TB (biggest dataset)  
Sessions: One long session per mouse  
Data complexity: Very high \- includes spectral analysis, cell type classification, and precise 3D electrode mapping  
What makes it useful: Demonstrates sophisticated analysis preservation. Shows how to handle detailed neuron characterization and frequency decomposition in NWB.

3\. Senzai \- Visual Cortex Layers

Brain region: Primary visual cortex (V1)  
Species: 19 house mice  
Size: 733.1 GB  
Sessions: One per mouse  
Data complexity: Very high \- layer-specific recordings with detailed single-neuron properties  
What makes it useful: Shows cortical layer organization and extensive neuron metadata. Good for understanding how to preserve physiological measurements and cell classifications.

4\. Girardeau \- Sleep Memory

Brain region: Hippocampus \+ amygdala  
Species: 4 brown rats  
Size: 1.8 TB  
Sessions: Multiple long sessions (about 450 GB per rat)  
Data complexity: Very high \- includes video recordings, event annotations, and multi-region coordination  
What makes it useful: Only dataset with video integration. Shows event-based experimental design with precise behavioral timing. Good for understanding cross-region recordings.

5\. Grosmark \- Hippocampal Sequences

Brain region: Hippocampus (bilateral)  
Species: 4 brown rats  
Size: 61.2 GB (smallest dataset)  
Sessions: 2 per rat  
Data complexity: Medium \- focuses on sequence analysis with linearized position tracking  
What makes it useful: Simplest multi-modal example. Good starting point for understanding basic behavioral integration without overwhelming complexity.

What I noticed:

Different complexity levels: The datasets range from simple (Grosmark) to extremely complex (Senzai datasets). This gives us conversion examples at different sophistication levels.

Consistent NWB structure: All datasets follow standard NWB organization (acquisition → processing → analysis) but with different data types in each section.

Species considerations: Mouse vs rat data might affect our conversion approach depending on what species we're working with.

Recommendations

For getting started: Grosmark dataset would be easiest to project since it has the simplest structure and smallest file sizes.  
