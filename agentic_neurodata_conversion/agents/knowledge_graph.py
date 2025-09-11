"""
Knowledge graph agent for semantic data representation and querying.

This agent handles the creation and management of knowledge graphs from
NWB data and metadata, providing semantic search and relationship discovery.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import json
import tempfile

from .base import BaseAgent, AgentCapability, AgentStatus

logger = logging.getLogger(__name__)


class KnowledgeGraphAgent(BaseAgent):
    """
    Agent responsible for knowledge graph creation and management.
    
    This agent creates semantic representations of NWB data and metadata,
    builds knowledge graphs, and provides querying capabilities for
    relationship discovery and semantic search.
    """
    
    def __init__(self, config: Optional[Any] = None, agent_id: Optional[str] = None):
        """
        Initialize the knowledge graph agent.
        
        Args:
            config: Agent configuration containing KG settings and format preferences.
            agent_id: Optional agent identifier.
        """
        self.knowledge_graphs: Dict[str, Any] = {}
        self.graph_cache: Dict[str, Any] = {}
        self.output_format = "ttl"
        self.namespaces: Dict[str, str] = {}
        self.ontologies: Dict[str, Any] = {}
        
        super().__init__(config, agent_id)
    
    def _initialize(self) -> None:
        """Initialize knowledge graph agent specific components."""
        # Register capabilities
        self.add_capability(AgentCapability.KNOWLEDGE_GRAPH)
        
        # Load configuration
        if self.config:
            self.output_format = getattr(self.config, 'knowledge_graph_format', 'ttl')
        
        # Initialize namespaces and ontologies
        self._initialize_namespaces()
        self._initialize_ontologies()
        
        # Update metadata
        self.update_metadata({
            "output_format": self.output_format,
            "namespaces": len(self.namespaces),
            "ontologies": len(self.ontologies),
            "active_graphs": 0,
            "cache_size": 0
        })
        
        logger.info(f"KnowledgeGraphAgent {self.agent_id} initialized with format={self.output_format}")
    
    def _initialize_namespaces(self) -> None:
        """Initialize standard namespaces for the knowledge graph."""
        self.namespaces = {
            "nwb": "https://nwb-schema.readthedocs.io/en/latest/",
            "prov": "http://www.w3.org/ns/prov#",
            "dcat": "http://www.w3.org/ns/dcat#",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "dcterms": "http://purl.org/dc/terms/",
            "schema": "https://schema.org/",
            "neuro": "https://neuroscience.org/ontology/",
            "units": "http://purl.obolibrary.org/obo/UO_",
            "time": "http://www.w3.org/2006/time#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "owl": "http://www.w3.org/2002/07/owl#"
        }
        
        logger.info(f"Initialized {len(self.namespaces)} standard namespaces")
    
    def _initialize_ontologies(self) -> None:
        """Initialize relevant ontologies for neuroscience data."""
        self.ontologies = {
            "nwb_schema": {
                "description": "NWB Schema ontology",
                "version": "2.6.0",
                "concepts": [
                    "TimeSeries", "ElectricalSeries", "SpikeEventSeries",
                    "BehavioralTimeSeries", "ProcessingModule", "Device"
                ]
            },
            "neuroscience": {
                "description": "General neuroscience ontology",
                "concepts": [
                    "Neuron", "Synapse", "ElectricalActivity", "Behavior",
                    "Experiment", "Subject", "Session"
                ]
            },
            "provenance": {
                "description": "Data provenance ontology",
                "concepts": [
                    "Activity", "Entity", "Agent", "Generation", "Usage"
                ]
            }
        }
        
        logger.info(f"Initialized {len(self.ontologies)} ontologies")
    
    def get_capabilities(self) -> Set[AgentCapability]:
        """Get the capabilities provided by this agent."""
        return {AgentCapability.KNOWLEDGE_GRAPH}
    
    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task assigned to the knowledge graph agent.
        
        Args:
            task: Task dictionary containing task type and parameters.
            
        Returns:
            Dictionary containing the processing result.
        """
        task_type = task.get("type")
        
        if task_type == "knowledge_graph":
            return await self._create_knowledge_graph(task)
        elif task_type == "graph_query":
            return await self._query_knowledge_graph(task)
        elif task_type == "graph_export":
            return await self._export_knowledge_graph(task)
        elif task_type == "graph_merge":
            return await self._merge_knowledge_graphs(task)
        else:
            raise NotImplementedError(f"Task type '{task_type}' not supported by KnowledgeGraphAgent")
    
    async def _create_knowledge_graph(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a knowledge graph from NWB data and metadata.
        
        Args:
            task: Task containing nwb_path, metadata, and graph parameters.
            
        Returns:
            Dictionary containing the created knowledge graph.
        """
        nwb_path = task.get("nwb_path")
        metadata = task.get("metadata", {})
        graph_id = task.get("graph_id", f"kg_{len(self.knowledge_graphs)}")
        include_provenance = task.get("include_provenance", True)
        
        if not nwb_path:
            raise ValueError("nwb_path is required for knowledge graph creation")
        
        nwb_file = Path(nwb_path)
        if not nwb_file.exists():
            raise FileNotFoundError(f"NWB file not found: {nwb_path}")
        
        # Check cache first
        cache_key = f"kg_{nwb_file.resolve()}_{graph_id}"
        if cache_key in self.graph_cache:
            logger.info(f"Returning cached knowledge graph for {nwb_path}")
            return self.graph_cache[cache_key]
        
        try:
            # Create knowledge graph
            knowledge_graph = await self._build_knowledge_graph(
                nwb_file, metadata, graph_id, include_provenance
            )
            
            # Store the graph
            self.knowledge_graphs[graph_id] = knowledge_graph
            self.graph_cache[cache_key] = knowledge_graph
            
            # Update metadata
            self.update_metadata({
                "active_graphs": len(self.knowledge_graphs),
                "cache_size": len(self.graph_cache)
            })
            
            return {
                "status": "success",
                "result": knowledge_graph,
                "agent_id": self.agent_id,
                "cached": False
            }
            
        except Exception as e:
            logger.error(f"Knowledge graph creation failed for {nwb_path}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "agent_id": self.agent_id
            }
    
    async def _build_knowledge_graph(self, nwb_file: Path, metadata: Dict[str, Any], 
                                   graph_id: str, include_provenance: bool) -> Dict[str, Any]:
        """
        Build a knowledge graph from NWB file and metadata.
        
        Args:
            nwb_file: Path to the NWB file.
            metadata: Additional metadata to include.
            graph_id: Identifier for the graph.
            include_provenance: Whether to include provenance information.
            
        Returns:
            Dictionary representing the knowledge graph.
        """
        knowledge_graph = {
            "graph_id": graph_id,
            "source_file": str(nwb_file),
            "created_timestamp": None,
            "format": self.output_format,
            "namespaces": self.namespaces.copy(),
            "entities": {},
            "relationships": [],
            "provenance": {} if include_provenance else None,
            "statistics": {}
        }
        
        try:
            # Extract entities from NWB file structure
            entities = await self._extract_nwb_entities(nwb_file, metadata)
            knowledge_graph["entities"] = entities
            
            # Build relationships between entities
            relationships = await self._build_entity_relationships(entities)
            knowledge_graph["relationships"] = relationships
            
            # Add provenance information if requested
            if include_provenance:
                provenance = await self._build_provenance_graph(nwb_file, metadata)
                knowledge_graph["provenance"] = provenance
            
            # Generate graph statistics
            statistics = self._calculate_graph_statistics(knowledge_graph)
            knowledge_graph["statistics"] = statistics
            
            logger.info(f"Built knowledge graph {graph_id} with {len(entities)} entities and {len(relationships)} relationships")
            
        except Exception as e:
            logger.error(f"Error building knowledge graph: {e}")
            raise
        
        return knowledge_graph
    
    async def _extract_nwb_entities(self, nwb_file: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract entities from NWB file structure and metadata.
        
        Args:
            nwb_file: Path to the NWB file.
            metadata: Additional metadata.
            
        Returns:
            Dictionary of extracted entities.
        """
        entities = {}
        
        # This is a placeholder implementation
        # In a real implementation, this would use pynwb to read the NWB file
        # and extract actual entities like TimeSeries, Devices, etc.
        
        # Create basic entities from metadata
        if "session_description" in metadata:
            entities["session"] = {
                "type": "nwb:Session",
                "id": f"session_{nwb_file.stem}",
                "description": metadata["session_description"],
                "properties": {
                    "session_start_time": metadata.get("session_start_time"),
                    "experimenter": metadata.get("experimenter"),
                    "institution": metadata.get("institution"),
                    "lab": metadata.get("lab")
                }
            }
        
        if "subject_id" in metadata:
            entities["subject"] = {
                "type": "nwb:Subject",
                "id": metadata["subject_id"],
                "properties": {
                    "species": metadata.get("species"),
                    "age": metadata.get("age"),
                    "sex": metadata.get("sex"),
                    "description": metadata.get("subject_description")
                }
            }
        
        # Create device entities
        devices = metadata.get("devices", {})
        for device_name, device_info in devices.items():
            entities[f"device_{device_name}"] = {
                "type": "nwb:Device",
                "id": device_name,
                "properties": device_info
            }
        
        # Create data entities (placeholder)
        entities["recording_data"] = {
            "type": "nwb:ElectricalSeries",
            "id": f"recording_{nwb_file.stem}",
            "properties": {
                "source_file": str(nwb_file),
                "file_size": nwb_file.stat().st_size,
                "data_type": "electrical_recording"
            }
        }
        
        logger.debug(f"Extracted {len(entities)} entities from NWB file")
        return entities
    
    async def _build_entity_relationships(self, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build relationships between extracted entities.
        
        Args:
            entities: Dictionary of entities.
            
        Returns:
            List of relationship dictionaries.
        """
        relationships = []
        
        # Build relationships based on entity types and properties
        session_entity = None
        subject_entity = None
        device_entities = []
        data_entities = []
        
        # Categorize entities
        for entity_id, entity in entities.items():
            entity_type = entity.get("type", "")
            if "Session" in entity_type:
                session_entity = entity_id
            elif "Subject" in entity_type:
                subject_entity = entity_id
            elif "Device" in entity_type:
                device_entities.append(entity_id)
            elif "Series" in entity_type:
                data_entities.append(entity_id)
        
        # Create relationships
        if session_entity and subject_entity:
            relationships.append({
                "subject": session_entity,
                "predicate": "nwb:hasSubject",
                "object": subject_entity,
                "type": "association"
            })
        
        if session_entity:
            for device_id in device_entities:
                relationships.append({
                    "subject": session_entity,
                    "predicate": "nwb:usedDevice",
                    "object": device_id,
                    "type": "usage"
                })
            
            for data_id in data_entities:
                relationships.append({
                    "subject": session_entity,
                    "predicate": "nwb:contains",
                    "object": data_id,
                    "type": "containment"
                })
        
        # Device-data relationships
        for device_id in device_entities:
            for data_id in data_entities:
                relationships.append({
                    "subject": data_id,
                    "predicate": "nwb:recordedBy",
                    "object": device_id,
                    "type": "generation"
                })
        
        logger.debug(f"Built {len(relationships)} relationships between entities")
        return relationships
    
    async def _build_provenance_graph(self, nwb_file: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build provenance information for the knowledge graph.
        
        Args:
            nwb_file: Path to the NWB file.
            metadata: Metadata containing provenance information.
            
        Returns:
            Dictionary containing provenance graph.
        """
        provenance = {
            "activities": {},
            "entities": {},
            "agents": {},
            "relationships": []
        }
        
        # Create conversion activity
        conversion_activity = {
            "id": f"conversion_{nwb_file.stem}",
            "type": "prov:Activity",
            "label": "NWB Conversion",
            "startTime": metadata.get("conversion_start_time"),
            "endTime": metadata.get("conversion_end_time"),
            "properties": {
                "converter": metadata.get("converter_name", "NeuroConv"),
                "converter_version": metadata.get("converter_version")
            }
        }
        provenance["activities"]["conversion"] = conversion_activity
        
        # Create source data entity
        source_data = {
            "id": f"source_data_{nwb_file.stem}",
            "type": "prov:Entity",
            "label": "Source Data",
            "properties": {
                "format": metadata.get("source_format"),
                "location": metadata.get("source_location")
            }
        }
        provenance["entities"]["source_data"] = source_data
        
        # Create NWB file entity
        nwb_entity = {
            "id": f"nwb_file_{nwb_file.stem}",
            "type": "prov:Entity",
            "label": "NWB File",
            "properties": {
                "path": str(nwb_file),
                "format": "NWB",
                "size": nwb_file.stat().st_size
            }
        }
        provenance["entities"]["nwb_file"] = nwb_entity
        
        # Create agent (experimenter/converter)
        if metadata.get("experimenter"):
            agent = {
                "id": f"agent_{metadata['experimenter']}",
                "type": "prov:Agent",
                "label": metadata["experimenter"],
                "properties": {
                    "role": "experimenter",
                    "institution": metadata.get("institution")
                }
            }
            provenance["agents"]["experimenter"] = agent
        
        # Create provenance relationships
        provenance["relationships"].extend([
            {
                "subject": "conversion",
                "predicate": "prov:used",
                "object": "source_data"
            },
            {
                "subject": "nwb_file",
                "predicate": "prov:wasGeneratedBy",
                "object": "conversion"
            }
        ])
        
        if "experimenter" in provenance["agents"]:
            provenance["relationships"].append({
                "subject": "conversion",
                "predicate": "prov:wasAssociatedWith",
                "object": "experimenter"
            })
        
        logger.debug("Built provenance graph with conversion history")
        return provenance
    
    def _calculate_graph_statistics(self, knowledge_graph: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate statistics for the knowledge graph.
        
        Args:
            knowledge_graph: The knowledge graph to analyze.
            
        Returns:
            Dictionary containing graph statistics.
        """
        entities = knowledge_graph.get("entities", {})
        relationships = knowledge_graph.get("relationships", [])
        provenance = knowledge_graph.get("provenance", {})
        
        # Entity type distribution
        entity_types = {}
        for entity in entities.values():
            entity_type = entity.get("type", "unknown")
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        # Relationship type distribution
        relationship_types = {}
        for rel in relationships:
            rel_type = rel.get("type", "unknown")
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
        
        statistics = {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "entity_types": entity_types,
            "relationship_types": relationship_types,
            "has_provenance": provenance is not None,
            "provenance_activities": len(provenance.get("activities", {})) if provenance else 0,
            "graph_density": len(relationships) / max(len(entities), 1)
        }
        
        return statistics
    
    async def _query_knowledge_graph(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query a knowledge graph using SPARQL-like queries.
        
        Args:
            task: Task containing graph_id and query parameters.
            
        Returns:
            Dictionary containing query results.
        """
        graph_id = task.get("graph_id")
        query = task.get("query", "")
        query_type = task.get("query_type", "entity_search")
        
        if not graph_id or graph_id not in self.knowledge_graphs:
            raise ValueError(f"Knowledge graph not found: {graph_id}")
        
        knowledge_graph = self.knowledge_graphs[graph_id]
        
        try:
            # Execute query based on type
            if query_type == "entity_search":
                results = self._search_entities(knowledge_graph, query)
            elif query_type == "relationship_search":
                results = self._search_relationships(knowledge_graph, query)
            elif query_type == "path_finding":
                results = self._find_paths(knowledge_graph, task.get("start_entity"), task.get("end_entity"))
            else:
                raise ValueError(f"Unsupported query type: {query_type}")
            
            return {
                "status": "success",
                "result": {
                    "query": query,
                    "query_type": query_type,
                    "graph_id": graph_id,
                    "results": results,
                    "result_count": len(results) if isinstance(results, list) else 1
                },
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            logger.error(f"Knowledge graph query failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "agent_id": self.agent_id
            }
    
    def _search_entities(self, knowledge_graph: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Search for entities matching the query."""
        entities = knowledge_graph.get("entities", {})
        results = []
        
        query_lower = query.lower()
        
        for entity_id, entity in entities.items():
            # Search in entity ID, type, and properties
            if (query_lower in entity_id.lower() or 
                query_lower in entity.get("type", "").lower() or
                any(query_lower in str(value).lower() for value in entity.get("properties", {}).values())):
                
                results.append({
                    "entity_id": entity_id,
                    "entity": entity,
                    "match_score": 1.0  # Simplified scoring
                })
        
        return results
    
    def _search_relationships(self, knowledge_graph: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Search for relationships matching the query."""
        relationships = knowledge_graph.get("relationships", [])
        results = []
        
        query_lower = query.lower()
        
        for rel in relationships:
            # Search in relationship predicate and type
            if (query_lower in rel.get("predicate", "").lower() or
                query_lower in rel.get("type", "").lower()):
                
                results.append({
                    "relationship": rel,
                    "match_score": 1.0
                })
        
        return results
    
    def _find_paths(self, knowledge_graph: Dict[str, Any], start_entity: str, end_entity: str) -> List[List[str]]:
        """Find paths between two entities in the graph."""
        if not start_entity or not end_entity:
            return []
        
        relationships = knowledge_graph.get("relationships", [])
        
        # Build adjacency list
        graph = {}
        for rel in relationships:
            subject = rel.get("subject")
            obj = rel.get("object")
            
            if subject not in graph:
                graph[subject] = []
            graph[subject].append(obj)
        
        # Simple BFS path finding
        paths = []
        queue = [(start_entity, [start_entity])]
        visited = set()
        
        while queue and len(paths) < 10:  # Limit to 10 paths
            current, path = queue.pop(0)
            
            if current == end_entity:
                paths.append(path)
                continue
            
            if current in visited:
                continue
            
            visited.add(current)
            
            for neighbor in graph.get(current, []):
                if neighbor not in path:  # Avoid cycles
                    queue.append((neighbor, path + [neighbor]))
        
        return paths
    
    async def _export_knowledge_graph(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export a knowledge graph to various formats.
        
        Args:
            task: Task containing graph_id and export parameters.
            
        Returns:
            Dictionary containing export results.
        """
        graph_id = task.get("graph_id")
        export_format = task.get("format", self.output_format)
        output_path = task.get("output_path")
        
        if not graph_id or graph_id not in self.knowledge_graphs:
            raise ValueError(f"Knowledge graph not found: {graph_id}")
        
        knowledge_graph = self.knowledge_graphs[graph_id]
        
        try:
            # Generate export content
            export_content = self._generate_export_content(knowledge_graph, export_format)
            
            # Save to file if path provided
            if output_path:
                export_path = Path(output_path)
                export_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write(export_content)
                
                logger.info(f"Exported knowledge graph to: {export_path}")
            else:
                # Create temporary file
                with tempfile.NamedTemporaryFile(
                    mode='w', 
                    suffix=f'.{export_format}',
                    prefix=f'kg_{graph_id}_',
                    delete=False
                ) as f:
                    f.write(export_content)
                    export_path = Path(f.name)
            
            return {
                "status": "success",
                "result": {
                    "export_path": str(export_path),
                    "format": export_format,
                    "content_size": len(export_content),
                    "graph_id": graph_id
                },
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            logger.error(f"Knowledge graph export failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "agent_id": self.agent_id
            }
    
    def _generate_export_content(self, knowledge_graph: Dict[str, Any], export_format: str) -> str:
        """
        Generate export content in the specified format.
        
        Args:
            knowledge_graph: The knowledge graph to export.
            export_format: Target format (ttl, rdf, jsonld, json).
            
        Returns:
            Export content as string.
        """
        if export_format == "json":
            return json.dumps(knowledge_graph, indent=2)
        elif export_format == "ttl":
            return self._generate_turtle_content(knowledge_graph)
        elif export_format == "jsonld":
            return self._generate_jsonld_content(knowledge_graph)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    def _generate_turtle_content(self, knowledge_graph: Dict[str, Any]) -> str:
        """Generate Turtle (TTL) format content."""
        content = []
        
        # Add namespace prefixes
        for prefix, uri in knowledge_graph.get("namespaces", {}).items():
            content.append(f"@prefix {prefix}: <{uri}> .")
        
        content.append("")  # Empty line
        
        # Add entities
        entities = knowledge_graph.get("entities", {})
        for entity_id, entity in entities.items():
            entity_type = entity.get("type", "owl:Thing")
            content.append(f":{entity_id} a {entity_type} ;")
            
            properties = entity.get("properties", {})
            for prop, value in properties.items():
                if isinstance(value, str):
                    content.append(f'    :{prop} "{value}" ;')
                else:
                    content.append(f'    :{prop} {value} ;')
            
            content.append("    .")
            content.append("")
        
        # Add relationships
        relationships = knowledge_graph.get("relationships", [])
        for rel in relationships:
            subject = rel.get("subject")
            predicate = rel.get("predicate")
            obj = rel.get("object")
            
            content.append(f":{subject} {predicate} :{obj} .")
        
        return "\n".join(content)
    
    def _generate_jsonld_content(self, knowledge_graph: Dict[str, Any]) -> str:
        """Generate JSON-LD format content."""
        jsonld = {
            "@context": knowledge_graph.get("namespaces", {}),
            "@graph": []
        }
        
        # Add entities
        entities = knowledge_graph.get("entities", {})
        for entity_id, entity in entities.items():
            jsonld_entity = {
                "@id": entity_id,
                "@type": entity.get("type")
            }
            
            properties = entity.get("properties", {})
            jsonld_entity.update(properties)
            
            jsonld["@graph"].append(jsonld_entity)
        
        return json.dumps(jsonld, indent=2)
    
    async def _merge_knowledge_graphs(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple knowledge graphs into one.
        
        Args:
            task: Task containing graph_ids to merge and merge parameters.
            
        Returns:
            Dictionary containing the merged knowledge graph.
        """
        graph_ids = task.get("graph_ids", [])
        merged_graph_id = task.get("merged_graph_id", f"merged_{len(self.knowledge_graphs)}")
        
        if not graph_ids:
            raise ValueError("graph_ids is required for merging")
        
        # Verify all graphs exist
        for graph_id in graph_ids:
            if graph_id not in self.knowledge_graphs:
                raise ValueError(f"Knowledge graph not found: {graph_id}")
        
        try:
            # Create merged graph
            merged_graph = {
                "graph_id": merged_graph_id,
                "source_graphs": graph_ids,
                "format": self.output_format,
                "namespaces": self.namespaces.copy(),
                "entities": {},
                "relationships": [],
                "provenance": None,
                "statistics": {}
            }
            
            # Merge entities and relationships
            for graph_id in graph_ids:
                source_graph = self.knowledge_graphs[graph_id]
                
                # Merge entities (with ID prefixing to avoid conflicts)
                for entity_id, entity in source_graph.get("entities", {}).items():
                    prefixed_id = f"{graph_id}_{entity_id}"
                    merged_graph["entities"][prefixed_id] = entity.copy()
                
                # Merge relationships (updating entity references)
                for rel in source_graph.get("relationships", []):
                    merged_rel = rel.copy()
                    merged_rel["subject"] = f"{graph_id}_{rel['subject']}"
                    merged_rel["object"] = f"{graph_id}_{rel['object']}"
                    merged_graph["relationships"].append(merged_rel)
            
            # Calculate statistics for merged graph
            merged_graph["statistics"] = self._calculate_graph_statistics(merged_graph)
            
            # Store merged graph
            self.knowledge_graphs[merged_graph_id] = merged_graph
            
            return {
                "status": "success",
                "result": merged_graph,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            logger.error(f"Knowledge graph merge failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "agent_id": self.agent_id
            }
    
    def get_available_graphs(self) -> List[str]:
        """Get list of available knowledge graph IDs."""
        return list(self.knowledge_graphs.keys())
    
    def remove_knowledge_graph(self, graph_id: str) -> bool:
        """
        Remove a knowledge graph from memory.
        
        Args:
            graph_id: ID of the graph to remove.
            
        Returns:
            True if removed, False if not found.
        """
        if graph_id in self.knowledge_graphs:
            del self.knowledge_graphs[graph_id]
            
            # Remove from cache as well
            cache_keys_to_remove = [key for key in self.graph_cache.keys() if graph_id in key]
            for key in cache_keys_to_remove:
                del self.graph_cache[key]
            
            self.update_metadata({
                "active_graphs": len(self.knowledge_graphs),
                "cache_size": len(self.graph_cache)
            })
            
            logger.info(f"Removed knowledge graph: {graph_id}")
            return True
        
        return False
    
    def clear_cache(self) -> None:
        """Clear the knowledge graph cache."""
        self.graph_cache.clear()
        self.update_metadata({"cache_size": 0})
        logger.info(f"Cleared knowledge graph cache for agent {self.agent_id}")
    
    async def shutdown(self) -> None:
        """Shutdown the knowledge graph agent."""
        # Clear all graphs and cache
        self.knowledge_graphs.clear()
        self.clear_cache()
        
        await super().shutdown()
        logger.info(f"KnowledgeGraphAgent {self.agent_id} shutdown completed")