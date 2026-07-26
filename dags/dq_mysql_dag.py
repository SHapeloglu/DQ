"""
dq_mysql_dag.py — DQ MySQL entegrasyon DAG'ı.

İki ayrı kontrol çalıştırır:
1. Airflow'un kendi DB'sini kontrol eder (airflow-db container)
2. Host makinedeki DQ DB'yi kontrol eder (lokal MySQL)
"""

from airflow import DAG
from airflow.utils.dates import days_ago
from dq_operator import DQOperator

with DAG(
    dag_id="dq_mysql_integration",
    description="DQ MySQL connector entegrasyon testi",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["dq", "mysql", "test"],
) as dag:

    # ── 1. Airflow DB kontrolü ─────────────────────────────────────────────
    check_airflow_db = DQOperator(
        task_id="check_airflow_db",
        config="/opt/airflow/dags/checks_airflow_db.toml",
        push_to_xcom=True,
        fail_on_error=False,   # test aşaması — hata olsa da devam et
    )

    # ── 2. Host MySQL — DQ DB kontrolü ────────────────────────────────────
    check_dq_db = DQOperator(
        task_id="check_dq_db",
        config="/opt/airflow/dags/checks_dq_db.toml",
        push_to_xcom=True,
        fail_on_error=False,
    )

    check_airflow_db >> check_dq_db
