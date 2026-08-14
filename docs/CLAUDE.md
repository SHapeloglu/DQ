# CLAUDE.md — İşbirliği Notları

## Bu Oturum Özeti (GÖREV 44-45)

### GÖREV 44: Anomali Trend Yönü Analizi ✅
- **Dosya**: dq/anomaly.py
- **Yenilik**: _detect_trend() helper — son N değerin eğilimi (up/stable/down)
- **Entegrasyon**: AnomalyResult.trend_direction field, to_check_dict() message'inde
- **UI**: anomaly.html'de trend badge (↑ yeşil, → gri, ↓ kırmızı)
- **Status**: 196 passed, 3 skipped ✅

### GÖREV 45: Read Replica Desteği (MetricStore) ✅
- **Dosya**: dq/metrics.py
- **Yenilik**: read_replica_dsn parametresi — okuma Postgres replicadan
- **Mantık**: 
  - Write ops (record/record_results) → primary (_pg_conn)
  - Read ops (history/known_metrics/get_recent_values) → replica (_pg_conn_read)
  - Backward compat: read_replica_dsn opsiyonel (yoksa primary'den oku)
- **Status**: 196 passed, 3 skipped ✅

## Test Durumu
- Önceki: 196 passed, 3 skipped
- Şimdi: 196 passed, 3 skipped (test regression yok)

## Git Tarihçesi (bu oturum)
2cd83ff feat: GOREV 45 — Read replica desteği (MetricStore)
01a5a97 feat: GOREV 44 — Anomali trend yönü analizi (up/stable/down)

## Backlog
- GÖREV 47: Custom assertion script upload (L)

## Başarılı Patterns (Bu Oturum)
✅ _detect_trend() — simple ortalama karşılaştırması (%5 tolerans)
✅ Read-write split: `self._pg_conn_read` vs `self._pg_conn`
✅ Backward compatibility: read_replica_dsn varsayılan None
