import os
import sys
import glob
import json
import logging
import argparse
import shutil
import time
from typing import Dict, Set
from datetime import datetime
from audit_utils import atomic_write_text, cached_config, setup_logger, get_config_checksum, verify_config_unchanged
from data_extract_to_json import extract_to_json
from audit_extract_helper import process_file
from audit_parse_detector import detect_missing_keys
from generate_status_log import generate_status

__version__ = "2.1.0"
__changelog__ = """
2.0.0:
- Initial implementation for executing all audit processing scripts
- Integrated with audit_utils for logging and config management
- Added parallel processing for XLSX generation
- Removed CSV output, enforced XLSX
- Added config checksum verification
- Added interactive config updates for multi-platform audit files
- Processes subfolders in audit directory
- Saves platform-specific temporary configs
- Enhanced logging for interactive field updates
2.0.1:
- Fixed handling of empty detected fields and undefined config['fields']
- Improved error handling in interactive_config_update
2.0.2:
- Removed interactive prompts, automatically uses detected fields
- Fixed 'config_file' error by setting default config path
- Ensured config['directories'] and config['fields'] are initialized
2.0.3:
- Added /config/ folder for platform-specific configs
- Separated JSON (/output files/json), XLSX (/output files/xlsx), CSV (/output files/csv)
- Added field accuracy logging to debug/field_accuracy_log.txt
- Limited screen output to status messages
- Added field correctness statistics
2.0.4:
- Moved audit file logs to debug/audit_logs
- Added XLSX conversion logging and statistics
- Fixed JSON file readability issues
2.0.5:
- Initialize logger before config loading
- Create default config.json if missing
- Improved error handling for missing config
2.0.6:
- Fixed 'true' to 'True' in default config for parallel_processing
2.0.7:
- Enforced 'description' as master key in all outputs
- Mirrored audit files folder structure in output files
- Added HTML output generation
2.0.8:
- Fixed TypeError in setup_field_accuracy_logger by providing default logging format
- Reordered main() to load config before logger setup
2.0.9:
- Removed master HTML generation
- Automatically create all folders except audit files
2.1.0:
- Updated to scan audit files/portal_audits/<platform>/*.audit for platform subfolders
- Removed all Nessus and master HTML references
"""

def setup_logging(debug_dir: str, config: Dict = None) -> logging.Logger:
    """Set up logger for execute_all_scripts."""
    os.makedirs(debug_dir, exist_ok=True)
    log_file = os.path.join(debug_dir, "execute_all_log.txt")
    config = config or {"logging": {"level": "INFO", "format": "%(asctime)s - %(levelname)s - %(message)s"}}
    return setup_logger("execute_all", log_file, config)

def setup_field_accuracy_logger(debug_dir: str, config: Dict = None) -> logging.Logger:
    """Set up logger for field accuracy."""
    os.makedirs(debug_dir, exist_ok=True)
    log_file = os.path.join(debug_dir, "field_accuracy_log.txt")
    logger = logging.getLogger("field_accuracy")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, encoding='utf-8')
    default_format = "%(asctime)s - %(levelname)s - %(message)s"
    log_format = config['logging']['format'] if config and 'logging' in config else default_format
    handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(handler)
    return logger

def create_default_config(config_path: str, logger: logging.Logger) -> Dict:
    """Create a default config.json if it doesn't exist."""
    default_config = {
        "directories": {
            "audit_dir": "audit files",
            "output_dir": "output files",
            "debug_dir": "debug",
            "config_file": "config.json"
        },
        "preprocessing": {
            "key_fields": [
                "description", "type", "cmd", "value", "file_path", "registry_key",
                "sql_query", "policy_name", "check_type", "systemvalue", "reg_key",
                "wmi_request", "info", "solution", "reference", "see_also"
            ]
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(levelname)s - %(message)s"
        },
        "output": {
            "output_format": ["xlsx", "html"],
            "parallel_processing": True
        }
    }
    try:
        os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
        atomic_write_text(config_path, json.dumps(default_config, indent=4))
        logger.info(f"Created default config at {config_path}")
        return default_config
    except Exception as e:
        logger.error(f"Failed to create default config at {config_path}: {str(e)}")
        raise

def save_platform_config(config: Dict, platform: str, config_dir: str, logger: logging.Logger) -> str:
    """Save platform-specific config file."""
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, f"config_{platform}.json")
    atomic_write_text(config_path, json.dumps(config, indent=4))
    checksum = get_config_checksum(config_path)
    logger.info(f"Saved platform config {config_path} with checksum {checksum}")
    return config_path

