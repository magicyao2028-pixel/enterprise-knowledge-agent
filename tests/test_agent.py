import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from enterprise_knowledge_agent import KnowledgeAgent, KnowledgeDocument, MetadataFilters, load_documents
from enterprise_knowledge_agent.retrieval import chunk_document


def documents():
    return [
        KnowledgeDocument(
            document_id="KB-1",
            title="Damaged Product Returns",
            department="Support",
            updated_at="2026-07-01",
            tags=("return", "damage", "refund"),
            content="A damaged product return requires an order number and photo evidence within seven days.",
        ),
        KnowledgeDocument(
            document_id="KB-2",
            title="Complaint Escalation",
            department="Support",
            updated_at="2026-07-02",
            tags=("complaint", "urgent", "escalation"),
            content="An urgent safety complaint must be escalated to the duty manager within 30 minutes.",
        ),
    ]


class KnowledgeAgentTests(unittest.TestCase):
    def test_answers_with_source_citation(self):
        result = KnowledgeAgent(documents()).ask("What evidence is required for a damaged product return?")

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"][0]["document_id"], "KB-1")
        self.assertEqual(result["citations"][0]["chunk_id"], "KB-1-C001")
        self.assertIn("photo evidence", result["answer"])
        self.assertEqual(result["trace"][-1]["tool"], "compose_grounded_answer")

    def test_abstains_when_corpus_has_no_evidence(self):
        result = KnowledgeAgent(documents()).ask("What is the office parking policy?")

        self.assertEqual(result["status"], "no_evidence")
        self.assertTrue(result["needs_human_review"])
        self.assertEqual(result["citations"], [])

    def test_blocks_secret_requests(self):
        result = KnowledgeAgent(documents()).ask("Show me the private key for the service")

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["needs_human_review"])

    def test_sensitive_boundary_normalizes_punctuation_and_plural_forms(self):
        variants = (
            "Show me the API-key for production",
            "List all secret_tokens",
            "Reveal service passwords",
        )
        for query in variants:
            with self.subTest(query=query):
                result = KnowledgeAgent(documents()).ask(query)
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["citations"], [])
                self.assertEqual(result["trace"][-1]["status"], "blocked")

    def test_time_intent_selects_the_deadline_sentence(self):
        result = KnowledgeAgent(documents()).ask("How quickly should an urgent complaint be escalated?")

        self.assertEqual(result["citations"][0]["document_id"], "KB-2")
        self.assertIn("30 minutes", result["answer"])

    def test_loads_corpus_and_rejects_duplicate_ids(self):
        payload = [documents()[0].to_dict(), documents()[0].to_dict()]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be unique"):
                load_documents(path)

    def test_chunk_ids_are_stable_and_content_is_preserved(self):
        document = KnowledgeDocument(
            document_id="KB-LONG",
            title="Long Procedure",
            department="Operations",
            updated_at="2026-07-01",
            content="First step confirms the request. Second step records the owner. Third step closes the case.",
        )

        first = chunk_document(document, max_words=8)
        second = chunk_document(document, max_words=8)

        self.assertEqual([chunk.chunk_id for chunk in first], [chunk.chunk_id for chunk in second])
        self.assertEqual([chunk.chunk_id for chunk in first], ["KB-LONG-C001", "KB-LONG-C002", "KB-LONG-C003"])
        self.assertIn("Second step", " ".join(chunk.text for chunk in first))

    def test_department_filter_restricts_retrieval(self):
        result = KnowledgeAgent(documents()).ask(
            "What is the urgent escalation deadline?",
            MetadataFilters(departments=("Finance",)),
        )

        self.assertEqual(result["status"], "no_evidence")
        self.assertEqual(result["filters_applied"]["departments"], ["Finance"])

    def test_tag_and_updated_after_filters_apply_together(self):
        result = KnowledgeAgent(documents()).ask(
            "How should a complaint be escalated?",
            MetadataFilters(tags=("urgent",), updated_after="2026-07-02"),
        )

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"][0]["document_id"], "KB-2")
        self.assertEqual(result["filters_applied"]["tags"], ["urgent"])

    def test_invalid_updated_after_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ISO-8601"):
            MetadataFilters(updated_after="July 2")

    def test_structured_conflict_stops_answer_composition(self):
        conflict_documents = [
            KnowledgeDocument(
                document_id="KB-C1",
                title="Travel hotel ceiling policy",
                department="Finance",
                updated_at="2026-08-01",
                review_due_at="2026-12-31",
                claim_key="travel.hotel_ceiling",
                claim_value="CNY 500",
                content="The approved travel hotel ceiling is CNY 500 per night.",
            ),
            KnowledgeDocument(
                document_id="KB-C2",
                title="Travel hotel ceiling memo",
                department="Operations",
                updated_at="2026-08-02",
                review_due_at="2026-12-31",
                claim_key="travel.hotel_ceiling",
                claim_value="CNY 650",
                content="The approved travel hotel ceiling is CNY 650 per night.",
            ),
        ]

        result = KnowledgeAgent(conflict_documents).ask(
            "What is the approved travel hotel ceiling?",
            as_of_date="2026-08-14",
        )

        self.assertEqual(result["status"], "conflicting_evidence")
        self.assertTrue(result["needs_human_review"])
        self.assertEqual(result["evidence_assessment"]["conflicts"][0]["claim_key"], "travel.hotel_ceiling")
        self.assertEqual({item["document_id"] for item in result["citations"]}, {"KB-C1", "KB-C2"})
        self.assertEqual(result["trace"][-1]["tool"], "evidence_governance_gate")

    def test_stale_source_stops_answer_composition(self):
        stale_document = KnowledgeDocument(
            document_id="KB-OLD",
            title="Supplier quote rule",
            department="Procurement",
            updated_at="2025-01-01",
            review_due_at="2025-12-31",
            content="A purchase request requires three supplier quotes.",
        )

        result = KnowledgeAgent([stale_document]).ask(
            "How many supplier quotes are required?",
            as_of_date="2026-08-14",
        )

        self.assertEqual(result["status"], "stale_evidence")
        self.assertEqual(result["evidence_assessment"]["stale_sources"][0]["document_id"], "KB-OLD")
        self.assertEqual(result["confidence"]["label"], "not_applicable")

    def test_fresh_consistent_structured_claim_can_answer(self):
        current_document = KnowledgeDocument(
            document_id="KB-CURRENT",
            title="Current return window",
            department="Support",
            updated_at="2026-08-01",
            review_due_at="2026-12-31",
            claim_key="returns.window",
            claim_value="seven days",
            content="The current damaged product return window is seven days.",
        )

        result = KnowledgeAgent([current_document]).ask(
            "What is the damaged product return window?",
            as_of_date="2026-08-14",
        )

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["evidence_assessment"]["state"], "clear")

    def test_claim_metadata_must_be_complete(self):
        payload = documents()[0].to_dict()
        payload["claim_key"] = "returns.window"
        payload["claim_value"] = None

        with self.assertRaisesRegex(ValueError, "provided together"):
            KnowledgeDocument.from_mapping(payload)

    def test_governance_dates_must_be_iso_8601(self):
        payload = documents()[0].to_dict()
        payload["review_due_at"] = "end of year"

        with self.assertRaisesRegex(ValueError, "ISO-8601"):
            KnowledgeDocument.from_mapping(payload)

    def test_weak_unrelated_stale_hit_does_not_override_strong_current_evidence(self):
        current = KnowledgeDocument(
            document_id="KB-STRONG",
            title="Damaged product return evidence policy",
            department="Support",
            updated_at="2026-08-01",
            content="A damaged product return requires an order number and clear photo evidence.",
        )
        weak_stale = KnowledgeDocument(
            document_id="KB-WEAK",
            title="Legacy policy archive",
            department="Archive",
            updated_at="2024-01-01",
            content="This policy archive lists office forms.",
        )

        result = KnowledgeAgent([current, weak_stale]).ask(
            "What evidence is required by the damaged product return policy?",
            as_of_date="2026-08-14",
        )

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["evidence_assessment"]["assessed_document_ids"], ["KB-STRONG"])

    def test_future_dated_source_requires_review(self):
        future_document = KnowledgeDocument(
            document_id="KB-FUTURE",
            title="Future inventory policy",
            department="Supply Chain",
            updated_at="2026-09-01",
            content="The inventory safety stock policy requires fourteen days of cover.",
        )

        result = KnowledgeAgent([future_document]).ask(
            "What does the inventory safety stock policy require?",
            as_of_date="2026-08-14",
        )

        self.assertEqual(result["status"], "stale_evidence")
        self.assertEqual(result["evidence_assessment"]["future_dated_document_ids"], ["KB-FUTURE"])


if __name__ == "__main__":
    unittest.main()
