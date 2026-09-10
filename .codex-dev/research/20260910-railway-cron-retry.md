# Railway cron retry research

- Accessed: 2026-09-10
- Decision: determine whether the existing hourly Railway cron schedule can
  provide a 30–60 minute retry window without an in-process sleep.
- Source: https://docs.railway.com/cron-jobs
- Findings: Railway cron services run their start command on the configured
  crontab schedule and expect the process to exit after the task. Schedules are
  UTC-based, can run as often as every five minutes, and may vary by a few
  minutes. If a prior execution is still running when the next schedule is due,
  Railway skips the new execution.
- Implication: keep the service short-lived; do not sleep inside the job. The
  existing `0 * * * *` schedule already retries on the next hourly run once the
  ingestion process exits cleanly after retaining the last good snapshot.
- Uncertainty: Railway's general cron documentation does not establish an
  automatic delayed retry after a crash; application-level fallback plus the
  next scheduled run is the reliable behavior for this project.
