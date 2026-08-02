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

from routers import sources, checks, api, ui
app.include_router(sources.router)
app.include_router(checks.router)
app.include_router(api.router)
app.include_router(ui.router)

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

