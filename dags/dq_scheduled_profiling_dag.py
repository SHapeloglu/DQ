"""
dq_scheduled_profiling_dag.py — Periyodik kolon profilleme DAG'ı.
TOML config'den kaynak ID'lerini okur, her biri için POST /api/profile/{id} çağırır.
"""
import tomllib
from pathlib import Path
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import urllib.request

CONFIG_PATH = Path("/opt/airflow/dags/scheduled_profiling.toml")

def _load_config() -> dict:
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)

def profile_source(source_id: int, **kwargs) -> dict:
    cfg = _load_config()
    base_url = cfg["global"]["dq_api_base_url"]
    url = f"{base_url}/api/profile/{source_id}"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return {"source_id": source_id, "status": resp.status}
    except Exception as exc:
        raise RuntimeError(f"Profil tetikleme başarısız (source_id={source_id}): {exc}")

cfg = _load_config()
base_schedule = cfg["global"].get("default_schedule", "@daily")
sources = [s for s in cfg["sources"] if s.get("enabled", True)]

with DAG(
    dag_id="dq_scheduled_profiling",
    description="Periyodik kaynak profilleme — tüm aktif kaynaklar",
    schedule_interval=base_schedule,
    start_date=days_ago(1),
    catchup=False,
    tags=["dq", "profiling", "scheduled"],
) as dag:
    tasks = []
    for src in sources:
        sid = src["source_id"]
        t = PythonOperator(
            task_id=f"profile_source_{sid}",
            python_callable=profile_source,
            op_kwargs={"source_id": sid},
        )
        tasks.append(t)
    # Sıralı çalıştır (paralel bant genişliği sorununu önler)
    for i in range(1, len(tasks)):
        tasks[i - 1] >> tasks[i]
