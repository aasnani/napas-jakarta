FROM python:3.12.11-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir "uv==0.8.17" \
    && uv sync --frozen --no-install-project --extra orchestration --extra llm
ENV PATH="/app/.venv/bin:$PATH"
ENV PREFECT_SERVER_ANALYTICS_ENABLED=false
COPY app app
COPY ingestion ingestion
COPY data data
COPY evaluation evaluation
COPY monitoring monitoring
CMD ["sh", "-c", "uvicorn app.web:app --host 0.0.0.0 --port ${PORT:-8502}"]
