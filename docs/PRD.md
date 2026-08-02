# Product Requirements Document

## 1. Document control

| Field | Value |
| --- | --- |
| Product | Enterprise Knowledge Agent |
| Version | 0.1 |
| Status | Product-validation MVP |
| Primary user | Employee in a small or medium-sized business |
| Public data policy | Synthetic documents only |

## 2. Problem statement

Employees lose time searching scattered procedures and can receive inconsistent answers. A useful AI application must show where an answer came from, refuse unsupported questions, preserve knowledge freshness metadata, and keep decision authority with a human.

## 3. Product hypothesis

If an employee can ask one question and receive a short answer with exact source metadata, they can identify the relevant internal procedure faster while a visible evidence gate reduces unsupported answers.

This hypothesis has not been validated with real users. v0.1 tests technical behavior only.

## 4. Users and jobs to be done

### Employee

- find the relevant policy without searching several files;
- see the exact source and last-updated date;
- know when the system lacks evidence;
- escalate ambiguous decisions to a knowledge owner.

### Knowledge owner

- review which document supported an answer;
- identify stale, missing or conflicting content;
- retain control over policy changes and high-impact decisions.

## 5. v0.1 scope

### In scope

1. Load a validated local JSON corpus.
2. Accept an English-language question.
3. Rank documents using transparent lexical evidence.
4. Compose an extractive answer from retrieved text.
5. Attach document ID, title, department and update date.
6. Abstain when the corpus has no matching evidence.
7. Block explicit requests for secrets or credentials.
8. Preserve an Agent execution trace.

### Out of scope

- semantic embeddings, vector databases or paid model calls;
- automatic ingestion from private drives or chat systems;
- user authentication, authorization and document-level permissions;
- multilingual retrieval;
- model-generated summaries or legal/financial decisions;
- production availability or measured business impact.

## 6. Functional requirements

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-01 | Load corpus | Must | Valid documents load; empty, malformed or duplicate-ID corpora fail clearly. |
| FR-02 | Retrieve evidence | Must | A known query ranks the expected document first. |
| FR-03 | Cite sources | Must | An answered response contains source metadata. |
| FR-04 | Abstain | Must | An unsupported question produces no citation and requests human review. |
| FR-05 | Protect secrets | Must | An explicit secret request is blocked before retrieval. |
| FR-06 | Expose trace | Should | Response lists the executed workflow steps and status. |
| FR-07 | Export JSON | Should | CLI writes a structured answer when `--output` is supplied. |

## 7. Success metrics for a future pilot

- top-1 and top-3 retrieval accuracy on a reviewed question set;
- citation correctness;
- unsupported-answer rate and abstention precision;
- median time to find the approved source;
- knowledge-owner acceptance/modification rate;
- stale-document incidents.

## 8. Release gate

Do not claim time savings, accuracy improvement, production use or employee adoption until a controlled private pilot establishes baseline and post-use evidence.
