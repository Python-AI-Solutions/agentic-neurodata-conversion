# Workflow Examples

This document provides complete workflow examples for using the agentic neurodata conversion system.

## Basic Conversion Workflow

### Complete Python Workflow

```python
#!/usr/bin/env python
"""
Complete workflow example for converting neuroscience data to NWB format.
"""

from pathlib import Path
import json
from examples.python_client.workflow_example import MCPClient

def main():
    """Run complete conversion workflow."""

    # Initialize client
    client = MCPClient(api_url="http://127.0.0.1:8000")

    # Configuration
    dataset_dir = "/path/to/your/dataset"
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    print("🚀 Starting agentic neurodata conversion workflow")

    # Step 1: Check server status
    print("\n📡 Checking MCP server status...")
    status = client.get_server_status()

    if status.get("status") != "running":
        print("❌ MCP server is not running. Please start it first.")
        return 1

    print(f"✅ Server is running with {status.get('registered_tools', 0)} tools")

    # Step 2: Analyze dataset
    print(f"\n🔍 Analyzing dataset: {dataset_dir}")
    analysis_result = client.analyze_dataset(
        dataset_dir=dataset_dir,
        use_llm=True  # Use LLM for enhanced metadata extraction
    )

    if analysis_result.get("status") != "success":
        print(f"❌ Dataset analysis failed: {analysis_result.get('message')}")
        return 1

    print("✅ Dataset analysis completed")

    # Display analysis summary
    result_data = analysis_result.get("result", {})
    if "summary" in result_data:
        summary = result_data["summary"]
        print(f"   📊 Files: {summary.get('total_files', 0)}")
        print(f"   📁 Directories: {summary.get('total_directories', 0)}")
        print(f"   💾 Size: {summary.get('size_mb', 0):.2f} MB")

    # Step 3: Prepare file mappings
    print("\n🗂️  Preparing file mappings...")

    # This would typically be done based on the analysis results
    # For this example, we'll use a simple mapping
    files_map = {
        "recording": str(Path(dataset_dir) / "recording.dat"),
        "behavior": str(Path(dataset_dir) / "behavior.csv")
    }

    # Verify files exist
    missing_files = []
    for data_type, file_path in files_map.items():
        if not Path(file_path).exists():
            missing_files.append(f"{data_type}: {file_path}")

    if missing_files:
        print("⚠️  Some mapped files don't exist:")
        for missing in missing_files:
            print(f"   - {missing}")
        print("   Continuing with available files...")
        files_map = {k: v for k, v in files_map.items() if Path(v).exists()}

    print(f"✅ File mapping prepared with {len(files_map)} files")

    # Step 4: Generate and execute conversion
    print("\n⚙️  Generating conversion script...")
    conversion_result = client.generate_conversion_script(files_map)

    if conversion_result.get("status") != "success":
        print(f"❌ Conversion failed: {conversion_result.get('message')}")
        return 1

    nwb_path = conversion_result.get("output_nwb_path")
    print(f"✅ Conversion completed: {nwb_path}")

    # Step 5: Evaluate the result
    print("\n🔬 Evaluating NWB file...")
    evaluation_result = client.evaluate_nwb_file(nwb_path)

    if evaluation_result.get("status") != "success":
        print(f"⚠️  Evaluation failed: {evaluation_result.get('message')}")
    else:
        eval_data = evaluation_result.get("result", {})
        summary = eval_data.get("summary", {})

        if summary.get("overall_valid"):
            print("✅ NWB file validation passed")
        else:
            print("⚠️  NWB file has validation issues")

        print(f"   🏆 Quality Score: {summary.get('quality_score', 0)}/100")
        print(f"   ❌ Errors: {summary.get('total_errors', 0)}")
        print(f"   ⚠️  Warnings: {summary.get('total_warnings', 0)}")

    # Step 6: Generate summary report
    print("\n📋 Generating workflow summary...")

    workflow_summary = {
        "workflow_id": f"conversion_{int(datetime.now().timestamp())}",
        "dataset_path": dataset_dir,
        "output_path": nwb_path,
        "analysis_result": analysis_result,
        "conversion_result": conversion_result,
        "evaluation_result": evaluation_result,
        "pipeline_state": client.pipeline_state,
        "timestamp": datetime.now().isoformat()
    }

    # Save summary to file
    summary_path = output_dir / "workflow_summary.json"
    with open(summary_path, "w") as f:
        json.dump(workflow_summary, f, indent=2)

    print(f"✅ Workflow summary saved: {summary_path}")

    print("\n🎉 Workflow completed successfully!")
    print(f"   📄 NWB File: {nwb_path}")
    print(f"   📊 Summary: {summary_path}")

    return 0

if __name__ == "__main__":
    from datetime import datetime
    exit_code = main()
    exit(exit_code)
```

