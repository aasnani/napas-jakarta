# Limitations and responsible use

Napas Jakarta is an educational air-quality information tool, not a medical
device or an official warning service. A station reading describes that station
and timestamp only; it does not represent every neighborhood in Jakarta.

- Runtime observations can be delayed, unavailable, or served from the clearly
  labelled packaged fallback. Check the source, timestamp, and source mode
  before acting.
- Raw pollutant concentration and Indonesian ISPU are different quantities. The
  application does not silently convert between ISPU, US AQI, or units.
- Historical charts are city-level modelled context, not official SPKU station
  history.
- WHO guideline values are health-based recommendations, not Indonesian legal
  thresholds. Regulations and policy status are date-bounded and should be
  checked with the responsible authority for current obligations.
- Missing observations are reported as unavailable, never as zero.
- The assistant does not diagnose symptoms, predict individual outcomes, or
  make causal claims about the source of pollution.
- The selected strict prompt has bounded provider **heuristic contract checks**
  for non-empty output, citation structure, numeric consistency, safety, and a
  simple language signal. Those checks are not a semantic assessment of answer
  quality or broad real-world performance.
- The human-reviewed 30-question all-system retrieval set includes structured
  tool, safety, and index routes as well as document retrieval. Its document-RAG
  subset is reported separately. Bahasa Indonesia document retrieval is weaker
  than English in the current set; expanding reviewed Indonesian evidence and
  retrieval coverage is the next improvement priority.

For product monitoring, the service stores question text, rewritten queries,
an anonymous session ID, answer metadata, and optional feedback comments in its
private PostgreSQL database. They are not public and are deleted by the
scheduled retention job after `INTERACTION_RETENTION_DAYS` (30 days by default).
Do not enter sensitive personal or health information.
