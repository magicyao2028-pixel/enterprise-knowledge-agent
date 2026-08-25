# Retrieval Evaluation Baseline

> Synthetic reviewed query set. Results are regression evidence, not production accuracy claims.

- Retrieval mode: `lexical`

## Summary

| Metric | Result |
| --- | --- |
| Cases passed | 15/16 |
| Status accuracy | 100% |
| Top-1 document accuracy | 92% |
| Top-3 document recall | 100% |
| Mean reciprocal rank | 0.958 |
| Abstention accuracy | 100% |
| Blocked-request accuracy | 100% |

## Cases

| Case | Expected | Actual | Expected source rank | Result |
| --- | --- | --- | --- | --- |
| `RET_EVIDENCE` | answered | answered | 1 | PASS |
| `RET_DEADLINE` | answered | answered | 1 | PASS |
| `SVC_URGENT` | answered | answered | 1 | PASS |
| `SVC_REPEAT` | answered | answered | 1 | PASS |
| `INV_INPUTS` | answered | answered | 1 | PASS |
| `INV_APPROVAL` | answered | answered | 1 | PASS |
| `CNT_CHECKS` | answered | answered | 1 | PASS |
| `CNT_RECORDS` | answered | answered | 1 | PASS |
| `RET_VIDEO` | answered | answered | 2 | FAIL |
| `SVC_RECORD` | answered | answered | 1 | PASS |
| `INV_TERMS` | answered | answered | 1 | PASS |
| `CNT_OWNER` | answered | answered | 1 | PASS |
| `NO_PARKING` | no_evidence | no_evidence | — | PASS |
| `NO_TRAVEL` | no_evidence | no_evidence | — | PASS |
| `NO_VPN` | no_evidence | no_evidence | — | PASS |
| `BLOCK_SECRET` | blocked | blocked | — | PASS |
## Retrieval-mode comparison

| Mode | Passed | Top-1 | Top-3 | MRR |
| --- | --- | --- | --- | --- |
| `lexical` | 15/16 | 92% | 100% | 0.958 |
| `local_vector` | 16/16 | 100% | 100% | 1.000 |
| `hybrid` | 16/16 | 100% | 100% | 1.000 |

## Interpretation boundary

- The corpus contains four synthetic documents and the questions were reviewed against those documents.
- A perfect fixture score can reveal regressions but cannot estimate production performance.
- Real deployment requires permission-aware retrieval, larger private test sets and knowledge-owner review.
