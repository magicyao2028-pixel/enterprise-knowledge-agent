from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .agent import KnowledgeAgent
from .models import KnowledgeDocument, MetadataFilters
from .retrieval import RetrievalMode


ACCESS_POLICY_SCHEMA_VERSION = "1.0"
_POLICY_FIELDS = {"schema_version", "policy_id", "source_type", "principals"}
_RULE_FIELDS = {"allowed_departments", "allowed_document_ids"}


@dataclass(frozen=True)
class PrincipalAccessRule:
    allowed_departments: tuple[str, ...]
    allowed_document_ids: tuple[str, ...]


@dataclass(frozen=True)
class AccessPolicy:
    policy_id: str
    source_type: str
    principals: dict[str, PrincipalAccessRule]

    @classmethod
    def from_mapping(cls, value: Any) -> "AccessPolicy":
        if not isinstance(value, dict):
            raise ValueError("Access policy must be a JSON object")
        if any(not isinstance(key, str) for key in value):
            raise ValueError("Access policy keys must be strings")
        missing = sorted(_POLICY_FIELDS.difference(value))
        unknown = sorted(set(value).difference(_POLICY_FIELDS))
        if missing or unknown:
            raise ValueError(
                "Access policy fields are invalid: "
                f"missing={missing or []}, unknown={unknown or []}"
            )
        if value["schema_version"] != ACCESS_POLICY_SCHEMA_VERSION:
            raise ValueError("Access policy schema_version must be 1.0")
        policy_id = value["policy_id"]
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise ValueError("Access policy_id must be a non-blank string")
        if value["source_type"] != "synthetic":
            raise ValueError("Public access policy source_type must be synthetic")
        raw_principals = value["principals"]
        if not isinstance(raw_principals, dict) or not raw_principals:
            raise ValueError("Access policy principals must be a non-empty object")

        principals: dict[str, PrincipalAccessRule] = {}
        seen_ids: set[str] = set()
        for principal_id, raw_rule in raw_principals.items():
            if (
                not isinstance(principal_id, str)
                or not principal_id.strip()
                or principal_id != principal_id.strip()
                or principal_id.casefold() in seen_ids
            ):
                raise ValueError("Access policy principal IDs must be unique non-blank strings")
            seen_ids.add(principal_id.casefold())
            if not isinstance(raw_rule, dict) or set(raw_rule) != _RULE_FIELDS:
                raise ValueError(
                    f"Access rule for {principal_id} must contain exactly "
                    "allowed_departments and allowed_document_ids"
                )
            departments = _strict_string_list(
                raw_rule["allowed_departments"],
                f"{principal_id}.allowed_departments",
            )
            document_ids = _strict_string_list(
                raw_rule["allowed_document_ids"],
                f"{principal_id}.allowed_document_ids",
            )
            if not departments and not document_ids:
                raise ValueError(f"Access rule for {principal_id} grants no documents")
            principals[principal_id] = PrincipalAccessRule(departments, document_ids)
        return cls(policy_id.strip(), "synthetic", principals)


def load_access_policy(path: Path) -> AccessPolicy:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid access policy JSON: {exc.msg}") from exc
    return AccessPolicy.from_mapping(value)


def prefilter_authorized_documents(
    documents: Iterable[KnowledgeDocument],
    policy: AccessPolicy,
    principal_id: str,
) -> tuple[list[KnowledgeDocument], dict[str, Any]]:
    """Apply one offline policy before retrieval and return a reviewable receipt."""
    source_documents = list(documents)
    if not source_documents:
        raise ValueError("Access-control input must contain at least one document")
    if not isinstance(principal_id, str) or not principal_id.strip():
        raise ValueError("principal_id must be a non-blank string")
    principal_id = principal_id.strip()
    rule = policy.principals.get(principal_id)
    if rule is None:
        return [], _authorization_receipt(
            policy,
            principal_id,
            authorized=False,
            reason="unknown_principal",
            rule=None,
            source_documents=source_documents,
            authorized_documents=[],
        )

    known_departments = {document.department.casefold() for document in source_documents}
    known_document_ids = {document.document_id for document in source_documents}
    unknown_departments = sorted(
        department
        for department in rule.allowed_departments
        if department.casefold() not in known_departments
    )
    unknown_document_ids = sorted(set(rule.allowed_document_ids).difference(known_document_ids))
    if unknown_departments or unknown_document_ids:
        raise ValueError(
            "Access policy references unknown corpus scope: "
            f"departments={unknown_departments}, document_ids={unknown_document_ids}"
        )

    department_scope = {item.casefold() for item in rule.allowed_departments}
    document_scope = set(rule.allowed_document_ids)
    authorized_documents = [
        document
        for document in source_documents
        if document.department.casefold() in department_scope
        or document.document_id in document_scope
    ]
    authorized = bool(authorized_documents)
    return authorized_documents, _authorization_receipt(
        policy,
        principal_id,
        authorized=authorized,
        reason="policy_match" if authorized else "no_authorized_documents",
        rule=rule,
        source_documents=source_documents,
        authorized_documents=authorized_documents,
    )