def detect_fields(audit_file: str, logger: logging.Logger) -> Set[str]:
    """Detect fields in an audit file."""
    try:
        missing_keys, all_keys = detect_missing_keys(audit_file, set())
        logger.info(f"Detected fields in {audit_file}: {sorted(all_keys)}")
        return all_keys
    except Exception as e:
        logger.error(f"Failed to detect fields in {audit_file}: {str(e)}")
        return set()

def update_config_fields(audit_file: str, platform: str, config: Dict, logger: logging.Logger, field_logger: logging.Logger) -> Dict:
    """Automatically update config fields, ensuring 'description' is included."""
    detected_fields = detect_fields(audit_file, logger)
    
    # Initialize config['fields'] and config['preprocessing']['key_fields']
    if 'fields' not in config:
        config['fields'] = []
    if 'preprocessing' not in config:
        config['preprocessing'] = {}
    if 'key_fields' not in config['preprocessing']:
        config['preprocessing']['key_fields'] = []
    
    # Ensure 'description' is always included
    if detected_fields:
        config['fields'] = ['description'] + sorted([f for f in detected_fields if f != 'description'])
        logger.info(f"Automatically updated config for {audit_file}: fields={config['fields']}")
    else:
        config['fields'] = ['description'] + config['fields']
        logger.warning(f"No fields detected for {audit_file}, using existing fields with description: {config['fields']}")
    
    # Log field accuracy
    expected_fields = set(config['preprocessing']['key_fields'])
    detected_field_set = set(config['fields'])
    missing_fields = expected_fields - detected_field_set
    unexpected_fields = detected_field_set - expected_fields
    
    field_logger.info(f"Field accuracy for {audit_file}:")
    field_logger.info(f"  Detected fields ({len(detected_field_set)}): {sorted(detected_field_set)}")
    field_logger.info(f"  Expected fields ({len(expected_fields)}): {sorted(expected_fields)}")
    if missing_fields:
        field_logger.warning(f"  Missing fields ({len(missing_fields)}): {sorted(missing_fields)}")
    if unexpected_fields:
        field_logger.info(f"  Unexpected fields ({len(unexpected_fields)}): {sorted(unexpected_fields)}")
    field_logger.info(f"  Accuracy: {len(expected_fields & detected_field_set)}/{len(expected_fields)} fields matched")
    
    return config

def process_audit_file(audit_file: str, platform: str, output_dir: str, config: Dict, logger: logging.Logger) -> bool:
    """Process a single audit file with the updated config."""
    try:
        # Skip if no fields defined
        if not config.get('fields'):
            logger.warning(f"No fields defined for {audit_file}, skipping processing")
            return False
        
        # Initialize config['directories']
        if 'directories' not in config:
            config['directories'] = {}
        if 'config_file' not in config['directories']:
            config['directories']['config_file'] = os.path.join(os.getcwd(), "config.json")
        
        # Create platform-specific output directories
        json_dir = os.path.join(output_dir, "json", platform)
        xlsx_dir = os.path.join(output_dir, "xlsx", platform)
        html_dir = os.path.join(output_dir, "html", platform)
        os.makedirs(json_dir, exist_ok=True)
        os.makedirs(xlsx_dir, exist_ok=True)
        os.makedirs(html_dir, exist_ok=True)
        
        # Save platform-specific config
        config_dir = os.path.join(os.getcwd(), "config")
        platform_config_path = save_platform_config(config, platform, config_dir, logger)
        
        # Extract to JSON
        json_output = extract_to_json(audit_file, json_dir, config, logger)
        if not json_output or not os.path.isfile(json_output):
            logger.error(f"Failed to extract JSON for {audit_file}")
            return False
        
        # Process to XLSX and HTML
        config['output']['xlsx_dir'] = xlsx_dir
        config['output']['html_dir'] = html_dir
        process_file(json_output, output_dir, config, logger)
        logger.info(f"Successfully processed {audit_file} to JSON, XLSX, and HTML")
        
        # Clean up platform config
        if os.path.exists(platform_config_path):
            os.remove(platform_config_path)
            logger.info(f"Removed temporary platform config {platform_config_path}")
            
        return True
    except Exception as e:
        logger.error(f"Failed to process {audit_file}: {str(e)}")
        return False

