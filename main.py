"""
main.py — DQ Web UI — FastAPI + Jinja2 + Tailwind + MySQL

Kurulum:
    pip install fastapi uvicorn jinja2 python-multipart pymysql python-dotenv tomli

Çalıştır:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import get_conn, init_db
from toml_import import parse_toml, toml_to_db

app = FastAPI(title="DQ — Veri Kalitesi Platformu")
templates = Jinja2Templates(directory="templates")

# ── Auth ve ek özellik route'larını kaydet ──────────────────────────────────
# Bunlar olmadan auth.py/main_extensions.py'deki route'lar (login, dashboard,
# alerts, users, export) hiç calismaz - dosyalar orada durur ama FastAPI
# hicbir zaman haberdar olmaz.
from auth import register_auth_routes
from main_extensions import register_routes

register_auth_routes(app, templates, get_conn)
register_routes(app, templates)

from routers import sources
app.include_router(sources.router)

# Static dosyalar varsa
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def startup():
    init_db()


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def flash(request: Request, message: str, type: str = "success"):
    """Basit flash mesaj — session cookie ile."""
    pass  # Template'de direkt query param kullanacağız


# ── Ana sayfa ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM sources")
            source_count = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM checks WHERE is_active = 1")
            check_count = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM runs")
            run_count = cur.fetchone()["cnt"]
            cur.execute("""
                SELECT r.*, s.name as source_name
                FROM runs r
                LEFT JOIN sources s ON r.source_id = s.id
                ORDER BY r.run_at DESC LIMIT 5
            """)
            recent_runs = cur.fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse("index.html", {
        "request":      request,
        "source_count": source_count,
        "check_count":  check_count,
        "run_count":    run_count,
        "recent_runs":  recent_runs,
    })


# ── Checks ────────────────────────────────────────────────────────────────────

@app.get("/checks", response_class=HTMLResponse)
def checks_list(request: Request, source_id: int = 0, msg: str = ""):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM sources ORDER BY name")
            sources = cur.fetchall()

            if source_id:
                cur.execute("""
                    SELECT c.*, s.name as source_name
                    FROM checks c JOIN sources s ON c.source_id = s.id
                    WHERE c.source_id = %s ORDER BY c.id
                """, (source_id,))
            else:
                cur.execute("""
                    SELECT c.*, s.name as source_name
                    FROM checks c JOIN sources s ON c.source_id = s.id
                    ORDER BY c.source_id, c.id
                """)
            checks = cur.fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse("checks.html", {
        "request":          request,
        "checks":           checks,
        "sources":          sources,
        "selected_source":  source_id,
        "msg":              msg,
    })


@app.get("/checks/new", response_class=HTMLResponse)
def check_new(request: Request, source_id: int = 0):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM sources ORDER BY name")
            sources = cur.fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse("check_form.html", {
        "request": request, "check": None,
        "sources": sources, "selected_source": source_id
    })


@app.post("/checks/new")
def check_create(
    source_id:    int = Form(...),
    name:         str = Form(...),
    query:        str = Form(...),
    assert_type:  str = Form(...),
    assert_value: str = Form(...),
    tags:         str = Form(""),
    column_name:         str = Form(""),   # wizard'dan gelirse dolu, manuel yazimda bos olabilir
    column_type:         str = Form(""),
    library_pattern_id:  str = Form(""),   # bir oneriden geldiyse dolu
):
    from profiler import fingerprint_query, record_rule_usage, record_suggestion_feedback

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO checks (source_id, name, query, assert_type, assert_value, tags)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (source_id, name, query, assert_type, assert_value, tags))
        conn.commit()

        # Rule library'yi besle - bu bir oneriden geldiyse "kabul edildi" olarak isaretle
        rule_type = fingerprint_query(query, assert_type)
        pid = int(library_pattern_id) if library_pattern_id.strip().isdigit() else None

        if column_name:
            record_rule_usage(
                conn, column_name, column_type, rule_type,
                {"assert_type": assert_type, "assert_value": assert_value},
                source_format="wizard_manual" if not pid else "sql",
            )
            if pid:
                record_suggestion_feedback(conn, pid, column_name, rule_type, accepted=True)
    finally:
        conn.close()
    return RedirectResponse("/checks?msg=Kural+eklendi", status_code=303)


@app.post("/api/suggestions/reject")
def reject_suggestion(
    column:             str = Form(...),
    suggestion_type:    str = Form(...),   # wizard'daki 'null'/'duplicate'/'range' vb.
    library_pattern_id: str = Form(""),
):
    """
    Wizard'da bir oneri reddedildiginde cagirilir - kutuphaneye negatif
    sinyal olarak isler, gelecekteki onerilerin guven puanini dusurur.
    """
    from profiler import record_suggestion_feedback, SUGGESTION_TYPE_TO_RULE_TYPE

    rule_type = SUGGESTION_TYPE_TO_RULE_TYPE.get(suggestion_type, suggestion_type)
    pid = int(library_pattern_id) if library_pattern_id.strip().isdigit() else None
    conn = get_conn()
    try:
        record_suggestion_feedback(conn, pid, column, rule_type, accepted=False)
    finally:
        conn.close()
    return {"ok": True}


@app.get("/checks/{check_id}/edit", response_class=HTMLResponse)
def check_edit(request: Request, check_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM checks WHERE id = %s", (check_id,))
            check = cur.fetchone()
            cur.execute("SELECT id, name FROM sources ORDER BY name")
            sources = cur.fetchall()
    finally:
        conn.close()

    if not check:
        raise HTTPException(404)

    return templates.TemplateResponse("check_form.html", {
        "request": request, "check": check,
        "sources": sources, "selected_source": check["source_id"]
    })


@app.post("/checks/{check_id}/edit")
def check_update(
    check_id:     int,
    source_id:    int = Form(...),
    name:         str = Form(...),
    query:        str = Form(...),
    assert_type:  str = Form(...),
    assert_value: str = Form(...),
    tags:         str = Form(""),
    is_active:    int = Form(1),
):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE checks
                SET source_id=%s, name=%s, query=%s,
                    assert_type=%s, assert_value=%s, tags=%s, is_active=%s
                WHERE id=%s
            """, (source_id, name, query, assert_type, assert_value,
                  tags, is_active, check_id))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/checks?msg=Kural+güncellendi", status_code=303)


