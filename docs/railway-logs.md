# Railway logs

Napas uses Railway's built-in logs for the first monitoring slice. There is no
additional logging service, volume, or paid dashboard to operate. Railway
captures each service's stdout and stderr, and the application emits one-line
JSON events so the Log Explorer can filter by fields.

## What is recorded

- `request_completed` records API route, status, duration, and a request ID.
- `chat_failure` records a bounded failure code and context counts with
  `critical=true` and `alertable=true`.
- `provider_failure` records Gemini dependency failures by bounded status code.
- `provider_configuration_missing` records a missing Gemini key without
  exposing the key.
- `telemetry_forward_failed` records a failed best-effort telemetry forward.

Prompt text, answers, authorization headers, cookies, and tokens are excluded
from these Railway events. Server-side exception events include a bounded
`stacktrace` for diagnosis. That trace stays in Railway logs and is never sent
to the browser or client telemetry. Existing interaction telemetry continues to
use its separate retention-controlled store.

## Viewing logs

Open the Railway project, select the `web` or `api` service, and open **Logs**.
Use the structured fields to filter for `event=chat_failure`,
`event=provider_failure`, or `critical=true`. Each API response also includes
the `X-Request-ID` value, which can be used to correlate a request with its
server log.

The CLI can be used for a quick live view from the repository:

```bash
railway logs --service web
railway logs --service api
```

Railway Hobby retains logs for a limited period, so export incidents or move to
a dedicated log backend only if longer retention or alerting becomes necessary.
