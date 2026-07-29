"""
dq_mongo_dag.py — DQ MongoDB entegrasyon DAG'ı.
MongoDB koleksiyonlarında veri kalitesi kontrolleri çalıştırır.
"""
from airflow import DAG
from airflow.utils.dates import days_ago
from dq_operator import DQOperator

with DAG(
    dag_id="dq_mongo_integration",
    description="DQ MongoDB connector entegrasyon testi",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["dq", "mongodb", "test"],
) as dag:
    # ── MongoDB kontrolü ───────────────────────────────────────────────────
    check_mongo_db = DQOperator(
        task_id="check_mongo_db",
        config="/opt/airflow/dags/checks_mongo_db.toml",
        push_to_xcom=True,
        fail_on_error=False,
    )
    
    check_mongo_db