## Batch Processing Workflow

### Processing Multiple Datasets

```python
#!/usr/bin/env python
"""
Batch processing workflow for converting multiple datasets.
"""

import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from examples.python_client.workflow_example import MCPClient

class BatchProcessor:
    """Batch processor for multiple dataset conversions."""

    def __init__(self, api_url: str = "http://127.0.0.1:8000", max_workers: int = 3):
        self.api_url = api_url
        self.max_workers = max_workers
        self.results = []

    def process_dataset(self, dataset_config: dict) -> dict:
        """Process a single dataset."""
        client = MCPClient(self.api_url)

        dataset_name = dataset_config["name"]
        dataset_dir = dataset_config["path"]
        files_map = dataset_config.get("files_map", {})

        print(f"🔄 Processing dataset: {dataset_name}")

        try:
            # Analysis
            analysis_result = client.analyze_dataset(dataset_dir)
            if analysis_result.get("status") != "success":
                return {
                    "dataset": dataset_name,
                    "status": "failed",
                    "stage": "analysis",
                    "error": analysis_result.get("message")
                }

            # Conversion
            conversion_result = client.generate_conversion_script(files_map)
            if conversion_result.get("status") != "success":
                return {
                    "dataset": dataset_name,
                    "status": "failed",
                    "stage": "conversion",
                    "error": conversion_result.get("message")
                }

            # Evaluation
            nwb_path = conversion_result.get("output_nwb_path")
            evaluation_result = client.evaluate_nwb_file(nwb_path)

            return {
                "dataset": dataset_name,
                "status": "success",
                "nwb_path": nwb_path,
                "analysis": analysis_result,
                "conversion": conversion_result,
                "evaluation": evaluation_result
            }

        except Exception as e:
            return {
                "dataset": dataset_name,
                "status": "error",
                "error": str(e)
            }

    def process_batch(self, datasets: list) -> list:
        """Process multiple datasets in parallel."""
        print(f"🚀 Starting batch processing of {len(datasets)} datasets")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_dataset = {
                executor.submit(self.process_dataset, dataset): dataset["name"]
                for dataset in datasets
            }

            # Collect results as they complete
            for future in as_completed(future_to_dataset):
                dataset_name = future_to_dataset[future]
                try:
                    result = future.result()
                    self.results.append(result)

                    if result["status"] == "success":
                        print(f"✅ {dataset_name} completed successfully")
                    else:
                        print(f"❌ {dataset_name} failed: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    print(f"❌ {dataset_name} crashed: {e}")
                    self.results.append({
                        "dataset": dataset_name,
                        "status": "crashed",
                        "error": str(e)
                    })

        return self.results

    def generate_batch_report(self, output_path: str = "batch_report.json"):
        """Generate comprehensive batch processing report."""
        successful = [r for r in self.results if r["status"] == "success"]
        failed = [r for r in self.results if r["status"] != "success"]

        report = {
            "batch_summary": {
                "total_datasets": len(self.results),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": len(successful) / len(self.results) * 100 if self.results else 0
            },
            "successful_conversions": successful,
            "failed_conversions": failed,
            "timestamp": datetime.now().isoformat()
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"📊 Batch report saved: {output_path}")
        return report

def main():
    """Main batch processing function."""

    # Define datasets to process
    datasets = [
        {
            "name": "experiment_001",
            "path": "/data/experiments/exp001",
            "files_map": {
                "recording": "/data/experiments/exp001/recording.dat",
                "behavior": "/data/experiments/exp001/behavior.csv"
            }
        },
        {
            "name": "experiment_002",
            "path": "/data/experiments/exp002",
            "files_map": {
                "recording": "/data/experiments/exp002/recording.dat",
                "behavior": "/data/experiments/exp002/behavior.csv"
            }
        },
        {
            "name": "experiment_003",
            "path": "/data/experiments/exp003",
            "files_map": {
                "recording": "/data/experiments/exp003/recording.dat"
            }
        }
    ]

    # Initialize batch processor
    processor = BatchProcessor(max_workers=2)  # Limit concurrent processing

    # Process all datasets
    results = processor.process_batch(datasets)

    # Generate report
    report = processor.generate_batch_report("outputs/batch_report.json")

    # Print summary
    print(f"\n📊 Batch Processing Summary:")
    print(f"   Total: {report['batch_summary']['total_datasets']}")
    print(f"   ✅ Successful: {report['batch_summary']['successful']}")
    print(f"   ❌ Failed: {report['batch_summary']['failed']}")
    print(f"   📈 Success Rate: {report['batch_summary']['success_rate']:.1f}%")

    return 0 if report['batch_summary']['failed'] == 0 else 1

if __name__ == "__main__":
    from datetime import datetime
    exit_code = main()
    exit(exit_code)
```

