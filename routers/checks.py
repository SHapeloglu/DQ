"""routers/checks.py — /checks CRUD + suggestions route'ları"""
from __future__ import annotations

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import get_conn

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/checks", response_class=HTMLResponse)
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
        "request":         request,
        "checks":          checks,
        "sources":         sources,
        "selected_source": source_id,
        "msg":             msg,
    })


@router.get("/checks/new", response_class=HTMLResponse)
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


@router.post("/checks/new")
def check_create(
    source_id:           int = Form(...),
    name:                str = Form(...),
    query:               str = Form(...),
    assert_type:         str = Form(...),
    assert_value:        str = Form(...),
    tags:                str = Form(""),
    column_name:         str = Form(""),
    column_type:         str = Form(""),
    library_pattern_id:  str = Form(""),
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


@router.post("/api/suggestions/reject")
def reject_suggestion(
    column:             str = Form(...),
    suggestion_type:    str = Form(...),
    library_pattern_id: str = Form(""),
):
    from profiler import record_suggestion_feedback, SUGGESTION_TYPE_TO_RULE_TYPE

    rule_type = SUGGESTION_TYPE_TO_RULE_TYPE.get(suggestion_type, suggestion_type)
    pid = int(library_pattern_id) if library_pattern_id.strip().isdigit() else None
    conn = get_conn()
    try:
        record_suggestion_feedback(conn, pid, column, rule_type, accepted=False)
    finally:
        conn.close()
    return {"ok": True}


@router.get("/checks/{check_id}/edit", response_class=HTMLResponse)
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


@router.post("/checks/{check_id}/edit")
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


@router.post("/checks/{check_id}/delete")
def check_delete(check_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM checks WHERE id = %s", (check_id,))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/checks?msg=Kural+silindi", status_code=303)
