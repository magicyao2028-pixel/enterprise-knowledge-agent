# Handoff

## Current state

- Release stage: v0.6 trial-readiness prototype.
- Maintenance completed: M5/10.
- Core flow: validated corpus → query safety → metadata filter → stable chunking → lexical/local-vector/hybrid retrieval → freshness/conflict assessment → chunk-cited answer or governed abstention.
- Public data: synthetic only.
- Runtime cost: zero paid API dependency.

## Verification command

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m enterprise_knowledge_agent.cli "How quickly should an urgent complaint be escalated?"
PYTHONPATH=src python -m enterprise_knowledge_agent.evaluation_cli
PYTHONPATH=src python -m enterprise_knowledge_agent.trial_cli
PYTHONPATH=src python -m enterprise_knowledge_agent.evaluation_cli --retrieval-mode lexical
```

## M5 result

- Added `lexical`, `local_vector` and `hybrid` modes to the API and CLI.
- The local adapter is a deterministic token/character-ngram reranker with no third-party runtime dependency.
- Vector modes retain lexical evidence gating, preventing hash collisions from creating unsupported answers.
- The synthetic 12-case evaluation remains 12/12 for the lexical baseline; the report records all three mode results and their limitations.

## Next maintenance round

M6 can evaluate a reviewed local embedding model only if a zero-cost, license-compatible dependency and a larger benchmark are available. Keep lexical retrieval available and do not treat the current hashed reranker as semantic search.

## Known limitations

- English lexical retrieval and an optional local hashed-vector reranker;
- exact metadata filters are retrieval controls, not user authorization;
- small synthetic corpus;
- perfect fixture scores do not estimate production retrieval accuracy;
- extractive answer composition;
- conflict detection depends on curated `claim_key` and `claim_value` metadata;
- freshness thresholds identify review risk rather than policy validity;
- heuristic confidence is not calibrated;
- browser and Python implementations are mirrored manually;
- the browser demo remains lexical-only and does not claim parity with the optional Python vector modes;
- the secret boundary is a conservative pattern screen, not a complete data-loss-prevention system;
- no authentication, permissions, persistence, API or real user study.
