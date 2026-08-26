# DQ — Data Quality Platform

> **Self-hosted, açık kaynak veri kalitesi platformu.**  
> PII/KVKK tespiti, anomali analizi ve 19 assert tipiyle rakip ticari çözümlere kıyasla **%99 daha düşük toplam sahip olma maliyeti.**

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)](https://www.mysql.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-196%20passed-brightgreen)]()

---

## 📋 İçindekiler

- [Neden DQ?](#neden-dq)
- [Özellikler](#özellikler)
- [Mimari](#mimari)
- [Hızlı Başlangıç](#hızlı-başlangıç)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Assert Tipleri](#assert-tipleri)
- [Anomali Tespiti](#anomali-tespiti)
- [PII/KVKK Tespiti](#piikvkk-tespiti)
- [Custom Assertion Scripts](#custom-assertion-scripts)
- [Apache Airflow Entegrasyonu](#apache-airflow-entegrasyonu)
- [Güvenlik](#güvenlik)
- [Rekabet Analizi](#rekabet-analizi)
- [Katkı](#katkı)

---

## Neden DQ?

| | DQ | Google Dataplex | AWS Glue DQ | Soda Core |
|---|:---:|:---:|:---:|:---:|
| **Assert tipi sayısı** | **19** | 17 | 15 | 15 |
| **PII/KVKK tespiti** | ✅ | ✅ | ❌ | ❌ |
| **Anomali (istatistiksel)** | ✅ Z-score + EWMA + HW | Sınırlı | ML blackbox | ❌ |
| **Self-hosted** | ✅ | ❌ | ❌ | ✅ |
| **Yıllık TCO (100TB)** | **~$500** | ~$150.000+ | ~$100.000+ | ~$500 |
| **Genel Puan** | **8.3/10** | 8.1/10 | 8.1/10 | 6.6/10 |

DQ, özellikle **PII-yoğun** ve **maliyet bilinçli** kuruluşlar için tasarlanmıştır. KVKK uyumluluğu gerektiren Türkiye bazlı ekipler için birincil tercih olarak konumlandırılmıştır.

---

## Özellikler

### 🔍 19 Assert Tipi
`not_empty`, `regex_match`, `accepted_values`, `freshness_hours`, `row_count_between`, `referential_integrity`, `equals`, `between`, `greater_than`, `less_than`, `completeness_ratio`, `statistical_anomaly`, `schema_drift`, `schema_check`, `duplicate_row`, `custom_sql`, `volume_anomaly`, `zscore_anomaly`, `row_condition`

### 🤖 Anomali Tespiti
- **Z-Score**: Küçük örneklem (n < 8) için
- **EWMA** (Exponential Weighted Moving Average): Orta örneklem (n < 14) için
- **Holt-Winters**: Büyük örneklem (n ≥ 14) için; mevsimsellik desteği
- **Otomatik yöntem seçimi**: n değerine göre en uygun algoritma
- **Trend yönü analizi**: ↑ Artış / → Sabit / ↓ Düşüş (%5 tolerans)
- **Read replica desteği**: Okuma/yazma ayrımı ile MetricStore

### 🔐 PII/KVKK Tespiti
- 24 adet önceden tanımlı PII pattern (TC kimlik, IBAN, e-posta, telefon vb.)
- Otomatik enum önerisi
- Regex kural önerisi
- PII dashboard + GDPR/KVKK etiketleme

### 🐍 Custom Assertion Scripts
- Kullanıcı tanımlı Python fonksiyonları yükleme
- AST tabanlı güvenlik doğrulaması
- Live test/dry-run arayüzü

### 🧙 Wizard UI
- Adım adım kaynak bağlantısı + profil çalıştırma + kural ekleme
- Profil bazlı otomatik öneri

### 📊 Diğer
- Veri profilleme (istatistik + PII + glossary)
- Health score dashboard + trend grafikleri
- Rule library (pattern bazlı kural öğrenme)
- Slack / e-posta / webhook alert entegrasyonu
- OData endpoint
- CSV/JSON profil export (`/api/profile-export/{source_id}`)
- Apache Airflow entegrasyonu

---

## Mimari

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Web App                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ /sources │ │ /checks  │ │ /scripts │ │ /api/*    │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│                        │                                  │
│  ┌─────────────────────▼──────────────────────────────┐ │
│  │               CheckEngine (dq/engine.py)            │ │
│  │  19 Assert Tipi + custom_script_assertion()         │ │
│  └─────────────────────┬──────────────────────────────┘ │
│                         │                                 │
│  ┌──────────────────────▼─────────────────────────────┐ │
│  │            AnomalyDetector (dq/anomaly.py)          │ │
│  │     Z-Score │ EWMA │ Holt-Winters │ Trend Yönü      │ │
│  └──────────────────────┬─────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                  │
    ┌─────▼──────┐                   ┌───────▼──────┐
    │  MySQL 8.0  │                   │  PostgreSQL   │
    │  (App DB)   │                   │  (MetricStore)│
    └─────────────┘                   └──────────────┘
          │
    ┌─────▼──────────────────┐
    │   Apache Airflow        │
    │   DQOperator            │
    │   (DAG tabanlı çalışma) │
    └────────────────────────┘
```

### Desteklenen Veri Kaynakları
- MySQL / PostgreSQL / Oracle
- MongoDB
- IBM DB2
- BigQuery
- CSV dosyaları
- SQLAlchemy uyumlu herhangi bir kaynak

---

## Hızlı Başlangıç

### Gereksinimler
- Docker & Docker Compose
- Python 3.11+ (lokal geliştirme için)
- Git

### 3 Adımda Kur

```bash
# 1. Repoyu klonla
git clone https://github.com/SHapeloglu/DQ.git
cd DQ

# 2. Secrets klasörü oluştur
mkdir -p secrets/files
echo "your_db_password" > secrets/files/DB_PASSWORD
echo ""                  > secrets/files/METRICS_PG_DSN
echo ""                  > secrets/files/METRICS_PG_PASSWORD
echo ""                  > secrets/files/ALERT_SMTP_PASS
echo ""                  > secrets/files/ALERT_SLACK_WEBHOOK

# 3. Başlat
docker compose up -d
```

Tarayıcıda aç: **http://localhost:8002**

---

## Kurulum

### Ortam Değişkenleri

Proje kökünde `.env` dosyası oluştur:

```env
DB_HOST=dq-db
DB_PORT=3306
DB_NAME=dq
DB_USER=root
```

Hassas bilgiler için `secrets/` klasörü kullanılır (Docker Secrets):

```
secrets/
├── files/
│   ├── DB_PASSWORD          # MySQL root şifresi
│   ├── METRICS_PG_DSN       # PostgreSQL MetricStore bağlantısı (opsiyonel)
│   ├── METRICS_PG_PASSWORD  # PostgreSQL şifresi (opsiyonel)
│   ├── ALERT_SMTP_PASS      # E-posta alert şifresi (opsiyonel)
│   └── ALERT_SLACK_WEBHOOK  # Slack webhook URL (opsiyonel)
└── .env.secrets.gpg         # GPG şifreli kopya (git'te)
```

### PostgreSQL MetricStore (Opsiyonel)

Anomali geçmişi ve metrik depolama için:

```bash
# PostgreSQL'de şema oluştur
psql -U postgres -c "CREATE DATABASE dqmetrics;"
psql -U postgres -d dqmetrics -f scripts/migrate_metrics_postgres.sql

# DSN'i secrets'a yaz
echo "postgresql://dquser:pass@localhost:5432/dqmetrics" > secrets/files/METRICS_PG_DSN
```

### Read Replica (Opsiyonel)

```env
# .env.secrets içinde
METRICS_PG_READ_DSN=postgresql://readonly:pass@replica:5432/dqmetrics
```

Ayarlanmazsa primary connection otomatik kullanılır.

### Lokal Geliştirme

```bash
# Sanal ortam oluştur
python3 -m venv venv
source venv/bin/activate

# Bağımlılıklar
pip install -r requirements.txt

# Test çalıştır
pytest tests/ -q
```

---

## Kullanım

### Web Arayüzü

| URL | Açıklama |
|-----|----------|
| `http://localhost:8002/` | Ana dashboard |
| `http://localhost:8002/wizard` | Adım adım kural oluşturma |
| `http://localhost:8002/checks` | Kural yönetimi |
| `http://localhost:8002/sources` | Kaynak yönetimi |
| `http://localhost:8002/scripts` | Custom assertion scripts |
| `http://localhost:8002/health` | Health score dashboard |
| `http://localhost:8002/anomaly` | Anomali dashboard |
| `http://localhost:8002/runs` | Çalışma geçmişi |

### REST API

```bash
# Profil çalıştır
curl -X POST http://localhost:8002/api/profile/1

# Health score
curl http://localhost:8002/api/health-score/1

# PII raporu
curl http://localhost:8002/api/pii-report/1

# Profil export (CSV)
curl http://localhost:8002/api/profile-export/1?format=csv -o profile.csv

# Profil export (JSON)
curl http://localhost:8002/api/profile-export/1?format=json -o profile.json

# Custom script test
curl -X POST http://localhost:8002/api/scripts/test \
  -F "code=def check(value): return float(value) > 0" \
  -F "function_name=check" \
  -F "test_value=42"
```

### TOML ile Check Tanımlama

```toml
[source]
type     = "mysql"
host     = "localhost"
port     = 3306
database = "production"
user     = "secret:DB_USER"
password = "secret:DB_PASSWORD"

[[checks]]
name  = "Siparişler boş olmamalı"
query = "SELECT COUNT(*) FROM orders"
assert = "greater_than"
value  = 0
tags   = ["critical"]

[[checks]]
name  = "Null müşteri oranı < %5"
query = "SELECT (COUNT(*) - COUNT(customer_id)) * 1.0 / COUNT(*) FROM orders"
assert = "completeness_ratio"
value  = 0.95
tags   = ["quality"]

[[checks]]
name  = "Sipariş tutarı anomali"
query = "SELECT AVG(amount) FROM orders WHERE created_at > NOW() - INTERVAL 1 DAY"
assert = "zscore_anomaly"
value  = "daily_order_amount"
tags   = ["anomaly"]
```

---

## Assert Tipleri

| Assert Tipi | Açıklama | `assert_value` Örneği |
|---|---|---|
| `not_empty` | Değer boş/null değil | — |
| `equals` | Değer eşit | `100` |
| `greater_than` | Değer büyük | `0` |
| `less_than` | Değer küçük | `5.0` |
| `between` | Değer aralıkta | `[1, 100]` |
| `row_count_between` | Satır sayısı aralıkta | `[1000, 50000]` |
| `completeness_ratio` | Doluluk oranı eşiği | `0.95` |
| `regex_match` | Regex eşleşmesi | `^\d{10}$` |
| `accepted_values` | İzin verilen değerler | `["A","B","C"]` |
| `freshness_hours` | Veri tazeliği | `24` |
| `referential_integrity` | Referans bütünlüğü | `["users","id"]` |
| `schema_drift` | Kolon sayısı değişmedi | `12` |
| `schema_check` | Kolon varlığı + tip kontrolü | `{"id":"int","name":"varchar"}` |
| `duplicate_row` | Tekrar eden satır eşiği | `0` |
| `statistical_anomaly` | Z-score eşiği | `3.0` |
| `zscore_anomaly` | MetricStore'dan geçmiş z-score | `"metric_name"` |
| `volume_anomaly` | Satır sayısı değişim % | `30.0` |
| `row_condition` | WHERE koşulu ihlali | `"amount > 0"` |
| `custom_sql` | Kullanıcı tanımlı SQL | `0` |
| `custom_script` | Python fonksiyonu | `1` (script ID) |

---

## Anomali Tespiti

DQ, geçmiş metrik verilerini kullanarak otomatik anomali tespiti yapar:

```
n < 8   → Z-Score       (basit, az veri için)
n < 14  → EWMA          (ağırlıklı ortalama, trend için)
n ≥ 14  → Holt-Winters  (mevsimsellik desteği)
```

### Trend Yönü

Her anomali sonucu bir trend yönü içerir:

- **↑ Artış** (yeşil) — son ölçümler yükseliyor
- **→ Sabit** (gri) — %5 tolerans dahilinde
- **↓ Düşüş** (kırmızı) — son ölçümler düşüyor

### Anomali Dashboard

`/anomaly` sayfasında yöntem filtresi (Z-Score / EWMA / Holt-Winters), trend rozeti ve geçmiş grafik görünür.

---

## PII/KVKK Tespiti

DQ, kolon bazında otomatik PII tespiti yapar:

| Pattern Kategorisi | Örnek |
|---|---|
| TC Kimlik No | `12345678901` |
| IBAN | `TR330006100519786457841326` |
| E-posta | `user@domain.com` |
| Telefon (TR) | `+90 532 123 45 67` |
| Kredi Kartı | `4111 1111 1111 1111` |
| IP Adresi | `192.168.1.1` |
| Doğum tarihi | `1990-05-15` |
| ... ve daha 17 pattern | |

PII tespit edilen kolonlara otomatik GDPR/KVKK etiketi atanır ve `/api/pii-report` ile raporlanır.

---

## Custom Assertion Scripts

Yerleşik assert tipleri yetmediğinde kendi Python fonksiyonunuzu yükleyebilirsiniz:

### 1. Web Arayüzü ile

`/scripts/new` → Python kodu yaz → Test Et → Kaydet

### 2. API ile

```bash
# Script oluştur
curl -X POST http://localhost:8002/scripts/new \
  -F "name=Özel Tutar Kontrolü" \
  -F "function_name=check" \
  -F "code=def check(value):
    v = float(value)
    return 0 < v < 999999 and v != 666" \
  -F "description=Tutar 0-999999 arasında ve 666 olmamalı"

# Check'te kullan (assert_value = script ID)
assert_type = "custom_script"
assert_value = "1"
```

### Güvenlik

AST doğrulaması ile aşağıdakiler otomatik reddedilir:

```python
# ❌ YASAK — import reddedilir
import os
import subprocess

# ❌ YASAK — fonksiyon reddedilir
eval("rm -rf /")
exec("os.system('ls')")
open("/etc/passwd")

# ✅ İZİNLİ
import math
import re
len, str, int, float, bool, abs, min, max, sum, round, isinstance
```

---

## Apache Airflow Entegrasyonu

DQ, `DQOperator` ile Airflow DAG'larına entegre edilir:

```python
from dq.airflow import DQOperator

with DAG("dq_daily", schedule_interval="@daily") as dag:
    task = DQOperator(
        task_id="run_checks",
        config_path="/app/dags/checks.toml",
    )
```

### Hazır DAG'lar

| DAG | Açıklama |
|-----|----------|
| `dq_mysql_dag.py` | MySQL kaynak kontrolleri |
| `dq_postgres_dag.py` | PostgreSQL kaynak kontrolleri |
| `dq_oracle_dag.py` | Oracle kaynak kontrolleri |
| `dq_mongo_dag.py` | MongoDB kaynak kontrolleri |
| `dq_scheduled_profiling_dag.py` | Zamanlanmış profilleme |

---

## Güvenlik

### Secrets Yönetimi

Credential yönetimi üç katmanlıdır:

```
1. Docker Secrets (/run/secrets/)     → Prodüksiyon (öncelikli)
2. .env.secrets dosyası               → Geliştirme
3. Ortam değişkenleri                 → Fallback
```

TOML dosyalarında `secret:` prefix kullanılır:

```toml
[source]
password = "secret:DB_PASSWORD"   # secrets_loader.py ile çözülür
```

### GPG Şifreleme

```bash
# Secrets dosyasını şifrele (git'e commit için)
gpg --recipient dq@localhost --encrypt secrets/.env.secrets

# Deploy sırasında çöz
bash scripts/decrypt_secrets.sh
```

---

## Rekabet Analizi

| Kategori | DQ | Dataplex | Soda Core | Great Expectations | AWS Glue |
|---|:---:|:---:|:---:|:---:|:---:|
| **Özellik (19 tip)** | **9.5** | 9.0 | 8.0 | 7.5 | 8.5 |
| **Anomali tespiti** | **8.5** | 7.0 | 5.0 | 5.5 | 9.0 |
| **PII/KVKK** | **9.0** | 9.0 | 4.0 | 3.0 | 4.0 |
| **UX/Wizard** | **8.5** | 7.5 | 6.0 | 6.5 | 5.5 |
| **Maliyet** | **9.5** | 5.0 | 9.0 | 9.0 | 6.0 |
| **Ölçeklenebilirlik** | 6.5 | 9.5 | 6.0 | 8.0 | 9.5 |
| **Entegrasyon** | 7.0 | 8.5 | 8.0 | 8.5 | 8.5 |
| **ORTALAMA** | **8.3/10** | 8.1/10 | 6.6/10 | 6.9/10 | 8.1/10 |

> Detaylı benchmark için → [`docs/BENCHMARK.md`](docs/BENCHMARK.md)

---

## Proje Yapısı

```
DQ/
├── dq/                        # Çekirdek motor
│   ├── engine.py              # CheckEngine + 19 assert tipi
│   ├── anomaly.py             # AnomalyDetector (Z-Score, EWMA, Holt-Winters)
│   ├── config.py              # SodaConfig + _ASSERTION_MAP
│   ├── metrics.py             # MetricStore (SQLite/PostgreSQL)
│   ├── connectors.py          # 8 veritabanı connector
│   ├── scoring.py             # Health score hesaplama
│   └── reporter_v2.py         # Rapor üretimi
├── routers/
│   ├── api.py                 # REST API endpoint'leri
│   ├── checks.py              # Kural CRUD
│   ├── sources.py             # Kaynak CRUD
│   ├── scripts.py             # Custom script CRUD
│   └── ui.py                  # Web sayfaları
├── templates/                 # Jinja2 HTML şablonları
├── dags/                      # Airflow DAG'ları + TOML config'ler
├── tests/                     # pytest test suite (196 test)
├── scripts/                   # Yardımcı scriptler
├── secrets/                   # Credential yönetimi
├── docs/                      # Mimari + benchmark dökümantasyonu
├── database.py                # MySQL şema init
├── profiler.py                # PII tespiti + profilleme
├── extensions.py              # Alert manager (Slack/email/webhook)
├── secrets_loader.py          # Secrets çözümleme
├── docker-compose.yml
└── Dockerfile
```

---

## Katkı

1. Fork'la
2. Feature branch oluştur (`git checkout -b feat/yeni-ozellik`)
3. Testleri yaz ve geçir (`pytest tests/ -q`)
4. Commit at (`git commit -m "feat: yeni özellik"`)
5. Push et ve PR aç

### Geliştirme Kuralları

- Yeni assert tipi eklerken: `engine.py` → `config.py` → `test_engine.py`
- Tüm testler geçmeli: `196 passed, 3 skipped`
- `from __future__ import annotations` ile `Optional[int]` type hint kullanma (Pydantic uyumsuz)
- Mock path: `routers.api.get_conn` (test'lerde)

---

## Lisans

[Apache License 2.0](LICENSE)

---

<div align="center">
  <strong>DQ</strong> — Self-hosted veri kalitesi, kurumsal maliyetsiz.
  <br>
  <a href="https://github.com/SHapeloglu/DQ">GitHub</a> ·
  <a href="docs/BENCHMARK.md">Benchmark</a> ·
  <a href="docs/ARCHITECTURE.md">Mimari</a>
</div>
