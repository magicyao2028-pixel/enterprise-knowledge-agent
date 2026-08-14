# Handoff

## Current state

- Release stage: v0.4 product-validation prototype.
- Maintenance completed: M3/10.
- Core flow: validated corpus → query safety → metadata filter → stable chunking → lexical retrieval → freshness/conflict assessment → chunk-cited answer or governed abstention.
- Public data: synthetic only.
- Runtime cost: zero paid API dependency.

## Verification command

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m enterprise_knowledge_agent.cli "How quickly should an urgent complaint be escalated?"
PYTHONPATH=src python -m enterprise_knowledge_agent.evaluation_cli
```

## Next maintenance round

M4 should add an optional local embedding adapter and compare it with the current lexical baseline. Keep lexical retrieval available, use no paid API and report fixture limitations.

## Known limitations

- English lexical retrieval only;
- exact metadata filters are retrieval controls, not user authorization;
- small synthetic corpus;
- perfect fixture scores do not estimate production retrieval accuracy;
- extractive answer composition;
- conflict detection depends on curated `claim_key` and `claim_value` metadata;
- freshness thresholds identify review risk rather than policy validity;
- heuristic confidence is not calibrated;
- browser and Python implementations are mirrored manually;
- no authentication, permissions, persistence, API or real user study.
