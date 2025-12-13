#!/usr/bin/env python3
"""
Analyze Neo4j Knowledge Graph state with comprehensive metrics and insights.

Usage Examples:
    # Basic analysis (all subjects)
    python analyze_kg_state.py

    # Analyze specific subject
    python analyze_kg_state.py --subject mouse001

    # Get JSON output for automation
    python analyze_kg_state.py --format json --output kg_state.json

    # Summary statistics only
    python analyze_kg_state.py --summary-only

    # Markdown report for documentation
    python analyze_kg_state.py --format markdown --output report.md

    # Include data quality metrics
    python analyze_kg_state.py --include-quality --include-ontology
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection


class KGAnalyzer:
    """Comprehensive Knowledge Graph state analyzer."""

    def __init__(self, args):
        """Initialize analyzer with command-line arguments."""
        self.args = args
        self.conn = None
        self.data: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "subjects": {},
            "inference": {},
            "quality": {},
            "ontology": {},
            "timings": {},
        }

    async def connect(self):
        """Connect to Neo4j database."""
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            print("ERROR: NEO4J_PASSWORD environment variable not set")
            print("Usage: NEO4J_PASSWORD=your-password python analyze_kg_state.py")
            sys.exit(1)

        self.conn = get_neo4j_connection(uri=self.args.uri, user=self.args.user, password=neo4j_password)
        await self.conn.connect()

    async def close(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()

    async def check_health(self) -> tuple[bool, str]:
        """Verify database connectivity and basic health."""
        try:
            # Test query
            result = await self.conn.execute_read("RETURN 1 as health", {})
            if not result:
                return False, "Database query returned no results"

            # Check total node count
            result = await self.conn.execute_read("MATCH (n) RETURN count(n) as total", {})
            total = result[0]["total"] if result else 0

            if total == 0:
                return False, "Database is empty (0 nodes)"

            return True, f"Database healthy ({total:,} nodes)"

        except Exception as e:
            return False, f"Database error: {str(e)}"

    async def get_summary_stats(self) -> dict[str, Any]:
        """Get overall KG statistics."""
        start_time = time.time()
        stats: dict[str, Any] = {}

        # Node counts by label
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(*) as count
        ORDER BY count DESC
        """
        results = await self.conn.execute_read(query, {})
        stats["nodes"] = {r["label"]: r["count"] for r in results}
        stats["total_nodes"] = sum(stats["nodes"].values())

        # Relationship counts
        query = """
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        """
        results = await self.conn.execute_read(query, {})
        stats["relationships"] = {r["rel_type"]: r["count"] for r in results}
        stats["total_relationships"] = sum(stats["relationships"].values())

        # Active subjects (excluding 'unknown')
        query = """
        MATCH (obs:Observation)
        WHERE obs.subject_id <> 'unknown'
        RETURN count(DISTINCT obs.subject_id) as subject_count
        """
        result = await self.conn.execute_read(query, {})
        stats["active_subjects"] = result[0]["subject_count"] if result else 0

        # Recent activity (last 24 hours)
        query = """
        MATCH (obs:Observation)
        WHERE obs.created_at >= datetime() - duration('P1D')
        RETURN count(*) as recent_count
        """
        result = await self.conn.execute_read(query, {})
        stats["recent_observations_24h"] = result[0]["recent_count"] if result else 0

        # Field diversity
        query = """
        MATCH (obs:Observation)
        RETURN count(DISTINCT obs.field_path) as field_count
        """
        result = await self.conn.execute_read(query, {})
        stats["unique_fields_tracked"] = result[0]["field_count"] if result else 0

        self.data["timings"]["summary_stats"] = time.time() - start_time
        return stats

    async def analyze_subjects(self, subject_id: str | None = None) -> dict[str, Any]:
        """Analyze observations by subject."""
        start_time = time.time()
        subjects = {}

        # Query for specific subject or all subjects
        where_clause = "WHERE obs.subject_id = $subject_id" if subject_id else ""
        params = {"subject_id": subject_id} if subject_id else {}

        query = f"""
        MATCH (obs:Observation)
        {where_clause}
        RETURN obs.subject_id AS subject_id,
               count(*) AS observation_count,
               collect(DISTINCT obs.field_path) AS fields,
               collect(DISTINCT obs.source_file) AS files,
               count(DISTINCT obs.source_file) AS file_count
        ORDER BY observation_count DESC
        """

        results = await self.conn.execute_read(query, params)

        for r in results:
            subject = {
                "observation_count": r["observation_count"],
                "fields_tracked": r["fields"],
                "field_count": len(r["fields"]),
                "source_files": [f.split("/")[-1] for f in r["files"]],  # Extract filenames
                "file_count": r["file_count"],
            }
            subjects[r["subject_id"]] = subject

        self.data["timings"]["analyze_subjects"] = time.time() - start_time
        return subjects

    async def analyze_subject_details(self, subject_id: str) -> dict[str, Any]:
        """Get detailed observations for a specific subject."""
        start_time = time.time()

        query = """
        MATCH (obs:Observation)
        WHERE obs.subject_id = $subject_id
        RETURN obs.observation_id AS id,
               obs.field_path AS field_path,
               obs.raw_value AS raw_value,
               obs.normalized_value AS normalized_value,
               obs.source_file AS source_file,
               obs.confidence AS confidence,
               obs.is_active AS is_active,
               obs.created_at AS created_at
        ORDER BY obs.field_path, obs.created_at
        """

        results = await self.conn.execute_read(query, {"subject_id": subject_id})

        # Group by field
        fields = defaultdict(list)
        for obs in results:
            fields[obs["field_path"]].append(
                {
                    "id": obs["id"],
                    "raw_value": obs["raw_value"],
                    "normalized_value": obs["normalized_value"],
                    "source_file": obs["source_file"].split("/")[-1],
                    "confidence": obs["confidence"],
                    "is_active": obs["is_active"],
                    "created_at": obs["created_at"],
                }
            )

        self.data["timings"]["subject_details"] = time.time() - start_time
        return dict(fields)

    async def analyze_inference_readiness(self, subject_id: str | None = None) -> dict[str, Any]:
        """Analyze which fields are ready for inference."""
        start_time = time.time()

        where_clause = "AND obs.subject_id = $subject_id" if subject_id else ""
        params = {"subject_id": subject_id} if subject_id else {}

        query = f"""
        MATCH (obs:Observation)
        WHERE obs.is_active = true {where_clause}
        WITH obs.subject_id as subject_id,
             obs.field_path AS field_path,
             count(DISTINCT obs.source_file) AS file_count,
             count(*) AS observation_count,
             collect(DISTINCT obs.normalized_value) AS unique_values
        RETURN subject_id,
               field_path,
               file_count,
               observation_count,
               unique_values,
               size(unique_values) AS value_diversity,
               CASE
                 WHEN file_count >= 2 AND size(unique_values) = 1
                   THEN 'ready'
                 WHEN file_count >= 2 AND size(unique_values) > 1
                   THEN 'conflicting'
                 WHEN file_count < 2
                   THEN 'insufficient'
                 ELSE 'unknown'
               END AS status
        ORDER BY subject_id, field_path
        """

        results = await self.conn.execute_read(query, params)

        # Group by subject
        inference: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: {"ready": [], "conflicting": [], "insufficient": []}
        )

        for r in results:
            sid = r["subject_id"]
            field_info = {
                "field_path": r["field_path"],
                "file_count": r["file_count"],
                "observation_count": r["observation_count"],
                "unique_values": r["unique_values"],
                "value_diversity": r["value_diversity"],
            }

            status = r["status"]
            if status in ["ready", "conflicting", "insufficient"]:
                inference[sid][status].append(field_info)

        self.data["timings"]["inference_readiness"] = time.time() - start_time
        return dict(inference)

    async def analyze_data_quality(self) -> dict[str, Any]:
        """Analyze data quality metrics."""
        start_time = time.time()
        quality = {}

        # Low confidence observations
        query = """
        MATCH (obs:Observation)
        WHERE obs.confidence < 0.8
        RETURN count(*) as low_confidence_count,
               avg(obs.confidence) as avg_confidence
        """
        result = await self.conn.execute_read(query, {})
        quality["low_confidence"] = result[0] if result else {"low_confidence_count": 0, "avg_confidence": 0}

        # Confidence distribution
        query = """
        MATCH (obs:Observation)
        WITH CASE
          WHEN obs.confidence >= 0.95 THEN 'very_high'
          WHEN obs.confidence >= 0.90 THEN 'high'
          WHEN obs.confidence >= 0.80 THEN 'medium'
          ELSE 'low'
        END as conf_range, COUNT(*) as count
        RETURN conf_range, count
        ORDER BY count DESC
        """
        results = await self.conn.execute_read(query, {})
        quality["confidence_distribution"] = {r["conf_range"]: r["count"] for r in results}

        # Unknown subjects
        query = """
        MATCH (obs:Observation)
        WHERE obs.subject_id = 'unknown'
        RETURN count(*) as unknown_subject_count
        """
        result = await self.conn.execute_read(query, {})
        quality["unknown_subjects"] = result[0]["unknown_subject_count"] if result else 0

        # Inactive observations
        query = """
        MATCH (obs:Observation)
        WHERE obs.is_active = false
        RETURN count(*) as inactive_count
        """
        result = await self.conn.execute_read(query, {})
        quality["inactive_observations"] = result[0]["inactive_count"] if result else 0

        # Active vs inactive ratio
        total_obs = self.data["summary"].get("nodes", {}).get("Observation", 0)
        if total_obs > 0:
            active_count = total_obs - quality["inactive_observations"]
            quality["active_ratio"] = round(active_count / total_obs, 2)
        else:
            quality["active_ratio"] = 0

        self.data["timings"]["data_quality"] = time.time() - start_time
        return quality

    async def analyze_ontology_coverage(self) -> dict[str, Any]:
        """Analyze ontology term usage and coverage."""
        start_time = time.time()
        ontology: dict[str, Any] = {}

        # Terms by ontology
        query = """
        MATCH (term:OntologyTerm)
        RETURN term.ontology_name as ontology,
               count(*) as term_count
        ORDER BY term_count DESC
        """
        results = await self.conn.execute_read(query, {})
        ontology["terms_by_ontology"] = {r["ontology"]: r["term_count"] for r in results}

        # Ontology usage in normalizations
        query = """
        MATCH (obs:Observation)-[:NORMALIZED_TO]->(term:OntologyTerm)
        RETURN term.ontology_name as ontology,
               count(DISTINCT obs.field_path) as fields_using,
               count(*) as total_normalizations
        ORDER BY total_normalizations DESC
        """
        results = await self.conn.execute_read(query, {})
        ontology["usage"] = {
            r["ontology"]: {"fields_using": r["fields_using"], "normalizations": r["total_normalizations"]}
            for r in results
        }

        # Most normalized terms
        query = """
        MATCH (obs:Observation)-[:NORMALIZED_TO]->(term:OntologyTerm)
        RETURN term.term_id as term_id,
               term.label as label,
               term.ontology_name as ontology,
               count(*) as normalization_count
        ORDER BY normalization_count DESC
        LIMIT 10
        """
        results = await self.conn.execute_read(query, {})
        ontology["top_terms"] = [
            {
                "term_id": r["term_id"],
                "label": r["label"],
                "ontology": r["ontology"],
                "count": r["normalization_count"],
            }
            for r in results
        ]

        self.data["timings"]["ontology_coverage"] = time.time() - start_time
        return ontology

    async def run_analysis(self) -> bool:
        """Run complete analysis."""
        try:
            # Connect to database
            await self.connect()

            # Health check
            healthy, message = await self.check_health()
            if not healthy:
                print(f"❌ {message}")
                return False

            if not self.args.quiet:
                print(f"✅ {message}\n")

            # Summary statistics (always run)
            self.data["summary"] = await self.get_summary_stats()

            # If summary-only, stop here
            if self.args.summary_only:
                return True

            # Subject analysis
            if self.args.subject:
                # Specific subject
                subjects = await self.analyze_subjects(self.args.subject)
                if self.args.subject in subjects:
                    self.data["subjects"][self.args.subject] = subjects[self.args.subject]
                    # Get detailed observations
                    self.data["subjects"][self.args.subject]["details"] = await self.analyze_subject_details(
                        self.args.subject
                    )
                else:
                    print(f"⚠️  Subject '{self.args.subject}' not found")
            else:
                # All subjects
                self.data["subjects"] = await self.analyze_subjects()

            # Inference readiness
            self.data["inference"] = await self.analyze_inference_readiness(self.args.subject)

            # Optional analyses
            if self.args.include_quality:
                self.data["quality"] = await self.analyze_data_quality()

            if self.args.include_ontology:
                self.data["ontology"] = await self.analyze_ontology_coverage()

            return True

        except Exception as e:
            print(f"ERROR: {e}")
            if self.args.verbose:
                import traceback

                traceback.print_exc()
            return False

        finally:
            await self.close()

    def output_text(self):
        """Output results in text format."""
        print("=" * 80)
        print("KNOWLEDGE GRAPH STATE ANALYSIS")
        print("=" * 80)
        print(f"Timestamp: {self.data['timestamp']}")
        print()

        # Summary
        print("📊 SUMMARY STATISTICS")
        print("-" * 80)
        summary = self.data["summary"]
        print(f"Total Nodes: {summary.get('total_nodes', 0):,}")
        print(f"Total Relationships: {summary.get('total_relationships', 0):,}")
        print(f"Active Subjects: {summary.get('active_subjects', 0)}")
        print(f"Unique Fields Tracked: {summary.get('unique_fields_tracked', 0)}")
        print(f"Recent Observations (24h): {summary.get('recent_observations_24h', 0)}")

        print("\nNode Distribution:")
        for label, count in summary.get("nodes", {}).items():
            print(f"  • {label}: {count:,}")

        print("\nRelationship Distribution:")
        for rel_type, count in summary.get("relationships", {}).items():
            print(f"  • {rel_type}: {count:,}")

        if self.args.summary_only:
            print("\n" + "=" * 80)
            return

        # Subjects
        print("\n" + "=" * 80)
        print("👥 SUBJECTS")
        print("-" * 80)
        for subject_id, subject_data in self.data["subjects"].items():
            print(f"\nSubject: {subject_id}")
            print(f"  Observations: {subject_data['observation_count']:,}")
            print(f"  Fields tracked: {subject_data['field_count']}")
            print(f"  Source files: {subject_data['file_count']}")

            if "details" in subject_data:
                print("\n  Field Details:")
                for field_path, observations in subject_data["details"].items():
                    print(f"\n    {field_path}:")
                    for obs in observations[:3]:  # Show first 3
                        print(f"      • {obs['normalized_value']}")
                        print(f"        Source: {obs['source_file']}")
                        print(f"        Confidence: {obs['confidence']:.2f}")
                    if len(observations) > 3:
                        print(f"      ... and {len(observations) - 3} more")

        # Inference readiness
        print("\n" + "=" * 80)
        print("🔮 INFERENCE READINESS")
        print("-" * 80)
        for subject_id, inference_data in self.data["inference"].items():
            print(f"\nSubject: {subject_id}")

            ready = inference_data.get("ready", [])
            if ready:
                print(f"\n  ✅ Ready ({len(ready)} fields):")
                for field in ready:
                    print(f"    • {field['field_path']}: '{field['unique_values'][0]}'")
                    print(f"      Evidence: {field['file_count']} files, {field['observation_count']} observations")

            conflicting = inference_data.get("conflicting", [])
            if conflicting:
                print(f"\n  ⚠️  Conflicting ({len(conflicting)} fields):")
                for field in conflicting:
                    print(f"    • {field['field_path']}: {field['value_diversity']} different values")
                    print(f"      Values: {', '.join(field['unique_values'][:3])}")

            insufficient = inference_data.get("insufficient", [])
            if insufficient:
                print(f"\n  ❌ Insufficient ({len(insufficient)} fields):")
                for field in insufficient:
                    print(f"    • {field['field_path']}: only {field['file_count']} file(s)")

        # Quality metrics
        if self.data.get("quality"):
            print("\n" + "=" * 80)
            print("📈 DATA QUALITY")
            print("-" * 80)
            quality = self.data["quality"]

            print("\nConfidence Distribution:")
            for conf_range, count in quality.get("confidence_distribution", {}).items():
                print(f"  • {conf_range}: {count:,}")

            print("\nQuality Metrics:")
            print(f"  • Active ratio: {quality.get('active_ratio', 0):.1%}")
            print(f"  • Unknown subjects: {quality.get('unknown_subjects', 0):,}")
            print(f"  • Inactive observations: {quality.get('inactive_observations', 0):,}")

            low_conf = quality.get("low_confidence", {})
            if low_conf.get("low_confidence_count", 0) > 0:
                print(f"  • Low confidence (<0.8): {low_conf['low_confidence_count']:,}")
                print(f"    Avg confidence: {low_conf.get('avg_confidence', 0):.2f}")

        # Ontology coverage
        if self.data.get("ontology"):
            print("\n" + "=" * 80)
            print("🔬 ONTOLOGY COVERAGE")
            print("-" * 80)
            ontology = self.data["ontology"]

            print("\nTerms by Ontology:")
            for ont, count in ontology.get("terms_by_ontology", {}).items():
                usage = ontology.get("usage", {}).get(ont, {})
                normalizations = usage.get("normalizations", 0)
                fields = usage.get("fields_using", 0)
                print(f"  • {ont}: {count} terms ({normalizations:,} normalizations, {fields} fields)")

            top_terms = ontology.get("top_terms", [])
            if top_terms:
                print("\nMost Normalized Terms:")
                for term in top_terms[:5]:
                    print(f"  • {term['label']} ({term['term_id']}): {term['count']:,} uses")

        # Timing
        if self.args.verbose and self.data.get("timings"):
            print("\n" + "=" * 80)
            print("⏱️  PERFORMANCE METRICS")
            print("-" * 80)
            total_time = sum(self.data["timings"].values())
            for section, duration in self.data["timings"].items():
                print(f"  • {section}: {duration:.2f}s ({duration / total_time * 100:.1f}%)")
            print(f"\nTotal analysis time: {total_time:.2f}s")

        print("\n" + "=" * 80)

    def output_json(self):
        """Output results in JSON format."""
        print(json.dumps(self.data, indent=2, default=str))

    def output_markdown(self):
        """Output results in Markdown format."""
        md = []
        md.append("# Knowledge Graph State Analysis")
        md.append("")
        md.append(f"**Generated**: {self.data['timestamp']}")
        md.append("")

        # Summary
        md.append("## Summary Statistics")
        md.append("")
        summary = self.data["summary"]
        md.append("| Metric | Value |")
        md.append("|--------|-------|")
        md.append(f"| Total Nodes | {summary.get('total_nodes', 0):,} |")
        md.append(f"| Total Relationships | {summary.get('total_relationships', 0):,} |")
        md.append(f"| Active Subjects | {summary.get('active_subjects', 0)} |")
        md.append(f"| Unique Fields | {summary.get('unique_fields_tracked', 0)} |")
        md.append(f"| Recent Activity (24h) | {summary.get('recent_observations_24h', 0)} |")
        md.append("")

        # Node distribution
        md.append("### Node Distribution")
        md.append("")
        for label, count in summary.get("nodes", {}).items():
            md.append(f"- **{label}**: {count:,}")
        md.append("")

        # Subjects
        if self.data.get("subjects") and not self.args.summary_only:
            md.append("## Subjects")
            md.append("")
            for subject_id, subject_data in list(self.data["subjects"].items())[:10]:  # Limit for markdown
                md.append(f"### {subject_id}")
                md.append("")
                md.append(f"- Observations: {subject_data['observation_count']:,}")
                md.append(f"- Fields: {subject_data['field_count']}")
                md.append(f"- Files: {subject_data['file_count']}")
                md.append("")

        # Inference
        if self.data.get("inference") and not self.args.summary_only:
            md.append("## Inference Readiness")
            md.append("")
            for subject_id, inference_data in list(self.data["inference"].items())[:5]:
                ready_count = len(inference_data.get("ready", []))
                conflict_count = len(inference_data.get("conflicting", []))
                insufficient_count = len(inference_data.get("insufficient", []))

                md.append(f"### {subject_id}")
                md.append("")
                md.append(f"- ✅ Ready: {ready_count} fields")
                md.append(f"- ⚠️ Conflicting: {conflict_count} fields")
                md.append(f"- ❌ Insufficient: {insufficient_count} fields")
                md.append("")

        print("\n".join(md))

    def output(self):
        """Output results in requested format."""
        if self.args.output:
            # Write output to file using context manager
            with open(self.args.output, "w") as f:
                original_stdout = sys.stdout
                sys.stdout = f
                try:
                    if self.args.format == "json":
                        self.output_json()
                    elif self.args.format == "markdown":
                        self.output_markdown()
                    else:
                        self.output_text()
                finally:
                    sys.stdout = original_stdout
            print(f"✅ Output saved to: {self.args.output}")
        else:
            if self.args.format == "json":
                self.output_json()
            elif self.args.format == "markdown":
                self.output_markdown()
            else:
                self.output_text()


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze Neo4j Knowledge Graph state",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  python analyze_kg_state.py

  # Analyze specific subject
  python analyze_kg_state.py --subject mouse001

  # Get JSON output
  python analyze_kg_state.py --format json --output state.json

  # Summary only with quality metrics
  python analyze_kg_state.py --summary-only --include-quality

  # Full analysis with all metrics
  python analyze_kg_state.py --include-quality --include-ontology --verbose
        """,
    )

    parser.add_argument("--subject", help="Analyze specific subject ID (default: all subjects)")

    parser.add_argument(
        "--format", choices=["text", "json", "markdown"], default="text", help="Output format (default: text)"
    )

    parser.add_argument("--output", help="Output file path (default: stdout)")

    parser.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j URI (default: bolt://localhost:7687)")

    parser.add_argument("--user", default="neo4j", help="Neo4j username (default: neo4j)")

    parser.add_argument("--summary-only", action="store_true", help="Show only summary statistics")

    parser.add_argument("--include-quality", action="store_true", help="Include data quality analysis")

    parser.add_argument("--include-ontology", action="store_true", help="Include ontology coverage analysis")

    parser.add_argument("--verbose", action="store_true", help="Show detailed timing and debug information")

    parser.add_argument("--quiet", action="store_true", help="Suppress status messages")

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    analyzer = KGAnalyzer(args)

    success = await analyzer.run_analysis()

    if success:
        analyzer.output()
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
