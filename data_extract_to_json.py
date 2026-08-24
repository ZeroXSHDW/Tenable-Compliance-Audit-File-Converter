import os
import re
import json
import logging
from typing import Dict, List, Set
from audit_utils import atomic_write_text, detect_encoding, validate_json_file

__version__ = "2.0.4"
__changelog__ = """
2.0.0:
- Initial implementation for extracting audit files to JSON
- Integrated with audit_utils for encoding detection and logging
- Supports dynamic fields from config
- Logs block counts (custom_item, item, variable)
- Validates output JSON
2.0.1:
- Updated log file path to debug/audit_logs
2.0.2:
- Prioritized 'description' field in JSON output
2.0.3:
- Removed erroneous self-import causing circular import error
2.0.4:
- Aligned folder creation with automatic setup in execute_all_scripts
"""

def is_valid_key(key: str) -> bool:
    """Check if a key is valid for inclusion in JSON."""
    return bool(re.match(r'^[a-zA-Z0-9_]+$', key))

def extract_to_json(audit_file: str, output_dir: str, config: Dict, logger: logging.Logger) -> str:
    """Extract audit file content to JSON."""
    file_logger = None
    file_handler = None
    try:
        # Validate input
        if not os.path.isfile(audit_file):
            logger.error(f"Audit file {audit_file} does not exist")
            return ""
        
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.basename(audit_file).replace(".audit", "")
        json_output = os.path.join(output_dir, f"extracted_data_{filename}.json")
        log_dir = os.path.join(config['directories']['debug_dir'], "audit_logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"extract_log_{filename}.txt")
        
        # Set up file-specific logger
        file_logger = logging.getLogger(f"extract_{filename}")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(config['logging']['format']))
        file_logger.addHandler(file_handler)
        file_logger.setLevel(getattr(logging, config['logging']['level']))
        
        # Read audit file
        encoding, content = detect_encoding(audit_file, file_logger)
        file_logger.info(f"Detected encoding for {audit_file}: {encoding}")
        
        # Parse audit file
        items: List[Dict] = []
        current_item: Dict = {}
        current_key: str = ""
        in_block = False
        block_type: str = ""
        block_counts = {"custom_item": 0, "item": 0, "variable": 0}
        
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Start of a block
            block_match = re.match(r'^\s*<(custom_item|item|variable)>\s*$', line)
            if block_match:
                if in_block and current_item:
                    items.append(current_item)
                    block_counts[block_type] += 1
                in_block = True
                block_type = block_match.group(1)
                current_item = {}
                continue
            
            # End of a block
            if in_block and re.match(r'^\s*</(custom_item|item|variable)>\s*$', line):
                if current_item:
                    items.append(current_item)
                    block_counts[block_type] += 1
                in_block = False
                current_item = {}
                continue
            
            # Key-value pair
            if in_block:
                kv_match = re.match(r'^\s*([a-zA-Z0-9_]+)\s*:\s*(.*)$', line)
                if kv_match:
                    key, value = kv_match.groups()
                    if is_valid_key(key):
                        current_item[key] = value.strip()
                        current_key = key
                    continue
                
                # Multi-line value continuation
                if current_key and line.startswith('"') and line.endswith('"'):
                    current_item[current_key] += " " + line.strip('"')
                    continue
        
        # Append last item if exists
        if in_block and current_item:
            items.append(current_item)
            block_counts[block_type] += 1
        
        # Filter items by config fields, ensuring 'description' is included
        fields = config.get('fields', [])
        if not fields:
            fields = ['description'] + sorted(set(k for item in items for k in item.keys() if k != 'description'))
        filtered_items = []
        for item in items:
            filtered_item = {k: item.get(k, "") for k in fields}
            if filtered_item.get('description'):  # Only include items with description
                filtered_items.append(filtered_item)
        
        # Write JSON output
        atomic_write_text(json_output, json.dumps(filtered_items, indent=4))
        
        # Log results
        file_logger.info(f"Extracted {len(filtered_items)} items to {json_output}")
        file_logger.info(f"Block counts: custom_item={block_counts['custom_item']}, item={block_counts['item']}, variable={block_counts['variable']}")
        
        # Validate JSON
        if not validate_json_file(json_output, file_logger):
            file_logger.error(f"Generated JSON {json_output} is invalid")
            return ""
        
        return json_output

    except Exception as e:
        logger.error(f"Failed to extract {audit_file} to JSON: {str(e)}")
        if file_logger is not None:
            file_logger.error(f"Extraction failed: {str(e)}")
        return ""
    finally:
        if file_logger is not None and file_handler is not None:
            file_logger.removeHandler(file_handler)
            file_handler.close()
