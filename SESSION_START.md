# DQ — Session Başlangıç Dosyası
Proje: DQ (Data Quality Platform)
Konum: /opt/dq/dq_docker (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL + Airflow + Docker

## Mimari (özet)
- dq/engine.py      → CheckEngine + assert tipleri (not_empty, regex_match, accepted_values, freshness_hours, row_count_between, referential_integrity) ✅
- dq/connectors.py  → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- dq/metrics.py     → MetricStore (SQLite dev + Postgres production) ✅
- dq/config.py      → SodaConfig + _resolve_env_vars() + referential_integrity ✅
- dq/scoring.py     → get_health_score(), get_score_trend(), get_all_scores() ✅
- dq/reporter_v2.py → full_report() + MetricStore entegrasyonu ✅
- dq/airflow.py     → DQOperator ✅
- main.py           → FastAPI app init + router include'ları (59 satır) ✅
- database.py       → MySQL init_db() + column_profiles PII + glossary kolonları ✅
- cache_layer.py    → TTLCache + profile_cache singleton (5 dk TTL) ✅
- profiler.py       → cache + PII tagging (24 pattern) + enum/regex/empty önerileri + SQL optimize ✅
- extensions.py     → AlertManager (email/slack/webhook) + load_alert_manager ✅

## Routers (routers/)
- routers/sources.py → /sources CRUD ✅
- routers/checks.py  → /checks CRUD + /api/suggestions/reject ✅
- routers/api.py     → /api/* + /odata + alerting + /api/health-score + /api/glossary + /api/pii-report + /api/alert-settings ✅
- routers/ui.py      → /wizard, /import, /runs, /health, / ✅

## Güvenlik Katmanı
- secrets/.env.secrets     → password'lar + SMTP/alert config (chmod 600, git ignore)
- secrets/.env.secrets.gpg → şifreli kopya (git'te ✅)
- scripts/decrypt_secrets.sh → deploy öncesi çalıştır
- GPG key: dq@localhost (RSA 4096, /root/.gnupg)
- Deploy akışı: bash scripts/decrypt_secrets.sh && docker-compose up -d

## Docker
- dq-web  → 0.0.0.0:8002 (uvicorn)
- dq-db   → 0.0.0.0:3308 (mysql:8.0)
- ÖNEMLİ: Kod değişikliklerinin yürürlüğe girmesi için `docker compose build dq-web && docker compose up -d dq-web` gerekir
  (sadece dags/ klasörü volume mount edilmiş, diğer dosyalar image içinde)

## Postgres (MetricStore — Production)
- DSN: postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics
- Şema: dwh_health_log.dq_metrics ✅

## Business Glossary
- column_profiles tablosuna eklendi: business_name, description, owner, tags
- GET  /api/glossary/{source_id}
- PUT  /api/glossary/{source_id}/{column_name}
- Wizard kolon kartında glossary bilgisi gösterilir (business_name, description, owner) ✅

## Alerting (GÖREV 7 ✅)
- alert_settings tablosu: slack_webhook, webhook_url, email_to, smtp_*
- sources.alert_enabled kolonu: kaynak bazlı aç/kapa
- GET/PUT /api/alert-settings
- PUT /api/sources/{id}/alert-enabled
- api_post_run → DB'den load_alert_manager + alert_enabled kontrolü

## PII / KVKK (GÖREV 8 ✅)
- profiler.py: 24 PII keyword (tckn, adres, pasaport, kredi, sifre, ip_, konum vb.)
- Regex pattern'leri: email, tc, telefon, iban, kredi kartı, pasaport
- GET /api/pii-report            → tüm kaynaklar KVKK özet
- GET /api/pii-report/{source_id} → kaynak bazlı PII kolon detayı
- Wizard'da profil sonucunda sarı PII uyarı banner ✅
- Health dashboard'da KVKK CSV export butonu ✅

## Airflow DAG'ları (dags/)
- dq_mysql_dag.py, dq_postgres_dag.py, dq_oracle_dag.py, dq_mongo_dag.py
- dq_scheduled_profiling_dag.py → scheduled_profiling.toml ile periyodik profil tetikleme ✅

## DB Tabloları
- sources (+ alert_enabled kolonu)
- checks, runs, run_results
- column_profiles (+ business_name, description, owner, tags, is_pii, pii_type)
- alert_settings (id=1 singleton)
- rule_library

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir
- DB migration: docker exec -i dq-db mysql -u root -proot dq -e "..."

## Test Durumu
108 passed, 3 skipped ✅

## Git Son Commitler
9a2eb57 perf: profile_column — temel istatistik + distinct tek sorguda birleştirildi
9512c61 feat: KVKK raporu CSV export — health dashboard'a indirme butonu eklendi
9c9738b feat: wizard PII uyarı banner — profil sonucunda KVKK kolonları sarı kutu ile gösterilir
e558cf7 feat: GÖREV 9 — wizard kolon kartında glossary bilgisi (business_name, description, owner)

## Backlog (Öncelik Sırasına Göre)

### Wizard'a Eklenecekler (Kolay)
- [ ] Schema Check — kolon varlığı + tip kontrolü, upstream değişiklik tespiti
- [ ] Duplicate Row — tüm satır tekrarı, yeni assert tipi, kolon seçimi gerekmez

### Wizard'a Eklenecekler (Orta)
- [ ] Custom SQL assert — textarea ile kullanıcı SQL yazar, sonuç beklenen değerle karşılaştırılır
- [ ] Volume Anomali — MetricStore geçmişinden satır sayısı ani değişim tespiti

### Ayrı Sayfa / Dashboard (Zor)
- [ ] Cross-table Check — iki farklı kaynakta çapraz kolon karşılaştırma (ayrı sayfa)
- [ ] Statistical Anomali — MetricStore + istatistik hesabı (health dashboard anomali sekmesi)
- [ ] Distribution Check — dağılım karşılaştırma (görsel grafik gerekiyor)

### Diğer
- [ ] Veri kalitesi trendi karşılaştırma — iki kaynak yan yana skor trendi
- [ ] Check sonuçları email özet raporu — günlük/haftalık özet
- [ ] Rule library UI — kural kütüphanesini wizard'da görsel yönetim
- [ ] Docker Secrets / Vault entegrasyonu (ertelendi)
- [ ] Airflow connection'ları secure store'dan yükle (ertelendi)

## Rakip Karşılaştırma Notları
- DQ-main güçlü: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10), business glossary
- DQ-main zayıf: Anomali tespiti (2/10), connector çeşitliliği (6/10), ölçeklenebilirlik (4/10)
- Backlog tamamlanırsa tahmini genel puan: 6.7 → 7.8/10

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md + TASKS.md yükle
2. Öncelikli backlog: Schema Check veya Duplicate Row (kolay, wizard'a eklenecek)
3. Anomali tespiti eksiği kritik — Volume Anomali ile başlamak önerilir
