"""Smoke tests for audit parsers (no Tenable tarball required)."""
from __future__ import annotations

import json
import logging
import os
import tempfile
import unittest
from pathlib import Path

import openpyxl

from audit_extract_helper import write_xlsx
from audit_utils import atomic_replace, sanitize_cell_value
from audit_parse_detector import detect_missing_keys
from data_extract_to_json import extract_to_json
from execute_all_scripts import create_default_config
from generate_status_log import generate_status

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "tiny.audit"


class TestAuditParseSmoke(unittest.TestCase):
    def test_ci_and_readme_enforce_patch_hygiene(self) -> None:
        readme = Path(__file__).resolve().parents[1].joinpath("README.md").read_text(encoding="utf-8")
        workflow = Path(__file__).resolve().parents[1].joinpath(".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("git diff --check", readme)
        self.assertIn("pip_audit -r requirements.txt", readme)
        self.assertIn("pip_audit -r requirements.txt", workflow)
        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertNotIn("runs-on: ubuntu-latest", workflow)
        self.assertNotIn("pip install --upgrade pip", workflow)
        self.assertNotIn("pip install --upgrade pip setuptools wheel", workflow)
        self.assertIn('pip install --disable-pip-version-check "pip-audit==2.9.0"', workflow)
        self.assertEqual(
            workflow.count("git diff --check"),
            workflow.count("uses: actions/checkout@"),
        )

    def test_fixture_exists(self) -> None:
        self.assertTrue(FIXTURE.is_file(), f"Missing fixture: {FIXTURE}")

    def test_atomic_replace_preserves_last_good_artifact_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "result.json"
            destination.write_text('{"status": "known-good"}', encoding="utf-8")

            def fail(_temporary_path: str) -> None:
                raise RuntimeError("simulated writer failure")

            with self.assertRaisesRegex(RuntimeError, "simulated writer failure"):
                atomic_replace(str(destination), fail)

            self.assertEqual('{"status": "known-good"}', destination.read_text(encoding="utf-8"))
            self.assertEqual([], list(destination.parent.glob(".result.json.*.tmp")))

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

    def test_formula_like_values_are_written_as_text(self) -> None:
        formula = '=HYPERLINK("https://example.test")'
        self.assertEqual(
            "'=HYPERLINK(\"https://example.test\")",
            sanitize_cell_value(formula, "description", "fixture"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "export.xlsx"
            logger = logging.getLogger("test_formula_export")
            logger.addHandler(logging.NullHandler())
            write_xlsx(
                str(output),
                ["description"],
                [{"description": formula}],
                {"logging": {"format": "%(message)s"}},
                logger,
            )
            workbook = openpyxl.load_workbook(output, data_only=False)
            cell = workbook.active["A2"]
            self.assertEqual("s", cell.data_type)
            self.assertTrue(str(cell.value).startswith("'="))

    def test_status_log_discovers_documented_nested_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "output files"
            json_dir = output / "json" / "Linux"
            xlsx_dir = output / "xlsx" / "Linux"
            debug_dir = root / "debug"
            json_dir.mkdir(parents=True)
            xlsx_dir.mkdir(parents=True)
            debug_dir.joinpath("audit_logs").mkdir(parents=True)
            (json_dir / "extracted_data_sample.json").write_text('[{"description": "ok"}]', encoding="utf-8")
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.append(["description"])
            sheet.append(["ok"])
            workbook.save(xlsx_dir / "extracted_sample.xlsx")
            (debug_dir / "audit_logs" / "extract_log_sample.txt").write_text(
                "Block counts: custom_item=1, item=1, variable=0\n", encoding="utf-8"
            )

            logger = logging.getLogger("test_status_log")
            logger.addHandler(logging.NullHandler())
            generate_status(str(output), {"directories": {"debug_dir": str(debug_dir)}}, logger)

            status = (debug_dir / "extract_parse_status_log.txt").read_text(encoding="utf-8")
            self.assertIn("JSON Files Found: 1", status)
            self.assertIn("XLSX Files Found: 1", status)
            self.assertIn("custom_item=1, item=1, variable=0", status)

    def test_default_config_supports_a_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                logger = logging.getLogger("test_default_config")
                logger.addHandler(logging.NullHandler())
                config = create_default_config("generated.json", logger)
            finally:
                os.chdir(previous_cwd)

            self.assertEqual("audit files", config["directories"]["audit_dir"])
            self.assertTrue((Path(tmp) / "generated.json").is_file())


if __name__ == "__main__":
    unittest.main()
