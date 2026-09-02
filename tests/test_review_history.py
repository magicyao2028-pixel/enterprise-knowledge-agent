import unittest

from enterprise_knowledge_agent.review_history import summarize_owner_review_history


class ReviewHistoryTests(unittest.TestCase):
    def setUp(self):
        self.queue = {
            "items": [{"document_id": "D-1"}, {"document_id": "D-2"}],
            "review_only": True,
            "evidence_mutated": False,
            "external_action_executed": False,
        }
        self.history = [
            {"review_id": "R-1", "document_id": "D-1", "reviewed_on": "2026-08-01", "decision": "renew", "owner": "Ops", "note": "ok", "approval_applied": False},
            {"review_id": "R-2", "document_id": "D-2", "reviewed_on": "2026-08-02", "decision": "defer", "owner": "Finance", "note": "wait", "approval_applied": False},
        ]

    def test_summary_is_non_writing(self):
        summary = summarize_owner_review_history(self.queue, self.history)
        self.assertEqual(summary["entry_count"], 2)
        self.assertEqual(summary["decision_counts"], {"defer": 1, "renew": 1})
        self.assertFalse(summary["evidence_mutated"])

    def test_unknown_document_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            summarize_owner_review_history(self.queue, [dict(self.history[0], document_id="D-X")])

    def test_duplicate_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            summarize_owner_review_history(self.queue, [*self.history, dict(self.history[0])])

    def test_out_of_order_dates_are_rejected(self):
        invalid = [dict(self.history[0]), dict(self.history[1], reviewed_on="2026-07-01")]
        with self.assertRaisesRegex(ValueError, "chronological"):
            summarize_owner_review_history(self.queue, invalid)


if __name__ == "__main__":
    unittest.main()
