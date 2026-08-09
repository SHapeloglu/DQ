"""routers/api.py — /api/* + /odata route'ları"""
from __future__ import annotations
import json as _json
from typing import List, Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
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
    # Alert gönder (sadece başarısız runlarda, source alert_enabled ise)
    if status == "fail":
        try:
            from extensions import load_alert_manager
            _ac = get_conn()
            try:
                with _ac.cursor() as _cur:
                    if payload.source_id:
                        _cur.execute("SELECT alert_enabled FROM sources WHERE id=%s", (payload.source_id,))
                        _row = _cur.fetchone()
                        _enabled = (_row or {}).get("alert_enabled", 1)
                    else:
                        _enabled = 1
                am = load_alert_manager(_ac) if _enabled else None
            finally:
                _ac.close()
            if am:
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

# ── Business Glossary ─────────────────────────────────────────────────────────
@router.get("/api/glossary/{source_id}")
def api_glossary_get(source_id: int):
    from database import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, column_name, business_name, description, owner, tags
                FROM column_profiles WHERE source_id = %s
                ORDER BY column_name
            """, (source_id,))
            return cur.fetchall()

@router.put("/api/glossary/{source_id}/{column_name}")
def api_glossary_update(source_id: int, column_name: str, payload: dict):
    allowed = {"business_name", "description", "owner", "tags"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        from fastapi import HTTPException
        raise HTTPException(400, "Güncellenecek alan yok")
    fields = ", ".join(f"{k}=%s" for k in updates)
    values = list(updates.values()) + [source_id, column_name]
    from database import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE column_profiles SET {fields}
                WHERE source_id=%s AND column_name=%s
            """, values)
        conn.commit()
    return {"ok": True, "updated": list(updates.keys())}

# ── Alert Ayarları ────────────────────────────────────────────────────────────
@router.get("/api/alert-settings")
def api_alert_settings_get():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM alert_settings LIMIT 1")
            row = cur.fetchone()
        return row or {}
    finally:
        conn.close()

@router.put("/api/alert-settings")
def api_alert_settings_put(payload: dict):
    allowed = {"slack_webhook","webhook_url","email_to","smtp_host","smtp_port","smtp_user","smtp_pass"}
    data = {k: v for k, v in payload.items() if k in allowed}
    if not data:
        from fastapi import HTTPException
        raise HTTPException(400, "Güncellenecek alan yok")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM alert_settings LIMIT 1")
            exists = cur.fetchone()
            if exists:
                fields = ", ".join(f"{k}=%s" for k in data)
                cur.execute(f"UPDATE alert_settings SET {fields} WHERE id=1", list(data.values()))
            else:
                fields = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                cur.execute(f"INSERT INTO alert_settings (id, {fields}) VALUES (1, {placeholders})", list(data.values()))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "updated": list(data.keys())}

@router.put("/api/sources/{source_id}/alert-enabled")
def api_source_alert_toggle(source_id: int, payload: dict):
    enabled = int(bool(payload.get("alert_enabled", 1)))
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE sources SET alert_enabled=%s WHERE id=%s", (enabled, source_id))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "source_id": source_id, "alert_enabled": enabled}

