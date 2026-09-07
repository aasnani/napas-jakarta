CREATE TABLE IF NOT EXISTS interactions (
  id TEXT PRIMARY KEY,
  interaction_id TEXT,
  session_id TEXT,
  created_at TEXT NOT NULL,
  event TEXT NOT NULL DEFAULT 'answer',
  question TEXT NOT NULL,
  rewritten_query TEXT,
  route TEXT,
  retrieval_mode TEXT,
  citation_grounded BOOLEAN,
  prompt_version TEXT,
  latency_ms DOUBLE PRECISION,
  token_usage INTEGER,
  estimated_cost DOUBLE PRECISION,
  data_age_seconds DOUBLE PRECISION,
  error_type TEXT,
  abstention_type TEXT,
  feedback TEXT,
  feedback_comment TEXT,
  source TEXT NOT NULL DEFAULT 'live'
  ,carried_entities TEXT
  ,source_count INTEGER
);
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS session_id TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS interaction_id TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS feedback_comment TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS conversation_turn INTEGER;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS history_messages INTEGER;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS history_summary_chars INTEGER;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS provider_model TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS carried_entities TEXT;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS source_count INTEGER;

CREATE TABLE IF NOT EXISTS measurements (
  station_id TEXT NOT NULL,
  station_name TEXT NOT NULL,
  district TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  pollutant TEXT NOT NULL,
  concentration DOUBLE PRECISION,
  concentration_unit TEXT NOT NULL,
  ispu_value INTEGER NOT NULL,
  ispu_category TEXT NOT NULL,
  source TEXT NOT NULL,
  averaging_period TEXT,
  quality_flag TEXT,
  fetched_at TIMESTAMPTZ,
  PRIMARY KEY (station_id, observed_at, pollutant)
);
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS averaging_period TEXT;
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS quality_flag TEXT;
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS historical_city_air_quality (
  observed_date DATE PRIMARY KEY,
  pm10 DOUBLE PRECISION,
  pm2_5 DOUBLE PRECISION,
  us_aqi DOUBLE PRECISION,
  source TEXT NOT NULL,
  refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
