-- Bu dosya PostgreSQL içinde dwh_health_log şeması için MetricStore (metrik deposu) tablosunu kurar.
-- Ne zaman: DQ servisi kurulurken bir kez psql ile çalıştırılır.
-- Güvenli: IF NOT EXISTS kullanılır, tekrar çalıştırmak hata vermez ve veriyi silmez.
-- Yıkıcı değildir: DROP veya TRUNCATE içermez.
-- MetricStore — dwh_health_log şeması migration
-- Çalıştır: psql $DSN -f scripts/migrate_metrics_postgres.sql

-- Şemayı oluşturur. Şema yoksa oluşturur, varsa dokunmaz.
CREATE SCHEMA IF NOT EXISTS dwh_health_log;

-- Her kalite ölçümünün sonucunu bir satır olarak tutar.
-- name: metriğin adı, value: ölçülen sayısal değer, run_at: ölçümün zamanı.
CREATE TABLE IF NOT EXISTS dwh_health_log.dq_metrics (
    id      BIGSERIAL PRIMARY KEY,
    name    TEXT             NOT NULL,
    value   DOUBLE PRECISION,
    run_at  TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- name üzerinde indeks: tek bir metriğin geçmişini hızlı getirmek için.
CREATE INDEX IF NOT EXISTS idx_dq_metrics_name   ON dwh_health_log.dq_metrics(name);
-- run_at üzerinde indeks: zaman aralığına göre (ör. son 7 gün) sorgular için.
CREATE INDEX IF NOT EXISTS idx_dq_metrics_run_at ON dwh_health_log.dq_metrics(run_at);
