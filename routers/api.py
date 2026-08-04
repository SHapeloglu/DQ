"""routers/api.py — /api/* + /odata route'ları"""
from __future__ import annotations
import json as _json
from typing import List, Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_conn

router = APIRouter()


# ── Profil ───────────────────────────────────────────────────────────────────

@router.get("/api/columns/{source_id}")
def api_get_columns(source_id: int):
    from profiler import get_columns
    from dq.connectors import build_connector

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM sources WHERE id = %s", (source_id,))
            source = cur.fetchone()
    finally:
        conn.close()

    if not source:
        raise HTTPException(404, "Kaynak bulunamadı")

    config = _json.loads(source["config"])
    config["type"] = source["type"]
    try:
        connector = build_connector(config)
        columns   = get_columns(connector)
        return {"source_id": source_id, "columns": columns}
    except Exception as e:
        return {"source_id": source_id, "columns": [], "error": str(e)}


@router.post("/api/profile/{source_id}")
def api_run_profile(source_id: int):
    from profiler import profile_source, suggest_rules
    from dq.connectors import build_connector

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM sources WHERE id = %s", (source_id,))
            source = cur.fetchone()
    except Exception as e:
        conn.close()
        raise HTTPException(500, str(e))

    if not source:
        conn.close()
        raise HTTPException(404, "Kaynak bulunamadı")

    config = _json.loads(source["config"])
    config["type"] = source["type"]
    try:
        connector = build_connector(config)
        result    = profile_source(connector, source_id, conn)
        if "columns" in result:
            result["suggestions"] = suggest_rules(result["columns"], conn)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@router.get("/api/profile/{source_id}")
def api_get_profile(source_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM column_profiles WHERE source_id = %s ORDER BY id",
                (source_id,)
            )
            columns = cur.fetchall()
        from profiler import suggest_rules
        suggestions = suggest_rules(columns, conn) if columns else []
    finally:
        conn.close()
    return {"source_id": source_id, "columns": columns, "suggestions": suggestions}


# ── Runs API ─────────────────────────────────────────────────────────────────

class RunPayload(BaseModel):
    source_id: Optional[int] = None
    dag_id:    Optional[str] = None
    task_id:   Optional[str] = None
    results:   List[Dict[str, Any]] = []
    summary:   Dict[str, Any] = {}


@router.post("/api/runs", status_code=201)
def api_post_run(payload: RunPayload):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            total  = payload.summary.get("total", len(payload.results))
            passed = payload.summary.get("passed", 0)
            failed = total - passed
            status = "pass" if failed == 0 else "fail"
            cur.execute("""
                INSERT INTO runs (source_id, dag_id, task_id, total, passed, failed, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (payload.source_id, payload.dag_id, payload.task_id,
                  total, passed, failed, status))
            run_id = cur.lastrowid
            for r in payload.results:
                cur.execute("""
                    INSERT INTO run_results
                        (run_id, check_name, passed, value_actual, expected, message)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    run_id,
                    r.get("name", ""),
                    int(r.get("passed", False)),
                    str(r.get("value", "")),
                    str(r.get("expected", "")),
                    r.get("message", ""),
                ))
        conn.commit()
    finally:
        conn.close()
    # Alert gönder (sadece başarısız runlarda)
    if status == "fail":
        try:
            import os
            from extensions import AlertManager
            am = AlertManager(
                email_to      = os.getenv("ALERT_EMAIL_TO") or None,
                smtp_host     = os.getenv("ALERT_SMTP_HOST", "localhost"),
                smtp_port     = int(os.getenv("ALERT_SMTP_PORT", "587")),
                smtp_user     = os.getenv("ALERT_SMTP_USER") or None,
                smtp_pass     = os.getenv("ALERT_SMTP_PASS") or None,
                slack_webhook = os.getenv("ALERT_SLACK_WEBHOOK") or None,
                webhook_url   = os.getenv("ALERT_WEBHOOK_URL") or None,
            )
            am.send(payload.results, run_id=run_id, source_name=payload.dag_id or "")
        except Exception:
            pass  # Alert hatası run'ı engellemez
    return {"run_id": run_id, "status": status}


@router.get("/api/results")
def api_results(limit: int = 500, passed: Optional[bool] = None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if passed is not None:
                cur.execute("""
                    SELECT rr.*, r.dag_id, r.task_id, r.run_at
                    FROM run_results rr JOIN runs r ON rr.run_id = r.id
                    WHERE rr.passed = %s ORDER BY r.run_at DESC LIMIT %s
                """, (int(passed), limit))
            else:
                cur.execute("""
                    SELECT rr.*, r.dag_id, r.task_id, r.run_at
                    FROM run_results rr JOIN runs r ON rr.run_id = r.id
                    ORDER BY r.run_at DESC LIMIT %s
                """, (limit,))
            return cur.fetchall()
    finally:
        conn.close()


# ── OData ─────────────────────────────────────────────────────────────────────

@router.get("/odata/Results")
def odata_results(top: int = 500, skip: int = 0):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT rr.*, r.dag_id, r.task_id, r.run_at
                FROM run_results rr JOIN runs r ON rr.run_id = r.id
                ORDER BY r.run_at DESC
                LIMIT %s OFFSET %s
            """, (top, skip))
            rows = cur.fetchall()
    finally:
        conn.close()
    for r in rows:
        r["passed"] = bool(r["passed"])
    return {"@odata.context": "/odata/$metadata#Results", "value": rows}


# ── Sağlık Skoru ─────────────────────────────────────────────────────────────
@router.get("/api/health-score")
def api_all_scores():
    from dq.scoring import get_all_scores
    return get_all_scores()

@router.get("/api/health-score/{source_id}")
def api_health_score(source_id: int):
    from dq.scoring import get_health_score
    return get_health_score(source_id)

@router.get("/api/health-score/{source_id}/trend")
def api_score_trend(source_id: int, days: int = 7):
    from dq.scoring import get_score_trend
    return get_score_trend(source_id, days)