## Interactive Workflow

### Jupyter Notebook Workflow

```python
# Cell 1: Setup and Imports
import sys
sys.path.append('..')

from examples.python_client.workflow_example import MCPClient
import pandas as pd
from IPython.display import display, JSON, HTML
import matplotlib.pyplot as plt
import json

# Initialize client
client = MCPClient()

print("🔧 MCP Client initialized")
print(f"📡 Server URL: {client.api_url}")

# Cell 2: Server Status Check
status = client.get_server_status()
display(JSON(status))

if status.get("status") == "running":
    print("✅ MCP Server is running")
    tools = client.get_available_tools()
    print(f"🛠️  Available tools: {len(tools.get('tools', {}))}")
else:
    print("❌ MCP Server is not accessible")

# Cell 3: Dataset Selection and Analysis
# Interactive dataset selection
dataset_path = input("Enter dataset path: ")
use_llm = input("Use LLM for analysis? (y/n): ").lower() == 'y'

print(f"🔍 Analyzing dataset: {dataset_path}")

analysis_result = client.analyze_dataset(dataset_path, use_llm=use_llm)

if analysis_result.get("status") == "success":
    print("✅ Analysis completed")

    # Display results
    result_data = analysis_result.get("result", {})

    if "summary" in result_data:
        summary = result_data["summary"]

        # Create summary DataFrame
        summary_df = pd.DataFrame([
            {"Metric": "Total Files", "Value": summary.get("total_files", 0)},
            {"Metric": "Total Directories", "Value": summary.get("total_directories", 0)},
            {"Metric": "Size (MB)", "Value": f"{summary.get('size_mb', 0):.2f}"},
            {"Metric": "Max Depth", "Value": summary.get("depth", 0)}
        ])

        display(summary_df)

        # File type distribution
        if "file_types" in summary:
            file_types = summary["file_types"]

            plt.figure(figsize=(10, 6))
            plt.bar(file_types.keys(), file_types.values())
            plt.title("File Type Distribution")
            plt.xlabel("File Extension")
            plt.ylabel("Count")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()

    # Display metadata if available
    if "normalized_metadata" in result_data:
        print("\n📋 Extracted Metadata:")
        display(JSON(result_data["normalized_metadata"]))

else:
    print(f"❌ Analysis failed: {analysis_result.get('message')}")

# Cell 4: File Mapping Configuration
print("🗂️  Configure file mappings:")

# Interactive file mapping
files_map = {}
data_types = ["recording", "behavior", "stimuli", "units"]

for data_type in data_types:
    file_path = input(f"Path for {data_type} data (or press Enter to skip): ")
    if file_path.strip():
        files_map[data_type] = file_path.strip()

print(f"📁 Configured {len(files_map)} file mappings:")
for data_type, path in files_map.items():
    print(f"   {data_type}: {path}")

# Cell 5: Conversion Execution
if files_map:
    print("⚙️  Starting conversion...")

    conversion_result = client.generate_conversion_script(files_map)

    if conversion_result.get("status") == "success":
        nwb_path = conversion_result.get("output_nwb_path")
        print(f"✅ Conversion completed: {nwb_path}")

        # Display conversion details
        result_data = conversion_result.get("result", {})

        if "script_content" in result_data:
            print("\n📜 Generated Script Preview:")
            script_lines = result_data["script_content"].split('\n')
            preview_lines = script_lines[:20]  # Show first 20 lines

            print("```python")
            for line in preview_lines:
                print(line)
            if len(script_lines) > 20:
                print(f"... ({len(script_lines) - 20} more lines)")
            print("```")
    else:
        print(f"❌ Conversion failed: {conversion_result.get('message')}")
        nwb_path = None