# ── PII / KVKK Raporu ─────────────────────────────────────────────────────────
@router.get("/api/pii-report")
def api_pii_report():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cp.source_id, s.name as source_name,
                       cp.column_name, cp.pii_type,
                       cp.is_pii, cp.tags
                FROM column_profiles cp
                JOIN sources s ON cp.source_id = s.id
                WHERE cp.is_pii = 1
                ORDER BY s.name, cp.column_name
            """)
            rows = cur.fetchall()
    finally:
        conn.close()
    summary: dict = {}
    for r in rows:
        sname = r["source_name"]
        if sname not in summary:
            summary[sname] = {"source_id": r["source_id"], "pii_columns": []}
        summary[sname]["pii_columns"].append({
            "column": r["column_name"],
            "pii_type": r["pii_type"],
            "tags": r["tags"],
        })
    return {
        "total_pii_columns": len(rows),
        "sources_affected": len(summary),
        "report": summary,
    }

@router.get("/api/pii-report/{source_id}")
def api_pii_report_source(source_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, pii_type, tags, null_pct, distinct_count
                FROM column_profiles
                WHERE source_id = %s AND is_pii = 1
                ORDER BY column_name
            """, (source_id,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return {"source_id": source_id, "pii_columns": rows, "count": len(rows)}

# ── PII / KVKK Raporu ─────────────────────────────────────────────────────────
@router.get("/api/pii-report")
def api_pii_report():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cp.source_id, s.name as source_name,
                       cp.column_name, cp.pii_type,
                       cp.is_pii, cp.tags
                FROM column_profiles cp
                JOIN sources s ON cp.source_id = s.id
                WHERE cp.is_pii = 1
                ORDER BY s.name, cp.column_name
            """)
            rows = cur.fetchall()
    finally:
        conn.close()
    summary: dict = {}
    for r in rows:
        sname = r["source_name"]
        if sname not in summary:
            summary[sname] = {"source_id": r["source_id"], "pii_columns": []}
        summary[sname]["pii_columns"].append({
            "column": r["column_name"],
            "pii_type": r["pii_type"],
            "tags": r["tags"],
        })
    return {
        "total_pii_columns": len(rows),
        "sources_affected": len(summary),
        "report": summary,
    }

@router.get("/api/pii-report/{source_id}")
def api_pii_report_source(source_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, pii_type, tags, null_pct, distinct_count
                FROM column_profiles
                WHERE source_id = %s AND is_pii = 1
                ORDER BY column_name
            """, (source_id,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return {"source_id": source_id, "pii_columns": rows, "count": len(rows)}


# ── Rule Library API ──────────────────────────────────────────────────────────

@router.get("/api/rule-library")
def api_rule_library_list():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM rule_library ORDER BY times_used DESC")
            rows = cur.fetchall()
    finally:
        conn.close()
    return {"rules": rows, "count": len(rows)}


@router.post("/api/rule-library")
async def api_rule_library_create(request: Request):
    from fastapi.responses import RedirectResponse
    form = await request.form()
    pattern   = form.get("column_name_pattern", "").strip()
    rule_type = form.get("rule_type", "").strip()
    col_type  = form.get("column_type", "").strip() or None
    if not pattern or not rule_type:
        return RedirectResponse("/rule-library?msg=Pattern+ve+kural+tipi+zorunludur", status_code=303)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT IGNORE INTO rule_library (column_name_pattern, column_type, rule_type)
                VALUES (%s, %s, %s)
            """, (pattern, col_type, rule_type))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/rule-library?msg=Pattern+eklendi", status_code=303)


@router.post("/api/rule-library/{rule_id}/delete")
def api_rule_library_delete(rule_id: int):
    from fastapi.responses import RedirectResponse
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM rule_library WHERE id = %s", (rule_id,))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/rule-library?msg=Pattern+silindi", status_code=303)

@router.get("/api/anomaly-results")
def api_anomaly_results(source_id=None, limit: int = 200):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if source_id:
                cur.execute("""
                    SELECT rr.check_name, rr.passed, rr.value_actual, rr.expected,
                           rr.message, r.run_at, r.source_id
                    FROM run_results rr JOIN runs r ON rr.run_id = r.id
                    WHERE r.source_id = %s
                      AND rr.check_name REGEXP 'anomal|zscore|volume|trend|distribution'
                    ORDER BY r.run_at DESC LIMIT %s
                """, (source_id, limit))
            else:
                cur.execute("""
                    SELECT rr.check_name, rr.passed, rr.value_actual, rr.expected,
                           rr.message, r.run_at, r.source_id
                    FROM run_results rr JOIN runs r ON rr.run_id = r.id
                    WHERE rr.check_name REGEXP 'anomal|zscore|volume|trend|distribution'
                    ORDER BY r.run_at DESC LIMIT %s
                """, (limit,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return {"results": rows, "count": len(rows)}
