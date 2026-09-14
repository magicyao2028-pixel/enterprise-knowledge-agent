# Reviewer Trial Guide

This is a 10–20 minute offline trial using a synthetic knowledge corpus. It demonstrates citation, abstention and governance behavior, not enterprise retrieval accuracy or production adoption.

## Clean start

Requirements: Python 3.10 or later. No paid API, model download, database or external account is required.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
knowledge-agent-trial
python -m unittest discover -s tests -v
```

The trial command validates the evidence index and external-component decisions, applies the synthetic access policy before the reviewed urgent-complaint lookup, checks its top citation, denies an unknown principal without retrieval, blocks a cross-scope department lookup, verifies a one-document grant, exercises missing-evidence abstention, and replays clearly synthetic common-credential and punctuation-bypass cases.

## Expected result

- `reports/trial_report.json` reports `overall_passed: true`;
- `access_control.passed` is true; the unknown principal returns `access_denied`, the cross-scope probe returns `no_evidence`, and the document grant cites only `KB-CNT-004`;
- the authorization receipt states that the prefilter ran before retrieval and that authentication, identity verification and tenant isolation remain false;
- the urgent complaint answer cites `KB-SVC-002` and contains `30 minutes`;
- an unsupported parking-policy question returns `no_evidence` with no citation;
- common client-secret, token, passcode, passphrase and PIN requests plus API-key punctuation variants are blocked before retrieval;
- no external request or model download occurs.

## Recovery

- `ModuleNotFoundError`: activate the environment and rerun `python -m pip install -e .`.
- Missing evidence path: restore the tracked artifact; do not weaken the index to conceal it.
- Changed citation: run the full tests and retrieval evaluation before changing expected evidence.
- Access-policy validation error: restore `data/access_policy.json`; do not relax unknown-field, duplicate-scope or unknown-corpus checks.

## Do not adopt when

- authentication, identity-bound production authorization or tenant isolation is required immediately;
- the approved corpus lacks accountable owners, update dates or review processes;
- semantic retrieval, multilingual search or large-scale ingestion is a hard requirement;
- users expect the prototype to infer legal validity or resolve policy conflicts autonomously.

A real pilot still requires authenticated identity, server-owned authorization policy, tenant isolation, private document review, ingestion monitoring, named knowledge owners and human verification before action. The caller-supplied principal in this trial is not authentication.