def ask_with_access_control(
    documents: Iterable[KnowledgeDocument],
    policy: AccessPolicy,
    principal_id: str,
    query: str,
    filters: MetadataFilters | None = None,
    *,
    top_k: int = 3,
    as_of_date: str | None = None,
    max_source_age_days: int = 90,
    retrieval_mode: RetrievalMode = "lexical",
) -> dict[str, object]:
    authorized_documents, receipt = prefilter_authorized_documents(
        documents, policy, principal_id
    )
    if not receipt["authorized"]:
        return {
            "query": query.strip() if isinstance(query, str) else query,
            "retrieval_mode": retrieval_mode,
            "status": "access_denied",
            "answer": "The offline document-access policy denied this caller claim.",
            "confidence": {"label": "not_applicable", "score": 0.0},
            "needs_human_review": True,
            "citations": [],
            "retrieved": [],
            "filters_applied": (filters or MetadataFilters()).to_dict(),
            "authorization_receipt": receipt,
            "trace": [
                {
                    "tool": "document_access_prefilter",
                    "purpose": "Apply the offline principal policy before retrieval.",
                    "status": "access_denied",
                }
            ],
        }

    response = KnowledgeAgent(authorized_documents, top_k=top_k).ask(
        query,
        filters,
        as_of_date=as_of_date,
        max_source_age_days=max_source_age_days,
        retrieval_mode=retrieval_mode,
    )
    response["authorization_receipt"] = receipt
    response["trace"].insert(
        0,
        {
            "tool": "document_access_prefilter",
            "purpose": "Apply the offline principal policy before retrieval.",
            "status": "authorized_scope_applied",
        },
    )
    return response


def _authorization_receipt(
    policy: AccessPolicy,
    principal_id: str,
    *,
    authorized: bool,
    reason: str,
    rule: PrincipalAccessRule | None,
    source_documents: list[KnowledgeDocument],
    authorized_documents: list[KnowledgeDocument],
) -> dict[str, Any]:
    return {
        "schema_version": ACCESS_POLICY_SCHEMA_VERSION,
        "policy_id": policy.policy_id,
        "policy_source_type": policy.source_type,
        "principal_id": principal_id,
        "principal_id_source": "caller_supplied",
        "authorized": authorized,
        "reason": reason,
        "allowed_departments": list(rule.allowed_departments) if rule else [],
        "allowed_document_ids": list(rule.allowed_document_ids) if rule else [],
        "authorized_document_ids": [
            document.document_id for document in authorized_documents
        ],
        "document_count_before": len(source_documents),
        "document_count_after": len(authorized_documents),
        "prefilter_applied_before_retrieval": True,
        "caller_claim_is_authentication": False,
        "authentication_performed": False,
        "identity_verified": False,
        "tenant_isolation_provided": False,
        "persistence_executed": False,
        "external_action_executed": False,
        "boundary": (
            "principal_id is a caller-supplied policy lookup claim; it is not "
            "authentication, identity verification or production authorization."
        ),
    }


def _strict_string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() or item != item.strip()
        for item in value
    ):
        raise ValueError(f"{field} must be a list of non-blank strings")
    folded = [item.casefold() for item in value]
    if len(folded) != len(set(folded)):
        raise ValueError(f"{field} must not contain duplicates")
    return tuple(value)


__all__ = [
    "ACCESS_POLICY_SCHEMA_VERSION",
    "AccessPolicy",
    "PrincipalAccessRule",
    "ask_with_access_control",
    "load_access_policy",
    "prefilter_authorized_documents",
]
