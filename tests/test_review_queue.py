import unittest

from enterprise_knowledge_agent import KnowledgeDocument
from enterprise_knowledge_agent.review_queue import build_owner_review_queue


class ReviewQueueTests(unittest.TestCase):
    def test_conflict_has_priority_and_queue_is_non_writing(self):
        docs = [
            KnowledgeDocument("a", "A", "Finance", "2026-08-01", "500", claim_key="ceiling", claim_value="500"),
            KnowledgeDocument("b", "B", "Ops", "2026-08-02", "650", claim_key="ceiling", claim_value="650"),
            KnowledgeDocument("c", "C", "Support", "2026-08-02", "current"),
        ]
        result = build_owner_review_queue(docs, as_of_date="2026-08-30", max_source_age_days=30)
        self.assertEqual(result["item_count"], 2)
        self.assertEqual(result["items"][0]["priority"], 1)
        self.assertTrue(result["review_only"])
        self.assertFalse(result["evidence_mutated"])
        self.assertFalse(result["external_action_executed"])

    def test_deterministic_empty_queue_and_validation(self):
        doc = KnowledgeDocument("a", "A", "Support", "2026-08-29", "current")
        first = build_owner_review_queue([doc], as_of_date="2026-08-30")
        self.assertEqual(first["items"], [])
        with self.assertRaisesRegex(ValueError, "ISO-8601"):
            build_owner_review_queue([doc], as_of_date="tomorrow")


if __name__ == "__main__":
    unittest.main()
