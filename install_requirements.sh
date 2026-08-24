#!/usr/bin/env bash
# install_requirements.sh
# Installs Python dependencies for the Tenable Compliance Audit File Converter.
# Portable across macOS (BSD) and Linux — no grep -P or bc required.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure Python 3.11 or higher is installed (portable version parse)
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
MAJOR="$(python3 -c 'import sys; print(sys.version_info[0])')"
MINOR="$(python3 -c 'import sys; print(sys.version_info[1])')"

if [[ "$MAJOR" -lt 3 ]] || { [[ "$MAJOR" -eq 3 ]] && [[ "$MINOR" -lt 11 ]]; }; then
    echo "Error: Python 3.11 or higher is required (found ${PYTHON_VERSION})."
    exit 1
fi

# Ensure pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install pip for Python 3."
    exit 1
fi

# Install runtime dependencies from requirements.txt (the operator-facing contract)
echo "Installing Python dependencies from requirements.txt..."
python3 -m pip install --disable-pip-version-check -r requirements.txt

# Verify installation
echo "Verifying installed packages..."
pip3 show openpyxl chardet tqdm beautifulsoup4

echo "Installation complete. You can now run the project scripts."
echo "Tip: quote paths that contain spaces, e.g.:"
echo "  python3 execute_all_scripts.py \"audit files\" \"output files\" --verbose"
