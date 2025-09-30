"""
RDF triple store service with SPARQL endpoint.

Constitutional compliance: 30-second query timeout, W3C SPARQL standards.
"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
import logging
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.plugins.sparql import prepareQuery
from rdflib.query import Result
import httpx


logger = logging.getLogger(__name__)


class TripleStoreService:
    """
    RDF triple store service with SPARQL query capabilities.

    Constitutional requirements:
    - 30-second timeout for complex queries
    - <200ms for simple queries
    - W3C SPARQL JSON format compliance
    """

    def __init__(self, store_type: str = "memory"):
        """Initialize triple store service."""
        self.graph = Graph()
        self.store_type = store_type

        # Define common namespaces
        self.KG = Namespace("http://knowledge-graph.org/ontology/")
        self.RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        self.RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
        self.PROV = Namespace("http://www.w3.org/ns/prov#")

        # Bind namespaces
        self.graph.bind("kg", self.KG)
        self.graph.bind("rdf", self.RDF)
        self.graph.bind("rdfs", self.RDFS)
        self.graph.bind("prov", self.PROV)

        logger.info(f"Initialized TripleStoreService with {store_type} store")

    async def execute_sparql_query(
        self,
        query: str,
        timeout: int = 30,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute SPARQL query with constitutional timeout compliance.

        Args:
            query: SPARQL query string
            timeout: Query timeout in seconds (max 30 per constitution)
            limit: Optional result limit

        Returns:
            W3C SPARQL JSON format result

        Raises:
            TimeoutError: If query exceeds timeout
            ValueError: If query is malformed
        """
        # Constitutional compliance: Enforce 30-second maximum timeout
        if timeout > 30:
            timeout = 30
            logger.warning("Query timeout capped at 30 seconds (constitutional requirement)")

        start_time = datetime.utcnow()

        try:
            # Validate and prepare query
            if not query.strip():
                raise ValueError("Query cannot be empty")

            # Add LIMIT if specified and not already present
            if limit and "LIMIT" not in query.upper():
                query = f"{query.rstrip()} LIMIT {limit}"

            # Parse and prepare the query
            prepared_query = prepareQuery(query)

            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_query_sync(prepared_query),
                timeout=timeout
            )

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Convert to W3C SPARQL JSON format
            sparql_result = self._format_sparql_result(result, execution_time)

            # Log performance for constitutional compliance monitoring
            if execution_time > 0.2:
                logger.info(f"Query execution time: {execution_time:.3f}s")
            if execution_time > 30:
                logger.error(f"Query exceeded constitutional timeout: {execution_time:.3f}s")

            return sparql_result

        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Query timed out after {execution_time:.3f}s")
            return {
                "error": f"Query timed out after {timeout} seconds",
                "execution_time": execution_time,
                "status": "timeout"
            }

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Query failed after {execution_time:.3f}s: {str(e)}")
            return {
                "error": f"Query execution failed: {str(e)}",
                "execution_time": execution_time,
                "status": "error"
            }

    async def _execute_query_sync(self, prepared_query) -> Result:
        """Execute the prepared query synchronously."""
        return self.graph.query(prepared_query)

    def _format_sparql_result(self, result: Result, execution_time: float) -> Dict[str, Any]:
        """
        Format query result to W3C SPARQL JSON format.

        Constitutional compliance: W3C SPARQL JSON format required.
        """
        if result.type == 'SELECT':
            # Extract variable names
            vars_list = [str(var) for var in result.vars] if result.vars else []

            # Convert bindings
            bindings = []
            for row in result:
                binding = {}
                for i, var in enumerate(vars_list):
                    if i < len(row) and row[i] is not None:
                        value = row[i]
                        if isinstance(value, URIRef):
                            binding[var] = {
                                "type": "uri",
                                "value": str(value)
                            }
                        elif isinstance(value, Literal):
                            binding[var] = {
                                "type": "literal",
                                "value": str(value)
                            }
                            if value.datatype:
                                binding[var]["datatype"] = str(value.datatype)
                            if value.language:
                                binding[var]["xml:lang"] = str(value.language)
                        else:
                            binding[var] = {
                                "type": "literal",
                                "value": str(value)
                            }
                bindings.append(binding)

            return {
                "head": {"vars": vars_list},
                "results": {"bindings": bindings},
                "execution_time": execution_time,
                "count": len(bindings)
            }

        elif result.type == 'ASK':
            return {
                "head": {},
                "boolean": bool(result),
                "execution_time": execution_time
            }

        else:  # CONSTRUCT, DESCRIBE
            # Convert graph result to JSON-LD
            graph_data = result.graph.serialize(format='json-ld')
            return {
                "results": json.loads(graph_data) if isinstance(graph_data, str) else graph_data,
                "execution_time": execution_time
            }

    async def add_dataset_triples(self, dataset_dict: Dict[str, Any]) -> bool:
        """Add dataset triples to the knowledge graph."""
        try:
            dataset_id = dataset_dict.get("@id", f"kg:dataset/{dataset_dict.get('dataset_id')}")

            # Add main dataset triples
            dataset_uri = URIRef(dataset_id)
            self.graph.add((dataset_uri, self.RDF.type, self.KG.Dataset))

            if dataset_dict.get("kg:title"):
                self.graph.add((dataset_uri, self.KG.title, Literal(dataset_dict["kg:title"])))

            if dataset_dict.get("kg:description"):
                self.graph.add((dataset_uri, self.KG.description, Literal(dataset_dict["kg:description"])))

            # Add NWB file relationships
            if dataset_dict.get("kg:hasNwbFiles"):
                for nwb_file in dataset_dict["kg:hasNwbFiles"]:
                    self.graph.add((dataset_uri, self.KG.hasNwbFile, Literal(nwb_file)))

            # Add lab relationship
            if dataset_dict.get("kg:belongsToLab"):
                lab_uri = URIRef(dataset_dict["kg:belongsToLab"])
                self.graph.add((dataset_uri, self.KG.belongsToLab, lab_uri))

            # Add provenance information
            activity_uri = URIRef(f"kg:activity/dataset_creation_{dataset_dict.get('dataset_id')}")
            self.graph.add((activity_uri, self.RDF.type, self.PROV.Activity))
            self.graph.add((dataset_uri, self.PROV.wasGeneratedBy, activity_uri))

            if dataset_dict.get("kg:createdAt"):
                self.graph.add((activity_uri, self.PROV.startedAtTime, Literal(dataset_dict["kg:createdAt"])))

            logger.info(f"Added dataset triples for {dataset_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add dataset triples: {str(e)}")
            return False

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        try:
            total_triples = len(self.graph)

            # Count entities by type
            type_counts = {}
            for rdf_type in [self.KG.Dataset, self.KG.Session, self.KG.Subject, self.KG.Device]:
                count_query = f"""
                SELECT (COUNT(?entity) as ?count) WHERE {{
                    ?entity rdf:type <{rdf_type}> .
                }}
                """
                result = await self.execute_sparql_query(count_query)
                if result.get("results", {}).get("bindings"):
                    count = result["results"]["bindings"][0].get("count", {}).get("value", "0")
                    type_counts[str(rdf_type).split("/")[-1]] = int(count)

            return {
                "total_triples": total_triples,
                "entity_counts": type_counts,
                "namespaces": dict(self.graph.namespaces()),
                "store_type": self.store_type
            }

        except Exception as e:
            logger.error(f"Failed to get graph statistics: {str(e)}")
            return {"error": str(e)}

    def get_sample_queries(self) -> Dict[str, str]:
        """Get sample SPARQL queries for testing."""
        return {
            "list_datasets": """
                SELECT ?dataset ?title WHERE {
                    ?dataset rdf:type kg:Dataset .
                    ?dataset kg:title ?title .
                } LIMIT 10
            """,
            "count_entities": """
                SELECT ?type (COUNT(?entity) as ?count) WHERE {
                    ?entity rdf:type ?type .
                    FILTER(STRSTARTS(STR(?type), "http://knowledge-graph.org/ontology/"))
                } GROUP BY ?type
            """,
            "dataset_with_subjects": """
                SELECT ?dataset ?subject ?species WHERE {
                    ?dataset rdf:type kg:Dataset .
                    ?dataset kg:hasSession ?session .
                    ?session kg:hasSubject ?subject .
                    ?subject kg:hasSpecies ?species .
                } LIMIT 10
            """
        }