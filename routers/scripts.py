"""routers/scripts.py — /scripts CRUD + custom assertion yönetimi"""
from __future__ import annotations

from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from database import get_conn, release_conn
from dq.engine import custom_script_assertion

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/scripts", response_class=HTMLResponse)
def scripts_list(request: Request, msg: str = ""):
    """Custom scripts listesi"""
    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
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
    name: str = Form(...),
    code: str = Form(...),
    function_name: str = Form("check"),
    description: str = Form(""),
):
    """Yeni custom script oluştur"""
    # Syntax validation — code parse edilebilir mi?
    try:
        custom_script_assertion(code, function_name)
    except ValueError as e:
        # Form sayfasına geri dön, hata mesajı ile
        return templates.TemplateResponse("script_form.html", {
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
        with conn.cursor(dictionary=True) as cur:
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
        custom_script_assertion(code, function_name)
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
    """Script'i test değeriyle çalıştır (dry-run)"""
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
