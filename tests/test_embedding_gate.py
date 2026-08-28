import unittest

from enterprise_knowledge_agent.embedding_gate import assess_embedding_candidate


BASELINE = {"case_count": 16, "status_accuracy": 1.0, "top1_accuracy": 0.9167, "abstention_accuracy": 1.0, "blocked_request_accuracy": 1.0}


def candidate(**overrides):
    value = {"repository": "https://github.com/example/retriever", "version": "1.0.0", "commit": "0123456789abcdef0123456789abcdef01234567", "license": "MIT", "decision": "adopted", "code_adopted": True, "reason": "Synthetic candidate", "model_artifact_available": True, "benchmark": dict(BASELINE)}
    value.update(overrides)
    return value


class EmbeddingGateTests(unittest.TestCase):
    def test_rejected_candidate_never_becomes_installable(self):
        result = assess_embedding_candidate(candidate(decision="rejected", code_adopted=False), BASELINE)
        self.assertEqual(result["status"], "screened_not_adopted")
        self.assertFalse(result["eligible_for_install"])

    def test_missing_artifact_and_benchmark_fail_closed(self):
        self.assertEqual(assess_embedding_candidate(candidate(model_artifact_available=False), BASELINE)["status"], "blocked_missing_model_artifact")
        self.assertEqual(assess_embedding_candidate(candidate(benchmark=None), BASELINE)["status"], "blocked_missing_benchmark")

    def test_metric_regression_is_blocked(self):
        metrics = dict(BASELINE)
        metrics["blocked_request_accuracy"] = 0.99
        result = assess_embedding_candidate(candidate(benchmark=metrics), BASELINE)
        self.assertEqual(result["status"], "blocked_benchmark_regression")
        self.assertIn("blocked_request_accuracy", result["regressions"])

    def test_passing_candidate_is_only_eligible_for_bounded_pilot(self):
        result = assess_embedding_candidate(candidate(), BASELINE)
        self.assertEqual(result["status"], "eligible_for_bounded_pilot")
        self.assertTrue(result["eligible_for_install"])


if __name__ == "__main__":
    unittest.main()
