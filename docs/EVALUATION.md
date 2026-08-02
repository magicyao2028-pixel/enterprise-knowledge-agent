# Evaluation Plan

## Objective

Determine whether the Agent retrieves the right approved source, cites it correctly, and abstains when evidence is absent.

## Evaluation layers

### 1. Deterministic correctness

- valid documents load consistently;
- duplicate IDs and malformed corpora fail clearly;
- the same query and corpus produce the same ranking;
- answered responses always contain citations;
- unsupported responses contain no invented citation;
- sensitive requests are blocked before retrieval.

### 2. Retrieval quality

Build a reviewed set of at least 50 questions with expected document IDs and label each as answerable or unanswerable.

Measure:

- top-1 accuracy;
- top-3 recall;
- mean reciprocal rank;
- false retrieval rate for unanswerable questions;
- performance by department and document type.

### 3. Grounding and abstention

For every answer, a reviewer checks whether the excerpt supports the claim and whether the source metadata is correct.

Measure:

- citation correctness;
- unsupported statement count;
- abstention precision and recall;
- escalation appropriateness;
- stale-source detection rate in a later version.

### 4. User task study

Compare existing manual file search with the prototype using the same approved corpus.

Measure:

- time to locate the policy;
- percentage of tasks ending with the correct source;
- user confidence and perceived clarity;
- knowledge-owner correction rate.

## Initial acceptance cases

| Case | Expected result |
| --- | --- |
| Damaged product evidence question | `KB-RET-001` appears first with a citation. |
| Urgent complaint question | `KB-SVC-002` appears first. |
| Unknown parking policy | Abstain and request human review. |
| Private-key request | Block before retrieval. |
| Duplicate document ID | Reject corpus with a clear error. |

## v1.0 gate

A technical demo is not evidence of business value. Production claims require a reviewed private corpus, access-control tests, a measured query set, a security review and a controlled pilot.
