# Limitations and responsible use

Napas Jakarta is an educational air-quality information tool, not a medical
device or an official warning service. A station reading describes that station
and timestamp only; it does not represent every neighborhood in Jakarta.

- The committed offline corpus is a small demo snapshot and can become stale.
  Answers expose observation time, source mode, and freshness so this is not
  hidden.
- Raw pollutant concentration and Indonesian ISPU are different quantities.
  The application does not silently convert between ISPU, US AQI, or units.
- WHO guideline values are health-based recommendations, not Indonesian legal
  thresholds.
- Missing observations are reported as unavailable, never as zero.
- The assistant does not diagnose symptoms, predict individual outcomes, or
  make causal claims about the source of pollution.
- Provider-backed generation, human-reviewed benchmark labels, and durable
  cloud deployment are submission steps that must be completed before making
  production-quality performance or uptime claims.
