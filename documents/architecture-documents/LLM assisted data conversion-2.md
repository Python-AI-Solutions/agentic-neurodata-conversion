# LLM assisted data conversion

#### Product description

* A prototype that converts user experimental input to standardized formats  
* Such a product could operate in two modes: archive input where all data is input at once or live input where experimental data is actively being gathered  
* An LLM based system will guide the data conversion and prompt the user for additional metadata  
* Validate output ([validator here](https://nwb-overview.readthedocs.io/en/latest/core_tools/core_tools_home.html#svg-version-1-1-width-1-5em-height-1-5em-class-sd-octicon-sd-octicon-code-review-viewbox-0-0-24-24-aria-hidden-true-path-d-m10-3-6-74a-75-75-0-0-1-04-1-06l-2-908-2-7-2-908-2-7a-75-75-0-1-1-1-02-1-1l-3-5-3-25a-75-75-0-0-1-0-1-1l3-5-3-25a-75-75-0-0-1-1-06-04zm3-44-1-06a-75-75-0-1-1-1-02-1-1l3-5-3-25a-75-75-0-0-1-0-1-1l-3-5-3-25a-75-75-0-1-1-1-02-1-1l2-908-2-7-2-908-2-7z-path-path-d-m1-5-4-25c0-966-784-1-75-1-75-1-75h17-5c-966-0-1-75-784-1-75-1-75v12-5a1-75-1-75-0-0-1-1-75-1-75h-9-69l-3-573-3-573a1-458-1-458-0-0-1-5-21-043v18-5h3-25a1-75-1-75-0-0-1-1-75-1-75zm3-25-4a-25-25-0-0-0-25-25v12-5c0-138-112-25-25-25h2-5a-75-75-0-0-1-75-75v3-19l3-72-3-72a-749-749-0-0-1-53-22h10a-25-25-0-0-0-25-25v4-25a-25-25-0-0-0-25-25z-path-svg-validating-nwb-files)) but also go beyond that to maximize utility of the conversion.  
* The interface may initially be a proof of concept pipeline, an mcp server, or web interface that utilizes the insight from the preceding steps

##### Rough strategy

* Create testing setup. Initial attempt will be to take some DANDI datasets and programmatically “mess them up” and use those as test sets that the LLM should restore to NWB format. Expanding this to other datasets that are actually messy (osf etc) will help expand this to a more generally useful solution (something that contains real-world challenges) though this requires more effort and pre-existing data should be found where possible.  
* Make use of catalystneuro’s expertise in the domain (including cookiecutter and open-sourced conversions)  
* Get LLM working  
  * Optimal tool-use (neuroconv and python) and context (RAG, prompt, MCP server(s) etc)  
  * Establish a helpful interaction with the user: ask the essential questions and surface the most important insights.  
  * Plan interactions between the different components according to priorities  
* In order to preserve as much information as possible and not commit to a spec instance consider NWB LinkML Schema / HDFM Spec-\> JSON Schema \-\> MCP Server  
* Prompt engineering (should be generic with adalflow or equivalent)  
* Get basic UI working  
* Figure out how to tie it all together into an application / System’s Design

John Thoughts:

* Tools for evaluation  
  * 

##### Longer term and non-goals for now:

* Lab notebook? (I think some good experimental tracking solutions exist already)  
* Possibly help upload to DANDI, openneuro etc.  
* Handles nesting NWB in BIDS or BIDS in NWB  
* Local model using [chatgpt-oss](https://openai.com/index/introducing-gpt-oss/)  
* Telemetry to guide our future development  
* Experiment types (decreasing order of priority for now)  
  * Ephys (neuroconv mediated?)  
  * Ndx extensions: [https://nwb-extensions.github.io/](https://nwb-extensions.github.io/)  
    * Support [HED annotations](https://bids-specification.readthedocs.io/en/stable/appendices/hed.html) (in BIDS and/or ndx-events)

  * BIDS (MRI scans) (some converters [here](https://github.com/bids-standard/awesome-bids/blob/main/README.md#converters))  
  * BIDS extensions (at least the [raw](https://github.com/bids-standard/awesome-bids/blob/main/README.md#raw) category)  
* Species:  
  * … (since scope might differ in eg human vs animal) …  
* Data formats/types  
  * DICOM  
  * Lab notebook records  
  * …  
  * Stimuli logs/scripts (as of PsychoPy, PTB-3, …), support for outputs from e.g. [https://psychopy-bids.readthedocs.io](https://psychopy-bids.readthedocs.io) ?

### Possible datasets

##### Tidy and for round tripping

DANDI

##### Messy with unknown truth

[https://osf.io/s93gq](https://osf.io/s93gq)  
[https://zenodo.org/communities/eu/records?q=electrophysiology\&f=resource\_type%3Adataset\&l=list\&p=1\&s=10\&sort=bestmatch](https://zenodo.org/communities/eu/records?q=electrophysiology&f=resource_type%3Adataset&l=list&p=1&s=10&sort=bestmatch)

##### Messy with known truth

##### Pre-existing conversions

* [https://catalystneuro.com/nwb-conversions/](https://catalystneuro.com/nwb-conversions/)

* 

### 

### Evaluation

* [https://humaneval.org/](https://humaneval.org/)  
* [https://github.com/microsoft/autogen/tree/main/python/packages/agbench](https://github.com/microsoft/autogen/tree/main/python/packages/agbench)  
* GuardRailsAI  
* DeepEval  
* RAGAs (for assessing RAG if we use it)  
* MCP [inspector](https://github.com/modelcontextprotocol/inspector) (for debugging MCP stuff)  
* Anthropic [notebook](https://github.com/anthropics/anthropic-cookbook/blob/main/misc/generate_test_cases.ipynb) on testing one’s prompts  
* Anthropic [notebook](https://github.com/anthropics/anthropic-cookbook/blob/main/misc/building_evals.ipynb) on evaluating model results  
* Observability: https://www.linkedin.com/posts/shantanuladhwe\_the-mother-of-ai-project-officially-activity-7356224556551782402-WH4m?utm\_source=share\&utm\_medium=member\_ios\&rcm=ACoAABoLPFsBQDNEEppy3cYUaKoQ2pklj7b2NRA

### Data representation

* [https://linkml.io/](https://linkml.io/)  
  * Can we write this from nwb? : Yes; either minimal overlay (fast) or reuse nwb-linkml translation patterns (heavier).   
    * Overlay approach: Create a minimal LinkML YAML that mirrors the subset of NWB/HDMF fields our pipeline consumes.   
    * [Translate NWB spec → LinkML (heavier)](https://nwb-linkml.readthedocs.io/en/latest/): Use nwb-linkml as reference or components to translate more of NWB core types if we need broader coverage.  
  * Checkout the mcp server satra posted about on linked in.  
    * MCP server for OME-Zarr conversion ([ngff-zarr-mcp](https://ngff-zarr.readthedocs.io/en/stable/spec_features.html)) with docs and PyPI package. It exposes conversion/validation tools to MCP hosts (Claude Desktop, Cursor, VS Code, etc.), and the docs explicitly list MCP integration as a feature in the NGFF-Zarr stack. This can be used as a future scope.   
  * Can we use this or will it be too hard to create the yml within the timeframe  
    * We can use it, it’s the right level of effort. Creating a minimal schema is not much of an effort.   
    * A full NWB re-modeling would be too heavy for the hackathon.  
* Context retrieval  
  * Can we compress the information into a single prompt  
- As the project proceeds further and we have to scale it, we will ultimately have to adapt a RAG pipeline. For the sake of hackathon if we are able to fit the whole KB into a single prompt we can simplify things.  
- The first step to check for the token size of the whole prompt is to try and ingest the neuroconv docs, for which we can use [context7](https://github.com/catalystneuro/neuroconv/pull/1450) integration.  
  * Use  a [knowledge graph](https://www.datacamp.com/blog/knowledge-graphs-and-llms)?  
- Knowledge graphs organize information in a graph-based structure, where nodes represent entities and edges represent their relationships. This structure is efficient for storing and retrieving factual and up-to-date information.  
- Graph databases like Neo4j can be helpful for implementation of Knowledge Graphs.  
- Better suited for scenarios where relationships and interconnectedness are the most important part of the data, I feel the traditional vector databases would be useful enough. This will also depend on how our KB grows, if we need to find semantically similar text chunks we can use the traditional vector database. We can also go with a hybrid approach.  
  * [https://www.anthropic.com/engineering/contextual-retrieval](https://www.anthropic.com/engineering/contextual-retrieval)  
- 200,000 tokens (about 500 pages of material) can fit in a single prompt.  
- Combining contextual embeddings, contextual BM25, and a reranking step offers the best performance improvements for contextual retrieval, a design decision which we can follow if we are following a RAG architecture. 

  * Useful tool for calculating token size:  
- [https://docs.anthropic.com/en/docs/build-with-claude/token-counting](https://docs.anthropic.com/en/docs/build-with-claude/token-counting)  
- [https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them](https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them): Applicable for OpenAI models but as a rule of thumb for English we can consider:

   \- 1 token ≈ 4 characters

  * Effort to create a pipeline that generates  summaries of all the tool examples:  
- [https://github.com/prady0t/conversion-pipeline](https://github.com/prady0t/conversion-pipeline)  
- Some tools have a lot of text, so we will have to use the “middle-out” transform in those cases.  
- Currently I’m extracting the documentation of neuroconv, converting it to txt using pandoc along with the file structure, and giving it’s context too. It takes about 65,000 tokens. We can also use “middle-out” transform here or generate a summary of this documentation as well to reduce the token size.  
- ​​gpt-5-mini’s context window size is 400,000 tokens.

### Prompt creation

* Creation and tuning: [https://console.anthropic.com/dashboard](https://console.anthropic.com/dashboard)  
* Useful Links:  
  * [https://www.techtarget.com/searchenterpriseai/tip/Prompt-engineering-tips-and-best-practices](https://www.techtarget.com/searchenterpriseai/tip/Prompt-engineering-tips-and-best-practices)  
  * [https://mirascope.com/blog/prompt-engineering-best-practices](https://mirascope.com/blog/prompt-engineering-best-practices)  
  * [https://www.bridgemind.ai/blog/prompt-engineering-best-practices](https://www.bridgemind.ai/blog/prompt-engineering-best-practices)  
* Components  
  * Neuroconv usage guidance as docs  
  * Neuroconv usage guidance based on distillation of pre-existing conversions  
  * Target specification (relevant part of the nwb spec)  
  * Ideal data representation (nwb-linkml)  
  * Guidance on how to create the conversion (instruction on using template and iteratively running the tool, assessing the result, communicating with the user)  
    * Guidance on how to assess the result  
    * Guidance on surfacing questions in order of priority to the user  
    * Guidance on reducing the manual effort of the user, the user should be able to apply conversions across multiple sessions with a single LLM instruction.  
    * Guidance on how to store and update the mapping between input and the target format as the iteration proceeds  
  * Evaluation rubric & metrics block  
  * Prompt skeleton template :   
    

### Agent frameworks

* CrewAI  
* LangGraph  
* [https://github.com/microsoft/autogen/tree/main](https://github.com/microsoft/autogen/tree/main)  
* AnythingLLM (alternative to MCP server for our deliverable)  
* [Configuring](https://www.anthropic.com/engineering/claude-code-best-practices) Claude code

#### Kiro hackathon

What can it do? What are the principles of the spec to keep in mind as we start to write it?  
[Agent hooks](https://kiro.dev/blog/automate-your-development-workflow-with-agent-hooks/)

#### Helpful links/thoughts

* Good starting point: [https://github.com/catalystneuro/cookiecutter-my-lab-to-nwb-template](https://github.com/catalystneuro/cookiecutter-my-lab-to-nwb-template)  
* [context7.com](http://context7.com) for tool specific MCP servers will be helpful.  
*  This is a nice overview of converting ephys data to nwb. This is an example of what we want to automate (but to expand our remit to all other experimental types too). [https://github.com/NeurodataWithoutBorders/exp2nwb](https://github.com/NeurodataWithoutBorders/exp2nwb)  
* AI enabled [data query](https://github.com/nimh-dsst/lunch-and-learn/tree/main/presentations/Natural_Language_Query_Agent)  
* [Instructor](https://python.useinstructor.com/#returning-the-original-completion-create_with_completion) for structured interaction with LLMs  
*  here’s a nice example of LLM based conversion for huge microscopy data types: [https://ngff-zarr.readthedocs.io/en/latest/mcp.html](https://ngff-zarr.readthedocs.io/en/latest/mcp.html)  
* Our tool should try to avoid overlap with other open efforts (except when we can entirely consume them perhaps). Examples of what I mean:  
  * Any data visualization efforts should take into account [Neurosift](https://nwb.org/tools/analysis/neurosift/)  
  * Examples of a notebook analysis (Jupyter in this case) that integrate with DANDI/NWB; this is the sort of prior art I don't want to replicate.   
    * [Explore NWB](https://nwb.org/tools/analysis/nwbexplorer/) with jupyter notebooks for analysis.  
    * [Use NWB](https://alleninstitute.github.io/openscope_databook/basics/background.htm) with jupyter for reproducible analysis  
  * the data acquisition itself has tools that write out the data: [https://nwb.org/tools/acquisition/](https://nwb.org/tools/acquisition/)  
* [Spyglass](https://lorenfranklab.github.io/spyglass/latest/) and [DataJoint](https://www.datajoint.com/solution/neuroscience) (partly closed source) are broadly scoped projects that have some overlap with the idea of a data converter. Worth mulling over… would we just be supporting bad practices (not organizing things during data collection and getting bitten afterwards when you forgot to track some metadata)  
* [LLM based file exploration](https://magland.github.io/neurosift-blog/posts/2024-12.html#chat-interface-for-nwb-file-exploration) (the far side of conversion)  
* Maybe provide help in suggesting plausible solutions for BIDS required details that are missing in the source data. E.g. Slice Timing for Philips scanners, Total Readout Time, or inferring phase encoding polarity.

**LinkML:** [https://linkml.io/linkml/generators/json-schema.html](https://linkml.io/linkml/generators/json-schema.html)

- Schema language written in YAML for defining data models  
- From a single YAML, it can generate:  
  - JSON Schema for validating JSON payloads,  
  - Pydantic models,  
  - RDF/JSON-LD/SHACL to sit in a semantic-web/ontological stack,  
  - plus Java/Python classes and more.  
- Why it fits us:  
  - We need the LLM to output strict, machine checkable metadata before we run conversion. LinkML gives us the one source of truth: write the minimal schema once, and we get JSON Schema (to force the LLM’s output to validate) and Pydantic (to parse/type-check in Python) for free. That reduces hallucinations and makes our loop reproducible.  
- Practical Use: https://linkml.io/linkml/generators/json-schema.html  
  - Draft a minimal LinkML YAML for the relevant fields   
  - Generate JSON Schema  
  - Generate Pydantic

# 

# **NWB \+ LinkML: can they work together?**

Yes. There’s already work mapping the NWB schema language into LinkML:

* [nwb-linkml](https://nwb-linkml.readthedocs.io/en/latest/): “A translation of the Neurodata Without Borders standard to LinkML”  supports translating NWB schema language → LinkML, generating Pydantic from the LinkML, and even reading NWB files. This shows the mapping is feasible and gives patterns for tricky bits like DynamicTable. [https://nwb-linkml.readthedocs.io/en/latest/](https://nwb-linkml.readthedocs.io/?utm_source=chatgpt.com)  
* NWB itself is specified in YAML via the NWB/HDMF specification language. That makes it structurally compatible with being projected into LinkML (directly or as a curated “overlay” for just the metadata we need).

## Timeline

### July 25th-28th \- Preliminary scoping

##### Draw up a spec document

##### Consider datasets that are messy

We will need some examples for testing etc. Figshare/osf/zenodo might be some places to look once we know what the scope of the project is.

### July 28th \- Discussion with Josh

GUI apps don’t have thorough support for all data types and require a lot of repetitive data entry to guide the process. Don’t necessarily incorporate the full range of experimental artifacts: pdf, word docs, eln apis etc.

Core task for the LLM: look at what’s been done and have a conversation about it to get to a standardized format. Can add directories etc.  
Approach: make ephys data messy, show the llm can guide the restoration to a standard format.

Other details:

* Labarchives has a basic Rest api (ELN API being developed at the moment so could incorporate that at a later date as part of the info provided.)  
* Fiber photometry is NWB data without GUIDE support. (TDT in neuroconv)  
* Frustration with guide: lots of repetition. grad/postbac will have to repeat themselves a lot. Josh has spent a lot of time guiding students in ELN… the opportunity is to replace the manual part of the GUIDE videos with an LLM guided process.  
* GEMMA 3 has good pdf import.   
* Adalflow: help with prompt engineering for the task  
* Synthetic data: dictionary mapping for replacement of metadata. Erroneous Name mapping is prevalent, time format consistency, expand these as test cases. Worddoc is a common file used for documentation.  
* IRP is guinea pig. ELN will be the future. Possibly a widespread requirement… and better maintained. Provides evidence for misconduct. There is less concern about privacy for NWB data so may be a better starting point. BIDS brushes up against PII issues more readily.  
* Example model usage strategies: [https://github.com/NarimanN2/ollama-playground](https://github.com/NarimanN2/ollama-playground)  
* GUIDE gives tables for editing… a nice user-interface we could mimic  
* zenodo also has examples of messy data

### July 31st \- Discuss with Satra

What a human could guide an llm to do vs   
Information vs standard  
Minimal metadata… allows for some search to reduce human burden  
Could we get to more useful… get as much as possible…  
Sata’s linked in post on mcp server  
Context engineering: rote knowledge in the specs, general documentation, human expertise: collated to markdown  
LinkML… can help guide (LBNL lab uses yaml to define a schema that can be converted to pydantic/json etc)  
HDMF defines the schema (linkml arrays is a related effort to try to make them work together)  
What could this do for people? (info space). BIDS/DANDI etc. taxonomy schema \-\> linkml  
It could provide an interface to convert between schemas  
Extension: more complex validation…   
Would love to see generative system for tools themselves. A nice thing to move towards to 

Omezarr: mcps gets lots of context: mcps,docs,   
Brainhack: objective: no code. Minicline to see where things were failing with vibe-coding.  
Some failures: installation… doesn’t pre-empt.  
Human touches and how to predict them is an interesting exploration.  
Keep things minimal  
Keeping things as text…  
Multimodal models… could handle images  
Dandi mcp instead of others developing it  
Notebook paper.  
Nidm:extensions over bids: get it to ontological space: make the review process quick  
How do you know its done a good job  
Heuristics beyond what’s in the data… task info for heudiconv…. Reproin facilitated this.  
Models capture structured representations well. In either case tools can be used. Which one has better errors for the llm to interpret.  
Gemini’s large context helps for dumping all docs  
Comparative analysis of models  
Different models critiquing the attempts  
Exporting the entire doc… neither docs are big enough.  
Instruct platform to understand the information space: repronim… look at the organisation and understand the patterns.  
What are the relevant components…  
    
Conversation level (Adhere to structure of prompt?)

* **Warm up**  
* Did the model engage in friendly conversation to start?  
* Did the model ask the child about the audiobook and follow-up?  
* **Vocab**  
* Did the model cover 2 vocabulary words  
* Vocab selection  
* Proper word choices?  
* New word if child already familiar?  
* Word introduction  
* Did the model introduce the words by saying, “Today, we’re going to learn a new word that you heard in your book. The word is \[word\].”  
* Did the model ask if the child knows the word?  
* Vocab Definition  
* Did the model define the word in simple terms?  
* Did the model use context to show how to get the meaning?  
* Vocab Reinforcement  
* Did the model ask the child to use the word in a new sentence?  
* Did the model ask the child to speak about aspects of the word (e.g. things you might find at a feast)  
* Did the model ask the child to repeat the word properly? (future work?)  
* Did the model present a simple choice related to the word?  
* Did the model ask for a sentence from a totally different context?  
* **Review and Recap**  
* Did the model prompt the child to define the word again?  
* Did the model prompt the child to use it in a new sentence, without any help?  
* Did the model give the formal definition again?  
* **Closing**  
* Did the model praise the child and encourage them to continue listening to their audiobook?

Response level

* Positive, motivational and encouraging  
* Which response sounds more like something a skilled teacher would say  
* Which response better understands the student?

### August 2nd \-6th \- Finalize spec

##### Pin down the likely technologies

##### Take Kiro spec best practices into account

### August 7th- August 13th \- Core sprint to deliver prototype

### Aug 14th-18th: Consolidation

### August 19th-22nd \- Final push

### Aug 23rd: Attempt submission

## Competition details

### Judging

Stage One) The first stage will determine via pass/fail whether the ideas meet a baseline level of viability, in that the Project reasonably fits the theme and reasonably applies the required APIs/SDKs featured in the Hackathon.  
Stage Two) All Submissions that pass Stage One will be evaluated in Stage Two based on the following equally weighted criteria (the “Judging Criteria”):  
Entries will be judged on the following equally weighted criteria, and according to the sole and absolute discretion of the judges:

* Potential Value

Includes the extent to which the solution can be widely useful, easy to use, accessible, etc.

* Implementation

Includes how well the idea is leveraging Kiro.

* Quality of the Idea

Includes creativity, originality of the project, such as finding and using unique public datasets, or solving a challenge in a unique way.

##### Socials/comms prizes aren’t worth the effort 

**~~How to Enter Social Blitz Prize~~**  
~~Enter by posting on social (X, LI, IG, or BlueSky) your favorite thing about Kiro with a description of how it changed the way you approached development. To be considered, you must post during the submission period, tag @kirodotdev in your post, and use the hashtag \#hookedonkiro. Sponsor will review submissions and select our favorite five. Sponsor reserves the right to choose any five posts as the winners.~~  
**~~Blog Post Bonus Prize~~**  
~~Blog Post Bonus Prize Submission Requirements Publish a blog post on [https://dev.to/kirodotdev](https://dev.to/kirodotdev) about your project during the Submission Period.~~

* ~~Use the hashtag \#kiro when posting on the dev.to space~~

~~Include a link to your published blog post on your Devpost Project submission form. Blog posts can cover similar topics but should be materially different than the Devpost text description.~~

### Other monetary consideration

* Consider a business model for sustainable longer term development/maintenance. This keeps the most useful technology free for all users  
  * We could provide technical support (I think this is along the lines of what CatalystNeuro do)  
  * We define a core product that we want everyone to use and wrap a SAAS around that or just add usage/tuning support. I think this generally leads to too much conflict of interest between free offering and the service.

### Motivation

- Publicity  
- Prize money  
- Tangential but can serve as preparation for NIH contract  
- Trying out the new AI kid on the block  
- Vague possibility of future revenue stream if it’s successful and people want to fund its development

### Rules to consider

* An Entrant may contract with a third party for technical assistance to create the Submission provided the Submission components are solely the Entrant’s work product and the result of the Entrant’s ideas and creativity, and the Entrant owns all rights to them.

