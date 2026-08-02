# DQ — Aktif Görevler

## Tamamlananlar (Son 3 Sprint)
- [x] Proje dizin yapısı `DQ-main` olarak düzenlendi
- [x] `.claude/` dokümantasyon katmanı kuruldu (CLAUDE.md, ARCHITECTURE.md, TASKS.md)
- [x] Token optimizasyon dosyaları hazırlandı (cache_layer.py, optimized_profiler.py, session_and_prompts.py)
- [x] **GÖREV 3 — MongoConnector** (pipeline + filter dict query)
- [x] **GÖREV 4 — DB2 Doğrulama** (ibm_db_sa kütüphanesi)
- [x] **GÖREV 5 — Airflow DAG Genişletme** (PostgreSQL, Oracle, MongoDB DAG'ları)

**Test Sonucu:** 73 passed, 3 skipped ✅

---

## Aktif Sprint

### ✅ GÖREV 1 — Güvenlik (Tamamlandı — commit: 5249127)
**Dosya:** `.env`, `.gitignore`, Docker Secrets / Vault

- [x] `.env.example` oluştur (template olarak)
- [ ] Production ortamı: Docker Secrets veya Vault entegrasyonu (ertelendi)
- [ ] Airflow connection'ları secure store'dan yükle (ertelendi)
- [ ] Database credentials encrypted olarak sakla (ertelendi)

**Test:** `git status` → `.env` ignored görünmeli

---

### ✅ GÖREV 2 — MetricStore Postgres'e Taşı (Tamamlandı — commit: e931715)
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

- [x] `MetricStore` sınıfına Postgres backend ekle
- [x] `dwh_health_log` tablo şeması oluştur (migration script)
- [x] `reporter_v2.py` çıktı hedefini güncelle
- [x] `reporter.py` (v1) deprecated olarak işaretle

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

---
## YENİ SPRINT — UX & İş Kullanıcısı

### GÖREV 6 — Sağlık Skoru Dashboard
**Öncelik:** Yüksek | **Efor:** M
- [ ] Kaynak başına 0-100 skor hesapla (passed/total oranı)
- [ ] Ana sayfada trafik ışığı göstergesi (yeşil/sarı/kırmızı)
- [ ] Trend: son 7 gün skor grafiği
- [ ] İş kullanıcısı tek bakışta durumu anlasın

### GÖREV 7 — Alerting (Email/Webhook)
**Öncelik:** Yüksek | **Efor:** S
- [ ] Kural başarısız → email bildirimi (SMTP)
- [ ] Webhook desteği (Slack/Teams için)
- [ ] Bildirim tercihleri: kaynak bazlı aç/kapa
- [ ] On-premise SMTP ile çalışmalı

### GÖREV 8 — PII Otomatik Tespiti & Tagging
**Öncelik:** Yüksek | **Efor:** M
- [ ] Kolon adı pattern'leri: tc_no, email, telefon, iban, ad, soyad vb.
- [ ] Wizard'da otomatik PII uyarısı
- [ ] PII kolonlar için otomatik kural önerisi (maskeleme/null kontrol)
- [ ] KVKK raporu: hangi kaynakta hangi PII kolonlar var

### GÖREV 9 — Business Glossary
**Öncelik:** Orta | **Efor:** S
- [ ] Kolona iş adı + açıklama + sahip ekle
- [ ] PII / Hassas / Kritik etiketleri
- [ ] Wizard'da kolon seçince glossary bilgisi göster

### GÖREV 10 — Scheduled Profiling
**Öncelik:** Orta | **Efor:** S
- [ ] Airflow DAG: periyodik profil tetikleme
- [ ] Kaynak bazlı zamanlama (cron)
- [ ] Profil değişince otomatik kural önerisi güncelle

---
## YENİ SPRINT — Eksik Kural Tipleri

### GÖREV 11 — Yeni Assert Tipleri (Değer Sırasına Göre)
**Öncelik:** Yüksek | **Efor:** S

#### 1. regex_match — En kritik
- [ ] engine.py: `regex_match(pattern)` assertion ekle
- [ ] Kullanım: email, TC no, telefon, IBAN format kontrolü
- [ ] Wizard'da PII kolonlar için otomatik öner

#### 2. not_empty — Yüksek değer
- [ ] `NULL` değil ama boş string ("") kontrolü
- [ ] Mevcut `not_null` bunu yakalamıyor
- [ ] String kolonlar için otomatik öner

#### 3. referential_integrity — Yüksek değer
- [ ] Tablo A'daki değer Tablo B'de var mı?
- [ ] FK benzeri kontrol, SQL JOIN ile
- [ ] Wizard'da "bu kolon başka tabloya referans veriyor mu?" sorusu

#### 4. freshness — Orta değer
- [ ] Tablodaki en son kayıt X saatten eski değil mi?
- [ ] `MAX(created_at) > NOW() - INTERVAL X HOUR`
- [ ] Airflow DAG'larına otomatik ekle

#### 5. accepted_values — Orta değer
- [ ] Kolon değeri izin verilen listede mi? (enum kontrolü)
- [ ] Örnek: `status IN ('active','passive','pending')`
- [ ] Wizard'da distinct değerler az (<20) ise otomatik öner

#### 6. row_count_between — Düşük/Orta
- [ ] Tablo satır sayısı beklenen aralıkta mı?
- [ ] Mevcut `row_count_at_least` var, `between` versiyonu ekle

#### 7. custom_sql — Düşük (zaten kısmen var)
- [ ] Serbest SQL + assert kombinasyonu
- [ ] Gelişmiş kullanıcılar için
