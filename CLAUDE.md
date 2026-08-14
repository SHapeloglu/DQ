# CLAUDE.md — İşbirliği Notları

## Bu Oturum Özeti (41-43)

### GÖREV 41: run_detail.html ewma badge desteği
- **Değişiklik**: Badge seçimini 2'den 3 yönteme çıkardı
- **Dosya**: templates/run_detail.html satır 63
- **Dosyalama**: Basit bir OR operatörü ekleme
- **Test**: 191 passed, 3 skipped ✅

### GÖREV 42: Anomali dashboard yöntem filtresi
- **Değişiklik**: methodFilter select + filterTable() güncelleme
- **Dosya**: templates/anomaly.html
- **Detay**:
  - HTML: statusFilter'dan sonra methodFilter div ekle (Tüm Yöntemler / Holt-Winters / EWMA / Z-score)
  - JS: filterTable() — m değişkeni ile tahmin= / [ewma] / z= kontrolleri
  - Badge: method tanımına EWMA (bg-warning) eklendi
- **Test**: 191 passed, 3 skipped ✅

### GÖREV 43: row_condition assert tipi
- **Amaç**: Dataplex gap kapamak — WHERE koşuluna uyan satır sayısını denetle
- **Dosyalar**: dq/engine.py, dq/config.py, tests/test_engine.py
- **Detay**:
  - `row_condition(condition: str)` → `lambda v: int(v) == 0`
  - Koşulu sağlamayan satır sayısı 0 olmalı (geçer)
  - _ASSERTION_MAP'e eklendi
  - 3 test eklendi
- **Test**: 194 passed (191 + 3), 3 skipped ✅

---

## Kod Desenler (Bu Oturum)

### Assert Tipi Ekleme (GÖREV 43 örneği)
1. dq/engine.py → fonksiyon yaz (dönen: Callable[int, bool])
2. dq/config.py → from satırında import et
3. dq/config.py → _ASSERTION_MAP dict'e lambda ekle
4. tests/test_engine.py → TestXxx sınıfı + test_in_assertion_map()
5. Commit: `feat: GOREV N — [açıklama]`

### HTML Template Güncelleme (GÖREV 41-42 örneği)
- Python inline script (`python3 - << 'PYEOF'`) ile str.replace() kullan
- Kesin string match ve assert(old in txt) kontrolü
- Multiple old/new pair's: `.replace(old1, new1).replace(old2, new2)...`

---

## Dosya Yapısı Özet

dq/
  engine.py (19 assert fonksiyonu + CheckEngine)
  config.py (_ASSERTION_MAP, 19 entry)
  anomaly.py (AnomalyDetector)
  connectors.py (8 veritabanı tipi)
  metrics.py (MetricStore)
  scoring.py (Health score)
  reporter_v2.py (Full report)
  airflow.py (DQOperator)
routers/
  api.py
  ui.py
  sources.py
  checks.py
templates/
  run_detail.html
  anomaly.html
  (diğer UI sayfaları)
tests/
  test_engine.py (194 test)
DATABASE: MySQL 8.0 @ localhost:3308
METRICS: PostgreSQL @ host.docker.internal:5432 (prod) | SQLite (dev)

---

## Kritik Bağımlılıklar

- statsmodels 0.14.2 (Holt-Winters)
- numpy 1.26.4
- fastapi, uvicorn
- apache-airflow
- sqlalchemy

---

## Performance Notları
- profile_column: 3 sorgu → 1 sorgu
- CheckEngine: ThreadPoolExecutor (max 4 worker)
- Anomali tespiti: n<8 zscore, n>=8 EWMA, n>=14 Holt-Winters

---

## İşbirliği Protokolü
- SESSION_START.md / CLAUDE.md / ARCHITECTURE.md / TASKS.md → zip
- Single command per turn
- Python inline script tercih: python3 - << 'PYEOF'

---

## Başarılı Patterns
✅ Python inline replace (str match + assert)
✅ pytest + git flow
✅ MD session docs (context restore)
✅ Single-commit-per-feature
✅ Test-first (194 passed)
