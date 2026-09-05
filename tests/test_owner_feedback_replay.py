import unittest

from enterprise_knowledge_agent.owner_feedback_replay import replay_owner_feedback


class OwnerFeedbackReplayTests(unittest.TestCase):
    def setUp(self):
        self.queue = {"review_only": True, "evidence_mutated": False, "external_action_executed": False}
        self.history = [{"review_id": "R1"}, {"review_id": "R2"}]
        self.feedback = [
            {"feedback_id": "A", "review_id": "R1", "recorded_on": "2026-08-31", "status": "accepted", "summary": "ok", "applied": False},
            {"feedback_id": "B", "review_id": "R2", "recorded_on": "2026-09-01", "status": "pending", "summary": "later", "applied": False},
        ]

    def test_replays_accepted_only(self):
        result = replay_owner_feedback(self.queue, self.history, self.feedback)
        self.assertEqual(result["replayed_count"], 1)
        self.assertEqual(result["excluded_count"], 1)
        self.assertFalse(result["approval_applied"])

    def test_rejects_unknown_review(self):
        self.feedback[0]["review_id"] = "R9"
        with self.assertRaisesRegex(ValueError, "review_id"):
            replay_owner_feedback(self.queue, self.history, self.feedback)

    def test_rejects_duplicate_feedback(self):
        self.feedback[1]["feedback_id"] = "A"
        with self.assertRaisesRegex(ValueError, "unique"):
            replay_owner_feedback(self.queue, self.history, self.feedback)

    def test_rejects_out_of_order_dates(self):
        self.feedback[1]["recorded_on"] = "2026-08-30"
        with self.assertRaisesRegex(ValueError, "chronological"):
            replay_owner_feedback(self.queue, self.history, self.feedback)

    def test_rejects_applied_feedback(self):
        self.feedback[0]["applied"] = True
        with self.assertRaisesRegex(ValueError, "approval"):
            replay_owner_feedback(self.queue, self.history, self.feedback)

    def test_rejects_invalid_status(self):
        self.feedback[0]["status"] = "renewed"
        with self.assertRaisesRegex(ValueError, "status"):
            replay_owner_feedback(self.queue, self.history, self.feedback)

    def test_rejects_writing_queue(self):
        self.queue["evidence_mutated"] = True
        with self.assertRaisesRegex(ValueError, "non-writing"):
            replay_owner_feedback(self.queue, self.history, self.feedback)

    def test_rejects_empty_batch(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            replay_owner_feedback(self.queue, self.history, [])


if __name__ == "__main__":
    unittest.main()
