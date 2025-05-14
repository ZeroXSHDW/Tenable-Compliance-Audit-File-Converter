import os
import re
import logging
from typing import Set, Tuple
from audit_utils import detect_encoding

__version__ = "2.0.0"
__changelog__ = """
2.0.0:
- Initial implementation for detecting keys in audit files
- Integrated with audit_utils for encoding detection
- Detects all keys and compares with config fields
- Logs missing and unexpected keys
2.0.1:
- Added missing import os to fix NameError
"""

def detect_missing_keys(audit_file: str, config_fields: Set[str]) -> Tuple[Set[str], Set[str]]:
    """Detect keys in an audit file and compare with config fields."""
    logger = logging.getLogger("audit_parse_detector")
    try:
        # Validate input
        if not audit_file.endswith(".audit") or not os.path.isfile(audit_file):
            logger.error(f"Invalid audit file: {audit_file}")
            return set(), set()
        
        # Read audit file
        encoding, content = detect_encoding(audit_file, logger)
        logger.debug(f"Detected encoding for {audit_file}: {encoding}")
        
        # Extract keys
        all_keys: Set[str] = set()
        lines = content.splitlines()
        in_block = False
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Start/end of block
            if re.match(r'^\s*<(custom_item|item|variable)>\s*$', line):
                in_block = True
                continue
            if re.match(r'^\s*</(custom_item|item|variable)>\s*$', line):
                in_block = False
                continue
            
            # Key-value pair
            if in_block:
                kv_match = re.match(r'^\s*([a-zA-Z0-9_]+)\s*:\s*(.*)$', line)
                if kv_match:
                    key = kv_match.group(1)
                    all_keys.add(key)
        
        # Compare with config fields
        missing_keys = config_fields - all_keys
        unexpected_keys = all_keys - config_fields
        
        if missing_keys:
            logger.warning(f"Missing keys in {audit_file}: {sorted(missing_keys)}")
        if unexpected_keys:
            logger.info(f"Unexpected keys in {audit_file}: {sorted(unexpected_keys)}")
        
        return missing_keys, all_keys
    
    except Exception as e:
        logger.error(f"Failed to detect keys in {audit_file}: {str(e)}")
        return set(), set()

def main() -> None:
    """Main function for testing audit_parse_detector."""
    import argparse
    parser = argparse.ArgumentParser(description="Detect keys in audit files.")
    parser.add_argument("audit_file", help="Input audit file")
    args = parser.parse_args()

    try:
        config_fields = {"type", "description", "cmd", "value"}
        logger = logging.getLogger("audit_parse_detector")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
        
        missing_keys, all_keys = detect_missing_keys(args.audit_file, config_fields)
        print(f"Missing keys: {sorted(missing_keys)}")
        print(f"All keys: {sorted(all_keys)}")
        
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()