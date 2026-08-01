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

from routers import sources, checks, api
app.include_router(sources.router)
app.include_router(checks.router)
app.include_router(api.router)

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


