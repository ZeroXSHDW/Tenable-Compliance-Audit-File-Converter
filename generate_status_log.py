import os
import sys
import glob
import json
import logging
import re
import time
from datetime import datetime
from audit_utils import cached_config, setup_logger, validate_json_file

__version__ = "2.0.0"
__changelog__ = """
2.0.0:
- Initial implementation for generating status logs
- Integrated with audit_utils for logging and config
- Fixed NameError by importing sys
- Fixed NameError by using dict instead of Dict
- Added block count summary from extract logs
- Enhanced block count logging for all files
- Added retry logic for file access errors
"""

def generate_status(output_dir: str, config: dict, logger: logging.Logger) -> None:
    """Generate a status log for processed files, including block counts."""
    try:
        output_dir = os.path.normpath(output_dir)
        if not os.path.isdir(output_dir):
            logger.error(f"Output directory {output_dir} does not exist or is not a directory")
            return

        json_files = glob.glob(os.path.join(output_dir, "json", "**", "*.json"), recursive=True)
        xlsx_files = glob.glob(os.path.join(output_dir, "xlsx", "**", "*.xlsx"), recursive=True)
        log_file = os.path.join(config['directories']['debug_dir'], "extract_parse_status_log.txt")
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n# Status Log ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
            f.write(f"Output Directory: {output_dir}\n")
            f.write(f"JSON Files Found: {len(json_files)}\n")
            f.write(f"XLSX Files Found: {len(xlsx_files)}\n")
            
            for json_file in json_files:
                retry_count = 3
                for attempt in range(retry_count):
                    try:
                        if not validate_json_file(json_file, logger):
                            f.write(f"ERROR - Invalid JSON file {json_file}: Invalid format\n")
                            break
                        
                        with open(json_file, 'r', encoding='utf-8') as jf:
                            items = json.load(jf)
                        item_count = len(items)
                        f.write(f"INFO - JSON file {json_file}: {item_count} items\n")
                        
                        filename = os.path.basename(json_file).replace("extracted_data_", "").replace(".json", "")
                        extract_log = os.path.join(
                            config['directories']['debug_dir'], "audit_logs", f"extract_log_{filename}.txt"
                        )
                        if not os.path.exists(extract_log):
                            # Keep compatibility with older flat debug logs.
                            extract_log = os.path.join(config['directories']['debug_dir'], f"extract_log_{filename}.txt")
                        if os.path.exists(extract_log):
                            with open(extract_log, 'r', encoding='utf-8') as ef:
                                content = ef.read()
                                block_match = re.search(r"Block counts: custom_item=(\d+), item=(\d+), variable=(\d+)", content)
                                if block_match:
                                    custom_item_count = int(block_match.group(1))
                                    item_count = int(block_match.group(2))
                                    variable_count = int(block_match.group(3))
                                    f.write(f"INFO - Block counts for {json_file}: custom_item={custom_item_count}, item={item_count}, variable={variable_count}, total={custom_item_count + item_count + variable_count}\n")
                                else:
                                    f.write(f"WARN - No block counts found in {extract_log}\n")
                        else:
                            f.write(f"WARN - Extract log {extract_log} not found\n")
                        break
                    except (PermissionError, IOError) as e:
                        if attempt < retry_count - 1:
                            logger.warning(f"Failed to access {json_file} on attempt {attempt + 1}: {str(e)}. Retrying...")
                            time.sleep(1)
                        else:
                            logger.error(f"Failed to process JSON file {json_file} after {retry_count} attempts: {str(e)}")
                            f.write(f"ERROR - Failed to process JSON file {json_file}: {str(e)}\n")
            
            for xlsx_file in xlsx_files:
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(xlsx_file)
                    ws = wb.active
                    row_count = sum(1 for _ in ws.rows) - 1  # Exclude header
                    f.write(f"INFO - XLSX file {xlsx_file}: {row_count} rows\n")
                    wb.close()
                except Exception as e:
                    logger.error(f"Failed to process XLSX file {xlsx_file}: {str(e)}")
                    f.write(f"ERROR - Invalid XLSX file {xlsx_file}: {str(e)}\n")

            valid_json_rows = 0
            for json_file in json_files:
                if not validate_json_file(json_file, logger):
                    continue
                try:
                    with open(json_file, 'r', encoding='utf-8') as json_handle:
                        valid_json_rows += len(json.load(json_handle))
                except (OSError, TypeError, ValueError) as e:
                    logger.error(f"Failed to count JSON rows in {json_file}: {str(e)}")

            valid_xlsx_rows = 0
            for xlsx_file in xlsx_files:
                if not os.path.exists(xlsx_file):
                    continue
                try:
                    workbook = openpyxl.load_workbook(xlsx_file, read_only=True)
                    valid_xlsx_rows += max(sum(1 for _ in workbook.active.rows) - 1, 0)
                    workbook.close()
                except Exception as e:
                    logger.error(f"Failed to count XLSX rows in {xlsx_file}: {str(e)}")

            f.write(
                f"Summary - JSON Files: {len(json_files)}, XLSX Files: {len(xlsx_files)}, "
                f"Valid Data Rows (json): {valid_json_rows}, "
                f"Valid Data Rows (xlsx): {valid_xlsx_rows}\n"
            )
        
        logger.info(f"Status log appended to {log_file}")
    
    except Exception as e:
        logger.error(f"Failed to generate status log: {str(e)}")

def main() -> None:
    """Main function to generate status log."""
    import argparse
    parser = argparse.ArgumentParser(description="Generate status log for processed audit files.")
    parser.add_argument("output_dir", help="Directory containing output files")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    try:
        config = cached_config()
        debug_dir = config['directories']['debug_dir']
        os.makedirs(debug_dir, exist_ok=True)
        
        logger = setup_logger(
            "status_log",
            os.path.join(debug_dir, "status_log_main_log.txt"),
            config
        )
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        
        generate_status(args.output_dir, config, logger)
    
    except Exception as e:
        logger.error(f"Status log generation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
