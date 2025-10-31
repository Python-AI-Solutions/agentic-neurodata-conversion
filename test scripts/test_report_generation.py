"""
Quick test to generate an example report in the new format.
"""
from pathlib import Path
from backend.src.services.report_service import ReportService

# Create sample validation result (matching the structure from your inspection_report.txt)
validation_result = {
    'nwb_file_path': '/Users/adityapatane/trial/Noise4Sam_test.nwb',
    'overall_status': 'PASSED_WITH_ISSUES',
    'issue_counts': {
        'BEST_PRACTICE_SUGGESTION': 5,
        'CRITICAL': 0,
        'ERROR': 0,
        'WARNING': 0,
    },
    'issues': [
        {
            'severity': 'BEST_PRACTICE_SUGGESTION',
            'message': 'Experimenter is missing.',
            'location': '/',
            'check_name': 'check_experimenter_exists',
            'object_type': 'NWBFile',
        },
        {
            'severity': 'BEST_PRACTICE_SUGGESTION',
            'message': 'Experiment description is missing.',
            'location': '/',
            'check_name': 'check_experiment_description',
            'object_type': 'NWBFile',
        },
        {
            'severity': 'BEST_PRACTICE_SUGGESTION',
            'message': 'Metadata /general/institution is missing.',
            'location': '/',
            'check_name': 'check_institution',
            'object_type': 'NWBFile',
        },
        {
            'severity': 'BEST_PRACTICE_SUGGESTION',
            'message': 'Metadata /general/keywords is missing.',
            'location': '/',
            'check_name': 'check_keywords',
            'object_type': 'NWBFile',
        },
        {
            'severity': 'BEST_PRACTICE_SUGGESTION',
            'message': 'Subject is missing.',
            'location': '/',
            'check_name': 'check_subject_exists',
            'object_type': 'NWBFile',
        },
    ],
    'file_info': {
        'nwb_version': '2.9.0',
        'file_size_bytes': 610304,  # 596 KB
        'creation_date': '2025-10-15 19:16:01',
        'identifier': 'Unknown',
        'session_description': 'N/A',
        'subject_id': 'N/A',
        'species': 'N/A',
        'experimenter': [],
        'institution': 'N/A',
    }
}

# Generate the report
report_service = ReportService()
output_path = Path('example_inspection_report.txt')

print("Generating example text report...")
report_service.generate_text_report(output_path, validation_result)

print(f"\nReport generated: {output_path}")
print("\n" + "="*60)
print("REPORT CONTENT:")
print("="*60 + "\n")

# Read and display the report
with open(output_path, 'r') as f:
    content = f.read()
    print(content)

print("\n" + "="*60)
print(f"Report saved to: {output_path.absolute()}")
print("="*60)
