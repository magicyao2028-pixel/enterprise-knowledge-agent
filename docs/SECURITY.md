# Security and Governance

## Public prototype controls

- synthetic documents only;
- no model API or external request;
- explicit block for common credential and secret requests;
- evidence-free questions produce abstention rather than a fabricated answer;
- all operational use requires human review.

## Threats not solved in v0.1

- document-level access control;
- prompt injection or malicious content inside uploaded documents;
- data exfiltration through a future model connector;
- conflicting, obsolete or unauthorized policy versions;
- personal information detection and retention;
- account takeover, service abuse and denial of service.

## Required controls before a private pilot

1. Authenticate users and enforce department/document permissions before retrieval.
2. Encrypt stored documents and transport connections.
3. Version documents and identify an accountable knowledge owner.
4. Log query, retrieved sources, response, approval and feedback without exposing secrets.
5. Apply retention, deletion and incident-response procedures.
6. Red-team document injection, permission bypass and unsupported-answer behavior.
7. Keep high-impact actions outside the Agent and require authorized approval.

Never commit credentials, customer data, employee records or proprietary internal documents to this public repository.
