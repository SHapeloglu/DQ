# CLAUDE.md — İşbirliği Notları

## Bu Oturum Özeti (GÖREV 46-48)

### GÖREV 46: Dataplex vs DQ Benchmark Raporu ✅
- **Dosya**: docs/BENCHMARK.md
- **İçerik**: 5 rakip (Dataplex, AWS Glue, Soda Core, Great Expectations)
- **Tablo**: 19 assert tipi karşılaştırması
- **Sonuç**: DQ-main 8.3/10
  - Güçlü: PII/KVKK (9/10), maliyet (9.5/10), anomali (8.5/10), wizard UX (8.5/10)
  - Zayıf: ölçeklenebilirlik (6.5/10)

### GÖREV 48: Data Profiling Export (CSV/JSON) ✅
- **Endpoint**: `/api/profile-export/{source_id}?format=csv|json`
- **Response Type**: StreamingResponse (dosya download)
- **İçerik**: column_profiles tablosundan istatistikler
- **Test**: test_profile_export_csv, test_profile_export_json (2 passed)
- **Status Code**: 200 (başarılı), 404 (profil yok)

## Test Durumu
- Önceki: 194 passed, 3 skipped
- Şimdi: 196 passed, 3 skipped (+2 test)

## Dosya Yapısı
docs/
  BENCHMARK.md (yeni)
routers/
  api.py (profile-export endpoint eklendi)
tests/
  test_profile_export.py (yeni)

## Git Tarihçesi
79a5173 feat: GOREV 48 — Data profiling export (CSV/JSON)
4ab7d9c feat: GOREV 46 — Dataplex vs DQ benchmark raporu

## Backlog
- GÖREV 44: Anomali trend analizi (trend direction: ↑/→/↓)
- GÖREV 45: Read replica desteği (MetricStore Postgres)
- GÖREV 47: Custom assertion script upload

## Başarılı Patterns (Bu Oturum)
✅ StreamingResponse ile memory-safe dosya download
✅ Mock'ta cursor.close() desteği
✅ Markdown benchmark raporu (rakip analiz)
✅ docs/ dizini (GitHub'dan browse edilebilir)
