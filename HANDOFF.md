# Handoff

## Current state

- Release stage: v1.1 post-M10 boundary-hardening prototype.
- Maintenance completed: M10/10.
- Post-M10 P2 Slot 2: strict synthetic principal policy → fail-closed department/document prefilter → query safety → metadata filter → stable chunking → lexical/local-vector/hybrid retrieval → freshness/conflict assessment → chunk-cited answer or governed abstention.
- Public data: synthetic only.
- Runtime cost: zero paid API dependency.

## Verification command

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m enterprise_knowledge_agent.cli "How quickly should an urgent complaint be escalated?"
PYTHONPATH=src python -m enterprise_knowledge_agent.cli "How quickly should an urgent complaint be escalated?" --access-policy data/access_policy.json --principal-id customer-operations-reviewer
PYTHONPATH=src python -m enterprise_knowledge_agent.evaluation_cli
PYTHONPATH=src python -m enterprise_knowledge_agent.trial_cli
PYTHONPATH=src python -m enterprise_knowledge_agent.evaluation_cli --retrieval-mode lexical
```

## M5 result

- Added `lexical`, `local_vector` and `hybrid` modes to the API and CLI.
- The local adapter is a deterministic token/character-ngram reranker with no third-party runtime dependency.
- Vector modes retain lexical evidence gating, preventing hash collisions from creating unsupported answers.
- The synthetic 12-case evaluation remains 12/12 for the lexical baseline; the report records all three mode results and their limitations.

## M6 result

- Added a larger 16-case synthetic benchmark covering four additional answerable queries while retaining three abstention/safety cases.
- The benchmark records lexical, local-vector and hybrid comparisons: lexical 15/16, local-vector 16/16 and hybrid 16/16 on this fixture.
- No embedding model dependency was adopted; the existing hashed reranker remains explicitly non-semantic and the lexical baseline remains available.

## M7 result

- Added a fail-closed embedding-candidate gate for repository/license metadata, reviewed local model-artifact availability and non-regressing benchmark metrics.
- Screened the public candidate fixture without installing or downloading a model; the lexical baseline and hashed reranker remain available.
- A candidate can become eligible only for a separately approved bounded pilot; the gate never installs dependencies or performs external actions.

## M8 result

- Added a deterministic owner-review queue for stale and structured-conflict documents.
- Queue items retain department ownership, reason codes, priority and a bounded next action.
- The queue is review-only: it does not mutate evidence, documents or retrieval behavior and performs no external action.

## Post-M10 P2 result

- Added `access_control.py` and a strict synthetic policy fixture mapping caller claims to allowed departments and/or document IDs.
- The authorized subset is selected before `KnowledgeAgent` can retrieve; an unknown principal returns `access_denied` with no citation and no retrieval call.
- `--access-policy` and `--principal-id` are paired CLI inputs. Department scoping cannot be presented as protected without them.
- Every protected response includes a deterministic receipt stating that the principal is caller supplied and that authentication, identity verification and tenant isolation were not performed.
- This is offline boundary evidence only. A real service must bind the principal to an authenticated identity and enforce production authorization outside this package.

## Next maintenance round

Post-M10 P2 Slot 2 is complete. Do not start another maintenance wave without a separately confirmed contract. Keep lexical retrieval available and do not treat the current hashed reranker as semantic search.

## M9 result

- Added a chronological owner-review history summary tied to queued document IDs.
- Duplicate IDs, unknown documents, invalid decisions and out-of-order dates fail closed.
- Decisions remain advisory: evidence, documents and retrieval are not mutated and no external action is executed.
- M10: added owner-feedback replay linked to review history; accepted feedback is visible while pending/rejected items are excluded and approval remains false.

## Known limitations

- English lexical retrieval and an optional local hashed-vector reranker;
- the access-policy fixture is an offline document-scope simulation, not authentication or production authorization;
- small synthetic corpus;
- perfect fixture scores do not estimate production retrieval accuracy;
- extractive answer composition;
- conflict detection depends on curated `claim_key` and `claim_value` metadata;
- freshness thresholds identify review risk rather than policy validity;
- heuristic confidence is not calibrated;
- browser and Python implementations are mirrored manually;
- the browser demo remains lexical-only and does not claim parity with the optional Python vector modes;
- the secret boundary is a conservative pattern screen, not a complete data-loss-prevention system;
- no authentication, verified identity, tenant isolation, persistence, service API or real user study.
