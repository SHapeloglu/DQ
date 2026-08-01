# Aktif Görevler ve Proje Durumu

## Tamamlananlar
- [x] Graphify kurulumu ve kod haritası oluşturuldu (507 node, 938 edge)
- [x] .claude/ dokümantasyon katmanı kuruldu
- [x] test_engine.py — test_multiple_checks düzeltildi (conftest MockConnector IS NULL keyword eklendi)
- [x] SqlAlchemyConnector — dialect/host/port/database/user/password parametreleri eklendi
- [x] OracleConnector — service_name parametresi eklendi, service_name/service alias desteği
- [x] 78/78 unit test geçiyor (integration testleri hariç — Oracle/SQLite bağlantısı gerektirir)

## Açık Teknik Borçlar
- [ ] `dq/airflow.py:L132` — DQOperator→ContractValidator bağlantısı INFERRED, explicit import yap
- [ ] `main.py` 672 satır — route'lar `routes.py`'ye taşınabilir
- [ ] pytest.ini oluştur — integration mark'ı kaydet, warning'i kaldır
- [ ] `pytest.mark.integration` warning'i gider

## Sıradaki Görevler
- [ ] pytest.ini veya pyproject.toml'a mark tanımı ekle
- [ ] DQOperator explicit import düzeltmesi
- [ ] Yapılacak yeni geliştirme adımlarının belirlenmesi
