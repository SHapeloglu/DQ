-- MetricStore — dwh_health_log şeması migration
-- Çalıştır: psql $DSN -f scripts/migrate_metrics_postgres.sql

CREATE SCHEMA IF NOT EXISTS dwh_health_log;

CREATE TABLE IF NOT EXISTS dwh_health_log.dq_metrics (
    id      BIGSERIAL PRIMARY KEY,
    name    TEXT             NOT NULL,
    value   DOUBLE PRECISION,
    run_at  TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dq_metrics_name   ON dwh_health_log.dq_metrics(name);
CREATE INDEX IF NOT EXISTS idx_dq_metrics_run_at ON dwh_health_log.dq_metrics(run_at);