else:
    print("⚠️  No file mappings configured, skipping conversion")
    nwb_path = None

# Cell 6: Evaluation and Validation
if nwb_path:
    print("🔬 Evaluating NWB file...")

    evaluation_result = client.evaluate_nwb_file(nwb_path)

    if evaluation_result.get("status") == "success":
        eval_data = evaluation_result.get("result", {})
        summary = eval_data.get("summary", {})

        # Create evaluation summary
        eval_df = pd.DataFrame([
            {"Metric": "Overall Valid", "Value": "✅ Yes" if summary.get("overall_valid") else "❌ No"},
            {"Metric": "Quality Score", "Value": f"{summary.get('quality_score', 0)}/100"},
            {"Metric": "Total Errors", "Value": summary.get("total_errors", 0)},
            {"Metric": "Total Warnings", "Value": summary.get("total_warnings", 0)},
            {"Metric": "File Size (MB)", "Value": f"{summary.get('file_size_mb', 0):.2f}"}
        ])

        display(eval_df)

        # Quality score visualization
        quality_score = summary.get("quality_score", 0)

        fig, ax = plt.subplots(figsize=(8, 6))

        # Create a gauge-like visualization
        colors = ['red' if quality_score < 50 else 'orange' if quality_score < 80 else 'green']
        ax.bar(['Quality Score'], [quality_score], color=colors[0], alpha=0.7)
        ax.set_ylim(0, 100)
        ax.set_ylabel('Score')
        ax.set_title('NWB File Quality Score')

        # Add score text
        ax.text(0, quality_score + 5, f'{quality_score}/100',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.show()

        # Display detailed report if available
        if "report" in eval_data:
            print("\n📄 Detailed Validation Report:")
            print("```markdown")
            print(eval_data["report"][:1000])  # Show first 1000 characters
            if len(eval_data["report"]) > 1000:
                print("... (truncated)")
            print("```")

    else:
        print(f"❌ Evaluation failed: {evaluation_result.get('message')}")

# Cell 7: Workflow Summary
print("📊 Workflow Summary")

# Create workflow summary
workflow_data = {
    "dataset_path": dataset_path,
    "analysis_status": analysis_result.get("status") if 'analysis_result' in locals() else "not_run",
    "conversion_status": conversion_result.get("status") if 'conversion_result' in locals() else "not_run",
    "evaluation_status": evaluation_result.get("status") if 'evaluation_result' in locals() else "not_run",
    "output_nwb": nwb_path,
    "pipeline_state": client.pipeline_state
}

display(JSON(workflow_data))

# Save workflow results
import json
from datetime import datetime

workflow_summary = {
    "workflow_id": f"interactive_{int(datetime.now().timestamp())}",
    "timestamp": datetime.now().isoformat(),
    "dataset_path": dataset_path,
    "files_map": files_map,
    "results": {
        "analysis": analysis_result if 'analysis_result' in locals() else None,
        "conversion": conversion_result if 'conversion_result' in locals() else None,
        "evaluation": evaluation_result if 'evaluation_result' in locals() else None
    },
    "pipeline_state": client.pipeline_state
}

# Save to file
output_file = f"workflow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(workflow_summary, f, indent=2)

print(f"💾 Workflow summary saved: {output_file}")
```

## CLI Workflow Script

### Command-Line Interface

```bash
#!/bin/bash
# cli_workflow.sh - Command-line workflow for dataset conversion

set -e  # Exit on any error

# Configuration
MCP_SERVER_URL="http://127.0.0.1:8000"
OUTPUT_DIR="outputs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if MCP server is running
check_server() {
    log_info "Checking MCP server status..."

    if curl -s "$MCP_SERVER_URL/status" > /dev/null; then
        log_success "MCP server is running"
        return 0
    else
        log_error "MCP server is not accessible at $MCP_SERVER_URL"
        return 1
    fi
}

# Analyze dataset
analyze_dataset() {
    local dataset_dir="$1"
    local use_llm="${2:-false}"

    log_info "Analyzing dataset: $dataset_dir"

    local params=$(jq -n \
        --arg dir "$dataset_dir" \
        --argjson llm "$use_llm" \
        '{dataset_dir: $dir, use_llm: $llm}')

    local result=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$params" \
        "$MCP_SERVER_URL/tool/dataset_analysis")

    local status=$(echo "$result" | jq -r '.status')

    if [ "$status" = "success" ]; then
        log_success "Dataset analysis completed"

        # Extract and display summary
        local total_files=$(echo "$result" | jq -r '.result.summary.total_files // 0')
        local size_mb=$(echo "$result" | jq -r '.result.summary.size_mb // 0')

        echo "   📊 Files: $total_files"
        echo "   💾 Size: ${size_mb} MB"

        # Save analysis result
        echo "$result" > "$OUTPUT_DIR/analysis_${TIMESTAMP}.json"
        return 0
    else
        local message=$(echo "$result" | jq -r '.message')
        log_error "Analysis failed: $message"
        return 1
    fi
}

# Convert dataset
convert_dataset() {
    local files_map_file="$1"

    log_info "Starting conversion..."

    if [ ! -f "$files_map_file" ]; then
        log_error "Files map file not found: $files_map_file"
        return 1
    fi

    # Read metadata and files map
    local metadata=$(cat "$OUTPUT_DIR/analysis_${TIMESTAMP}.json" | jq '.result.normalized_metadata // {}')
    local files_map=$(cat "$files_map_file")

    local params=$(jq -n \
        --argjson metadata "$metadata" \
        --argjson files_map "$files_map" \
        '{normalized_metadata: $metadata, files_map: $files_map}')

    local result=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$params" \
        "$MCP_SERVER_URL/tool/conversion_orchestration")

    local status=$(echo "$result" | jq -r '.status')

    if [ "$status" = "success" ]; then
        local nwb_path=$(echo "$result" | jq -r '.output_nwb_path')
        log_success "Conversion completed: $nwb_path"

        # Save conversion result
        echo "$result" > "$OUTPUT_DIR/conversion_${TIMESTAMP}.json"
        echo "$nwb_path" > "$OUTPUT_DIR/nwb_path_${TIMESTAMP}.txt"
        return 0
    else
        local message=$(echo "$result" | jq -r '.message')
        log_error "Conversion failed: $message"
        return 1
    fi
}

# Evaluate NWB file
evaluate_nwb() {
    local nwb_path_file="$OUTPUT_DIR/nwb_path_${TIMESTAMP}.txt"

    if [ ! -f "$nwb_path_file" ]; then
        log_error "NWB path file not found: $nwb_path_file"
        return 1
    fi

    local nwb_path=$(cat "$nwb_path_file")

    log_info "Evaluating NWB file: $nwb_path"

    local params=$(jq -n \
        --arg path "$nwb_path" \
        --argjson report true \
        '{nwb_path: $path, generate_report: $report}')

    local result=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$params" \
        "$MCP_SERVER_URL/tool/evaluate_nwb_file")

    local status=$(echo "$result" | jq -r '.status')

    if [ "$status" = "success" ]; then
        local overall_valid=$(echo "$result" | jq -r '.result.summary.overall_valid')
        local quality_score=$(echo "$result" | jq -r '.result.summary.quality_score')
        local total_errors=$(echo "$result" | jq -r '.result.summary.total_errors')

        if [ "$overall_valid" = "true" ]; then
            log_success "NWB file validation passed"
        else
            log_warning "NWB file has validation issues"
        fi

        echo "   🏆 Quality Score: $quality_score/100"
        echo "   ❌ Errors: $total_errors"

        # Save evaluation result
        echo "$result" > "$OUTPUT_DIR/evaluation_${TIMESTAMP}.json"

        # Save detailed report
        echo "$result" | jq -r '.result.report // ""' > "$OUTPUT_DIR/validation_report_${TIMESTAMP}.md"

        return 0
    else
        local message=$(echo "$result" | jq -r '.message')
        log_warning "Evaluation failed: $message"
        return 1
    fi
}

# Generate workflow summary
generate_summary() {
    log_info "Generating workflow summary..."

    local summary_file="$OUTPUT_DIR/workflow_summary_${TIMESTAMP}.json"

    # Combine all results
    jq -n \
        --arg timestamp "$TIMESTAMP" \
        --arg dataset_dir "$DATASET_DIR" \
        --slurpfile analysis "$OUTPUT_DIR/analysis_${TIMESTAMP}.json" \
        --slurpfile conversion "$OUTPUT_DIR/conversion_${TIMESTAMP}.json" \
        --slurpfile evaluation "$OUTPUT_DIR/evaluation_${TIMESTAMP}.json" \
        '{
            workflow_id: ("cli_" + $timestamp),
            timestamp: now | strftime("%Y-%m-%dT%H:%M:%SZ"),
            dataset_dir: $dataset_dir,
            results: {
                analysis: $analysis[0],
                conversion: $conversion[0],
                evaluation: $evaluation[0]
            }
        }' > "$summary_file"

    log_success "Workflow summary saved: $summary_file"
}

