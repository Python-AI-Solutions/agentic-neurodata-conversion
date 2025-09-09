# Evaluation and Reporting Design

## Overview

This design document outlines evaluation and reporting systems that generate comprehensive assessments, interactive visualizations, and human-readable summaries of conversion results.

## Architecture

### High-Level Evaluation Architecture

```
Evaluation and Reporting Systems
├── Quality Assessment Engine
├── Report Generation System  
├── Visualization Framework
├── Collaborative Review System
└── Integration and API Layer
```

## Core Components

### 1. Quality Assessment Engine

The quality assessment engine evaluates conversions from multiple perspectives.

### 2. Report Generation System

Generates comprehensive reports in multiple formats.

### 3. Visualization Framework

Creates interactive visualizations for data exploration.

### 4. Collaborative Review System

Supports expert review and validation workflows.

### 5. Integration Layer

Provides APIs and integration with external systems.

## Detailed Component Design

### 1. Quality Assessment Engine

#### Technical Quality Evaluator
```python
# agentic_neurodata_conversion/evaluation/quality_assessment.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

class QualityDimension(Enum):
    """Quality assessment dimensions."""
    TECHNICAL = "technical"
    SCIENTIFIC = "scientific"
    USABILITY = "usability"

@dataclass
class QualityMetric:
    """Individual quality metric."""
    name: str
    value: float
    max_value: float
    description: str
    dimension: QualityDimension
    weight: float = 1.0
    
    @property
    def normalized_score(self) -> float:
        """Get normalized score (0-1)."""
        return self.value / self.max_value if self.max_value > 0 else 0.0

@dataclass
class QualityAssessment:
    """Complete quality assessment results."""
    overall_score: float
    dimension_scores: Dict[QualityDimension, float]
    metrics: List[QualityMetric]
    recommendations: List[str]
    strengths: List[str]
    weaknesses: List[str]

class TechnicalQualityEvaluator:
    """Evaluates technical quality aspects."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def evaluate(self, nwb_path: str, validation_results: Dict[str, Any]) -> List[QualityMetric]:
        """Evaluate technical quality metrics."""
        metrics = []
        
        # Schema compliance
        schema_score = self._evaluate_schema_compliance(validation_results)
        metrics.append(QualityMetric(
            name="schema_compliance",
            value=schema_score,
            max_value=1.0,
            description="Compliance with NWB schema requirements",
            dimension=QualityDimension.TECHNICAL
        ))
        
        # Data integrity
        integrity_score = self._evaluate_data_integrity(nwb_path)
        metrics.append(QualityMetric(
            name="data_integrity",
            value=integrity_score,
            max_value=1.0,
            description="Data consistency and integrity",
            dimension=QualityDimension.TECHNICAL
        ))
        
        # File structure quality
        structure_score = self._evaluate_file_structure(nwb_path)
        metrics.append(QualityMetric(
            name="file_structure",
            value=structure_score,
            max_value=1.0,
            description="Quality of file organization and structure",
            dimension=QualityDimension.TECHNICAL
        ))
        
        return metrics
    
    def _evaluate_schema_compliance(self, validation_results: Dict[str, Any]) -> float:
        """Evaluate schema compliance score."""
        nwb_inspector_results = validation_results.get('nwb_inspector', {})
        issues = nwb_inspector_results.get('issues', [])
        
        if not issues:
            return 1.0
        
        # Weight issues by severity
        critical_issues = len([i for i in issues if i.get('severity') == 'critical'])
        warning_issues = len([i for i in issues if i.get('severity') == 'warning'])
        
        # Calculate score based on issue severity
        penalty = (critical_issues * 0.2) + (warning_issues * 0.05)
        return max(0.0, 1.0 - penalty)
    
    def _evaluate_data_integrity(self, nwb_path: str) -> float:
        """Evaluate data integrity score."""
        try:
            import pynwb
            with pynwb.NWBHDF5IO(nwb_path, 'r') as io:
                nwbfile = io.read()
                
                # Check for empty datasets
                empty_datasets = 0
                total_datasets = 0
                
                for obj in nwbfile.objects.values():
                    if hasattr(obj, 'data') and obj.data is not None:
                        total_datasets += 1
                        if hasattr(obj.data, 'shape') and 0 in obj.data.shape:
                            empty_datasets += 1
                
                if total_datasets == 0:
                    return 0.5  # No data is concerning but not necessarily wrong
                
                return 1.0 - (empty_datasets / total_datasets)
                
        except Exception as e:
            self.logger.error(f"Error evaluating data integrity: {e}")
            return 0.0
    
    def _evaluate_file_structure(self, nwb_path: str) -> float:
        """Evaluate file structure quality."""
        try:
            import pynwb
            with pynwb.NWBHDF5IO(nwb_path, 'r') as io:
                nwbfile = io.read()
                
                score = 0.0
                
                # Check for proper organization
                if nwbfile.acquisition:
                    score += 0.3
                if nwbfile.processing:
                    score += 0.3
                if nwbfile.analysis:
                    score += 0.2
                if nwbfile.stimulus:
                    score += 0.2
                
                return min(1.0, score)
                
        except Exception as e:
            self.logger.error(f"Error evaluating file structure: {e}")
            return 0.0

class ScientificQualityEvaluator:
    """Evaluates scientific quality aspects."""
    
    def evaluate(self, nwb_path: str, metadata: Dict[str, Any]) -> List[QualityMetric]:
        """Evaluate scientific quality metrics."""
        metrics = []
        
        # Experimental completeness
        completeness_score = self._evaluate_experimental_completeness(metadata)
        metrics.append(QualityMetric(
            name="experimental_completeness",
            value=completeness_score,
            max_value=1.0,
            description="Completeness of experimental metadata",
            dimension=QualityDimension.SCIENTIFIC
        ))
        
        # Scientific validity
        validity_score = self._evaluate_scientific_validity(metadata)
        metrics.append(QualityMetric(
            name="scientific_validity",
            value=validity_score,
            max_value=1.0,
            description="Scientific validity of experimental design",
            dimension=QualityDimension.SCIENTIFIC
        ))
        
        return metrics
    
    def _evaluate_experimental_completeness(self, metadata: Dict[str, Any]) -> float:
        """Evaluate experimental completeness."""
        required_fields = [
            'experimenter', 'lab', 'institution', 'session_description',
            'identifier', 'session_start_time'
        ]
        
        present_fields = sum(1 for field in required_fields if metadata.get(field))
        return present_fields / len(required_fields)
    
    def _evaluate_scientific_validity(self, metadata: Dict[str, Any]) -> float:
        """Evaluate scientific validity."""
        # This would implement domain-specific validation logic
        # For now, return a placeholder score
        return 0.8

class UsabilityQualityEvaluator:
    """Evaluates usability quality aspects."""
    
    def evaluate(self, nwb_path: str, metadata: Dict[str, Any]) -> List[QualityMetric]:
        """Evaluate usability quality metrics."""
        metrics = []
        
        # Documentation quality
        doc_score = self._evaluate_documentation_quality(metadata)
        metrics.append(QualityMetric(
            name="documentation_quality",
            value=doc_score,
            max_value=1.0,
            description="Quality and completeness of documentation",
            dimension=QualityDimension.USABILITY
        ))
        
        # Discoverability
        discover_score = self._evaluate_discoverability(metadata)
        metrics.append(QualityMetric(
            name="discoverability",
            value=discover_score,
            max_value=1.0,
            description="How easily the data can be discovered and understood",
            dimension=QualityDimension.USABILITY
        ))
        
        return metrics
    
    def _evaluate_documentation_quality(self, metadata: Dict[str, Any]) -> float:
        """Evaluate documentation quality."""
        description = metadata.get('session_description', '')
        if not description:
            return 0.0
        
        # Simple heuristic: longer descriptions are generally better
        if len(description) > 100:
            return 1.0
        elif len(description) > 50:
            return 0.7
        elif len(description) > 20:
            return 0.5
        else:
            return 0.2
    
    def _evaluate_discoverability(self, metadata: Dict[str, Any]) -> float:
        """Evaluate data discoverability."""
        discoverable_fields = ['keywords', 'related_publications', 'notes']
        present_fields = sum(1 for field in discoverable_fields if metadata.get(field))
        return present_fields / len(discoverable_fields)

class QualityAssessmentEngine:
    """Main quality assessment engine."""
    
    def __init__(self):
        self.technical_evaluator = TechnicalQualityEvaluator()
        self.scientific_evaluator = ScientificQualityEvaluator()
        self.usability_evaluator = UsabilityQualityEvaluator()
        self.logger = logging.getLogger(__name__)
    
    def assess_quality(self, nwb_path: str, validation_results: Dict[str, Any], 
                      metadata: Dict[str, Any]) -> QualityAssessment:
        """Perform comprehensive quality assessment."""
        
        all_metrics = []
        
        # Collect metrics from all evaluators
        all_metrics.extend(self.technical_evaluator.evaluate(nwb_path, validation_results))
        all_metrics.extend(self.scientific_evaluator.evaluate(nwb_path, metadata))
        all_metrics.extend(self.usability_evaluator.evaluate(nwb_path, metadata))
        
        # Calculate dimension scores
        dimension_scores = {}
        for dimension in QualityDimension:
            dimension_metrics = [m for m in all_metrics if m.dimension == dimension]
            if dimension_metrics:
                weighted_sum = sum(m.normalized_score * m.weight for m in dimension_metrics)
                total_weight = sum(m.weight for m in dimension_metrics)
                dimension_scores[dimension] = weighted_sum / total_weight
            else:
                dimension_scores[dimension] = 0.0
        
        # Calculate overall score
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_metrics, dimension_scores)
        strengths = self._identify_strengths(all_metrics)
        weaknesses = self._identify_weaknesses(all_metrics)
        
        return QualityAssessment(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            metrics=all_metrics,
            recommendations=recommendations,
            strengths=strengths,
            weaknesses=weaknesses
        )
    
    def _generate_recommendations(self, metrics: List[QualityMetric], 
                                dimension_scores: Dict[QualityDimension, float]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        # Identify low-scoring metrics
        low_metrics = [m for m in metrics if m.normalized_score < 0.7]
        
        for metric in low_metrics:
            if metric.name == "schema_compliance":
                recommendations.append("Address schema validation issues to improve compliance")
            elif metric.name == "experimental_completeness":
                recommendations.append("Add missing experimental metadata fields")
            elif metric.name == "documentation_quality":
                recommendations.append("Improve session description and documentation")
        
        # Dimension-specific recommendations
        if dimension_scores[QualityDimension.TECHNICAL] < 0.7:
            recommendations.append("Focus on technical quality improvements")
        if dimension_scores[QualityDimension.SCIENTIFIC] < 0.7:
            recommendations.append("Enhance scientific metadata completeness")
        if dimension_scores[QualityDimension.USABILITY] < 0.7:
            recommendations.append("Improve documentation and discoverability")
        
        return recommendations
    
    def _identify_strengths(self, metrics: List[QualityMetric]) -> List[str]:
        """Identify conversion strengths."""
        strengths = []
        high_metrics = [m for m in metrics if m.normalized_score >= 0.8]
        
        for metric in high_metrics:
            strengths.append(f"Excellent {metric.description.lower()}")
        
        return strengths
    
    def _identify_weaknesses(self, metrics: List[QualityMetric]) -> List[str]:
        """Identify conversion weaknesses."""
        weaknesses = []
        low_metrics = [m for m in metrics if m.normalized_score < 0.5]
        
        for metric in low_metrics:
            weaknesses.append(f"Poor {metric.description.lower()}")
        
        return weaknesses
```### 2. Re
port Generation System

