# Security and Governance

## Public prototype controls

- synthetic documents only;
- no model API or external request;
- conservative fail-safe pre-retrieval block for recognized password, passcode, passphrase, PIN, credential, key, secret, token, OTP, MFA-code and related sensitive-object categories, including common punctuation and plural variants; this deliberately over-blocks some informational questions and routes them to a human;
- evidence-free questions produce abstention rather than a fabricated answer;
- stale, future-dated or structurally conflicting evidence stops answer composition;
- all operational use requires human review.

## Threats not solved in v0.1

- document-level access control;
- prompt injection or malicious content inside uploaded documents;
- data exfiltration through a future model connector;
- semantic conflicts without structured claim metadata, and unauthorized policy versions;
- personal information detection and retention;
- account takeover, service abuse and denial of service.
- novel secret labels, obfuscation and semantic exfiltration beyond the explicit pre-retrieval patterns; this prototype is not a complete data-loss-prevention system.

## Required controls before a private pilot

1. Authenticate users and enforce department/document permissions before retrieval.
2. Encrypt stored documents and transport connections.
3. Version documents and identify an accountable knowledge owner.
4. Require claim-key ownership, review deadlines and an approved source-of-truth resolution process.
5. Log query, retrieved sources, response, approval and feedback without exposing secrets.
6. Apply retention, deletion and incident-response procedures.
7. Red-team document injection, permission bypass and unsupported-answer behavior.
8. Keep high-impact actions outside the Agent and require authorized approval.

Never commit credentials, customer data, employee records or proprietary internal documents to this public repository.
