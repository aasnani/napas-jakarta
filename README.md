<p align="center">
  <img src="assets/napas-jakarta-air-icon.png" width="104" alt="Napas Jakarta air-quality mark">
</p>

<h1 align="center">Napas Jakarta</h1>

<p align="center"><strong>Understand Jakarta’s air, why it changes, and what you can do next.</strong></p>

<p align="center">
  A bilingual, citation-grounded companion for current station observations,
  city-level air-quality context, policy, and practical exposure reduction.
</p>

<p align="center">
  <a href="https://web-production-e07b9.up.railway.app"><strong>Open the live app →</strong></a>
  · <a href="https://web-production-e07b9.up.railway.app/docs">API</a>
  · <a href="https://web-production-e07b9.up.railway.app/monitoring">Monitoring</a>
  · <a href="https://web-production-e07b9.up.railway.app/health">Health</a>
</p>

[![Tests](https://github.com/aasnani/napas-jakarta/actions/workflows/test.yml/badge.svg)](https://github.com/aasnani/napas-jakarta/actions/workflows/test.yml)

<details>
<summary>Contents</summary>

- [Why Jakarta needs this](#why-jakarta-needs-this)
- [What residents can do here](#what-residents-can-do-here)
- [Data you can trust—and its boundaries](#data-you-can-trustand-its-boundaries)
- [How a question becomes an answer](#how-a-question-becomes-an-answer)
- [Run locally](#run-locally)
- [Evaluation and reliability](#evaluation-and-reliability)
- [Deploy and operate](#deploy-and-operate)
</details>

## Why Jakarta needs this

Jakarta faces persistent particulate-pollution risk and recurring unhealthy-air episodes, often intensified in the dry season. This is **not** a claim of a simple, proven year-on-year decline: daily conditions also change with rainfall, wind, atmospheric mixing, season, and emissions from the wider Jakarta airshed. DKI’s 2020 emissions inventory attributed 67.03% of Jakarta’s PM₂.₅ emissions to transport. A separate 2019–2020 receptor study estimated transport’s share of measured PM₂.₅ at 32–57%, depending on sampling location and season; it also identified coal combustion, construction, open burning, soil, and road dust. [DKI inventory and source-apportionment summary](https://rendahemisi.jakarta.go.id/learn) · [DKI/ITB/Vital Strategies study summary](https://rendahemisi.jakarta.go.id/article/37/mencari-sumber-polusi-di-udara-melalui-source-apportionment)

A bare ISPU number cannot answer a resident’s everyday questions: *Where was it measured? When? Is it a station reading or city-level context? Why might it be elevated? What is actually in force, and what practical step is proportionate today?* Napas Jakarta connects local readings and timestamps with separately labelled historical context and cited public-health and policy evidence. It helps residents stay informed, reduce avoidable exposure, and understand ways to support cleaner air—without pretending individual action can replace emission control. [DKI dry-season guidance](https://lingkunganhidup.jakarta.go.id/detail-artikel/masuki-musim-kemarau-pemprov-dki-minta-masyarakat-waspadai-penurunan-kualitas-udara) · [WHO on personal interventions and emissions reduction](https://www.who.int/news-room/questions-and-answers/item/air-pollution-personal-interventions-and-risk-communication)

## What residents can do here

- **Check a nearby reading.** Explore the latest available station snapshot by district, pollutant, category, and freshness; each result keeps its location and observation time visible.
- **Understand the number.** See what ISPU, PM₂.₅, and PM₁₀ mean in plain language, and compare stations without treating one station as the entire city.
- **Ask why and what next.** Get cited explanations of likely sources, regulation and implementation status, bad-air-day protection, and realistic individual or civic actions.
- **Inspect the evidence.** Follow source links, distinguish official observations from city-level model history, and use aggregate Monitoring without exposing people’s questions.

### Questions to try

| Current conditions | Context and action |
| --- | --- |
| What is the latest PM2.5 reading in Jakarta Pusat, and when was it observed? | What causes Jakarta’s PM2.5 pollution? |
| How does Jakarta Timur compare with Jakarta Barat? | What can I do on a polluted day if I need to be outdoors? |
| How does that compare with the north? | Is ERP an enacted rule, a proposal, or something else? |
|  | Does a high-rise apartment always reduce particle exposure? |

## Data you can trust—and its boundaries

Napas does not merge unlike data into one implied truth. The label, source, timestamp, and scope stay with the result.

| Data layer | Used for | Read it as | Do not read it as |
| --- | --- | --- | --- |
| [Official Jakarta SPKU observations](https://udara.jakarta.go.id/) | Live map, overview, current-reading answers | A station’s pollutant, index, and observation time | A citywide average, neighbourhood forecast, or indoor measurement |
| Zenodo / [Open-Meteo CAMS](https://open-meteo.com/en/docs/air-quality-api) city context | Trends | Separately labelled daily city-level model context | Official SPKU station history |
| Curated DKI, Indonesian-law, WHO, EPA, and research sources | Causes, regulation, protection, evidence questions | Cited context with source status and scope | A medical diagnosis, legal advice, or proof of one reading’s cause |

For the fuller provenance record, see the [data contract](docs/data-contract.md), [source and citation notes](docs/corpus-and-citations.md), and [limitations](docs/limitations.md).

## How a question becomes an answer

~~~mermaid
flowchart LR
  U[Resident] --> W[NiceGUI + FastAPI]
  W --> R{Question type}
  R -->|current reading, station difference, history| T[Typed measurement and policy tools]
  R -->|causes, regulations, protection| H[Hybrid evidence retrieval]
  S[Official SPKU portal] --> I[Scheduled ingestion]
  I --> P[(PostgreSQL runtime data)]
  P --> T
  D[Curated DKI, WHO and policy sources] --> H
  T --> A[Grounded answer + source details]
  H --> L[Claude Haiku when configured<br/>or cited fallback]
  L --> A
  A --> W
  W --> M[Aggregate, privacy-preserving telemetry]
~~~

- **Structured answers use typed tools.** Current readings, station differences, history, policy timelines, and ISPU interpretation come from validated application data rather than language-model arithmetic.
- **Documentary answers retrieve evidence.** Causes, regulations, public-health guidance, and implementation questions search the curated corpus using hybrid retrieval; citations must resolve to retrieved evidence.
- **The app has a useful failure mode.** Claude Haiku streams when configured. If a provider is unavailable, the application returns a cited deterministic response rather than inventing an answer.

## Technical snapshot

| Layer | Choice |
| --- | --- |
| Web and API | NiceGUI + FastAPI on one ASGI deployment |
| Answer model | Anthropic Claude Haiku, with cited deterministic fallback |
| Runtime data | PostgreSQL; labelled packaged fallback for local/offline availability |
| Evidence retrieval | Hybrid retrieval; optional Qdrant index in local Compose |
| Ingestion | Validated official-source and historical-context jobs |
| Quality | Human-reviewed retrieval set, contract tests, Ruff, GitHub Actions |
| Observability | Aggregate telemetry; private interaction text excluded from the dashboard |
| Deployment | Railway web, PostgreSQL, and scheduled ingestion |

~~~text
app/          web UI, API, routing, tools, retrieval, and providers
data/         source manifest, curated evidence, current fallback, city context
ingestion/    validation, official connector, history refresh, and indexing
evaluation/   reviewed set, evaluators, and reproducible result artefacts
monitoring/   retention, interaction logging, and aggregate analytics
tests/        unit, contract, provenance, UI, and artefact checks
docs/         architecture, data, evaluation, deployment, and limitations
~~~

## Run locally

**Prerequisites:** Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/). An Anthropic key enables streamed Claude answers; without one, the cited deterministic fallback still works.

~~~bash
git clone https://github.com/aasnani/napas-jakarta.git
cd napas-jakarta
cp .env.example .env
uv sync --frozen --extra dev
uv run uvicorn app.web:app --host 0.0.0.0 --port 8502
~~~

Open <http://localhost:8502>. Set ANTHROPIC_API_KEY in .env to enable Claude Haiku streaming. To validate a checkout:

~~~bash
make test
make eval
make validate-sources
uv run ruff check .
~~~

For the full local stack—web, standalone API, PostgreSQL, Qdrant, Grafana, ingestion, and index jobs:

~~~bash
docker compose up --build -d
make smoke
~~~

See [local deployment and smoke checks](docs/deployment.md), the committed [.env.example](.env.example), and the [data contract](docs/data-contract.md) before changing a source URL.

## Evaluation and reliability

Retrieval is evaluated on **30 bilingual questions** whose relevant structure-aware chunks were completed through human review. The application selects hybrid retrieval for production; typed-data and abstention routes are tested separately.

| All-system hybrid result | Value |
| --- | ---: |
| Question hit@5 | 0.6667 |
| Chunk recall@5 | 0.5789 |
| MRR@5 | 0.4694 |
| nDCG@5 | 0.4856 |

The reviewed set covers more than document retrieval, so these figures are not a claim that every answer is semantically correct or equally good in both languages. In the current reviewed slice, Indonesian document retrieval trails English; that gap is a documented improvement priority. See the [reviewed question set](evaluation/gold_review_30_final.jsonl), [result artefact](evaluation/results/retrieval_gold_review_30.json), [retrieval visual](evaluation/results/retrieval_plot.png), and [evaluation method](docs/evaluation.md).

Additional checks cover citation resolution and locators, deterministic numeric and freshness behaviour, unsupported-calculation rejection, ingestion idempotency, chunking, query rewriting, safety and out-of-domain abstention, and 29 multi-turn conversation cases.

## Deploy and operate

The live app runs on [Railway](https://web-production-e07b9.up.railway.app) with a web service, PostgreSQL runtime store, and scheduled ingestion service. Railway may cold-start after inactivity; the ingestion job is finite and idempotent. The [deployment guide](docs/deployment-railway.md) documents configuration, verification, source fallback, and teardown.

The [Monitoring page](https://web-production-e07b9.up.railway.app/monitoring) shows aggregate requests, latency, answer routes, retrieval modes, citation rate, feedback totals, and estimated usage/cost. It never renders raw questions or feedback comments. Private interaction content is retained for 30 days by default; do not enter sensitive personal or health information.

## Responsible use

- Air quality can change quickly. Check the station, pollutant, observation time, and source mode before acting; a packaged fallback is not a live observation.
- One station does not describe every neighbourhood, indoor exposure, or tomorrow’s air. The historical chart is city-level model context, not official SPKU station history.
- Health information is educational, not diagnosis or triage. Seek professional care for concerning symptoms or urgent help for severe breathing difficulty, chest pain, fainting, or rapidly worsening symptoms.
- Regulations and policy status are source- and date-bounded. Use displayed citations to verify obligations with the responsible authority or a qualified adviser.

## Learn more

Start with [architecture](docs/architecture.md), [data and provenance](docs/data-contract.md), [evaluation](docs/evaluation.md), [Railway deployment](docs/deployment-railway.md), and [limitations](docs/limitations.md).
