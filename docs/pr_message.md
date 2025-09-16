{"body":"**Title:**\r\n\r\n**KG specs: adopt NWB-LinkML schema; add JSON-LD
context/SHACL; update tasks**\r\n\r\n**Summary**\r\nAdopt NWB-LinkML as the
canonical schema for NWB knowledge graph modeling.\r\nIntroduce schema-driven
JSON-LD context, SHACL validation, and RDF/OWL artifact generation.\r\nAlign
design, requirements, and tasks to schema-first workflows with provenance and
versioning.\r\n\r\n**Changes**\r\nUpdated
/.kiro/specs/knowledge-graph-systems/design.md\r\nAdded Schema and Validation
Layer (NWB-LinkML).\r\nRevised data flow: LinkML instance validation → SHACL →
RDF generation → KG ingestion.\r\nClarified artifact generation: JSON-LD
@context, SHACL shapes, OWL/RDF; provenance capture.\r\nUpdated
/.kiro/specs/knowledge-graph-systems/requirements.md\r\nAdded schema-driven
validation requirements (LinkML instance validation, SHACL from schema, JSON-LD
@context).\r\nAdded artifact/version management (pin schema version, provenance
recording).\r\nUpdated /.kiro/specs/knowledge-graph-systems/tasks.md\r\nAdded
tasks for NWB-LinkML integration and schema artifact generation.\r\nMade
SPARQL/validation schema-aware; added schema-aware API endpoints.\r\nCapture
schema version and artifact hashes in
exports/provenance.\r\n\r\n**Rationale**\r\nEnsures consistent IRIs and
structure across pipelines via schema-derived JSON-LD.\r\nEnforces structural
correctness with SHACL generated from the same schema source.\r\nImproves
traceability by recording schema version in PROV-O
provenance.\r\n\r\n**Scope**\r\nSpecs-only change (no runtime code
changes).\r\nPrepares the ground for implementation of schema validation, SHACL
checks, and exporters.\r\n\r\n**Implementation Notes**\r\nLinkML artifacts to
produce: JSON-LD @context, SHACL shapes, RDF/OWL.\r\nCache/version artifacts;
pin versions in provenance.\r\nAlign external ontologies (NIFSTD, UBERON) to
NWB-LinkML classes/slots.\r\n\r\n**Validation**\r\n[ ] Specs render and read
clearly.\r\n[ ] Requirements map to tasks (schema validation, SHACL,
exporters).\r\n[ ] No breaking changes to code or tests.\r\n\r\n**Backwards
Compatibility**\r\nDocs/specs only; no runtime impact.\r\nFuture PRs will
implement schema validation and artifact pipelines.\r\n","title":"KG specs:
adopt NWB-LinkML schema; add JSON-LD/SHACL; update tasks"}
