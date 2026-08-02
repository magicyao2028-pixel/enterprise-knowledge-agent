# Handoff

## Current state

- Release stage: v0.1 product-validation prototype.
- Maintenance completed: 0/10.
- Core flow: validated corpus → query safety → lexical retrieval → evidence gate → cited answer or abstention.
- Public data: synthetic only.
- Runtime cost: zero paid API dependency.

## Verification command

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m enterprise_knowledge_agent.cli "How quickly should an urgent complaint be escalated?"
```

## Next maintenance round

M1 should add a reviewed query dataset and generate a reproducible retrieval-quality report. It should retain lexical retrieval as the baseline and should not add a vector database yet.

## Known limitations

- English lexical retrieval only;
- small synthetic corpus;
- extractive answer composition;
- heuristic confidence is not calibrated;
- browser and Python implementations are mirrored manually;
- no authentication, permissions, persistence, API or real user study.
