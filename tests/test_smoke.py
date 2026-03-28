"""
Smoke tests: config, JSON parsing, metadata mapping, prompt placeholders.
Run: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Repo root on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from scripts import extract_esg_fields as ex


class TestSettings(unittest.TestCase):
    def test_get_bool(self):
        with mock.patch.dict(os.environ, {"T_BOOL": "true"}, clear=False):
            self.assertTrue(settings.get_bool("T_BOOL", False))
        with mock.patch.dict(os.environ, {"T_BOOL": "0"}, clear=False):
            self.assertFalse(settings.get_bool("T_BOOL", True))

    def test_get_str_empty_falls_back(self):
        with mock.patch.dict(os.environ, {"T_S": ""}, clear=False):
            self.assertEqual(settings.get_str("T_S", "d"), "d")

    def test_get_path_relative_to_repo(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            p = settings.get_path("MISSING_KEY", "data/foo")
            self.assertTrue(str(p).endswith(os.path.join("data", "foo")))

    def test_get_int_optional(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(settings.get_int_optional("N"))
        with mock.patch.dict(os.environ, {"N": "3"}, clear=False):
            self.assertEqual(settings.get_int_optional("N"), 3)


class TestExtractJson(unittest.TestCase):
    def test_parse_json_clean(self):
        d, err = ex.parse_json_response('{"a": 1, "claims": []}')
        self.assertIsNone(err)
        self.assertEqual(d.get("a"), 1)

    def test_parse_json_extra_text(self):
        raw = 'Here:\n{"x": "y"}\n'
        d, err = ex.parse_json_response(raw)
        self.assertIsNone(err)
        self.assertEqual(d.get("x"), "y")

    def test_parse_empty(self):
        d, err = ex.parse_json_response("")
        self.assertEqual(err, "empty_response")


class TestCoerceBool(unittest.TestCase):
    def test_strings(self):
        self.assertTrue(ex._coerce_bool("true"))
        self.assertFalse(ex._coerce_bool("false"))
        self.assertIsNone(ex._coerce_bool("maybe"))

    def test_bool_to_csv(self):
        self.assertEqual(ex._bool_to_csv("true"), "true")
        self.assertEqual(ex._bool_to_csv("false"), "false")


class TestPostprocessClaims(unittest.TestCase):
    def test_truncates_quote(self):
        long_q = "x" * 600
        data = {
            "claims": [
                {
                    "claim_id": 1,
                    "evidence_lines": [{"page": 1, "quote": long_q}],
                }
            ]
        }
        out = ex._postprocess_claims(data, max_claims=10, max_quote_chars=500)
        q = out["claims"][0]["evidence_lines"][0]["quote"]
        self.assertLessEqual(len(q), 500)

    def test_max_claims_slice(self):
        data = {"claims": [{"claim_id": i} for i in range(20)]}
        out = ex._postprocess_claims(data, max_claims=3, max_quote_chars=100)
        self.assertEqual(len(out["claims"]), 3)
        self.assertEqual([c["claim_id"] for c in out["claims"]], [1, 2, 3])

    def test_renumber_claim_ids_skips_non_dict(self):
        data = {"claims": ["bad", {"evidence_lines": []}, {"evidence_lines": []}]}
        out = ex._postprocess_claims(data, max_claims=10, max_quote_chars=100)
        self.assertEqual(out["claims"][1]["claim_id"], 1)
        self.assertEqual(out["claims"][2]["claim_id"], 2)


class TestBuildPrompt(unittest.TestCase):
    def test_placeholders(self):
        t = "Max {{MAX_CLAIMS}} quote {{MAX_QUOTE_CHARS}}"
        self.assertEqual(ex.build_prompt(t, 7, 120), "Max 7 quote 120")


class TestLoadMetadata(unittest.TestCase):
    def test_sector_from_companies_json(self):
        companies = [
            {
                "company_isin": "VN000000DHG0",
                "company_ticker": "DHG",
                "company_sector": "Health Care",
            }
        ]
        reports = [
            {
                "company_slug": "dhg-pharmaceutical",
                "report_year": 2024,
                "report_type": "SR",
                "report_id": 1,
                "company_isin": "VN000000DHG0",
                "company_name": "DHG",
            }
        ]
        with tempfile.TemporaryDirectory() as td:
            rp = Path(td) / "r.json"
            cp = Path(td) / "c.json"
            rp.write_text(json.dumps(reports), encoding="utf-8")
            cp.write_text(json.dumps(companies), encoding="utf-8")
            with mock.patch.object(ex.LOG, "warning"):
                lookup = ex.load_metadata(rp, cp)
        fn = "dhg-pharmaceutical_2024_SR_1.pdf"
        self.assertIn(fn, lookup)
        self.assertEqual(lookup[fn]["company_sector"], "Health Care")
        self.assertEqual(lookup[fn]["company_ticker"], "DHG")


class TestRowToJsonl(unittest.TestCase):
    def test_claims_array(self):
        row = {
            "pdf_filename": "x.pdf",
            "claims_json": '[{"claim_id":1}]',
        }
        rec = ex.row_to_jsonl_record(row)
        self.assertEqual(rec["claims"], [{"claim_id": 1}])
        self.assertNotIn("claims_json", rec)


class TestCliHelp(unittest.TestCase):
    def _sub_env(self) -> dict:
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        return env

    def test_extract_help(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "extract_esg_fields.py"), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            env=self._sub_env(),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        out = (r.stdout + r.stderr).lower()
        self.assertIn("pdf-dir", out)
        self.assertIn(".env", out)

    def test_crawl_help(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "crawl_vietnam_sustainability_reports.py"), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            env=self._sub_env(),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        out = (r.stdout + r.stderr).lower()
        self.assertIn("vietnam", out)
        self.assertIn(".env", out)


if __name__ == "__main__":
    unittest.main()
