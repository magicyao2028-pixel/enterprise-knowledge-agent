# Handoff

## Current state

- Release stage: v0.2 product-validation prototype.
- Maintenance completed: M1/10.
- Core flow: validated corpus → query safety → lexical retrieval → evidence gate → cited answer or abstention.
- Public data: synthetic only.
- Runtime cost: zero paid API dependency.

## Verification command

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m enterprise_knowledge_agent.cli "How quickly should an urgent complaint be escalated?"
PYTHONPATH=src python -m enterprise_knowledge_agent.evaluation_cli
```

## Next maintenance round

M2 should add document chunking and metadata filters while preserving the current lexical baseline for comparison. It should not add a vector database yet.

## Known limitations

- English lexical retrieval only;
- small synthetic corpus;
- perfect fixture scores do not estimate production retrieval accuracy;
- extractive answer composition;
- heuristic confidence is not calibrated;
- browser and Python implementations are mirrored manually;
- no authentication, permissions, persistence, API or real user study.
