# Retrieval evaluation — 150-question expanded-corpus benchmark

This is an offline benchmark over the expanded corpus. Questions are stratified seed labels and carry `review_status=seeded_pending_human_review`; manually review them before submission.

| Mode | Hit rate@5 | MRR@5 | nDCG@5 | p50 latency (ms) |
|---|---:|---:|---:|---:|
| bm25 | 0.6133 | 0.4133 | 0.4552 | 6.2744 |
| dense | 0.6600 | 0.5130 | 0.5378 | 6.2497 |
| hybrid | 0.7067 | 0.5274 | 0.5630 | 6.2717 |
| hybrid_rerank | 0.6933 | 0.4789 | 0.5268 | 6.8546 |

Language hit@5 and multi-source recall:

- **bm25** — English=0.7200, Bahasa Indonesia=0.5067; multi-source=0.0
- **dense** — English=0.8800, Bahasa Indonesia=0.4400; multi-source=0.7
- **hybrid** — English=0.8133, Bahasa Indonesia=0.6000; multi-source=0.3
- **hybrid_rerank** — English=0.7867, Bahasa Indonesia=0.6000; multi-source=0.3
