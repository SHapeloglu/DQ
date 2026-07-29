"""
dq_postgres_dag.py — DQ PostgreSQL entegrasyon DAG'ı.
PostgreSQL veritabanında veri kalitesi kontrolleri çalıştırır.
"""
from airflow import DAG
from airflow.utils.dates import days_ago
from dq_operator import DQOperator

with DAG(
    dag_id="dq_postgres_integration",
    description="DQ PostgreSQL connector entegrasyon testi",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["dq", "postgres", "test"],
) as dag:
    # ── PostgreSQL kontrolü ────────────────────────────────────────────────
    check_postgres_db = DQOperator(
        task_id="check_postgres_db",
        config="/opt/airflow/dags/checks_postgres_db.toml",
        push_to_xcom=True,
        fail_on_error=False,
    )
    
    check_postgres_db
