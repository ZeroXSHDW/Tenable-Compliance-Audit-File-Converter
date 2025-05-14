import os
import logging
from datetime import datetime
import openpyxl
from typing import List, Tuple

__version__ = "1.0.0"
__changelog__ = """
1.0.0:
- Initial implementation to scan XLSX files for rows containing 'Nessus'
- Outputs results to debug/nessus_rows_log.txt
- Logs file processing and match details
"""

def setup_logger(debug_dir: str) -> logging.Logger:
    """Set up logger for Nessus row scanning."""
    os.makedirs(debug_dir, exist_ok=True)
    log_file = os.path.join(debug_dir, "nessus_rows_log.txt")
    logger = logging.getLogger("nessus_rows")
    logger.setLevel(logging.INFO)
    # Clear existing handlers to avoid duplicate logs
    logger.handlers = []
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger

def find_nessus_rows(xlsx_file: str, logger: logging.Logger) -> List[Tuple[int, List[str]]]:
    """Scan an XLSX file for rows containing 'Nessus' and return matching rows."""
    matches = []
    try:
        wb = openpyxl.load_workbook(xlsx_file, read_only=True)
        for sheet in wb:
            logger.info(f"Scanning sheet '{sheet.title}' in {xlsx_file}")
            for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                row_values = [str(cell) if cell is not None else "" for cell in row]
                # Check if 'Nessus' is in any cell (case-insensitive)
                if any("nessus" in val.lower() for val in row_values):
                    matches.append((row_idx, row_values))
        wb.close()
        return matches
    except Exception as e:
        logger.error(f"Failed to process {xlsx_file}: {str(e)}")
        return []

def main() -> None:
    """Main function to scan XLSX files for rows containing 'Nessus'."""
    # Define directories
    base_dir = os.getcwd()
    xlsx_dir = os.path.join(base_dir, "output files", "xlsx")
    debug_dir = os.path.join(base_dir, "debug")

    # Set up logger
    logger = setup_logger(debug_dir)
    logger.info(f"Starting Nessus row scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Scanning XLSX files in {xlsx_dir}")

    # Verify xlsx_dir exists
    if not os.path.isdir(xlsx_dir):
        logger.error(f"XLSX directory {xlsx_dir} does not exist")
        print(f"Error: XLSX directory {xlsx_dir} does not exist")
        return

    # Find all XLSX files
    xlsx_files = [f for f in os.listdir(xlsx_dir) if f.endswith(".xlsx")]
    if not xlsx_files:
        logger.warning(f"No XLSX files found in {xlsx_dir}")
        print(f"No XLSX files found in {xlsx_dir}")
        return

    logger.info(f"Found {len(xlsx_files)} XLSX files to scan")
    total_matches = 0

    # Process each XLSX file
    for xlsx_file in sorted(xlsx_files):
        full_path = os.path.join(xlsx_dir, xlsx_file)
        logger.info(f"Processing {xlsx_file}")
        matches = find_nessus_rows(full_path, logger)
        
        if matches:
            logger.info(f"Found {len(matches)} rows with 'Nessus' in {xlsx_file}:")
            for row_idx, row_values in matches:
                logger.info(f"  Row {row_idx}: {row_values}")
            total_matches += len(matches)
        else:
            logger.info(f"No rows with 'Nessus' found in {xlsx_file}")

    logger.info(f"Scan complete: {total_matches} rows found across {len(xlsx_files)} files")
    print(f"Scan complete: {total_matches} rows found. Check {os.path.join(debug_dir, 'nessus_rows_log.txt')} for details")

if __name__ == "__main__":
    main()