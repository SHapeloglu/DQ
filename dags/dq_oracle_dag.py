"""
dq_oracle_dag.py — DQ Oracle entegrasyon DAG'ı.
Oracle veritabanında veri kalitesi kontrolleri çalıştırır.
"""
from airflow import DAG
from airflow.utils.dates import days_ago
from dq_operator import DQOperator

with DAG(
    dag_id="dq_oracle_integration",
    description="DQ Oracle connector entegrasyon testi",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["dq", "oracle", "test"],
) as dag:
    # ── Oracle kontrolü ────────────────────────────────────────────────────
    check_oracle_db = DQOperator(
        task_id="check_oracle_db",
        config="/opt/airflow/dags/checks_oracle_db.toml",
        push_to_xcom=True,
        fail_on_error=False,
    )
    
    check_oracle_db