#### Executive Summary Generator
```python
# agentic_neurodata_conversion/evaluation/report_generation.py
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime
from .quality_assessment import QualityAssessment, QualityDimension

class ExecutiveSummaryGenerator:
    """Generates executive summaries for non-technical audiences."""
    
    def generate_summary(self, quality_assessment: QualityAssessment, 
                        conversion_metadata: Dict[str, Any]) -> str:
        """Generate executive summary."""
        
        # Overall quality grade
        grade = self._score_to_grade(quality_assessment.overall_score)
        
        summary = f"""# Conversion Quality Summary

## Overall Assessment: {grade} ({quality_assessment.overall_score:.1%})

### Key Findings

**Strengths:**
{chr(10).join(f"• {strength}" for strength in quality_assessment.strengths)}

**Areas for Improvement:**
{chr(10).join(f"• {weakness}" for weakness in quality_assessment.weaknesses)}

### Quality Dimensions

"""
        
        for dimension, score in quality_assessment.dimension_scores.items():
            dimension_grade = self._score_to_grade(score)
            summary += f"- **{dimension.value.title()}**: {dimension_grade} ({score:.1%})\\n"
        
        summary += f"""
### Recommendations

{chr(10).join(f"• {rec}" for rec in quality_assessment.recommendations)}

### Dataset Information

- **Identifier**: {conversion_metadata.get('identifier', 'Not specified')}
- **Experimenter**: {conversion_metadata.get('experimenter', 'Not specified')}
- **Lab**: {conversion_metadata.get('lab', 'Not specified')}
- **Conversion Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This summary provides a high-level overview of the conversion quality. 
For detailed technical information, please refer to the full technical report.
"""
        
        return summary
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 0.9:
            return "A (Excellent)"
        elif score >= 0.8:
            return "B (Good)"
        elif score >= 0.7:
            return "C (Satisfactory)"
        elif score >= 0.6:
            return "D (Needs Improvement)"
        else:
            return "F (Poor)"

class TechnicalReportGenerator:
    """Generates detailed technical reports."""
    
    def generate_report(self, quality_assessment: QualityAssessment,
                       validation_results: Dict[str, Any],
                       conversion_metadata: Dict[str, Any],
                       provenance_data: Dict[str, Any]) -> str:
        """Generate comprehensive technical report."""
        
        report = f"""# Technical Conversion Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Quality Assessment Summary

### Overall Score: {quality_assessment.overall_score:.3f} ({quality_assessment.overall_score:.1%})

### Dimension Scores
"""
        
        for dimension, score in quality_assessment.dimension_scores.items():
            report += f"- **{dimension.value.title()}**: {score:.3f} ({score:.1%})\\n"
        
        report += """
### Detailed Metrics

| Metric | Score | Max | Normalized | Description |
|--------|-------|-----|------------|-------------|
"""
        
        for metric in quality_assessment.metrics:
            report += f"| {metric.name} | {metric.value:.3f} | {metric.max_value:.3f} | {metric.normalized_score:.3f} | {metric.description} |\\n"
        
        # Validation Results Section
        report += """
## Validation Results

### NWB Inspector Results
"""
        
        nwb_inspector = validation_results.get('nwb_inspector', {})
        if nwb_inspector.get('issues'):
            report += "#### Issues Found:\\n"
            for issue in nwb_inspector['issues']:
                severity = issue.get('severity', 'unknown')
                message = issue.get('message', 'No message')
                location = issue.get('location', 'Unknown location')
                report += f"- **{severity.upper()}**: {message} (Location: {location})\\n"
        else:
            report += "No issues found by NWB Inspector.\\n"
        
        # Provenance Section
        report += """
## Provenance Information

### Metadata Sources
"""
        
        if provenance_data:
            source_counts = {}
            for field, provenance_list in provenance_data.items():
                if provenance_list:
                    latest_provenance = provenance_list[-1]  # Most recent
                    source = latest_provenance.get('source', 'unknown')
                    source_counts[source] = source_counts.get(source, 0) + 1
            
            for source, count in source_counts.items():
                report += f"- **{source.replace('_', ' ').title()}**: {count} fields\\n"
        
        # Recommendations Section
        report += """
## Recommendations

### Priority Actions
"""
        
        for i, recommendation in enumerate(quality_assessment.recommendations, 1):
            report += f"{i}. {recommendation}\\n"
        
        report += """
## Technical Details

### File Information
"""
        
        report += f"- **NWB File**: {conversion_metadata.get('nwb_path', 'Not specified')}\\n"
        report += f"- **Original Dataset**: {conversion_metadata.get('dataset_path', 'Not specified')}\\n"
        report += f"- **Conversion Method**: Agentic Neurodata Converter\\n"
        
        return report

class ContextSummaryGenerator:
    """Generates human-readable context summaries."""
    
    def generate_context_summary(self, conversion_metadata: Dict[str, Any],
                                provenance_data: Dict[str, Any],
                                knowledge_graph_data: Dict[str, Any]) -> str:
        """Generate context summary explaining conversion decisions."""
        
        summary = f"""# Conversion Context Summary

## Experimental Context

This dataset represents a neuroscience experiment conducted by {conversion_metadata.get('experimenter', 'an unspecified researcher')} at {conversion_metadata.get('lab', 'an unspecified laboratory')}.

### Experiment Description
{conversion_metadata.get('session_description', 'No description provided.')}

### Key Experimental Details
- **Subject**: {conversion_metadata.get('subject_id', 'Not specified')}
- **Species**: {conversion_metadata.get('species', 'Not specified')}
- **Age**: {conversion_metadata.get('age', 'Not specified')}
- **Session Start**: {conversion_metadata.get('session_start_time', 'Not specified')}

## Conversion Decisions

### Automated Decisions Made
"""
        
        if provenance_data:
            ai_decisions = []
            auto_extractions = []
            
            for field, provenance_list in provenance_data.items():
                if provenance_list:
                    latest = provenance_list[-1]
                    source = latest.get('source', '')
                    
                    if source == 'ai_generated':
                        ai_decisions.append(f"- **{field}**: {latest.get('value', 'Unknown')} (AI suggested)")
                    elif source == 'auto_extracted':
                        auto_extractions.append(f"- **{field}**: {latest.get('value', 'Unknown')} (Automatically detected)")
            
            if ai_decisions:
                summary += "\\n#### AI-Generated Suggestions:\\n"
                summary += "\\n".join(ai_decisions)
            
            if auto_extractions:
                summary += "\\n#### Automatically Extracted Information:\\n"
                summary += "\\n".join(auto_extractions)
        
        # Knowledge Graph Context
        if knowledge_graph_data:
            summary += f"""

## Semantic Relationships

The conversion process identified {knowledge_graph_data.get('entities_count', 0)} entities and their relationships:

### Key Relationships Discovered
"""
            
            relationships = knowledge_graph_data.get('key_relationships', [])
            for rel in relationships[:5]:  # Show top 5
                summary += f"- {rel.get('subject', 'Unknown')} → {rel.get('predicate', 'relates to')} → {rel.get('object', 'Unknown')}\\n"
        
        summary += """
## Data Quality Insights

### What This Means for Your Data

The conversion process has transformed your raw neuroscience data into the standardized NWB format, making it:

1. **Interoperable**: Compatible with NWB-based analysis tools
2. **Discoverable**: Enriched with standardized metadata
3. **Reusable**: Properly documented for future research
4. **Shareable**: Ready for publication and data sharing

### Next Steps

Based on the conversion results, consider:
- Reviewing any AI-generated suggestions for accuracy
- Adding additional metadata if recommended
- Validating the converted data with your analysis workflows
- Sharing the data through appropriate repositories
"""
        
        return summary

class MultiFormatOutputEngine:
    """Generates reports in multiple formats."""
    
    def __init__(self):
        self.executive_generator = ExecutiveSummaryGenerator()
        self.technical_generator = TechnicalReportGenerator()
        self.context_generator = ContextSummaryGenerator()
    
    def generate_all_reports(self, output_dir: str, quality_assessment: QualityAssessment,
                           validation_results: Dict[str, Any], conversion_metadata: Dict[str, Any],
                           provenance_data: Dict[str, Any], knowledge_graph_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate all report formats."""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        # Executive Summary (Markdown)
        exec_summary = self.executive_generator.generate_summary(quality_assessment, conversion_metadata)
        exec_path = output_path / "executive_summary.md"
        exec_path.write_text(exec_summary)
        generated_files['executive_summary'] = str(exec_path)
        
        # Technical Report (Markdown)
        tech_report = self.technical_generator.generate_report(
            quality_assessment, validation_results, conversion_metadata, provenance_data
        )
        tech_path = output_path / "technical_report.md"
        tech_path.write_text(tech_report)
        generated_files['technical_report'] = str(tech_path)
        
        # Context Summary (Markdown)
        context_summary = self.context_generator.generate_context_summary(
            conversion_metadata, provenance_data, knowledge_graph_data
        )
        context_path = output_path / "context_summary.md"
        context_path.write_text(context_summary)
        generated_files['context_summary'] = str(context_path)
        
        # JSON Report (Machine-readable)
        json_report = {
            'quality_assessment': {
                'overall_score': quality_assessment.overall_score,
                'dimension_scores': {d.value: s for d, s in quality_assessment.dimension_scores.items()},
                'metrics': [
                    {
                        'name': m.name,
                        'value': m.value,
                        'max_value': m.max_value,
                        'normalized_score': m.normalized_score,
                        'description': m.description,
                        'dimension': m.dimension.value
                    }
                    for m in quality_assessment.metrics
                ],
                'recommendations': quality_assessment.recommendations,
                'strengths': quality_assessment.strengths,
                'weaknesses': quality_assessment.weaknesses
            },
            'validation_results': validation_results,
            'conversion_metadata': conversion_metadata,
            'provenance_data': provenance_data,
            'knowledge_graph_data': knowledge_graph_data,
            'generation_timestamp': datetime.now().isoformat()
        }
        
        json_path = output_path / "evaluation_report.json"
        json_path.write_text(json.dumps(json_report, indent=2, default=str))
        generated_files['json_report'] = str(json_path)
        
        return generated_files
```### 3. 
Visualization Framework

