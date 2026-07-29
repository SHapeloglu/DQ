# DQ — Aktif Görevler

## Tamamlananlar (Son 3 Sprint)
- [x] Proje dizin yapısı `DQ-main` olarak düzenlendi
- [x] `.claude/` dokümantasyon katmanı kuruldu (CLAUDE.md, ARCHITECTURE.md, TASKS.md)
- [x] Token optimizasyon dosyaları hazırlandı (cache_layer.py, optimized_profiler.py, session_and_prompts.py)
- [x] **GÖREV 3 — MongoConnector** (pipeline + filter dict query)
- [x] **GÖREV 4 — DB2 Doğrulama** (ibm_db_sa kütüphanesi)
- [x] **GÖREV 5 — Airflow DAG Genişletme** (PostgreSQL, Oracle, MongoDB DAG'ları)

**Test Sonucu:** 69 passed, 1 skipped ✅

---

## Aktif Sprint

### GÖREV 1 — Güvenlik (Öncelik: KRİTİK)
**Dosya:** `.env`, `.gitignore`, Docker Secrets / Vault

- [ ] `.env.example` oluştur (template olarak)
- [ ] Production ortamı: Docker Secrets veya Vault entegrasyonu
- [ ] Airflow connection'ları secure store'dan yükle
- [ ] Database credentials encrypted olarak sakla

**Test:** `git status` → `.env` ignored görünmeli

---

### GÖREV 2 — MetricStore Postgres'e Taşı (Öncelik: YÜKSEK)
**Dosya:** `dq/metrics.py`, `dq/reporter_v2.py`

Mevcut durum:
```python
# dq/metrics.py — SQLite kullanıyor
MetricStore("dq_metrics.db")  # ← BUNU değiştir
```

Hedef:
```python
# dwh_health_log şemasına Postgres'e yaz
MetricStore(dsn="postgresql://...")
```

- [ ] `MetricStore` sınıfına Postgres backend ekle
- [ ] `dwh_health_log` tablo şeması oluştur (migration script)
- [ ] `reporter_v2.py` çıktı hedefini güncelle
- [ ] `reporter.py` (v1) deprecated olarak işaretle

**Test:** `pytest tests/test_engine.py` geçmeli

---

## Tamamlanan Görevler (Archiv)

### ✅ GÖREV 3 — MongoDB Connector (Tamamlandı)
- [x] `MongoConnector` sınıfı (`BaseConnector`'dan türet)
- [x] `execute()` → pipeline/filter dict kabul
- [x] `CheckEngine`'in dict query'yi çağırması
- [x] `CONNECTOR_REGISTRY['mongo']` ekle
- [x] `pymongo>=4.0` → requirements.txt
- [x] Unit testler yazıldı ve geçti (2 test)

**Test Sonuç:** `pytest tests/test_connectors.py -k mongo` → 2 passed ✓

---

### ✅ GÖREV 4 — DB2 Doğrulama (Tamamlandı)
- [x] `ibm_db>=2.3.0` + `ibm_db_sa>=0.4.0` kuruldu
- [x] `SqlAlchemyConnector` DB2 dialect'ini destekliyor
- [x] `test_connection()` metodunu test ettik

**Test Sonuç:** `pytest tests/test_connectors.py -k db2` → 2 passed ✓

---

### ✅ GÖREV 5 — Airflow DAG Genişletme (Tamamlandı)
- [x] `dq_postgres_dag.py` yazıldı
- [x] `dq_oracle_dag.py` yazıldı
- [x] `dq_mongo_dag.py` yazıldı
- [x] TOML config dosyaları oluşturuldu
- [x] Syntax check geçti

**DAG'lar:**
```
dags/
  dq_mysql_dag.py
  dq_postgres_dag.py      ← yeni
  dq_oracle_dag.py        ← yeni
  dq_mongo_dag.py         ← yeni
  checks_*.toml           ← 3 yeni
```

---

## Sıra / Bağımlılık

```
GÖREV 1 (Güvenlik)     → Bağımsız, kritik
GÖREV 2 (Postgres)     → Bağımsız, yüksek
GÖREV 3 (MongoDB)      → ✅ TAMAMLANDI
GÖREV 4 (DB2)          → ✅ TAMAMLANDI
GÖREV 5 (Airflow DAG)  → ✅ TAMAMLANDI
```

---

## Yeni Session Açıldığında — Bağlam Girişi

Aşağıdaki bloğu kopyalayıp yeni chat'e yapıştır:

```
DQ projesi Contabo VPS'de çalışıyor.
Son tamamlanan: GÖREV 3+4+5 (MongoConnector, DB2, Airflow DAGs)
Test sonucu: 69 passed, 1 skipped ✅

Bağlam dosyaları:
- CLAUDE.md (kurallar ve standartlar)
- ARCHITECTURE.md (mimari ve teknik borçlar)
- SESSION_START.md (mevcut durum)
- TASKS.md (görev durumu)

Şimdi başlamak istiyorum: GÖREV 1 (Güvenlik) veya GÖREV 2 (Postgres)
```
