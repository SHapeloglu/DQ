# CLAUDE.md — İşbirliği Notları

## Oturum Geçmişi

### GÖREV 47: Custom Assertion Script Upload ✅ (Bu Oturum)
- **Dosyalar**: dq/engine.py, dq/config.py, routers/scripts.py, templates/scripts.html, templates/script_form.html
- **DB**: custom_scripts tablosu (id, name, code, function_name, description, is_active)
- **Güvenlik**: AST validation — os, subprocess, sys, shutil, pathlib, socket, urllib, requests yasaklı; eval, exec, open, compile yasaklı
- **Execution**: Kısıtlı __builtins__ ile exec() — len, str, int, float, bool, abs, min, max, math vb.
- **API**: /scripts CRUD + /api/scripts/test dry-run endpoint
- **Commit**: fb777c2

### GÖREV 44: Anomali Trend Yönü Analizi ✅
- **Dosya**: dq/anomaly.py
- **Yenilik**: _detect_trend() — up/stable/down, %5 tolerans, AnomalyResult.trend_direction
- **UI**: templates/anomaly.html — ↑ (yeşil), → (gri), ↓ (kırmızı) badge
- **Commit**: 01a5a97

### GÖREV 45: Read Replica Desteği ✅
- **Dosya**: dq/metrics.py
- **Yenilik**: MetricStore(read_replica_dsn=...) — write→primary, read→replica
- **Geriye uyumlu**: read_replica_dsn opsiyonel
- **Commit**: 2cd83ff

### GÖREV 46: Benchmark Raporu ✅
- **Dosya**: docs/BENCHMARK.md — 19 assert tipi karşılaştırması, anomali deep-dive, PII, TCO
- **Commit**: 4ab7d9c

### GÖREV 48: Profile Export ✅
- **Endpoint**: /api/profile-export/{source_id}?format=csv|json
- **Yöntem**: StreamingResponse (FileResponse değil)
- **Commit**: 79a5173

---

## Kritik Patterns (Öğrenilen)

| Problem | Çözüm |
|---|---|
| Turkish UTF-8 içerik | python3 - << 'PYEOF' veya /tmp/fix_*.py |
| sed güvenilmez | String replace script, assert old in txt guard ile |
| Pydantic + from __future__ import annotations | Optional[int] KULLANMA, Request import et |
| Test mock | routers.api.get_conn — database.get_conn değil |
| pymysql venv'de yok | Testlerde MagicMock, database.py import etme |
| DB migration | docker exec -i dq-db mysql -u root -proot dq << 'SQL' |
| Büyük değişiklik | py_compile → pytest → Docker build sırası |

---

## Test Durumu

**Baseline: 196 passed, 3 skipped** (regression hiç olmadı)

---

## Git Tarihçesi (Son 10)

2dc7372 docs: GOREV 47 sonrası senkronizasyon
fb777c2 feat: GOREV 47 — Custom assertion script upload
d3b0e5d chore: root klasörünü temizle
4b90fa6 docs: ARCHITECTURE ve BENCHMARK senkronizasyon düzeltmesi
37f34eb docs: SESSION_START, CLAUDE, ARCHITECTURE, TASKS güncellendi
99872b4 docs: GOREV 44-45 sonrası güncellendi
2cd83ff feat: GOREV 45 — Read replica desteği
b815896 docs: SESSION_START GOREV 44 sonrası güncellendi
01a5a97 feat: GOREV 44 — Anomali trend yönü analizi
5800416 docs: tüm session MD'leri docs/ dizinine eklendi

---

## Backlog Kalan

Boş — tüm core feature'lar tamamlandı.

Potansiyel: Wizard custom script entegrasyonu (GÖREV 49), ölçeklenebilirlik (GÖREV 50)
