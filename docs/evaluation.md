# Evaluation

Run the offline checks from a locked checkout:

```bash
make eval
PYTHONPATH=. uv run python evaluation/eval_gold_review_30_retrieval.py
make validate-sources
uv run ruff check .
```

## Retrieval

`evaluation/gold_review_30_final.jsonl` contains 30 bilingual questions with
completed human review of relevant structure-aware chunks. The evaluator maps a
reviewed chunk to its parent document rank and writes
`evaluation/results/retrieval_gold_review_30.json` and CSV.

The primary comparison is the `document_rag` slice: routes expected to use
documentary evidence. Typed measurement, index, and abstention routes remain in
the all-system set and are checked separately through deterministic tool and
safety contracts. The artifact names the exact route list used for the slice.
The selected `hybrid` method is configured by `RETRIEVAL_MODE=hybrid` in the
environment template and is used by the API, NiceGUI, and local compatibility
UI unless a supported value is explicitly supplied.

The all-system hybrid result has question hit@5 of 0.6667 and chunk recall@5 of
0.5789. Its English hit@5 is 0.8667 and Bahasa Indonesia hit@5 is 0.4667; the
four multi-turn questions have hit@5 of 0.25. This is an important limitation,
not a claim of equal bilingual quality. The follow-up work is to expand reviewed
Bahasa Indonesia evidence and inspect retrieval failures before changing the
selected method.

## Answer generation

`app.provider.PROMPTS` is the single source for generation prompt variants.
The runtime uses `PROMPT_VARIANT=strict` by default and records `strict-v1` in
answer telemetry. `evaluation/eval_generation.py` imports those exact strings;
it does not maintain separate shortened prompts.

The offline fallback and provider outputs are **heuristic contract checks**. They measure
non-empty output, citation-token structure, numeric consistency, safety, and a
simple Bahasa signal. They do not judge semantic relevance, factual
groundedness, completeness of every claim, or user usefulness. Provider calls
are never made by ordinary tests. The result artifact also records a shared
prompt regression contract: the selected variant/version and stable hashes for
the exact runtime/evaluator prompt strings. The deterministic fallback does not
invoke a model, so it is not presented as a prompt-arm comparison. When an
approved configured provider key is
available, bound a rerun explicitly, for example:

```bash
GENERATION_PROVIDER_LIMIT=2 uv run python -m evaluation.eval_generation
```

This command sends two representative cases through each named prompt variant
for the configured model, records the exact prompt version, and writes
`evaluation/results/generation_results.json`. Inspect the answers as well as the
heuristics; a small bounded run does not establish broad performance.

## Other contracts

`eval_tools.py` covers deterministic route arguments, numeric/unit consistency,
freshness, missing data, and unsupported calculations. `eval_abstention.py`
checks safety and out-of-domain refusals. `eval_conversation.py` checks bounded
two- and three-turn follow-ups. `eval_ingestion.py` runs isolated demo ingests
to verify validation and idempotency. `make validate-sources` verifies required
source provenance fields.

Use `make export-review` to create a spreadsheet-friendly review sheet. The
finalizer accepts only completed review rows and validates every reviewed chunk
ID against the current corpus.
