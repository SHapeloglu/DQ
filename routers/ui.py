"""routers/ui.py — /wizard, /import, /runs UI route'ları"""
from __future__ import annotations

from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import get_conn
from toml_import import parse_toml, toml_to_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ── Wizard ───────────────────────────────────────────────────────────────────

@router.get("/wizard", response_class=HTMLResponse)
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

@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request, msg: str = "", error: str = ""):
    return templates.TemplateResponse("import.html", {
        "request": request, "msg": msg, "error": error
    })


@router.post("/import")
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

@router.get("/runs", response_class=HTMLResponse)
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


@router.get("/runs/{run_id}", response_class=HTMLResponse)
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


# ── Ana sayfa ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
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
    from dq.scoring import get_all_scores
    scores = get_all_scores()
    return templates.TemplateResponse("index.html", {
        "request":      request,
        "source_count": source_count,
        "check_count":  check_count,
        "run_count":    run_count,
        "recent_runs":  recent_runs,
        "scores":       scores,
    })


# ── Sağlık Skoru Dashboard ────────────────────────────────────────────────────

@router.get("/health", response_class=HTMLResponse)
def health_dashboard(request: Request):
    from dq.scoring import get_all_scores
    scores = get_all_scores()
    return templates.TemplateResponse("health.html", {
        "request": request,
        "scores":  scores,
    })


# ── Rule Library ─────────────────────────────────────────────────────────────

@router.get("/rule-library", response_class=HTMLResponse)
def rule_library_page(request: Request, msg: str = ""):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, column_name_pattern, column_type, rule_type,
                       rule_definition, times_used, times_accepted, times_rejected,
                       last_used_at, created_at
                FROM rule_library
                ORDER BY times_used DESC, created_at DESC
            """)
            rules = cur.fetchall()
    finally:
        conn.close()
    return templates.TemplateResponse("rule_library.html", {
        "request": request,
        "rules":   rules,
        "msg":     msg,
    })
