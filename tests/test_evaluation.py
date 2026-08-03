import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from enterprise_knowledge_agent.evaluation import evaluate_queries, load_query_cases, write_evaluation_report


ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "data" / "knowledge.json"
QUERIES = ROOT / "data" / "evaluation_queries.json"


class RetrievalEvaluationTests(unittest.TestCase):
    def test_reviewed_query_set_passes(self):
        report = evaluate_queries(CORPUS, QUERIES)

        self.assertEqual(report["summary"]["passed_cases"], 12)
        self.assertEqual(report["summary"]["top1_accuracy"], 1.0)
        self.assertEqual(report["summary"]["abstention_accuracy"], 1.0)
        self.assertEqual(report["summary"]["blocked_request_accuracy"], 1.0)

    def test_mismatched_expected_source_is_visible(self):
        cases = load_query_cases(QUERIES)
        cases[0]["expected_document_id"] = "KB-SVC-002"
        with TemporaryDirectory() as directory:
            changed_queries = Path(directory) / "queries.json"
            changed_queries.write_text(json.dumps(cases), encoding="utf-8")
            report = evaluate_queries(CORPUS, changed_queries)

        self.assertFalse(report["cases"][0]["passed"])
        self.assertNotEqual(report["cases"][0]["expected_document_rank"], 1)

    def test_writes_reproducible_reports(self):
        with TemporaryDirectory() as directory:
            json_path = Path(directory) / "report.json"
            markdown_path = Path(directory) / "report.md"
            report = write_evaluation_report(CORPUS, QUERIES, json_path, markdown_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), report)
            self.assertIn("Top-1 document accuracy", markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
