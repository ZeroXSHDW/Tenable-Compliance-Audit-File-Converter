# Tenable Compliance Audit File Converter

![Tenable Compliance Audit File Converter](assets/banner.jpg)

## Overview

Converts Tenable Compliance Audit Files (`audits.tar.gz` from [Tenable](https://www.tenable.com/downloads/download-all-compliance-audit-files)) into formatted XLSX and HTML documents. The pipeline prioritizes the `description` field and mirrors the input folder structure.

### Features
- **Input**: `audit files/<platform>/*.audit` (e.g., `audit files/AS400/ibm_v7_r2_iseries.audit`).
- **Outputs**:
  - JSON: `output files/json/<platform>/*.json`.
  - XLSX: `output files/xlsx/<platform>/*.xlsx` (bold headers, auto-sized columns, text wrapping, borders, alternating colors, frozen top row).
  - HTML: `output files/html/<platform>/*.html`.
- **Logging**: Logs in `debug/` (e.g., `execute_all_log.txt`, `xlsx_conversion_log.txt`).
- **Statistics**: Field accuracy and XLSX conversion metrics.

## Prerequisites
- Python 3.11+
- Tenable `audits.tar.gz`

## Setup

1. **Clone from GitHub**:
   ```bash
   git clone https://github.com/ZeroXSHDW/Tenable-Compliance-Audit-File-Converter.git
   cd Tenable-Compliance-Audit-File-Converter
   ```

2. **Set Permissions**:
   ```bash
   chmod +x install_requirements.sh
   chmod 644 *.py config.json
   ```

3. **Install Dependencies**:
   ```bash
   pip3 install -r requirements.txt
   # or (macOS / Linux — uses python3 version checks, no grep -P / bc)
   ./install_requirements.sh
   ```

4. **Extract Audit Files**:
   - Download `audits.tar.gz` from [Tenable](https://www.tenable.com/downloads/download-all-compliance-audit-files).
   - Follow `audit files/INSTRUCTIONS.txt` to place and extract it into `audit files/`.

## Usage

**Always quote paths that contain spaces** (`audit files`, `output files`).

```bash
python3 execute_all_scripts.py "audit files" "output files" --verbose
```

- Creates `output files/{json,xlsx,html,csv}`, `debug/audit_logs`, and `config` folders as needed.
- Processes `.audit` files into JSON, XLSX, and HTML.
- See CLI help: `python3 execute_all_scripts.py --help`

Without quotes, the shell splits on spaces and the script will receive wrong arguments.

## Paths with spaces

| Do | Don't |
| :--- | :--- |
| `python3 execute_all_scripts.py "audit files" "output files"` | `python3 execute_all_scripts.py audit files output files` |
| `ls -l "audit files"/*` or `ls -l audit\ files/*` | `ls -l audit files/*` |

## Outputs
- **JSON**: `output files/json/AS400/extracted_data_*.json`
- **XLSX**: `output files/xlsx/AS400/extracted_*.xlsx` (formatted)
- **HTML**: `output files/html/AS400/extracted_*.html`
- **Logs**: `debug/execute_all_log.txt`, `debug/xlsx_conversion_log.txt`, `debug/field_accuracy_log.txt`, `debug/audit_logs/*.txt`, `debug/extract_parse_status_log.txt`

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
        "key_fields": ["description", "type"]
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
  cat debug/execute_all_log.txt
  ./install_requirements.sh
  ```
- **No Audit Files**:
  ```bash
  ls -l "audit files"/*
  ```
- **XLSX Formatting**:
  ```bash
  grep __version__ audit_extract_helper.py
  ```
  Should be `2.0.5`.
- **Permissions**:
  ```bash
  chmod -R u+rw .
  ```

## License
This project is licensed under the Apache 2.0 License. See `LICENSE` file for details.
