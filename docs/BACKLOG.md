# docs/BACKLOG.md — DQ (Data Quality Platform) Fikir Havuzu

Aktif görev listesi `docs/TASKS.md`'de (GÖREV 1–48 tamamlandı, "Backlog: Boş"; 196 test geçiyor). Bu dosya `TASKS.md`'deki rakip karşılaştırması ve pazar geri bildiriminden çıkan, henüz göreve dönüşmemiş fikirleri tutar.

## Rekabet açıkları (TASKS.md "Rakip Karşılaştırma")

- **Ölçeklenebilirlik (6/10, en zayıf alan):** kontroller `ThreadPoolExecutor` ile en fazla 4 paralel çalışıyor. Seçenekler: kaynak başına havuz, Celery/RQ kuyruğu, Airflow DAG'larına daha fazla iş dağıtımı. Büyük tablolarda örnekleme (sampling) modu.
- Soda Core / Great Expectations / Dataplex / AWS Glue DQ karşısında güçlü yanları koru: PII/KVKK (9/10), maliyet, sağlık skoru, wizard UX, anomali trendi.

## Pazar geri bildiriminden

- Kullanıcılar **kolay kullanım + kural çeşitliliği** istiyor → kural kütüphanesine (`templates/rule_library.html`) sektör şablonları (e-ticaret, finans, CRM) ve tek tıkla ekleme.
- AWS Glue `DetectAnomalies`'e karşı 3 yöntemli anomali sistemi avantaj — açıklanabilirlik (neden anomali?) ekranı ile pekiştir.

## Diğer fikirler

- VCE (`ValidityControlEngine`) ve DataPortal kalite kurallarıyla ortak kural formatı / skor modeli.
- Kontrol sonuçlarını Prometheus metriklerine aktarma (dwh-db-monitor ile aynı Grafana'da).
- AutoSleep'ten uyanma süresini kısaltmak için hafif "durum" sayfası (dq.powerbi.com.tr ilk açılış gecikmesi).

## Ekleme Şablonu

```markdown
### Başlık
- **Kategori:** yeni özellik / iyileştirme / teknik borç / araştırma
- **Neden:** kısa gerekçe
- **Notlar:** büyüklük, bağımlılıklar, riskler
```