# Main workflow function
main() {
    echo "🚀 Starting CLI workflow for agentic neurodata conversion"

    # Parse command line arguments
    DATASET_DIR="$1"
    FILES_MAP="$2"
    USE_LLM="${3:-false}"

    if [ -z "$DATASET_DIR" ] || [ -z "$FILES_MAP" ]; then
        echo "Usage: $0 <dataset_dir> <files_map.json> [use_llm]"
        echo ""
        echo "Example:"
        echo "  $0 /path/to/dataset files_map.json true"
        echo ""
        echo "files_map.json format:"
        echo '  {"recording": "/path/to/recording.dat", "behavior": "/path/to/behavior.csv"}'
        exit 1
    fi

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    # Check server
    if ! check_server; then
        exit 1
    fi

    # Run workflow steps
    if analyze_dataset "$DATASET_DIR" "$USE_LLM"; then
        if convert_dataset "$FILES_MAP"; then
            evaluate_nwb
            generate_summary

            log_success "🎉 Workflow completed successfully!"
            echo "   📁 Output directory: $OUTPUT_DIR"
            echo "   📊 Summary: $OUTPUT_DIR/workflow_summary_${TIMESTAMP}.json"
        fi
    fi
}

# Run main function with all arguments
main "$@"
```

These workflow examples demonstrate different approaches to using the agentic neurodata conversion system:

1. **Basic Python Workflow**: Complete programmatic workflow with error handling
2. **Batch Processing**: Parallel processing of multiple datasets
3. **Interactive Jupyter**: Step-by-step interactive workflow with visualizations
4. **CLI Script**: Command-line workflow for automation and scripting

Each example shows best practices for error handling, progress reporting, and result management.
