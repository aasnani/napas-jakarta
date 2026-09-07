# Local deployment and smoke checks

`docker compose up --build -d` starts the full local stack: the combined
NiceGUI/FastAPI web service, standalone API, PostgreSQL, Qdrant, Grafana, and
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
The current product command is `make run`, which starts NiceGUI and FastAPI
together. `make run-streamlit` remains only for the legacy local compatibility
UI and is not the deployed surface.

`GET /sources` separates the current runtime store from packaged fallback
metadata. `GET /version` exposes safe build metadata and the selected retrieval
and prompt variants. `GET /docs` is the FastAPI OpenAPI page. For Railway
configuration and public verification, see
[deployment on Railway](deployment-railway.md).
