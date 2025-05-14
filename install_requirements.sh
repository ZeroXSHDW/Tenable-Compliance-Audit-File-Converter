#!/bin/bash
# install_requirements.sh
# Installs Python dependencies for the Tenable Compliance Audit File Converter

# Ensure Python 3.11 or higher is installed
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
if [[ -z "$PYTHON_VERSION" || $(echo "$PYTHON_VERSION < 3.11" | bc -l) -eq 1 ]]; then
    echo "Error: Python 3.11 or higher is required."
    exit 1
fi

# Ensure pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install pip for Python 3."
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
pip3 install openpyxl==3.1.3 chardet tqdm beautifulsoup4

# Verify installation
echo "Verifying installed packages..."
pip3 show openpyxl chardet tqdm beautifulsoup4

echo "Installation complete. You can now run the project scripts."