def compute_field_statistics(audit_dir: str, config: Dict, logger: logging.Logger, field_logger: logging.Logger) -> Dict:
    """Compute statistics on field correctness."""
    stats = {
        "total_files": 0,
        "files_with_fields": 0,
        "total_expected_fields": 0,
        "total_detected_fields": 0,
        "total_matched_fields": 0,
        "platform_stats": {}
    }
    
    expected_fields = set(config.get('preprocessing', {}).get('key_fields', []))
    
    portal_audits_dir = os.path.join(audit_dir, "portal_audits")
    if not os.path.isdir(portal_audits_dir):
        logger.warning(f"No portal_audits directory found in {audit_dir}")
        return stats
    
    for platform in sorted(os.listdir(portal_audits_dir)):
        platform_dir = os.path.join(portal_audits_dir, platform)
        if not os.path.isdir(platform_dir):
            continue
        
        platform_stats = {"files": 0, "matched_fields": 0, "expected_fields": 0, "detected_fields": 0}
        audit_files = glob.glob(os.path.join(platform_dir, "*.audit"))
        
        for audit_file in sorted(audit_files):
            stats["total_files"] += 1
            platform_stats["files"] += 1
            
            detected_fields = detect_fields(audit_file, logger)
            if not detected_fields:
                continue
            
            stats["files_with_fields"] += 1
            detected_field_set = set(detected_fields)
            matched_fields = len(expected_fields & detected_field_set)
            
            stats["total_expected_fields"] += len(expected_fields)
            stats["total_detected_fields"] += len(detected_field_set)
            stats["total_matched_fields"] += matched_fields
            
            platform_stats["expected_fields"] += len(expected_fields)
            platform_stats["detected_fields"] += len(detected_field_set)
            platform_stats["matched_fields"] += matched_fields
        
        stats["platform_stats"][platform] = platform_stats
    
    # Log statistics
    field_logger.info("Field Detection Statistics:")
    field_logger.info(f"Total audit files: {stats['total_files']}")
    field_logger.info(f"Files with detected fields: {stats['files_with_fields']}")
    field_logger.info(f"Total expected fields: {stats['total_expected_fields']}")
    field_logger.info(f"Total detected fields: {stats['total_detected_fields']}")
    field_logger.info(f"Total matched fields: {stats['total_matched_fields']}")
    accuracy = (stats['total_matched_fields'] / stats['total_expected_fields'] * 100) if stats['total_expected_fields'] > 0 else 0
    field_logger.info(f"Overall accuracy: {accuracy:.2f}%")
    
    field_logger.info("Per-platform statistics:")
    for platform, p_stats in stats["platform_stats"].items():
        p_accuracy = (p_stats['matched_fields'] / p_stats['expected_fields'] * 100) if p_stats['expected_fields'] > 0 else 0
        field_logger.info(f"  {platform}:")
        field_logger.info(f"    Files: {p_stats['files']}")
        field_logger.info(f"    Expected fields: {p_stats['expected_fields']}")
        field_logger.info(f"    Detected fields: {p_stats['detected_fields']}")
        field_logger.info(f"    Matched fields: {p_stats['matched_fields']}")
        field_logger.info(f"    Accuracy: {p_accuracy:.2f}%")
    
    return stats