#### Interactive Knowledge Graph Viewer
```python
# agentic_neurodata_conversion/evaluation/visualization.py
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import html

class InteractiveKnowledgeGraphViewer:
    """Creates interactive knowledge graph visualizations."""
    
    def generate_interactive_graph(self, knowledge_graph_data: Dict[str, Any], 
                                 output_path: str) -> str:
        """Generate interactive HTML visualization of knowledge graph."""
        
        # Extract nodes and edges from knowledge graph data
        nodes = self._extract_nodes(knowledge_graph_data)
        edges = self._extract_edges(knowledge_graph_data)
        
        # Generate HTML with D3.js visualization
        html_content = self._generate_graph_html(nodes, edges)
        
        output_file = Path(output_path)
        output_file.write_text(html_content)
        
        return str(output_file)
    
    def _extract_nodes(self, kg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract nodes from knowledge graph data."""
        nodes = []
        entities = kg_data.get('entities', [])
        
        for entity in entities:
            nodes.append({
                'id': entity.get('uri', ''),
                'label': entity.get('label', 'Unknown'),
                'type': entity.get('type', 'Entity'),
                'properties': entity.get('properties', {})
            })
        
        return nodes
    
    def _extract_edges(self, kg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract edges from knowledge graph data."""
        edges = []
        relationships = kg_data.get('relationships', [])
        
        for rel in relationships:
            edges.append({
                'source': rel.get('subject', ''),
                'target': rel.get('object', ''),
                'label': rel.get('predicate', 'relates_to'),
                'properties': rel.get('properties', {})
            })
        
        return edges
    
    def _generate_graph_html(self, nodes: List[Dict], edges: List[Dict]) -> str:
        """Generate HTML with interactive graph visualization."""
        
        nodes_json = json.dumps(nodes)
        edges_json = json.dumps(edges)
        
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Graph Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .graph-container {{ width: 100%; height: 600px; border: 1px solid #ccc; }}
        .node {{ cursor: pointer; }}
        .node circle {{ fill: #69b3a2; stroke: #333; stroke-width: 2px; }}
        .node text {{ font-size: 12px; text-anchor: middle; }}
        .link {{ stroke: #999; stroke-opacity: 0.6; stroke-width: 2px; }}
        .link-label {{ font-size: 10px; fill: #666; }}
        .tooltip {{ position: absolute; padding: 10px; background: rgba(0,0,0,0.8); 
                   color: white; border-radius: 5px; pointer-events: none; }}
        .controls {{ margin-bottom: 20px; }}
        .controls button {{ margin-right: 10px; padding: 5px 10px; }}
    </style>
</head>
<body>
    <h1>Knowledge Graph Visualization</h1>
    
    <div class="controls">
        <button onclick="resetZoom()">Reset Zoom</button>
        <button onclick="toggleLabels()">Toggle Labels</button>
        <select id="nodeFilter" onchange="filterNodes()">
            <option value="all">All Nodes</option>
            <option value="Dataset">Datasets</option>
            <option value="Subject">Subjects</option>
            <option value="Device">Devices</option>
            <option value="Protocol">Protocols</option>
        </select>
    </div>
    
    <div id="graph" class="graph-container"></div>
    
    <div id="tooltip" class="tooltip" style="display: none;"></div>
    
    <script>
        const nodes = {nodes_json};
        const edges = {edges_json};
        
        const width = 800;
        const height = 600;
        
        const svg = d3.select("#graph")
            .append("svg")
            .attr("width", width)
            .attr("height", height);
        
        const g = svg.append("g");
        
        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }});
        
        svg.call(zoom);
        
        // Create force simulation
        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(edges).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));
        
        // Create links
        const link = g.append("g")
            .selectAll("line")
            .data(edges)
            .enter().append("line")
            .attr("class", "link");
        
        // Create link labels
        const linkLabel = g.append("g")
            .selectAll("text")
            .data(edges)
            .enter().append("text")
            .attr("class", "link-label")
            .text(d => d.label);
        
        // Create nodes
        const node = g.append("g")
            .selectAll("g")
            .data(nodes)
            .enter().append("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        node.append("circle")
            .attr("r", 8)
            .style("fill", d => getNodeColor(d.type));
        
        node.append("text")
            .attr("dy", -12)
            .text(d => d.label);
        
        // Add tooltips
        node.on("mouseover", function(event, d) {{
            const tooltip = d3.select("#tooltip");
            tooltip.style("display", "block")
                .html(`<strong>${{d.label}}</strong><br/>Type: ${{d.type}}<br/>Properties: ${{Object.keys(d.properties).length}}`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px");
        }})
        .on("mouseout", function() {{
            d3.select("#tooltip").style("display", "none");
        }});
        
        // Update positions on simulation tick
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            linkLabel
                .attr("x", d => (d.source.x + d.target.x) / 2)
                .attr("y", d => (d.source.y + d.target.y) / 2);
            
            node
                .attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});
        
        function getNodeColor(type) {{
            const colors = {{
                'Dataset': '#ff7f0e',
                'Subject': '#2ca02c',
                'Device': '#d62728',
                'Protocol': '#9467bd',
                'Lab': '#8c564b'
            }};
            return colors[type] || '#69b3a2';
        }}
        
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        function resetZoom() {{
            svg.transition().duration(750).call(
                zoom.transform,
                d3.zoomIdentity
            );
        }}
        
        function toggleLabels() {{
            const labels = g.selectAll(".node text");
            const isVisible = labels.style("display") !== "none";
            labels.style("display", isVisible ? "none" : "block");
        }}
        
        function filterNodes() {{
            const filterValue = document.getElementById("nodeFilter").value;
            
            node.style("display", d => {{
                return filterValue === "all" || d.type === filterValue ? "block" : "none";
            }});
            
            link.style("display", d => {{
                const sourceVisible = filterValue === "all" || d.source.type === filterValue;
                const targetVisible = filterValue === "all" || d.target.type === filterValue;
                return sourceVisible && targetVisible ? "block" : "none";
            }});
        }}
    </script>
</body>
</html>
"""
        
        return html_template

class QualityMetricsDashboard:
    """Creates interactive quality metrics dashboard."""
    
    def generate_dashboard(self, quality_assessment, output_path: str) -> str:
        """Generate interactive quality metrics dashboard."""
        
        # Prepare data for visualization
        dimension_data = [
            {'dimension': d.value.title(), 'score': s}
            for d, s in quality_assessment.dimension_scores.items()
        ]
        
        metrics_data = [
            {
                'name': m.name.replace('_', ' ').title(),
                'score': m.normalized_score,
                'dimension': m.dimension.value
            }
            for m in quality_assessment.metrics
        ]
        
        html_content = self._generate_dashboard_html(dimension_data, metrics_data, quality_assessment)
        
        output_file = Path(output_path)
        output_file.write_text(html_content)
        
        return str(output_file)
    
    def _generate_dashboard_html(self, dimension_data: List[Dict], 
                               metrics_data: List[Dict], quality_assessment) -> str:
        """Generate HTML dashboard with charts."""
        
        dimension_json = json.dumps(dimension_data)
        metrics_json = json.dumps(metrics_data)
        
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Quality Metrics Dashboard</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .dashboard {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .chart-container {{ border: 1px solid #ccc; padding: 20px; }}
        .overall-score {{ text-align: center; font-size: 24px; margin-bottom: 20px; }}
        .score-circle {{ width: 100px; height: 100px; border-radius: 50%; 
                        display: inline-flex; align-items: center; justify-content: center;
                        color: white; font-weight: bold; font-size: 18px; }}
        .recommendations {{ grid-column: 1 / -1; }}
        .rec-list {{ list-style-type: none; padding: 0; }}
        .rec-item {{ background: #f0f0f0; margin: 5px 0; padding: 10px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Quality Assessment Dashboard</h1>
    
    <div class="overall-score">
        <h2>Overall Quality Score</h2>
        <div class="score-circle" style="background-color: {self._get_score_color(quality_assessment.overall_score)}">
            {quality_assessment.overall_score:.1%}
        </div>
    </div>
    
    <div class="dashboard">
        <div class="chart-container">
            <h3>Quality Dimensions</h3>
            <div id="dimension-chart"></div>
        </div>
        
        <div class="chart-container">
            <h3>Detailed Metrics</h3>
            <div id="metrics-chart"></div>
        </div>
        
        <div class="recommendations">
            <h3>Recommendations</h3>
            <ul class="rec-list">
                {''.join(f'<li class="rec-item">{rec}</li>' for rec in quality_assessment.recommendations)}
            </ul>
        </div>
    </div>
    
    <script>
        const dimensionData = {dimension_json};
        const metricsData = {metrics_json};
        
        // Create dimension bar chart
        const dimensionMargin = {{top: 20, right: 30, bottom: 40, left: 100}};
        const dimensionWidth = 400 - dimensionMargin.left - dimensionMargin.right;
        const dimensionHeight = 200 - dimensionMargin.top - dimensionMargin.bottom;
        
        const dimensionSvg = d3.select("#dimension-chart")
            .append("svg")
            .attr("width", dimensionWidth + dimensionMargin.left + dimensionMargin.right)
            .attr("height", dimensionHeight + dimensionMargin.top + dimensionMargin.bottom)
            .append("g")
            .attr("transform", `translate(${{dimensionMargin.left}},${{dimensionMargin.top}})`);
        
        const xScale = d3.scaleLinear()
            .domain([0, 1])
            .range([0, dimensionWidth]);
        
        const yScale = d3.scaleBand()
            .domain(dimensionData.map(d => d.dimension))
            .range([0, dimensionHeight])
            .padding(0.1);
        
        dimensionSvg.selectAll(".bar")
            .data(dimensionData)
            .enter().append("rect")
            .attr("class", "bar")
            .attr("x", 0)
            .attr("y", d => yScale(d.dimension))
            .attr("width", d => xScale(d.score))
            .attr("height", yScale.bandwidth())
            .attr("fill", d => getScoreColor(d.score));
        
        dimensionSvg.append("g")
            .attr("transform", `translate(0,${{dimensionHeight}})`)
            .call(d3.axisBottom(xScale).tickFormat(d3.format(".0%")));
        
        dimensionSvg.append("g")
            .call(d3.axisLeft(yScale));
        
        // Add score labels
        dimensionSvg.selectAll(".label")
            .data(dimensionData)
            .enter().append("text")
            .attr("class", "label")
            .attr("x", d => xScale(d.score) + 5)
            .attr("y", d => yScale(d.dimension) + yScale.bandwidth() / 2)
            .attr("dy", "0.35em")
            .text(d => (d.score * 100).toFixed(0) + "%");
        
        function getScoreColor(score) {{
            if (score >= 0.8) return "#2ca02c";
            if (score >= 0.6) return "#ff7f0e";
            return "#d62728";
        }}
    </script>
</body>
</html>
"""
        
        return html_template
    
    def _get_score_color(self, score: float) -> str:
        """Get color based on score."""
        if score >= 0.8:
            return "#2ca02c"  # Green
        elif score >= 0.6:
            return "#ff7f0e"  # Orange
        else:
            return "#d62728"  # Red

class VisualizationFramework:
    """Main visualization framework coordinator."""
    
    def __init__(self):
        self.kg_viewer = InteractiveKnowledgeGraphViewer()
        self.dashboard = QualityMetricsDashboard()
    
    def generate_all_visualizations(self, output_dir: str, quality_assessment,
                                  knowledge_graph_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate all visualization outputs."""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        # Knowledge graph visualization
        if knowledge_graph_data:
            kg_viz_path = output_path / "knowledge_graph.html"
            self.kg_viewer.generate_interactive_graph(knowledge_graph_data, str(kg_viz_path))
            generated_files['knowledge_graph'] = str(kg_viz_path)
        
        # Quality metrics dashboard
        dashboard_path = output_path / "quality_dashboard.html"
        self.dashboard.generate_dashboard(quality_assessment, str(dashboard_path))
        generated_files['quality_dashboard'] = str(dashboard_path)
        
        return generated_files
```##
# 4. Integration with MCP Server

