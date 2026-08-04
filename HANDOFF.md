# Handoff

## Current state

- Release stage: v0.3 product-validation prototype.
- Maintenance completed: M2/10.
- Core flow: validated corpus → query safety → metadata filter → stable chunking → lexical retrieval → evidence gate → chunk-cited answer or abstention.
- Public data: synthetic only.
- Runtime cost: zero paid API dependency.

## Verification command

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m enterprise_knowledge_agent.cli "How quickly should an urgent complaint be escalated?"
PYTHONPATH=src python -m enterprise_knowledge_agent.evaluation_cli
```

## Next maintenance round

M3 should add conflicting-source and freshness handling. It should surface ambiguity and stale evidence rather than adding a vector database yet.

## Known limitations

- English lexical retrieval only;
- exact metadata filters are retrieval controls, not user authorization;
- small synthetic corpus;
- perfect fixture scores do not estimate production retrieval accuracy;
- extractive answer composition;
- heuristic confidence is not calibrated;
- browser and Python implementations are mirrored manually;
- no authentication, permissions, persistence, API or real user study.
