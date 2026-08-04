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


if __name__ == "__main__":
    unittest.main()