@app.post("/checks/{check_id}/delete")
def check_delete(check_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM checks WHERE id = %s", (check_id,))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/checks?msg=Kural+silindi", status_code=303)


# ── Profil ───────────────────────────────────────────────────────────────────

@app.get("/api/columns/{source_id}")
def api_get_columns(source_id: int):
    """
    Katman 2: Hızlı kolon listesi.
    Wizard'da kaynak seçilince AJAX ile çağrılır.
    """
    from profiler import get_columns
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM sources WHERE id = %s", (source_id,))
            source = cur.fetchone()
    finally:
        conn.close()

    if not source:
        raise HTTPException(404, "Kaynak bulunamadı")

    import json as _json
    from dq.connectors import build_connector
    config = _json.loads(source["config"])
    config["type"] = source["type"]

    try:
        connector = build_connector(config)
        columns   = get_columns(connector)
        return {"source_id": source_id, "columns": columns}
    except Exception as e:
        return {"source_id": source_id, "columns": [], "error": str(e)}


@app.post("/api/profile/{source_id}")
def api_run_profile(source_id: int):
    """
    Katman 3: Detaylı profil — tüm kolonları tara, DB'ye kaydet.
    """
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from profiler import profile_source, suggest_rules
    import json as _json
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


@app.get("/api/profile/{source_id}")
def api_get_profile(source_id: int):
    """Kaydedilmiş profil sonuçlarını döndürür."""
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

    return {
        "source_id": source_id,
        "columns":   columns,
        "suggestions": suggestions,
    }


# ── Wizard ───────────────────────────────────────────────────────────────────

@app.get("/wizard", response_class=HTMLResponse)
def wizard_page(request: Request, msg: str = ""):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, type FROM sources ORDER BY name")
            sources = cur.fetchall()
    finally:
        conn.close()
    return templates.TemplateResponse("wizard.html", {
        "request": request,
        "sources": sources,
        "msg":     msg,
    })


# ── TOML Import ───────────────────────────────────────────────────────────────

@app.get("/import", response_class=HTMLResponse)
def import_page(request: Request, msg: str = "", error: str = ""):
    return templates.TemplateResponse("import.html", {
        "request": request, "msg": msg, "error": error
    })


@app.post("/import")
async def import_toml(file: UploadFile = File(...)):
    try:
        content = await file.read()
        raw     = parse_toml(content)
        conn    = get_conn()
        try:
            result = toml_to_db(raw, conn)
        finally:
            conn.close()

        return RedirectResponse(
            f"/checks?source_id={result['source_id']}&msg="
            f"TOML+import+edildi:+{result['check_count']}+kural+eklendi",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(f"/import?error={str(e)}", status_code=303)


# ── Run Geçmişi ───────────────────────────────────────────────────────────────

@app.get("/runs", response_class=HTMLResponse)
def runs_list(request: Request):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.*, s.name as source_name
                FROM runs r
                LEFT JOIN sources s ON r.source_id = s.id
                ORDER BY r.run_at DESC
                LIMIT 100
            """)
            runs = cur.fetchall()
    finally:
        conn.close()
    return templates.TemplateResponse("runs.html", {
        "request": request, "runs": runs
    })


@app.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.*, s.name as source_name
                FROM runs r LEFT JOIN sources s ON r.source_id = s.id
                WHERE r.id = %s
            """, (run_id,))
            run = cur.fetchone()
            cur.execute(
                "SELECT * FROM run_results WHERE run_id = %s ORDER BY id",
                (run_id,)
            )
            results = cur.fetchall()
    finally:
        conn.close()

    if not run:
        raise HTTPException(404)

    return templates.TemplateResponse("run_detail.html", {
        "request": request, "run": run, "results": results
    })


# ── API — Airflow buraya POST atar ────────────────────────────────────────────

from pydantic import BaseModel
from typing import List, Any, Dict

class RunPayload(BaseModel):
    source_id: Optional[int] = None
    dag_id:    Optional[str] = None
    task_id:   Optional[str] = None
    results:   List[Dict[str, Any]] = []
    summary:   Dict[str, Any] = {}


@app.post("/api/runs", status_code=201)
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
    return {"run_id": run_id, "status": status}


@app.get("/api/results")
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


@app.get("/odata/Results")
def odata_results(
    top:  int = 500,
    skip: int = 0,
):
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

    return {
        "@odata.context": "/odata/$metadata#Results",
        "value": rows,
    }