#### MCP Tools for Evaluation and Reporting
```python
# agentic_neurodata_conversion/mcp_server/tools/evaluation_reporting.py
from ..server import mcp
from ...evaluation.quality_assessment import QualityAssessmentEngine
from ...evaluation.report_generation import MultiFormatOutputEngine
from ...evaluation.visualization import VisualizationFramework
from typing import Dict, Any, Optional

@mcp.tool(
    name="generate_evaluation_report",
    description="Generate comprehensive evaluation report with quality assessment and visualizations"
)
async def generate_evaluation_report(
    nwb_path: str,
    validation_results: Dict[str, Any],
    conversion_metadata: Dict[str, Any],
    provenance_data: Optional[Dict[str, Any]] = None,
    knowledge_graph_data: Optional[Dict[str, Any]] = None,
    output_dir: str = "evaluation_outputs",
    include_visualizations: bool = True,
    server=None
) -> Dict[str, Any]:
    """Generate comprehensive evaluation report."""
    
    try:
        # Initialize evaluation components
        quality_engine = QualityAssessmentEngine()
        report_engine = MultiFormatOutputEngine()
        viz_framework = VisualizationFramework()
        
        # Perform quality assessment
        quality_assessment = quality_engine.assess_quality(
            nwb_path=nwb_path,
            validation_results=validation_results,
            metadata=conversion_metadata
        )
        
        # Generate reports
        report_files = report_engine.generate_all_reports(
            output_dir=output_dir,
            quality_assessment=quality_assessment,
            validation_results=validation_results,
            conversion_metadata=conversion_metadata,
            provenance_data=provenance_data or {},
            knowledge_graph_data=knowledge_graph_data or {}
        )
        
        # Generate visualizations if requested
        visualization_files = {}
        if include_visualizations:
            visualization_files = viz_framework.generate_all_visualizations(
                output_dir=output_dir,
                quality_assessment=quality_assessment,
                knowledge_graph_data=knowledge_graph_data or {}
            )
        
        return {
            "status": "success",
            "quality_assessment": {
                "overall_score": quality_assessment.overall_score,
                "dimension_scores": {d.value: s for d, s in quality_assessment.dimension_scores.items()},
                "recommendations": quality_assessment.recommendations,
                "strengths": quality_assessment.strengths,
                "weaknesses": quality_assessment.weaknesses
            },
            "generated_files": {
                **report_files,
                **visualization_files
            },
            "output_directory": output_dir
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool(
    name="assess_conversion_quality",
    description="Assess quality of converted NWB file from multiple perspectives"
)
async def assess_conversion_quality(
    nwb_path: str,
    validation_results: Dict[str, Any],
    conversion_metadata: Dict[str, Any],
    server=None
) -> Dict[str, Any]:
    """Assess conversion quality from technical, scientific, and usability perspectives."""
    
    try:
        quality_engine = QualityAssessmentEngine()
        
        quality_assessment = quality_engine.assess_quality(
            nwb_path=nwb_path,
            validation_results=validation_results,
            metadata=conversion_metadata
        )
        
        return {
            "status": "success",
            "overall_score": quality_assessment.overall_score,
            "dimension_scores": {d.value: s for d, s in quality_assessment.dimension_scores.items()},
            "detailed_metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "max_value": m.max_value,
                    "normalized_score": m.normalized_score,
                    "description": m.description,
                    "dimension": m.dimension.value
                }
                for m in quality_assessment.metrics
            ],
            "recommendations": quality_assessment.recommendations,
            "strengths": quality_assessment.strengths,
            "weaknesses": quality_assessment.weaknesses
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool(
    name="generate_context_summary",
    description="Generate human-readable context summary explaining conversion decisions"
)
async def generate_context_summary(
    conversion_metadata: Dict[str, Any],
    provenance_data: Dict[str, Any],
    knowledge_graph_data: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    server=None
) -> Dict[str, Any]:
    """Generate context summary explaining conversion decisions and relationships."""
    
    try:
        from ...evaluation.report_generation import ContextSummaryGenerator
        
        context_generator = ContextSummaryGenerator()
        
        context_summary = context_generator.generate_context_summary(
            conversion_metadata=conversion_metadata,
            provenance_data=provenance_data,
            knowledge_graph_data=knowledge_graph_data or {}
        )
        
        result = {
            "status": "success",
            "context_summary": context_summary
        }
        
        # Save to file if path provided
        if output_path:
            from pathlib import Path
            Path(output_path).write_text(context_summary)
            result["output_file"] = output_path
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool(
    name="create_interactive_visualization",
    description="Create interactive HTML visualizations of conversion results"
)
async def create_interactive_visualization(
    visualization_type: str,  # "knowledge_graph" or "quality_dashboard"
    data: Dict[str, Any],
    output_path: str,
    server=None
) -> Dict[str, Any]:
    """Create interactive HTML visualization."""
    
    try:
        viz_framework = VisualizationFramework()
        
        if visualization_type == "knowledge_graph":
            output_file = viz_framework.kg_viewer.generate_interactive_graph(
                knowledge_graph_data=data,
                output_path=output_path
            )
        elif visualization_type == "quality_dashboard":
            # Reconstruct quality assessment from data
            from ...evaluation.quality_assessment import QualityAssessment, QualityDimension, QualityMetric
            
            # This would need proper reconstruction logic
            quality_assessment = data  # Simplified for now
            
            output_file = viz_framework.dashboard.generate_dashboard(
                quality_assessment=quality_assessment,
                output_path=output_path
            )
        else:
            return {
                "status": "error",
                "message": f"Unknown visualization type: {visualization_type}"
            }
        
        return {
            "status": "success",
            "output_file": output_file,
            "visualization_type": visualization_type
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool(
    name="compare_conversion_quality",
    description="Compare quality metrics between multiple conversions"
)
async def compare_conversion_quality(
    conversion_results: List[Dict[str, Any]],
    comparison_criteria: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    server=None
) -> Dict[str, Any]:
    """Compare quality metrics between multiple conversion results."""
    
    try:
        # Default comparison criteria
        if comparison_criteria is None:
            comparison_criteria = [
                "overall_score", "technical_score", "scientific_score", "usability_score"
            ]
        
        comparison_results = {
            "conversions": [],
            "summary": {},
            "recommendations": []
        }
        
        # Process each conversion
        for i, conversion in enumerate(conversion_results):
            conversion_summary = {
                "id": conversion.get("id", f"conversion_{i}"),
                "overall_score": conversion.get("quality_assessment", {}).get("overall_score", 0),
                "dimension_scores": conversion.get("quality_assessment", {}).get("dimension_scores", {}),
                "strengths": conversion.get("quality_assessment", {}).get("strengths", []),
                "weaknesses": conversion.get("quality_assessment", {}).get("weaknesses", [])
            }
            comparison_results["conversions"].append(conversion_summary)
        
        # Generate comparison summary
        if comparison_results["conversions"]:
            scores = [c["overall_score"] for c in comparison_results["conversions"]]
            comparison_results["summary"] = {
                "best_conversion": max(comparison_results["conversions"], key=lambda x: x["overall_score"])["id"],
                "worst_conversion": min(comparison_results["conversions"], key=lambda x: x["overall_score"])["id"],
                "average_score": sum(scores) / len(scores),
                "score_range": max(scores) - min(scores)
            }
        
        # Generate recommendations
        if comparison_results["summary"].get("score_range", 0) > 0.2:
            comparison_results["recommendations"].append(
                "Significant quality variation detected. Review conversion parameters."
            )
        
        # Save to file if requested
        if output_path:
            import json
            from pathlib import Path
            Path(output_path).write_text(json.dumps(comparison_results, indent=2))
        
        return {
            "status": "success",
            "comparison_results": comparison_results,
            "output_file": output_path if output_path else None
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
```

