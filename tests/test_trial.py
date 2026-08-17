import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from enterprise_knowledge_agent.trial import (
    load_json_object,
    run_trial,
    validate_evidence_index,
    validate_external_intake,
    validate_feedback,
    write_trial_report,
)


ROOT = Path(__file__).parents[1]


class TrialReadinessTests(unittest.TestCase):
    def test_complete_trial_passes(self):
        report = run_trial(ROOT)
        self.assertTrue(report["overall_passed"])
        self.assertEqual(report["core_flow"]["top_document_id"], "KB-SVC-002")
        self.assertEqual(report["feedback_regression"]["status"], "blocked")

    def test_evidence_index_links_real_files(self):
        payload = load_json_object(ROOT / "evidence" / "evidence_index.json")
        checked = validate_evidence_index(ROOT, payload)
        self.assertGreaterEqual(len(checked), 6)
        self.assertTrue(all(item["passed"] for item in checked))

    def test_external_intake_rejects_short_commit(self):
        payload = load_json_object(ROOT / "evidence" / "external_intake.json")
        changed = deepcopy(payload)
        changed["candidates"][0]["commit"] = "abc123"
        with self.assertRaisesRegex(ValueError, "full SHA"):
            validate_external_intake(changed)

    def test_feedback_source_must_be_explicit(self):
        payload = load_json_object(ROOT / "evidence" / "feedback_case.json")
        changed = deepcopy(payload)
        changed["source_type"] = "knowledge owner"
        with self.assertRaisesRegex(ValueError, "real or synthetic"):
            validate_feedback(ROOT, changed)

    def test_governance_metadata_rejects_inconsistent_adoption_and_bad_date(self):
        external = load_json_object(ROOT / "evidence" / "external_intake.json")
        inconsistent = deepcopy(external)
        inconsistent["candidates"][0]["code_adopted"] = True
        with self.assertRaisesRegex(ValueError, "must agree"):
            validate_external_intake(inconsistent)

        feedback = load_json_object(ROOT / "evidence" / "feedback_case.json")
        bad_date = deepcopy(feedback)
        bad_date["recorded_on"] = "August 17"
        with self.assertRaisesRegex(ValueError, "ISO-8601"):
            validate_feedback(ROOT, bad_date)

    def test_report_is_reproducible(self):
        with TemporaryDirectory() as directory:
            json_path = Path(directory) / "trial.json"
            md_path = Path(directory) / "trial.md"
            first = write_trial_report(ROOT, json_path, md_path)
            second = write_trial_report(ROOT, json_path, md_path)
        self.assertEqual(first, second)
        self.assertTrue(json.loads(json.dumps(first))["overall_passed"])

    def test_browser_mirror_contains_punctuated_secret_gate(self):
        script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
        self.assertIn(r"api[\s_-]*keys?", script)
        self.assertIn("sensitivePatterns.some", script)


if __name__ == "__main__":
    unittest.main()
