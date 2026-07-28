"""Smoke tests for audit parsers (no Tenable tarball required)."""
from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path

from audit_parse_detector import detect_missing_keys
from data_extract_to_json import extract_to_json

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "tiny.audit"


class TestAuditParseSmoke(unittest.TestCase):
    def test_fixture_exists(self) -> None:
        self.assertTrue(FIXTURE.is_file(), f"Missing fixture: {FIXTURE}")

    def test_detect_missing_keys(self) -> None:
        missing, all_keys = detect_missing_keys(str(FIXTURE), {"description", "type", "cmd", "value"})
        self.assertIn("description", all_keys)
        self.assertIn("type", all_keys)
        self.assertIn("cmd", all_keys)
        self.assertTrue(missing.issubset({"value"}))

    def test_extract_to_json(self) -> None:
        logger = logging.getLogger("test_audit_parse_smoke")
        logger.addHandler(logging.NullHandler())
        with tempfile.TemporaryDirectory() as tmp:
            config = {
                "directories": {"debug_dir": tmp},
                "logging": {"level": "INFO", "format": "%(message)s"},
                "fields": ["description", "type", "cmd", "value", "file"],
            }
            json_path = extract_to_json(str(FIXTURE), tmp, config, logger)
            self.assertTrue(Path(json_path).is_file())
            with open(json_path, encoding="utf-8") as fh:
                data = json.load(fh)
            items = data if isinstance(data, list) else data.get("items", data)
            self.assertIsInstance(items, list)
            self.assertGreaterEqual(len(items), 1)
            self.assertTrue(any(item.get("description") for item in items))


if __name__ == "__main__":
    unittest.main()
