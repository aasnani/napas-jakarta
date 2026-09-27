# Napas Jakarta product brief

Napas Jakarta is a bilingual air-quality intelligence product for organizations that need to make local environmental information understandable and useful. It combines current station observations, an interactive map, source-grounded retrieval, and a conversational advisor in one web experience.

## Why organizations use it

The commercial value is in making a difficult public-data problem useful to a real audience. A deployment can help an organization:

- offer a differentiated public, customer, workplace, campus, or community service;
- improve engagement with timely local information people can understand and act on;
- support duty-of-care and exposure-reduction communications for staff, students, residents, or visitors;
- demonstrate evidence-led environmental and social programmes; and
- avoid building and maintaining a separate map, station-data pipeline, retrieval layer, citation system, and bilingual interface.

These are value opportunities, not guaranteed revenue outcomes. Results depend on the audience, distribution, service design, and operating model chosen by the organization.

## What the product includes

- **Station map:** ISPU and PM2.5 readings, observation time, freshness status, station selection, district filtering, direct station source links, and a heatmap view.
- **Conversational advisor:** current-air-quality, comparison, historical-context, standards, policy, health-guidance, and exposure-reduction questions with structured retrieval and citations.
- **English and Bahasa Indonesia:** the user interface, controls, guidance, and advisor can be switched between English and Bahasa Indonesia without a page reload.
- **Source transparency:** answers and station details preserve source names, direct URLs, timestamps, data mode, and the distinction between official observations and contextual evidence.
- **Responsive delivery:** the same product adapts to desktop and mobile, including a dedicated mobile map view and accessible controls.
- **Operational monitoring:** private aggregate views for service health, latency, token usage, estimated model cost, citation grounding, retrieval behaviour, feedback, and failures.

## Data and evidence

The source catalogue is maintained in [`data/sources.yaml`](../data/sources.yaml) and can be reviewed before a deployment changes its data contract.

| Source | Product use | Important boundary |
| --- | --- | --- |
| [Udara Jakarta](https://udara.jakarta.go.id/) | Current DKI station observations, ISPU, PM2.5, timestamps, and station attribution | A station reading is local and time-stamped, not a citywide or indoor average |
| [Satu Data Jakarta ISPU 2023](https://satudata.jakarta.go.id/open-data/detail/data-indeks-standar-pencemar-udara-ispu-di-provinsi-dki-jakarta-2023) | Historical structured measurements | Historical catalogue data is not automatically treated as a current reading |
| [Permen LHK No. 14 Tahun 2020](https://peraturan.bpk.go.id/Details/163466/permen-lhk-no-14-tahun-2020) | Indonesian ISPU methodology and categories | The product preserves the distinction between an index and a concentration unit |
| DKI regulations, policy, emissions, and public guidance | Policy status, source-apportionment context, and local action information | Legal status is source- and date-bounded |
| [WHO Global Air Quality Guidelines](https://www.who.int/publications/i/item/9789240034228) and personal-intervention guidance | Health context and exposure-reduction guidance | Recommendations are not Indonesian law or a medical diagnosis |
| [Zenodo / Open-Meteo CAMS](https://zenodo.org/records/18673885) | City-level historical trend context | Model context is clearly labelled and is not official station history |

When a live source is unavailable or fails validation, the product labels the packaged snapshot or stale reading instead of presenting it as current live data.

## Telemetry and privacy

No login is required. The current product does not create user accounts, profiles, or persistent chat history. Anonymous telemetry exists for reliability, cost, and product improvement. Depending on deployment configuration, it may retain the question, generated answer, a random page-visit grouping ID, turn metadata, and explicit feedback. The default retention period is 30 days and can be changed by the operator.

The monitoring view exposes aggregate counts, rates, timing, costs, retrieval, citation, and error signals rather than raw questions or comments. Chat telemetry does not request names, email addresses, account IDs, contact details, or device identifiers. Users should not enter sensitive personal or health details. The product is not designed for advertising profiles or data harvesting.

Model keys stay on the server. The public web service calls a private FastAPI boundary through an internal token; input limits, payload validation, rate limits, and disabled attachments protect the chat and telemetry paths. A future customer login or SSO flow is an integration option, not a hidden assumption of the current product.

## Integration and deployment

The default topology is:

1. a public Next.js/Eve web service;
2. a private FastAPI service for station data, typed retrieval tools, citations, and telemetry; and
3. optional PostgreSQL and scheduled ingestion when a deployment needs durable live-data history.

The product can run as a standalone service under an organization’s domain, with approved source feeds configured through environment variables and a private service-to-service token. Typed endpoints cover station catalogues, latest readings, history, comparisons, standards, policy, evidence, guidance, sources, health, and version metadata. The current default does not include embedding, customer-specific tenancy, SSO, billing, or a formal SLA; those can be scoped separately.

## Cost posture

The initial architecture is designed for a strict **$0 infrastructure starting point** using Railway free allocation, one web service, one private API service, and bounded JSONL telemetry without a paid database. PostgreSQL, a scheduled ingestion process, a custom domain, or shared edge-rate-limiting can be added as the service grows.

This is an infrastructure starting point, not a permanent cost guarantee. Model-provider requests, hosting beyond free quotas, domains, and paid database or edge capacity can create charges. The private monitoring view includes estimated model cost so an operator can understand usage before choosing a larger operating plan.

## Boundaries

Napas Jakarta is an information and communication product. It does not replace official authorities, regulatory advice, medical care, indoor monitoring, or emergency services. Every operational deployment should verify source permissions, attribution, freshness targets, retention settings, provider quotas, and the organization’s privacy and security requirements.
