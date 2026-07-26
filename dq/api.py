"""
api.py — DQ sonuçlarını sunan FastAPI uygulaması.

Kurulum:
    pip install fastapi uvicorn

Çalıştır:
    uvicorn dq.api:app --host 0.0.0.0 --port 8000

Endpointler:
    POST /api/runs              → Airflow / CLI sonuç gönderir
    GET  /api/runs              → tüm run'lar (JSON)
    GET  /api/runs/{run_id}     → tek run detayı
    GET  /api/results           → düzleştirilmiş check sonuçları (BI için)
    GET  /api/results.csv       → CSV export (Excel, her BI aracı)
    GET  /odata/Results         → OData v4 (Power BI, Qlik native connector)
    GET  /health                → sağlık kontrolü
"""

from __future__ import annotations
import csv
import io
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import StreamingResponse, JSONResponse
    from pydantic import BaseModel
except ImportError:
    raise ImportError("pip install fastapi uvicorn")


# ── Uygulama ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="DQ API",
    description="Veri kalitesi sonuçları — REST, CSV ve OData",
    version="1.0.0",
)

DB_PATH = Path("dq_results.db")


# ── Veritabanı ────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id   TEXT PRIMARY KEY,
            dag_id   TEXT,
            task_id  TEXT,
            config   TEXT,
            mode     TEXT,
            run_at   TEXT,
            payload  TEXT    -- ham JSON
        );
        CREATE TABLE IF NOT EXISTS check_results (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id   TEXT,
            name     TEXT,
            passed   INTEGER,
            value    REAL,
            expected TEXT,
            run_at   TEXT,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        );
        CREATE INDEX IF NOT EXISTS idx_cr_run_id ON check_results(run_id);
        CREATE INDEX IF NOT EXISTS idx_cr_name   ON check_results(name);
        CREATE INDEX IF NOT EXISTS idx_cr_run_at ON check_results(run_at);
    """)
    conn.commit()
    return conn


# ── Pydantic modelleri ────────────────────────────────────────────────────────

class RunPayload(BaseModel):
    """Airflow DQOperator veya CLI'dan gelen payload."""
    dag_id:  str | None = None
    task_id: str | None = None
    run_id:  str | None = None
    run_at:  str | None = None
    config:  str | None = None
    mode:    str = "checks"
    results: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# ── Endpointler ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "time": _now_iso()}


# ── Run yaz ──────────────────────────────────────────────────────────────────

@app.post("/api/runs", status_code=201)
def post_run(payload: RunPayload):
    """Airflow DQOperator veya CLI bu endpoint'e POST atar."""
    run_id = payload.run_id or str(uuid.uuid4())
    run_at = payload.run_at or _now_iso()

    db = _get_db()
    try:
        db.execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?)",
            (run_id, payload.dag_id, payload.task_id,
             payload.config, payload.mode, run_at,
             json.dumps(payload.model_dump())),
        )

        for r in payload.results:
            passed = r.get("passed")
            if passed is None:
                passed = not r.get("is_anomaly", False)
            db.execute(
                "INSERT INTO check_results (run_id,name,passed,value,expected,run_at) "
                "VALUES (?,?,?,?,?,?)",
                (run_id,
                 r.get("name") or r.get("metric_name", "unknown"),
                 int(bool(passed)),
                 r.get("value") or r.get("current"),
                 str(r.get("expected", "")),
                 run_at),
            )
        db.commit()
    finally:
        db.close()

    return {"run_id": run_id, "accepted": len(payload.results)}


# ── Run listesi ──────────────────────────────────────────────────────────────

