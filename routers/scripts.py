"""routers/scripts.py — /scripts CRUD + custom assertion yönetimi

Güvenlik notu: özel script kodu web sürecinde çalıştırılmaz. Sandbox ayrı süreç/konteyner
olarak tamamlanana kadar (bkz. task.md 🔴) kayıt ve düzenleme yalnızca sözdizimini
`ast.parse` ile kontrol eder; /api/scripts/test 503 döner. Kontrol olarak da bağlı değildir.
"""
from __future__ import annotations

import ast

from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from database import get_conn, release_conn

# Sandbox hazır olana kadar false. True yapılırsa exec yolu yeniden açılır (dq/engine.py custom_script_assertion).
CUSTOM_SCRIPT_CALISTIR = False
CALISTIRMA_DEVRE_DISI_MESAJI = "Özel script çalıştırma devre dışı: sandbox henüz tamamlanmadı (task.md 🔴)."

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _sozdizimi_kontrol(code: str) -> None:
    """Kodu yalnızca ayrıştırır (çalıştırmaz). Hatalıysa ValueError fırlatır."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax hatası: {e}")


@router.get("/scripts", response_class=HTMLResponse)
def scripts_list(request: Request, msg: str = ""):
    """Custom scripts listesi"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description, is_active, created_at, function_name
                FROM custom_scripts ORDER BY id DESC
            """)
            scripts = cur.fetchall()
    finally:
        release_conn(conn)
    
    return templates.TemplateResponse("scripts.html", {
        "request": request,
        "scripts": scripts,
        "msg": msg,
    })


@router.get("/scripts/new", response_class=HTMLResponse)
def script_new(request: Request):
    """Yeni script formu"""
    return templates.TemplateResponse("script_form.html", {
        "request": request,
        "script": None,
    })


@router.post("/scripts/new")
def script_create(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    function_name: str = Form("check"),
    description: str = Form(""),
):
    """Yeni custom script oluştur"""
    # Syntax validation — code parse edilebilir mi? (çalıştırılmaz)
    try:
        _sozdizimi_kontrol(code)
    except ValueError as e:
        # Form sayfasına geri dön, hata mesajı ile
        return templates.TemplateResponse("script_form.html", {
            "request": request,
            "script": None,
            "error": str(e),
        }, status_code=400)
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO custom_scripts (name, code, function_name, description)
                VALUES (%s, %s, %s, %s)
            """, (name, code, function_name, description))
        conn.commit()
    except Exception as e:
        release_conn(conn)
        raise HTTPException(400, f"Hata: {e}")
    finally:
        release_conn(conn)
    
    return RedirectResponse("/scripts?msg=Script+eklendi", status_code=303)


@router.get("/scripts/{script_id}/edit", response_class=HTMLResponse)
def script_edit(request: Request, script_id: int):
    """Script düzenleme formu"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM custom_scripts WHERE id = %s", (script_id,))
            script = cur.fetchone()
    finally:
        release_conn(conn)
    
    if not script:
        raise HTTPException(404)
    
    return templates.TemplateResponse("script_form.html", {
        "request": request,
        "script": script,
    })


@router.post("/scripts/{script_id}/edit")
def script_update(
    script_id: int,
    name: str = Form(...),
    code: str = Form(...),
    function_name: str = Form("check"),
    description: str = Form(""),
    is_active: int = Form(1),
):
    """Script güncelle"""
    try:
        _sozdizimi_kontrol(code)
    except ValueError as e:
        raise HTTPException(400, f"Kod hatası: {e}")
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE custom_scripts
                SET name=%s, code=%s, function_name=%s, description=%s, is_active=%s
                WHERE id=%s
            """, (name, code, function_name, description, is_active, script_id))
        conn.commit()
    finally:
        release_conn(conn)
    
    return RedirectResponse("/scripts?msg=Script+güncellendi", status_code=303)


@router.post("/scripts/{script_id}/delete")
def script_delete(script_id: int):
    """Script sil"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM custom_scripts WHERE id = %s", (script_id,))
        conn.commit()
    finally:
        release_conn(conn)
    
    return RedirectResponse("/scripts?msg=Script+silindi", status_code=303)


@router.post("/api/scripts/test")
async def script_test(
    code: str = Form(...),
    function_name: str = Form("check"),
    test_value: str = Form(""),
):
    """Script'i test değeriyle çalıştır (dry-run). Şu an devre dışı: kod çalıştırılmaz."""
    if not CUSTOM_SCRIPT_CALISTIR:
        return JSONResponse({
            "ok": False,
            "error": CALISTIRMA_DEVRE_DISI_MESAJI
        }, status_code=503)

    from dq.engine import custom_script_assertion  # bayrak açıldığında yüklenir

    try:
        assertion_fn = custom_script_assertion(code, function_name)

        # Test değerini convert et
        try:
            test_val = float(test_value) if test_value else None
        except ValueError:
            test_val = test_value if test_value else None

        result = assertion_fn(test_val)
        return JSONResponse({
            "ok": True,
            "result": result,
            "value": test_val,
            "message": f"Test geçti: {result}"
        })
    except ValueError as e:
        return JSONResponse({
            "ok": False,
            "error": str(e)
        }, status_code=400)
