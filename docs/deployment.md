# Local deployment and smoke checks

`docker compose up --build -d` starts the full local stack: the standalone
FastAPI data service, Next.js web service, PostgreSQL, Qdrant, Grafana, and
the one-shot `ingest` and `index` services. The application services wait for
those one-shot jobs to finish successfully; inspect their completion status
before treating the stack as ready.

```bash
cp .env.example .env
docker compose up --build -d
make smoke
```

Expected `make smoke` output is four successful JSON or health responses for:

- `http://localhost:8000/health` (standalone API)
- `http://localhost:8502/health` (combined web/API service)
- `http://localhost:3000/api/health` (Grafana)
- `http://localhost:6333/healthz` (Qdrant)

Use `docker compose ps` to confirm `ingest` and `index` completed successfully.
The current Python service command is `make run`, which starts the FastAPI data
and telemetry boundary. Start the public Next.js workspace from `web/` with
`npm run dev`; use `npm run dev:api` when the browser needs the local API
boundary.

`GET /sources` separates the current runtime store from packaged fallback
metadata. `GET /version` exposes safe build metadata and the selected retrieval
and prompt variants. `GET /docs` is the FastAPI OpenAPI page. For Railway
configuration and public verification, see
[deployment on Railway](deployment-railway.md).
