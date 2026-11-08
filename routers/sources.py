"""routers/sources.py — /sources CRUD route'ları"""
from __future__ import annotations
import json

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import get_conn, release_conn

router = APIRouter()
# Şablon klasörü göreli bir yol olarak verilmiş; uygulama proje kök klasöründen başlatılmalıdır.
templates = Jinja2Templates(directory="templates")


@router.get("/sources", response_class=HTMLResponse)
def sources_list(request: Request, msg: str = ""):
    """Kaynakların listesini HTML sayfası olarak gösterir. Her kaynak için aktif kontrol sayısı da hesaplanır. `msg` varsa sayfada bilgi mesajı olarak görünür."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.*, COUNT(c.id) as check_count
                FROM sources s
                LEFT JOIN checks c ON s.id = c.source_id AND c.is_active = 1
                GROUP BY s.id
                ORDER BY s.created_at DESC
            """)
            sources = cur.fetchall()
    finally:
        release_conn(conn)
    return templates.TemplateResponse("sources.html", {
        "request": request, "sources": sources, "msg": msg
    })


@router.get("/sources/new", response_class=HTMLResponse)
def source_new(request: Request):
    """Yeni kaynak ekleme formunu gösterir (boş form)."""
    return templates.TemplateResponse("source_form.html", {
        "request": request, "source": None
    })


@router.post("/sources/new")
def source_create(
    name:     str = Form(...),
    type:     str = Form(...),
    path:     str = Form(""),
    host:     str = Form(""),
    port:     str = Form(""),
    database: str = Form(""),
    user:     str = Form(""),
    password: str = Form(""),
):
    """
    Yeni kaynağı kaydeder. Tür `csv` ise yalnız dosya yolu, değilse sunucu/veritabanı bilgileri saklanır. Bilgiler JSON metin olarak `config` alanına yazılır.
    Başarılıysa kaynak listesine yönlendirilir.
    """
    config = {}
    if type == "csv":
        config["path"] = path
    else:
        # DİKKAT: Şifre dahil bağlantı bilgileri veritabanına düz metin JSON olarak yazılır.
        config = {"host": host, "port": port, "database": database,
                  "user": user, "password": password}

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sources (name, type, config) VALUES (%s, %s, %s)",
                (name, type, json.dumps(config))
            )
        conn.commit()
    finally:
        release_conn(conn)

    return RedirectResponse("/sources?msg=Source+eklendi", status_code=303)


@router.get("/sources/{source_id}/edit", response_class=HTMLResponse)
def source_edit(request: Request, source_id: int):
    """Kaynak düzenleme formunu gösterir. `config` JSON'dan sözlüğe çevrilip forma konur. Kaynak yoksa 404 döner."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM sources WHERE id = %s", (source_id,))
            source = cur.fetchone()
    finally:
        release_conn(conn)

    if not source:
        raise HTTPException(404)

    # DİKKAT: Bu sözlük şablona gönderilir; şifre de form alanında görünebilir.
    source["config"] = json.loads(source["config"])
    return templates.TemplateResponse("source_form.html", {
        "request": request, "source": source
    })


@router.post("/sources/{source_id}/edit")
def source_update(
    source_id: int,
    name:     str = Form(...),
    type:     str = Form(...),
    path:     str = Form(""),
    host:     str = Form(""),
    port:     str = Form(""),
    database: str = Form(""),
    user:     str = Form(""),
    password: str = Form(""),
):
    """
    Mevcut kaynağın adını, türünü ve bağlantı bilgilerini günceller. Tüm `config` her zaman baştan yazılır.
    İşlem sonunda kaynak listesine yönlendirilir.
    """
    config = {}
    if type == "csv":
        config["path"] = path
    else:
        # DİKKAT: Şifre dahil bağlantı bilgileri veritabanına düz metin JSON olarak yazılır.
        config = {"host": host, "port": port, "database": database,
                  "user": user, "password": password}

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                # DİKKAT: Düzenleme formunda şifre alanı boş gönderilirse, mevcut şifre korunmaz; boş değer yazılır.
                "UPDATE sources SET name=%s, type=%s, config=%s WHERE id=%s",
                (name, type, json.dumps(config), source_id)
            )
        conn.commit()
    finally:
        release_conn(conn)

    return RedirectResponse("/sources?msg=Source+güncellendi", status_code=303)


@router.post("/sources/{source_id}/delete")
def source_delete(source_id: int):
    """Kaynağı siler ve listeye yönlendirir. Silme geri alınamaz."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sources WHERE id = %s", (source_id,))
        conn.commit()
    finally:
        release_conn(conn)
    return RedirectResponse("/sources?msg=Source+silindi", status_code=303)
