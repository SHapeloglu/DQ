# CLAUDE.md — İşbirliği Notları

## Bu Oturum Özeti (GÖREV 44-45-47)

### GÖREV 44: Anomali Trend Yönü Analizi ✅
- **Dosya**: dq/anomaly.py
- **Yenilik**: _detect_trend() helper, AnomalyResult.trend_direction field, templates/anomaly.html trend badge
- **Status**: 196 passed, 3 skipped ✅

### GÖREV 45: Read Replica Desteği (MetricStore) ✅
- **Dosya**: dq/metrics.py
- **Yenilik**: read_replica_dsn parametresi, write→primary, read→replica
- **Status**: 196 passed, 3 skipped ✅

### GÖREV 47: Custom Assertion Script Upload ✅
- **Dosya**: dq/engine.py (custom_script_assertion), dq/config.py (_ASSERTION_MAP), routers/scripts.py (/scripts CRUD + /api/scripts/test)
- **Yenilik**: AST security validation (os, subprocess vb. yasaklı), kısıtlı __builtins__, DB'den script yükleme
- **Templates**: scripts.html (liste) + script_form.html (editör + test alanı)
- **Status**: 196 passed, 3 skipped ✅

### Önceki GÖREV'ler (Session 1-3)
- GÖREV 46: Dataplex vs DQ benchmark raporu
- GÖREV 48: Data profiling export CSV/JSON
- GÖREV 41-43: run_detail ewma badge, anomali dashboard filtresi, row_condition

## Test Durumu
- Baseline: 196 passed, 3 skipped (regression yok)

## Dosya Yapısı
- docs/ — SESSION_START.md, CLAUDE.md, ARCHITECTURE.md, TASKS.md, BENCHMARK.md
- dq/anomaly.py — trend_direction
- dq/metrics.py — read_replica_dsn
- routers/api.py — profile-export endpoint
- templates/anomaly.html — trend badge
- tests/test_profile_export.py — GOREV 48 testleri

## Git Tarihçesi
99872b4 docs: GOREV 44-45 sonrası güncellendi
2cd83ff feat: GOREV 45 — Read replica desteği (MetricStore)
01a5a97 feat: GOREV 44 — Anomali trend yönü analizi (up/stable/down)
4ab7d9c feat: GOREV 46 — Dataplex vs DQ benchmark raporu
79a5173 feat: GOREV 48 — Data profiling export (CSV/JSON)

## Backlog Kalan
Boş — tüm core feature'lar tamamlandı

## Başarılı Patterns
✅ _detect_trend() — %5 tolerans, minimal
✅ Read-write split: psycopg2 native
✅ Backward compatibility: read_replica_dsn optional
✅ Trend badge: regex pattern match
✅ AST-based code security — exec() kısıtlı __builtins__ ile
✅ DB-backed custom functions — script_id → config.py helper
✅ Dry-run test endpoint (/api/scripts/test) — live validation
