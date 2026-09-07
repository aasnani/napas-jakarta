# Evaluation

Run `make eval` to regenerate the committed retrieval and generation artifacts.
Run `python -m ingestion.corpus` to regenerate the document/chunk inventory and
`data/index/corpus_report.json`; it records manifest/local identity mismatches,
duplicate checksums, rejection diagnostics and the corpus fingerprint.
The committed retrieval set now contains 150 stratified seed questions. Each
row is explicitly marked `seeded_pending_human_review`; manually review and
correct the questions and relevance labels before submission. The benchmark
reports hit@5, MRR, nDCG, and p50 latency while retaining the planned categories.

Use `make export-review` to create a spreadsheet-friendly review sheet. After
filling `reviewed_relevant_document_ids`, apply it to a separate artifact:

```bash
uv run python -m evaluation.review_ground_truth \
  --apply evaluation/ground_truth_review.csv \
  --reviewer YOUR_NAME \
  --output evaluation/ground_truth_reviewed.jsonl
```

Blank decisions remain pending and the committed seed file is never overwritten.

For a compact review pass, run `PYTHONPATH=. python evaluation/build_gold_review_30.py`
to regenerate the 30-row packet and evidence from the frozen corpus. The
packet records its corpus and chunk fingerprints, all four local retrieval
modes, proposed chunk locators, and blank human fields. Use the focused
workbook's `Start Here` sheet for progress and `Evidence` to inspect passages;
do not mix its results with the 120-row development pool. The finalizer in
`evaluation/finalize_gold_review.py` accepts only a complete CSV export with
no `Pending` rows and checks every human chunk ID against `data/index/chunks.jsonl`.
Run `make validate-sources` to check that every manifest entry has the required
provenance, legal-status, geographic-scope, and checksum fields.
Validate the resulting artifact with `uv run python -m evaluation.validate_ground_truth
--input evaluation/ground_truth_reviewed.jsonl` before using it in the benchmark.

`evaluation/results/retrieval_results.json` records the expanded-v1 corpus
fingerprint and all four retrieval arms, including nDCG@5 and p50 latency. The
current production choice is `hybrid` because it leads on MRR and nDCG; the
shipped default is synchronized in `.env.example`, `app/api.py`, and `app/rag.py`.
`generation_results.json` is an offline contract harness covering the expanded
154-case local set (150 benchmark rows plus four core contract cases),
citations, route selection, and health-safety refusal; provider-backed model/prompt arms
require an explicitly configured `OPENAI_API_KEY`.
The app also supports Claude's native Messages API: set `LLM_PROVIDER=anthropic`,
`ANTHROPIC_API_KEY`, and `LLM_MODEL=claude-haiku-4-5-20251001` in the local
`.env` file. The key is never read from committed files.
It also records two deterministic prompt arms and their selected winner so the
comparison is reproducible without network access; these fallback results must
be replaced or supplemented with provider-backed outputs before claiming an
LLM score.
The answer contract distinguishes unknown citations from citation omissions:
`contract_valid` is true only when citations are both supplied and drawn from
the retrieved evidence.
Exact citations use `[source-id § locator]` and response `citations` records map
each claim to a retrieved `source_id`, `chunk_id`, locator, excerpt and URL.
`citation_validation` rejects unknown chunks/locators; `app.citations` keeps
legacy tokens parseable for existing clients. Current claim-level human review
and provider-backed groundedness scores are pending and must not be inferred
from the offline retrieval or fallback artifacts.
The deterministic fallback includes targeted ISPU/category and WHO-versus-law
answers, so these contract metrics remain meaningful even without an API key.
When configured, `eval_generation.py` runs two temperature-zero prompt arms and
optionally a second model from `LLM_MODEL_2`, always against the same retrieved
context, and records outputs for manual/judge assessment. It never calls a provider
during ordinary tests.
The OpenAI-compatible provider path has a mocked contract test (including base
URL, timeout, retry, model, and language parameters); provider failures return
to the deterministic cited fallback.
With the local Claude configuration, a bounded four-question provider smoke
run was completed using `claude-haiku-4-5-20251001`; its two prompt arms are
saved in `evaluation/results/generation_provider_claude_smoke.json`. Larger
provider runs should be scheduled with an appropriate request budget/rate
limit rather than launched accidentally from an offline test.
The latest bounded provider artifact contains 10 representative intent-group
cases per arm (20 requests) using Claude Haiku 4.5. The strict arm scored 1.0
on relevance, citation, numeric consistency, and safety, with 0.9 on the
language heuristic; the helpful arm scored 0.7 citation correctness and 0.6
citation completeness. The strict arm is therefore the current prompt choice.
`GENERATION_PROVIDER_LIMIT` controls this budget when rerunning the provider arm.

`eval_tools.py` evaluates 50 stratified route cases and checks latest and
historical tool execution, argument resolution, numeric/unit consistency,
metadata completeness, staleness detection, missing-data behavior, and
rejection of unsupported calculations. It also records p50/p95 route latency
and p50 latest-tool latency. `eval_rewrite.py` compares rewriting
off versus deterministic Jakarta abbreviation normalization. These are local
contract benchmarks; the final submission should add human-reviewed examples
and measured latency slices.
`eval_chunking.py` runs the fixed/structure/semantic chunker comparison through
the dense retrieval protocol and commits its result for the final decision.
`eval_abstention.py` evaluates 18 safety and out-of-domain cases and verifies
that refusals do not fabricate citations.
`eval_conversation.py` evaluates 29 representative two- and three-turn follow-ups,
including district comparison, topic carry-over, policy status, and vulnerable-
group safety context. It verifies standalone-query resolution and route
selection, including topic switches and carried-forward entities.
`eval_ingestion.py` runs two isolated demo ingestions and records stable
fingerprints, accepted rows, and validation errors in `ingestion_results.json`.
Generation cases include both English and Bahasa Indonesia; provider-backed
runs can be sliced by the recorded `language` field.