### 5. Collaborative Review System

#### Expert Review Interface
```python
# agentic_neurodata_conversion/evaluation/collaborative_review.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json
from pathlib import Path

class ReviewStatus(Enum):
    """Review status options."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"

@dataclass
class ReviewAnnotation:
    """Individual review annotation."""
    id: str
    reviewer: str
    timestamp: datetime
    field: str
    annotation_type: str  # "comment", "correction", "approval", "concern"
    content: str
    severity: str  # "info", "warning", "critical"
    resolved: bool = False

@dataclass
class ReviewSession:
    """Complete review session."""
    session_id: str
    conversion_id: str
    reviewer: str
    start_time: datetime
    end_time: Optional[datetime]
    status: ReviewStatus
    annotations: List[ReviewAnnotation]
    overall_comments: str
    approval_decision: Optional[bool]

class ExpertReviewInterface:
    """Interface for expert review and validation."""
    
    def __init__(self, review_storage_path: str = "reviews"):
        self.storage_path = Path(review_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def create_review_session(self, conversion_id: str, reviewer: str) -> str:
        """Create new review session."""
        session_id = f"review_{conversion_id}_{reviewer}_{int(datetime.now().timestamp())}"
        
        session = ReviewSession(
            session_id=session_id,
            conversion_id=conversion_id,
            reviewer=reviewer,
            start_time=datetime.now(),
            end_time=None,
            status=ReviewStatus.PENDING,
            annotations=[],
            overall_comments="",
            approval_decision=None
        )
        
        self._save_review_session(session)
        return session_id
    
    def add_annotation(self, session_id: str, field: str, annotation_type: str,
                      content: str, severity: str = "info") -> str:
        """Add annotation to review session."""
        session = self._load_review_session(session_id)
        
        annotation_id = f"ann_{len(session.annotations) + 1}"
        annotation = ReviewAnnotation(
            id=annotation_id,
            reviewer=session.reviewer,
            timestamp=datetime.now(),
            field=field,
            annotation_type=annotation_type,
            content=content,
            severity=severity
        )
        
        session.annotations.append(annotation)
        session.status = ReviewStatus.IN_PROGRESS
        
        self._save_review_session(session)
        return annotation_id
    
    def finalize_review(self, session_id: str, overall_comments: str,
                       approval_decision: bool) -> ReviewSession:
        """Finalize review session."""
        session = self._load_review_session(session_id)
        
        session.end_time = datetime.now()
        session.overall_comments = overall_comments
        session.approval_decision = approval_decision
        session.status = ReviewStatus.APPROVED if approval_decision else ReviewStatus.REJECTED
        
        self._save_review_session(session)
        return session
    
    def get_review_summary(self, conversion_id: str) -> Dict[str, Any]:
        """Get summary of all reviews for a conversion."""
        review_files = list(self.storage_path.glob(f"review_{conversion_id}_*.json"))
        
        reviews = []
        for review_file in review_files:
            session = self._load_review_session(review_file.stem)
            reviews.append({
                "session_id": session.session_id,
                "reviewer": session.reviewer,
                "status": session.status.value,
                "annotation_count": len(session.annotations),
                "approval_decision": session.approval_decision,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None
            })
        
        # Calculate summary statistics
        total_reviews = len(reviews)
        approved_reviews = len([r for r in reviews if r["approval_decision"] is True])
        rejected_reviews = len([r for r in reviews if r["approval_decision"] is False])
        pending_reviews = len([r for r in reviews if r["approval_decision"] is None])
        
        return {
            "conversion_id": conversion_id,
            "total_reviews": total_reviews,
            "approved_reviews": approved_reviews,
            "rejected_reviews": rejected_reviews,
            "pending_reviews": pending_reviews,
            "reviews": reviews
        }
    
    def _save_review_session(self, session: ReviewSession):
        """Save review session to storage."""
        session_file = self.storage_path / f"{session.session_id}.json"
        
        session_data = {
            "session_id": session.session_id,
            "conversion_id": session.conversion_id,
            "reviewer": session.reviewer,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "status": session.status.value,
            "annotations": [
                {
                    "id": ann.id,
                    "reviewer": ann.reviewer,
                    "timestamp": ann.timestamp.isoformat(),
                    "field": ann.field,
                    "annotation_type": ann.annotation_type,
                    "content": ann.content,
                    "severity": ann.severity,
                    "resolved": ann.resolved
                }
                for ann in session.annotations
            ],
            "overall_comments": session.overall_comments,
            "approval_decision": session.approval_decision
        }
        
        session_file.write_text(json.dumps(session_data, indent=2))
    
    def _load_review_session(self, session_id: str) -> ReviewSession:
        """Load review session from storage."""
        session_file = self.storage_path / f"{session_id}.json"
        
        if not session_file.exists():
            raise ValueError(f"Review session not found: {session_id}")
        
        session_data = json.loads(session_file.read_text())
        
        annotations = [
            ReviewAnnotation(
                id=ann["id"],
                reviewer=ann["reviewer"],
                timestamp=datetime.fromisoformat(ann["timestamp"]),
                field=ann["field"],
                annotation_type=ann["annotation_type"],
                content=ann["content"],
                severity=ann["severity"],
                resolved=ann["resolved"]
            )
            for ann in session_data["annotations"]
        ]
        
        return ReviewSession(
            session_id=session_data["session_id"],
            conversion_id=session_data["conversion_id"],
            reviewer=session_data["reviewer"],
            start_time=datetime.fromisoformat(session_data["start_time"]),
            end_time=datetime.fromisoformat(session_data["end_time"]) if session_data["end_time"] else None,
            status=ReviewStatus(session_data["status"]),
            annotations=annotations,
            overall_comments=session_data["overall_comments"],
            approval_decision=session_data["approval_decision"]
        )

class ReviewWorkflowManager:
    """Manages review workflows and approval processes."""
    
    def __init__(self, review_interface: ExpertReviewInterface):
        self.review_interface = review_interface
    
    def initiate_review_workflow(self, conversion_id: str, reviewers: List[str],
                                review_type: str = "standard") -> Dict[str, str]:
        """Initiate review workflow with multiple reviewers."""
        review_sessions = {}
        
        for reviewer in reviewers:
            session_id = self.review_interface.create_review_session(conversion_id, reviewer)
            review_sessions[reviewer] = session_id
        
        return review_sessions
    
    def check_review_completion(self, conversion_id: str) -> Dict[str, Any]:
        """Check if review process is complete."""
        summary = self.review_interface.get_review_summary(conversion_id)
        
        total_reviews = summary["total_reviews"]
        completed_reviews = summary["approved_reviews"] + summary["rejected_reviews"]
        
        is_complete = summary["pending_reviews"] == 0
        consensus_reached = summary["approved_reviews"] > summary["rejected_reviews"]
        
        return {
            "is_complete": is_complete,
            "consensus_reached": consensus_reached,
            "completion_rate": completed_reviews / total_reviews if total_reviews > 0 else 0,
            "summary": summary
        }
    
    def generate_review_report(self, conversion_id: str) -> str:
        """Generate comprehensive review report."""
        summary = self.review_interface.get_review_summary(conversion_id)
        
        report = f"""# Review Report for Conversion {conversion_id}

## Review Summary

- **Total Reviews**: {summary['total_reviews']}
- **Approved**: {summary['approved_reviews']}
- **Rejected**: {summary['rejected_reviews']}
- **Pending**: {summary['pending_reviews']}

## Individual Reviews

"""
        
        for review in summary['reviews']:
            status_emoji = "✅" if review['approval_decision'] else "❌" if review['approval_decision'] is False else "⏳"
            report += f"""### {review['reviewer']} {status_emoji}

- **Status**: {review['status']}
- **Annotations**: {review['annotation_count']}
- **Started**: {review['start_time']}
- **Completed**: {review['end_time'] or 'In progress'}

"""
        
        # Add recommendations
        completion_status = self.check_review_completion(conversion_id)
        
        report += "## Recommendations\\n\\n"
        
        if completion_status['is_complete']:
            if completion_status['consensus_reached']:
                report += "✅ **Recommendation**: Approve conversion - consensus reached\\n"
            else:
                report += "⚠️ **Recommendation**: Review conflicts - additional review needed\\n"
        else:
            report += "⏳ **Recommendation**: Awaiting completion of pending reviews\\n"
        
        return report

# Integration with evaluation system
class CollaborativeEvaluationSystem:
    """Integrates collaborative review with evaluation system."""
    
    def __init__(self):
        self.review_interface = ExpertReviewInterface()
        self.workflow_manager = ReviewWorkflowManager(self.review_interface)
    
    def create_review_package(self, conversion_id: str, evaluation_results: Dict[str, Any],
                            output_dir: str) -> str:
        """Create review package for expert evaluation."""
        
        package_dir = Path(output_dir) / f"review_package_{conversion_id}"
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # Create review instructions
        instructions = f"""# Review Instructions for Conversion {conversion_id}

## Overview
Please review the conversion results and provide feedback on the following aspects:

### Technical Quality
- Schema compliance and validation results
- Data integrity and structure
- File organization and metadata completeness

### Scientific Quality  
- Experimental metadata accuracy
- Scientific validity of the conversion
- Completeness of experimental documentation

### Usability Quality
- Documentation clarity and completeness
- Data discoverability and accessibility
- Ease of use for downstream analysis

## Review Process
1. Examine the generated reports and visualizations
2. Use the review interface to add annotations and comments
3. Provide overall approval/rejection decision with rationale

## Files Included
- Executive Summary: executive_summary.md
- Technical Report: technical_report.md
- Context Summary: context_summary.md
- Quality Dashboard: quality_dashboard.html
- Knowledge Graph: knowledge_graph.html (if available)

## Contact
For questions about the review process, contact the conversion team.
"""
        
        (package_dir / "REVIEW_INSTRUCTIONS.md").write_text(instructions)
        
        # Copy evaluation results
        import shutil
        for file_type, file_path in evaluation_results.get("generated_files", {}).items():
            if Path(file_path).exists():
                shutil.copy2(file_path, package_dir / Path(file_path).name)
        
        return str(package_dir)
```

This comprehensive evaluation and reporting design provides multiple perspectives on conversion quality, interactive visualizations, collaborative review capabilities, and seamless integration with the MCP server architecture.