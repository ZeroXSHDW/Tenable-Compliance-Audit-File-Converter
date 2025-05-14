# Tenable Compliance Audit File Converter

## Overview

Converts Tenable Compliance Audit Files (`audits.tar.gz` from [Tenable](https://www.tenable.com/downloads/download-all-compliance-audit-files)) into formatted XLSX and HTML documents. The pipeline prioritizes the `description` field, mirrors the input folder structure, and generates a master HTML summary.

### Features
- **Input**: `audit files/<platform>/*.audit` (e.g., `audit files/AS400/ibm_v7_r2_iseries.audit`).
- **Outputs**:
  - JSON: `output files/json/<platform>/*.json`.
  - XLSX: `output files/xlsx/<platform>/*.xlsx` (bold headers, auto-sized columns, text wrapping, borders, alternating colors, frozen top row).
  - HTML: `output files/html/<platform>/*.html`.
  - Master HTML: `output files/master_output.html` (links and embeds all HTML tables).
- **Logging**: Logs in `debug/` (e.g., `execute_all_log.txt`, `xlsx_conversion_log.txt`).
- **Statistics**: Field accuracy and XLSX conversion metrics.

## Prerequisites
- Python 3.11+
- Tenable `audits.tar.gz`

## Setup

1. **Place Scripts**:
   In `~/Documents/Oracle`:
   - `execute_all_scripts.py`
   - `audit_extract_helper.py`
   - `data_extract_to_json.py`
   - `audit_parse_detector.py`
   - `generate_status_log.py`
   - `generate_master_html.py`
   - `config.json`
   - `install_requirements.sh`

2. **Set Permissions**:
   ```bash
   chmod +x ~/Documents/Oracle/install_requirements.sh
   chmod 644 ~/Documents/Oracle/*.py ~/Documents/Oracle/config.json
   ```

3. **Install Dependencies**:
   ```bash
   cd ~/Documents/Oracle
   ./install_requirements.sh
   ```

4. **Extract Audit Files**:
   ```bash
   mkdir -p ~/Documents/Oracle/audit\ files
   tar -xzf audits.tar.gz -C ~/Documents/Oracle/audit\ files
   ```

5. **Create Folders**:
   ```bash
   mkdir -p ~/Documents/Oracle/output\ files/{json,xlsx,html,csv} ~/Documents/Oracle/debug/audit_logs ~/Documents/Oracle/config
   ```

## Usage

1. **Convert Audit Files**:
   ```bash
   cd ~/Documents/Oracle
   python execute_all_scripts.py "audit files" "output files" --verbose
   ```

2. **Generate Master HTML**:
   ```bash
   python generate_master_html.py "output files"
   ```

## Outputs
- **JSON**: `output files/json/AS400/extracted_data_*.json`
- **XLSX**: `output files/xlsx/AS400/extracted_*.xlsx` (formatted)
- **HTML**: `output files/html/AS400/extracted_*.html`
- **Master HTML**: `output files/master_output.html`
- **Logs**: `debug/execute_all_log.txt`, `debug/xlsx_conversion_log.txt`, `debug/field_accuracy_log.txt`, `debug/audit_logs/*.txt`, `debug/master_html_log.txt`

## Configuration
`config.json`:
```json
{
    "directories": {
        "audit_dir": "audit files",
        "output_dir": "output files",
        "debug_dir": "debug",
        "config_file": "config.json"
    },
    "preprocessing": {
        "key_fields": ["description", "type", ...]
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(levelname)s - %(message)s"
    },
    "output": {
        "output_format": ["xlsx", "html"],
        "parallel_processing": true
    }
}
```

## Troubleshooting
- **Errors**:
  ```bash
  cat ~/Documents/Oracle/debug/execute_all_log.txt
  ```
  Check dependencies:
  ```bash
  ./install_requirements.sh
  ```
- **No Audit Files**:
  ```bash
  ls -l ~/Documents/Oracle/audit\ files/*
  ```
- **XLSX Formatting**:
  Verify `audit_extract_helper.py` version:
  ```bash
  grep __version__ ~/Documents/Oracle/audit_extract_helper.py
  ```
  Should be `2.0.4`.
- **Permissions**:
  ```bash
  chmod -R u+rw ~/Documents/Oracle
  ```

## License
MIT License. See [LICENSE](LICENSE).