def compute_xlsx_statistics(output_dir: str, logger: logging.Logger, field_logger: logging.Logger) -> Dict:
    """Compute statistics on XLSX conversions."""
    stats = {
        "total_files": 0,
        "total_rows": 0,
        "total_load_time": 0.0,
        "total_write_time": 0.0,
        "average_time_per_row": 0.0,
        "platform_stats": {}
    }
    
    xlsx_base_dir = os.path.join(output_dir, "xlsx")
    if not os.path.isdir(xlsx_base_dir):
        return stats
    
    log_file = os.path.join(os.path.dirname(output_dir), "debug", "xlsx_conversion_log.txt")
    if not os.path.isfile(log_file):
        return stats
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_file = None
    current_platform = None
    current_items = 0
    current_load_time = 0.0
    current_write_time = 0.0
    
    for line in lines:
        if "Converted" in line:
            parts = line.split("Converted ")[1].split(" to ")
            current_file = parts[1].strip()
            current_platform = os.path.basename(os.path.dirname(current_file))
        elif "Items: " in line:
            current_items = int(line.split("Items: ")[1].strip())
        elif "JSON load time: " in line:
            current_load_time = float(line.split("JSON load time: ")[1].split(" seconds")[0])
        elif "XLSX write time: " in line:
            current_write_time = float(line.split("XLSX write time: ")[1].split(" seconds")[0])
            if current_file and current_platform:
                stats["total_files"] += 1
                stats["total_rows"] += current_items
                stats["total_load_time"] += current_load_time
                stats["total_write_time"] += current_write_time
                
                if current_platform not in stats["platform_stats"]:
                    stats["platform_stats"][current_platform] = {
                        "files": 0,
                        "rows": 0,
                        "load_time": 0.0,
                        "write_time": 0.0
                    }
                stats["platform_stats"][current_platform]["files"] += 1
                stats["platform_stats"][current_platform]["rows"] += current_items
                stats["platform_stats"][current_platform]["load_time"] += current_load_time
                stats["platform_stats"][current_platform]["write_time"] += current_write_time
                
                current_file = None
    
    # Compute average time per row
    stats["average_time_per_row"] = (stats["total_load_time"] + stats["total_write_time"]) / stats["total_rows"] if stats["total_rows"] > 0 else 0.0
    
    # Log statistics
    field_logger.info("XLSX Conversion Statistics:")
    field_logger.info(f"Total XLSX files: {stats['total_files']}")
    field_logger.info(f"Total rows: {stats['total_rows']}")
    field_logger.info(f"Total JSON load time: {stats['total_load_time']:.3f} seconds")
    field_logger.info(f"Total XLSX write time: {stats['total_write_time']:.3f} seconds")
    field_logger.info(f"Average time per row: {stats['average_time_per_row']:.6f} seconds")
    
    field_logger.info("Per-platform XLSX statistics:")
    for platform, p_stats in stats["platform_stats"].items():
        p_avg_time = (p_stats['load_time'] + p_stats['write_time']) / p_stats['rows'] if p_stats['rows'] > 0 else 0.0
        field_logger.info(f"  {platform}:")
        field_logger.info(f"    Files: {p_stats['files']}")
        field_logger.info(f"    Rows: {p_stats['rows']}")
        field_logger.info(f"    JSON load time: {p_stats['load_time']:.3f} seconds")
        field_logger.info(f"    XLSX write time: {p_stats['write_time']:.3f} seconds")
        field_logger.info(f"    Average time per row: {p_avg_time:.6f} seconds")
    
    return stats

