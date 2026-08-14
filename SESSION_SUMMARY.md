# DQ Proje — GÖREV 3+4+5 Tamamlandı ✨

## İstatistikler
- **Testler**: 69 passed, 1 skipped ✅
- **Connector'lar**: +1 MongoDB
- **Database desteği**: +DB2 (ibm_db_sa)
- **DAG'lar**: +3 yeni (PostgreSQL, Oracle, MongoDB)

## GÖREV 3 — MongoDB Connector ✅
- MongoConnector sınıfı (BaseConnector'dan)
- connect(), execute(), close() metodları
- Dict query desteği (pipeline + filter)
- pymongo>=4.0 eklendi
- 2 test geçti

## GÖREV 4 — DB2 Doğrulama ✅
- ibm-db>=2.3.0 + ibm-db-sa>=0.4.0 eklendi
- SqlAlchemyConnector dialect desteği
- 2 test geçti

## GÖREV 5 — Airflow DAG Genişletme ✅
- dq_postgres_dag.py, dq_oracle_dag.py, dq_mongo_dag.py
- checks_postgres_db.toml, checks_oracle_db.toml, checks_mongo_db.toml
- Tüm DAG'lar syntax check'ten geçti

## Git
- Commit: a7203b4 GÖREV 3+4+5: MongoConnector, DB2, Airflow DAGs
- 9 files changed, 423 insertions, 169 deletions

## Test Sonuçları
======================== 69 passed, 1 skipped ==========================
