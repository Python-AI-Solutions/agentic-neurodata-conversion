#!/bin/bash

# Setup script for NWB conversion project with CatalystNeuro conversions
# This script sets up the complete environment including DataLad and conversions

set -e

echo "🚀 NWB Conversion Project Setup"
echo "================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base directory - use current directory if already in nwb-conversion-project
if [[ "$(basename "$(pwd)")" == "nwb-conversion-project" ]]; then
    BASE_DIR="$(pwd)"
else
    BASE_DIR="$(pwd)/nwb-conversion-project"
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check for pixi
if ! command_exists pixi; then
    print_error "pixi is not installed. Please install it first."
    echo "Visit: https://pixi.sh/latest/"
    exit 1
fi

# Check for git
if ! command_exists git; then
    print_error "git is not installed. Please install it first."
    exit 1
fi

# Step 1: Ensure DataLad is available through pixi
echo ""
echo "📦 Step 1: Setting up DataLad..."
echo "---------------------------------"

# Check if datalad is already available
if pixi run datalad --version >/dev/null 2>&1; then
    print_status "DataLad is already available"
else
    print_warning "DataLad not found in pixi environment"
    echo "Installing DataLad..."
    pixi add datalad

    if pixi run datalad --version >/dev/null 2>&1; then
        print_status "DataLad installed successfully"
    else
        print_warning "Could not install DataLad via pixi, trying pip..."
        pixi run pip install datalad
    fi
fi

# Step 2: Initialize DataLad datasets
echo ""
echo "📊 Step 2: Initializing DataLad datasets..."
echo "-------------------------------------------"

# Create main data directory as DataLad dataset
DATA_DIR="${BASE_DIR}/etl/data"

if [ -d "${DATA_DIR}/.datalad" ]; then
    print_status "DataLad dataset already exists at ${DATA_DIR}"
else
    echo "Creating DataLad dataset..."
    pixi run datalad create -c text2git "${DATA_DIR}"
    print_status "DataLad dataset created"
fi

# Step 3: Install neuroconv
echo ""
echo "🧠 Step 3: Installing neuroconv..."
echo "-----------------------------------"

if pixi run python -c "import neuroconv" 2>/dev/null; then
    print_status "neuroconv is already installed"
else
    echo "Installing neuroconv and dependencies..."
    pixi run pip install neuroconv
    print_status "neuroconv installed"
fi

# Step 4: Run the Python script to clone conversions
echo ""
echo "📥 Step 4: Cloning CatalystNeuro conversions..."
echo "-----------------------------------------------"

# No need to specify base-path if we're already in the right directory
if [[ "${BASE_DIR}" == "$(pwd)" ]]; then
    pixi run python install_catalystneuro_conversions.py
else
    pixi run python install_catalystneuro_conversions.py --base-path "${BASE_DIR}"
fi

# Step 5: Create subdatasets for large conversion repos (optional)
echo ""
echo "🔗 Step 5: Setting up DataLad subdatasets..."
echo "---------------------------------------------"

cd "${DATA_DIR}"

# Add conversions as subdatasets
CONVERSIONS_DIR="${DATA_DIR}/conversions"
if [ -d "${CONVERSIONS_DIR}" ]; then
    for conversion in "${CONVERSIONS_DIR}"/*-to-nwb; do
        if [ -d "$conversion" ]; then
            conversion_name=$(basename "$conversion")

            # Check if it's already a subdataset
            if [ ! -d "${conversion}/.datalad" ]; then
                echo "Adding ${conversion_name} as subdataset..."
                pixi run datalad create -c text2git "${conversion}"
            fi
        fi
    done
    print_status "Subdatasets configured"
fi

cd - > /dev/null

# Step 6: Create example configuration files
echo ""
echo "📝 Step 6: Creating configuration files..."
echo "------------------------------------------"

# Create a pixi.toml for the project
cat > "${BASE_DIR}/pixi.toml" << 'EOF'
[project]
name = "nwb-conversion-project"
version = "0.1.0"
description = "NWB conversion project with CatalystNeuro tools"
authors = ["Your Name <your.email@example.com>"]
channels = ["conda-forge", "pytorch"]
platforms = ["linux-64", "osx-64", "osx-arm64"]

[dependencies]
python = ">=3.9,<3.12"
pip = "*"
git = "*"
jupyterlab = "*"
pandas = "*"
numpy = "*"
matplotlib = "*"
h5py = "*"
pynwb = "*"

[feature.datalad.dependencies]
datalad = "*"
git-annex = "*"

[environments]
default = ["datalad"]

[tasks]
install-neuroconv = "pip install neuroconv"
install-conversions = "python install_catalystneuro_conversions.py"
jupyter = "jupyter lab"
test = "python -m pytest tests/"
EOF

print_status "pixi.toml created"

# Create .gitignore
cat > "${BASE_DIR}/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# DataLad
.datalad/
.git-annex/

# Data files
*.nwb
*.h5
*.hdf5
*.mat
*.dat

# IDEs
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Jupyter
.ipynb_checkpoints/

# Logs
*.log

# Pixi
.pixi/
EOF

print_status ".gitignore created"

# Step 7: Final summary
echo ""
echo "======================================"
echo "✨ Setup Complete!"
echo "======================================"
echo ""
echo "Project structure created at: ${BASE_DIR}"
echo ""
echo "📁 Directory Structure:"
echo "  └── etl/"
echo "      ├── workflows/         - Data processing workflows"
echo "      ├── data/             - DataLad-managed data"
echo "      │   ├── specifications/"
echo "      │   ├── conversions/   - CatalystNeuro conversions"
echo "      │   └── pre-existing-conversions/"
echo "      ├── prompt-input-data/ - LLM prompt data"
echo "      └── evaluation-data/   - Test datasets"
echo "  └── llm-assisted-conversion-tool/"
echo "      ├── prompt/           - LLM prompts"
echo "      └── cli/              - CLI interface"
echo "  └── tests/"
echo "      ├── unit/             - Unit tests"
echo "      └── evaluation/       - Evaluation tests"
echo ""
echo "🎯 Next Steps:"
echo "1. cd ${BASE_DIR}"
echo "2. Explore conversions: ls etl/data/conversions/"
echo "3. Run Jupyter: pixi run jupyter"
echo "4. Create your first conversion using the cookiecutter template"
echo ""
echo "📚 Resources:"
echo "- CatalystNeuro Docs: https://neuroconv.readthedocs.io/"
echo "- NWB Overview: https://www.nwb.org/"
echo "- DataLad Docs: https://www.datalad.org/"
