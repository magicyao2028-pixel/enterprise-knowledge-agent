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

The trial command validates the evidence index and external-component decisions, asks the reviewed urgent-complaint question, checks its top citation, exercises missing-evidence abstention, and replays a clearly synthetic punctuated-secret feedback case.

## Expected result

- `reports/trial_report.json` reports `overall_passed: true`;
- the urgent complaint answer cites `KB-SVC-002` and contains `30 minutes`;
- an unsupported parking-policy question returns `no_evidence` with no citation;
- `API-key`, plural and underscore secret variants are blocked before retrieval;
- no external request or model download occurs.

## Recovery

- `ModuleNotFoundError`: activate the environment and rerun `python -m pip install -e .`.
- Missing evidence path: restore the tracked artifact; do not weaken the index to conceal it.
- Changed citation: run the full tests and retrieval evaluation before changing expected evidence.

## Do not adopt when

- authentication, document-level authorization or tenant isolation is required immediately;
- the approved corpus lacks accountable owners, update dates or review processes;
- semantic retrieval, multilingual search or large-scale ingestion is a hard requirement;
- users expect the prototype to infer legal validity or resolve policy conflicts autonomously.

A real pilot still requires access control, private document review, ingestion monitoring, named knowledge owners and human verification before action.