def execute_all(audit_dir: str, output_dir: str, config: Dict, logger: logging.Logger, field_logger: logging.Logger, verbose: bool) -> None:
    """Execute all audit processing scripts with automatic field detection."""
    try:
        audit_dir = os.path.normpath(audit_dir)
        output_dir = os.path.normpath(output_dir)
        
        # Automatically create required folders (except audit_dir)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "json"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "xlsx"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "html"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "csv"), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(output_dir), "debug", "audit_logs"), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(output_dir), "config"), exist_ok=True)
        
        print(f"Starting audit processing in {audit_dir}")
        logger.info(f"Starting audit processing in {audit_dir}")
        logger.info(f"Output directory: {output_dir}")
        if verbose:
            logger.setLevel(logging.DEBUG)
            logger.debug("Verbose logging enabled")
        
        # Clean up existing CSV files
        csv_dir = os.path.join(output_dir, "csv")
        for csv_file in glob.glob(os.path.join(csv_dir, "*.csv")):
            os.remove(csv_file)
            logger.info(f"Removed residual CSV file: {csv_file}")
        
        # Accept either portal_audits/<platform>/*.audit (raw Tenable extract)
        # or <platform>/*.audit (flattened layout from INSTRUCTIONS.txt / README).
        portal_audits_dir = os.path.join(audit_dir, "portal_audits")
        if os.path.isdir(portal_audits_dir):
            platforms_root = portal_audits_dir
            layout = "portal_audits"
        else:
            platforms_root = audit_dir
            layout = "flat"

        skip_names = {"portal_audits", "debug", "config", "__pycache__"}
        platforms = [
            d for d in os.listdir(platforms_root)
            if os.path.isdir(os.path.join(platforms_root, d)) and d not in skip_names
            and not d.startswith(".")
        ]
        platforms_with_audits = [
            p for p in platforms
            if glob.glob(os.path.join(platforms_root, p, "*.audit"))
        ]

        if not platforms_with_audits:
            msg = (
                f"No platform folders with *.audit files found under {audit_dir}. "
                "Expected either "
                f"{os.path.join(audit_dir, 'portal_audits', '<platform>', '*.audit')} "
                f"or {os.path.join(audit_dir, '<platform>', '*.audit')}."
            )
            logger.error(msg)
            print(f"Error: {msg}")
            raise FileNotFoundError(msg)

        logger.info(f"Using {layout} layout; platforms: {', '.join(sorted(platforms_with_audits))}")
        print(f"Found {len(platforms_with_audits)} platforms ({layout} layout)")
        
        processed_files = 0
        failed_files = 0
        
        for platform in sorted(platforms_with_audits):
            platform_dir = os.path.join(platforms_root, platform)
            audit_files = glob.glob(os.path.join(platform_dir, "*.audit"))
            
            print(f"Processing platform: {platform} ({len(audit_files)} audit files)")
            logger.info(f"Processing platform: {platform} ({len(audit_files)} audit files)")
            
            for audit_file in sorted(audit_files):
                # Create a fresh config copy
                config_copy = json.loads(json.dumps(config))  # Deep copy
                updated_config = update_config_fields(audit_file, platform, config_copy, logger, field_logger)
                if process_audit_file(audit_file, platform, output_dir, updated_config, logger):
                    processed_files += 1
                else:
                    failed_files += 1
        
        # Generate status log
        generate_status(output_dir, config, logger)
        
        # Compute and log statistics
        field_stats = compute_field_statistics(audit_dir, config, logger, field_logger)
        xlsx_stats = compute_xlsx_statistics(output_dir, logger, field_logger)
        
        print(f"Processing complete: {processed_files} files processed, {failed_files} failures")
        logger.info(f"Processing complete: {processed_files} files processed, {failed_files} failures")
        if failed_files:
            raise RuntimeError(f"{failed_files} audit file(s) failed during processing")
        
    except Exception as e:
        logger.error(f"Audit processing failed: {str(e)}")
        print(f"Execution failed: {str(e)}")
        raise

def main() -> None:
    """Main function to execute all scripts."""
    parser = argparse.ArgumentParser(
        description="Execute all audit file processing scripts with automatic field detection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Expected input layouts (either works):\n"
            "  1) <audit_dir>/portal_audits/<platform>/*.audit  (raw Tenable extract)\n"
            "  2) <audit_dir>/<platform>/*.audit               (flattened per INSTRUCTIONS.txt)\n"
            "\n"
            "Always quote paths that contain spaces:\n"
            "  python3 execute_all_scripts.py \"audit files\" \"output files\"\n"
        ),
    )
    parser.add_argument(
        "audit_dir",
        help="Directory containing platform audit folders (see --help epilog for layouts)",
    )
    parser.add_argument(
        "output_dir",
        help="Directory for output JSON, XLSX, and HTML files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging for the main execute_all logger",
    )
    args = parser.parse_args()

    # Initialize logger early
    debug_dir = os.path.join(os.getcwd(), "debug")
    os.makedirs(debug_dir, exist_ok=True)
    logger = setup_logging(debug_dir)

    original_checksum = None
    try:
        # Load or create config early
        config_path = os.path.join(os.getcwd(), "config.json")
        if not os.path.isfile(config_path):
            logger.warning(f"Config file {config_path} not found, creating default")
            config = create_default_config(config_path, logger)
        else:
            original_checksum = get_config_checksum(config_path)
            config = cached_config(config_path)
            logger.info(f"Original config checksum: {original_checksum}")

        # Initialize field accuracy logger with config
        field_logger = setup_field_accuracy_logger(debug_dir, config)

        # Initialize config['directories'] and config['output']
        if 'directories' not in config:
            config['directories'] = {}
        if 'config_file' not in config['directories']:
            config['directories']['config_file'] = config_path
        if 'debug_dir' not in config['directories']:
            config['directories']['debug_dir'] = "debug"
        if 'output' not in config:
            config['output'] = {}
        if 'output_format' not in config['output']:
            config['output']['output_format'] = ["xlsx", "html"]
        
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        
        # Execute processing
        execute_all(args.audit_dir, args.output_dir, config, logger, field_logger, args.verbose)
        
        # Verify config unchanged
        if original_checksum is not None and os.path.isfile(config_path):
            verify_config_unchanged(config_path, original_checksum)
        
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}")
        print(f"Execution failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