@app.get("/api/runs")
def get_runs(
    limit: int = Query(50, ge=1, le=1000),
    dag_id: str | None = None,
):
    db = _get_db()
    try:
        if dag_id:
            rows = db.execute(
                "SELECT run_id,dag_id,task_id,config,mode,run_at "
                "FROM runs WHERE dag_id=? ORDER BY run_at DESC LIMIT ?",
                (dag_id, limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT run_id,dag_id,task_id,config,mode,run_at "
                "FROM runs ORDER BY run_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    db = _get_db()
    try:
        row = db.execute(
            "SELECT payload FROM runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Run bulunamadı")
        return json.loads(row["payload"])
    finally:
        db.close()


# ── Düzleştirilmiş sonuçlar (BI için) ────────────────────────────────────────

@app.get("/api/results")
def get_results(
    limit:   int = Query(500, ge=1, le=10000),
    name:    str | None = None,
    passed:  bool | None = None,
    dag_id:  str | None = None,
):
    """
    Tüm check sonuçları — Power BI, Qlik, Superset bu endpoint'i kullanır.

    Filtreler:
        ?name=siparis_sayisi
        ?passed=false          → sadece başarısız olanlar
        ?dag_id=orders_quality
    """
    db = _get_db()
    try:
        where, params = [], []

        if name:
            where.append("cr.name = ?"); params.append(name)
        if passed is not None:
            where.append("cr.passed = ?"); params.append(int(passed))
        if dag_id:
            where.append("r.dag_id = ?"); params.append(dag_id)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        params.append(limit)

        rows = db.execute(f"""
            SELECT
                cr.id, cr.run_id, cr.name, cr.passed,
                cr.value, cr.expected, cr.run_at,
                r.dag_id, r.task_id, r.config, r.mode
            FROM check_results cr
            LEFT JOIN runs r ON cr.run_id = r.run_id
            {where_sql}
            ORDER BY cr.run_at DESC
            LIMIT ?
        """, params).fetchall()

        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


# ── CSV export ────────────────────────────────────────────────────────────────

@app.get("/api/results.csv")
def get_results_csv(limit: int = Query(500, ge=1, le=10000)):
    """
    CSV olarak indir — Excel, Tableau, her BI aracı açar.
    Power BI'da: Veri Al → Web → bu URL
    """
    db = _get_db()
    try:
        rows = db.execute("""
            SELECT cr.run_id, cr.name, cr.passed, cr.value,
                   cr.expected, cr.run_at, r.dag_id, r.task_id
            FROM check_results cr
            LEFT JOIN runs r ON cr.run_id = r.run_id
            ORDER BY cr.run_at DESC LIMIT ?
        """, (limit,)).fetchall()
    finally:
        db.close()

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=dict(rows[0]).keys())
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dq_results.csv"},
    )


# ── OData v4 (Power BI + Qlik native connector) ───────────────────────────────

@app.get("/odata/$metadata")
def odata_metadata():
    """OData metadata — Power BI ve Qlik bunu otomatik okur."""
    xml = """<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="DQ" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <EntityType Name="Result">
        <Key><PropertyRef Name="id"/></Key>
        <Property Name="id"       Type="Edm.Int32"    Nullable="false"/>
        <Property Name="run_id"   Type="Edm.String"/>
        <Property Name="name"     Type="Edm.String"/>
        <Property Name="passed"   Type="Edm.Boolean"/>
        <Property Name="value"    Type="Edm.Double"/>
        <Property Name="expected" Type="Edm.String"/>
        <Property Name="run_at"   Type="Edm.String"/>
        <Property Name="dag_id"   Type="Edm.String"/>
        <Property Name="task_id"  Type="Edm.String"/>
      </EntityType>
      <EntityContainer Name="DQService">
        <EntitySet Name="Results" EntityType="DQ.Result"/>
      </EntityContainer>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>"""
    from fastapi.responses import Response
    return Response(content=xml, media_type="application/xml")


@app.get("/odata/Results")
def odata_results(
    top:    int = Query(500, alias="$top"),
    skip:   int = Query(0,   alias="$skip"),
    filter: str | None = Query(None, alias="$filter"),
):
    """
    OData v4 endpoint — Power BI ve Qlik Sense native connector ile bağlanır.

    Power BI'da:
        Veri Al → OData Akışı → http://dq-api:8000/odata/Results

    Qlik Sense'te:
        Yeni bağlantı → REST → http://dq-api:8000/odata/Results
    """
    db = _get_db()
    try:
        rows = db.execute("""
            SELECT cr.id, cr.run_id, cr.name, cr.passed,
                   cr.value, cr.expected, cr.run_at,
                   r.dag_id, r.task_id
            FROM check_results cr
            LEFT JOIN runs r ON cr.run_id = r.run_id
            ORDER BY cr.run_at DESC
            LIMIT ? OFFSET ?
        """, (top, skip)).fetchall()
    finally:
        db.close()

    values = []
    for r in rows:
        d = dict(r)
        d["passed"] = bool(d["passed"])   # OData boolean
        values.append(d)

    # OData JSON format (Power BI ve Qlik bunu bekler)
    return JSONResponse({
        "@odata.context": "/odata/$metadata#Results",
        "@odata.count":   len(values),
        "value":          values,
    })
