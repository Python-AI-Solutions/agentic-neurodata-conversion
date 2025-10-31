#!/usr/bin/env python3
"""
Test script for HTML report generation.
"""
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'src'))

from services.report_service import ReportService

# Sample validation result data
validation_result = {
    'session_id': 'test_session_123',
    'overall_status': 'PASSED_WITH_ISSUES',
    'nwb_file_path': '/path/to/test_file.nwb',
    'file_info': {
        'nwb_version': '2.6.0',
        'file_size_bytes': 1024000,
        'creation_date': '2024-01-15',
        'identifier': 'TEST_123',
        'session_description': 'Test recording session',
        'session_start_time': '2024-01-15T10:00:00',
        'experimenter': ['John Doe', 'Jane Smith'],
        'institution': 'MIT',
        'lab': 'Neural Systems Lab',
        'subject_id': 'mouse_001',
        'species': 'Mus musculus',
        'sex': 'M',
        'age': 'P90D',
        'date_of_birth': '2023-10-16',
        'description': 'Adult male mouse for neural recording experiments',
        '_provenance': {
            'experimenter': 'user-specified',
            'institution': 'ai-parsed',
            'lab': 'file-extracted',
            'subject_id': 'user-specified',
            'species': 'file-extracted',
            'sex': 'file-extracted',
            'age': 'ai-inferred',
        },
        '_missing_fields': ['keywords', 'related_publications'],
    },
    'issues': [
        {
            'severity': 'CRITICAL',
            'check_name': 'missing_timestamps',
            'message': 'TimeSeries data is missing required timestamps',
            'location': '/acquisition/ElectricalSeries',
            'context': {'series_name': 'ElectricalSeries', 'data_shape': '(1000, 32)'},
            'suggestion': 'Add timestamps array to match data length',
            'references': [
                {'title': 'NWB TimeSeries Documentation', 'url': 'https://nwb-schema.readthedocs.io/en/latest/'}
            ],
        },
        {
            'severity': 'ERROR',
            'check_name': 'invalid_unit',
            'message': 'Unit "volts" is not in standard SI units',
            'location': '/acquisition/ElectricalSeries/data',
            'suggestion': 'Use "V" for volts according to SI standards',
        },
        {
            'severity': 'WARNING',
            'check_name': 'missing_metadata',
            'message': 'Session keywords are recommended for better discoverability',
            'location': '/general',
        },
        {
            'severity': 'WARNING',
            'check_name': 'incomplete_provenance',
            'message': 'Device description is missing',
            'location': '/general/devices',
        },
        {
            'severity': 'BEST_PRACTICE',
            'check_name': 'missing_related_pubs',
            'message': 'Consider adding related publications if available',
            'location': '/general',
        },
    ],
    'issue_counts': {
        'CRITICAL': 1,
        'ERROR': 1,
        'WARNING': 2,
        'BEST_PRACTICE': 1,
    },
}

# Sample LLM analysis
llm_analysis = {
    'executive_summary': 'The NWB file has good overall structure but requires attention to critical timestamp issues and standardization of units.',
    'quality_assessment': {
        'completeness_score': '85%',
        'metadata_quality': 'Good',
        'data_integrity': 'Needs Improvement',
        'scientific_value': 'High',
    },
    'recommendations': [
        'Add required timestamps to TimeSeries data to enable proper temporal alignment',
        'Standardize all units to SI format for better interoperability',
        'Complete device metadata for full experimental context',
    ],
    'dandi_ready': False,
}

# Sample workflow trace - matches actual conversion metadata
workflow_trace = {
    'metadata_provenance': {
        'experimenter': {
            'provenance': 'ai-parsed',
            'confidence': 95,
            'source': 'AI parsed from: "Dr. Jane Smith"',
            'needs_review': False,
        },
        'institution': {
            'provenance': 'user-specified',
            'confidence': 100,
            'source': 'User provided: "Massachusetts Institute of Technology"',
            'needs_review': False,
        },
        'session_description': {
            'provenance': 'ai-inferred',
            'confidence': 70,
            'source': 'Session description synthesized from text describing the recording purpose and methods',
            'needs_review': True,
        },
        'experiment_description': {
            'provenance': 'auto-extracted',
            'confidence': 85,
            'source': 'Automatically extracted from file analysis of nwb_uploads',
            'needs_review': False,
        },
        'subject_id': {
            'provenance': 'user-specified',
            'confidence': 100,
            'source': 'User explicitly provided in conversation',
            'needs_review': False,
        },
        'species': {
            'provenance': 'user-specified',
            'confidence': 100,
            'source': 'User explicitly provided in conversation',
            'needs_review': False,
        },
        'sex': {
            'provenance': 'user-specified',
            'confidence': 100,
            'source': 'User explicitly provided in conversation',
            'needs_review': False,
        },
        'age': {
            'provenance': 'user-specified',
            'confidence': 100,
            'source': 'User explicitly provided in conversation',
            'needs_review': False,
        },
        'lab': {
            'provenance': 'auto-extracted',
            'confidence': 100,
            'source': 'Extracted from source file',
            'needs_review': False,
        },
        'identifier': {
            'provenance': 'default',
            'confidence': 100,
            'source': 'System fallback value',
            'needs_review': False,
        },
        'session_start_time': {
            'provenance': 'user-specified',
            'confidence': 100,
            'source': 'User explicitly provided in conversation',
            'needs_review': False,
        },
    },
    'steps': [
        {
            'name': 'File Upload',
            'status': 'COMPLETED',
            'description': 'User uploaded source data file',
            'timestamp': '2024-01-15T10:00:00',
            'duration_ms': 1500,
        },
        {
            'name': 'Format Detection',
            'status': 'COMPLETED',
            'description': 'Detected format as ABF v1.83',
            'timestamp': '2024-01-15T10:00:02',
            'duration_ms': 500,
        },
        {
            'name': 'Metadata Parsing',
            'status': 'COMPLETED',
            'description': 'Extracted metadata from file headers',
            'timestamp': '2024-01-15T10:00:03',
            'duration_ms': 2000,
            'warnings': ['Some metadata fields missing from file'],
        },
        {
            'name': 'NWB Conversion',
            'status': 'COMPLETED',
            'description': 'Converted data to NWB format',
            'timestamp': '2024-01-15T10:00:05',
            'duration_ms': 5000,
        },
        {
            'name': 'Validation',
            'status': 'COMPLETED',
            'description': 'Validated NWB file against schema',
            'timestamp': '2024-01-15T10:00:10',
            'duration_ms': 3000,
        },
    ],
}

# Generate HTML report
print("Generating HTML report...")
report_service = ReportService()

output_path = Path('/Users/adityapatane/agentic-neurodata-conversion-14/test_report.html')

try:
    result_path = report_service.generate_html_report(
        output_path=output_path,
        validation_result=validation_result,
        llm_analysis=llm_analysis,
        workflow_trace=workflow_trace,
    )
    print(f"✓ HTML report generated successfully: {result_path}")
    print(f"  File size: {result_path.stat().st_size / 1024:.1f} KB")

    # Save workflow_trace to JSON file (simulating what the actual system does)
    import json
    workflow_trace_path = Path('/Users/adityapatane/agentic-neurodata-conversion-14/test_workflow_trace.json')
    with open(workflow_trace_path, 'w') as f:
        json.dump(workflow_trace, f, indent=2, default=str)
    print(f"  Workflow trace saved to: {workflow_trace_path}")

    print(f"\n  Open in browser: file://{result_path}")
except Exception as e:
    print(f"✗ Error generating HTML report: {e}")
    import traceback
    traceback.print_exc()
