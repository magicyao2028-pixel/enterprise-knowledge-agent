import json
import unittest
from copy import deepcopy
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from enterprise_knowledge_agent import (
    AccessPolicy,
    MetadataFilters,
    __version__,
    ask_with_access_control,
    load_access_policy,
    load_documents,
)
from enterprise_knowledge_agent.cli import parse_args


ROOT = Path(__file__).parents[1]


class AccessControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = load_documents(ROOT / "data" / "knowledge.json")
        cls.policy = load_access_policy(ROOT / "data" / "access_policy.json")

    def test_department_policy_prefilters_before_retrieval(self):
        result = ask_with_access_control(
            self.documents,
            self.policy,
            "customer-operations-reviewer",
            "How quickly should an urgent complaint be escalated?",
            as_of_date="2026-08-17",
        )
        receipt = result["authorization_receipt"]

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"][0]["document_id"], "KB-SVC-002")
        self.assertEqual(
            {item["department"] for item in result["retrieved"]},
            {"Customer Operations"},
        )
        self.assertEqual(receipt["document_count_before"], 4)
        self.assertEqual(receipt["document_count_after"], 2)
        self.assertEqual(receipt["principal_id_source"], "caller_supplied")
        self.assertTrue(receipt["prefilter_applied_before_retrieval"])
        self.assertFalse(receipt["authentication_performed"])
        self.assertFalse(receipt["identity_verified"])
        self.assertFalse(receipt["tenant_isolation_provided"])
        self.assertFalse(receipt["persistence_executed"])
        self.assertFalse(receipt["external_action_executed"])
        self.assertFalse(receipt["caller_claim_is_authentication"])

    def test_document_id_policy_grants_only_named_document(self):
        result = ask_with_access_control(
            self.documents,
            self.policy,
            "content-checklist-reviewer",
            "What must be reviewed before AI-generated content is published?",
            as_of_date="2026-08-17",
        )
        self.assertEqual(result["status"], "answered")
        self.assertEqual(
            result["authorization_receipt"]["authorized_document_ids"],
            ["KB-CNT-004"],
        )
        self.assertEqual(
            {item["document_id"] for item in result["citations"]},
            {"KB-CNT-004"},
        )

    @patch("enterprise_knowledge_agent.agent.search_documents")
    def test_unknown_principal_is_denied_without_retrieval(self, search_documents):
        result = ask_with_access_control(
            self.documents,
            self.policy,
            "unknown-principal",
            "What is the inventory policy?",
        )
        self.assertEqual(result["status"], "access_denied")
        self.assertEqual(result["citations"], [])
        self.assertFalse(result["authorization_receipt"]["authorized"])
        self.assertEqual(
            result["authorization_receipt"]["reason"], "unknown_principal"
        )
        search_documents.assert_not_called()

    def test_authorized_scope_cannot_retrieve_another_department(self):
        result = ask_with_access_control(
            self.documents,
            self.policy,
            "customer-operations-reviewer",
            "What must be reviewed before AI-generated content is published?",
            MetadataFilters(departments=("Content Operations",)),
            as_of_date="2026-08-17",
        )
        self.assertEqual(result["status"], "no_evidence")
        self.assertEqual(result["citations"], [])
        self.assertNotIn("KB-CNT-004", result["authorization_receipt"]["authorized_document_ids"])

    def test_policy_is_strict_and_rejects_unknown_corpus_scope(self):
        raw = json.loads((ROOT / "data" / "access_policy.json").read_text(encoding="utf-8"))
        changed = deepcopy(raw)
        changed["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "fields are invalid"):
            AccessPolicy.from_mapping(changed)

        changed = deepcopy(raw)
        changed["principals"]["customer-operations-reviewer"]["allowed_departments"] = [
            "Customer Operations",
            "customer operations",
        ]
        with self.assertRaisesRegex(ValueError, "must not contain duplicates"):
            AccessPolicy.from_mapping(changed)

        changed = deepcopy(raw)
        changed["principals"]["customer-operations-reviewer"]["allowed_document_ids"] = [
            "KB-UNKNOWN"
        ]
        policy = AccessPolicy.from_mapping(changed)
        with self.assertRaisesRegex(ValueError, "unknown corpus scope"):
            ask_with_access_control(self.documents, policy, "customer-operations-reviewer", "question")

    def test_cli_requires_policy_and_principal_together(self):
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                parse_args(["question", "--access-policy", "data/access_policy.json"])
            with self.assertRaises(SystemExit):
                parse_args(["question", "--principal-id", "customer-operations-reviewer"])
            with self.assertRaises(SystemExit):
                parse_args(["question", "--department", "Customer Operations"])

        parsed = parse_args(
            [
                "question",
                "--department",
                "Customer Operations",
                "--access-policy",
                "data/access_policy.json",
                "--principal-id",
                "customer-operations-reviewer",
            ]
        )
        self.assertEqual(parsed.principal_id, "customer-operations-reviewer")

    def test_policy_file_round_trip_is_deterministic(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            raw = (ROOT / "data" / "access_policy.json").read_text(encoding="utf-8")
            path.write_text(raw, encoding="utf-8")
            loaded = load_access_policy(path)
        self.assertEqual(loaded, self.policy)

    def test_release_version_is_consistent(self):
        project_metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(__version__, "1.1.0")
        self.assertIn('version = "1.1.0"', project_metadata)


if __name__ == "__main__":
    unittest.main()
