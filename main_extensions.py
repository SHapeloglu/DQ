"""
main_extensions.py — main.py'ye eklenecek route'lar.

Bu fonksiyonları main.py'deki app'e ekle:

    from main_extensions import register_routes
    register_routes(app)

Veya fonksiyonları main.py'ye direkt yapıştır.
"""

from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import get_conn
from extensions import checks_to_toml, AlertManager, run_migration, load_alert_manager


def register_routes(app: FastAPI, templates: Jinja2Templates):

    # ── Dashboard ─────────────────────────────────────────────────────────────

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard(request: Request):
        conn = get_conn()
        try:
            with conn.cursor() as cur:

                # Genel istatistikler
                cur.execute("SELECT COUNT(*) as cnt FROM runs")
                total_runs = cur.fetchone()["cnt"]

                cur.execute("""
                    SELECT
                        SUM(passed) as total_passed,
                        SUM(total)  as grand_total
                    FROM runs
                """)
                row = cur.fetchone()
                tp  = row["total_passed"] or 0
                gt  = row["grand_total"]  or 1
                success_rate = round(tp * 100 / gt)

                cur.execute("""
                    SELECT SUM(total) as cnt FROM runs
                    WHERE DATE(run_at) = CURDATE()
                """)
                today_checks = cur.fetchone()["cnt"] or 0

                cur.execute("""
                    SELECT SUM(failed) as cnt FROM runs
                    WHERE DATE(run_at) = CURDATE()
                """)
                failed_checks = cur.fetchone()["cnt"] or 0

                # Son 14 gün trend
                cur.execute("""
                    SELECT
                        DATE(run_at)    as date,
                        SUM(passed)     as passed,
                        SUM(failed)     as failed
                    FROM runs
                    WHERE run_at >= NOW() - INTERVAL 14 DAY
                    GROUP BY DATE(run_at)
                    ORDER BY date ASC
                """)
                trend_rows = cur.fetchall()
                trend_data = [
                    {
                        "date":   str(r["date"]),
                        "passed": int(r["passed"] or 0),
                        "failed": int(r["failed"] or 0),
                    }
                    for r in trend_rows
                ]

                # Kaynak bazlı başarı oranı
                cur.execute("""
                    SELECT
                        s.name as source_name,
                        ROUND(SUM(r.passed)*100/NULLIF(SUM(r.total),0)) as success_rate
                    FROM runs r
                    LEFT JOIN sources s ON r.source_id = s.id
                    GROUP BY s.id, s.name
                    ORDER BY success_rate ASC
                """)
                source_data = [
                    {
                        "source_name":  row["source_name"] or "Bilinmeyen",
                        "success_rate": int(row["success_rate"] or 0),
                    }
                    for row in cur.fetchall()
                ]

                # En çok başarısız olan kurallar
                cur.execute("""
                    SELECT
                        check_name,
                        COUNT(*) as total_count,
                        SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) as fail_count
                    FROM run_results
                    GROUP BY check_name
                    HAVING fail_count > 0
                    ORDER BY fail_count DESC
                    LIMIT 10
                """)
                failures = []
                for row in cur.fetchall():
                    total = row["total_count"] or 1
                    fail  = row["fail_count"]  or 0
                    failures.append({
                        "check_name":  row["check_name"],
                        "fail_count":  fail,
                        "total_count": total,
                        "fail_pct":    round(fail * 100 / total),
                        "trend":       "stable",
                    })

        finally:
            conn.close()

        return templates.TemplateResponse("dashboard.html", {
            "request":      request,
            "stats": {
                "total_runs":    total_runs,
                "success_rate":  success_rate,
                "today_checks":  today_checks,
                "failed_checks": failed_checks,
            },
            "trend_data":   trend_data,
            "source_data":  source_data,
            "top_failures": failures,
        })


    # ── TOML Export ───────────────────────────────────────────────────────────

    @app.get("/export/toml/{source_id}")
    def export_toml(source_id: int):
        """DB'deki kuralları TOML olarak indir."""
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sources WHERE id = %s", (source_id,))
                source = cur.fetchone()
                if not source:
                    raise HTTPException(404, "Kaynak bulunamadı")

                cur.execute(
                    "SELECT * FROM checks WHERE source_id = %s AND is_active = 1 ORDER BY id",
                    (source_id,)
                )
                checks = cur.fetchall()
        finally:
            conn.close()

        toml_content = checks_to_toml(source, checks)
        filename     = f"dq_{source['name'].replace(' ', '_')}.toml"

        return PlainTextResponse(
            content=toml_content,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type":        "application/toml",
            }
        )


    # ── active_flag + test_flag ───────────────────────────────────────────────

    @app.post("/checks/{check_id}/toggle-active")
    def toggle_active(check_id: int, reason: str = Form("")):
        """Kuralı aktif/pasif yap."""
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT is_active FROM checks WHERE id = %s", (check_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404)

                new_state = 0 if row["is_active"] else 1
                cur.execute(
                    "UPDATE checks SET is_active = %s, non_active_description = %s WHERE id = %s",
                    (new_state, reason if not new_state else None, check_id)
                )
            conn.commit()
        finally:
            conn.close()

        return RedirectResponse("/checks?msg=Kural+durumu+güncellendi", status_code=303)


    @app.post("/checks/{check_id}/toggle-test")
    def toggle_test(check_id: int):
        """Kuralı test moduna al/çıkar."""
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT test_flag FROM checks WHERE id = %s", (check_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404)
                new_flag = 0 if (row.get("test_flag") or 0) else 1
                cur.execute(
                    "UPDATE checks SET test_flag = %s WHERE id = %s",
                    (new_flag, check_id)
                )
            conn.commit()
        finally:
            conn.close()

        return RedirectResponse("/checks?msg=Test+modu+güncellendi", status_code=303)


    # ── Uyarı Ayarları ────────────────────────────────────────────────────────

    @app.get("/settings/alerts", response_class=HTMLResponse)
    def alerts_page(request: Request, msg: str = "", error: str = ""):
        """Uyarı ayarları sayfası."""
        conn = get_conn()
        try:
            _ensure_alert_table(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM alert_settings LIMIT 1")
                settings = cur.fetchone() or {}
        finally:
            conn.close()

        return templates.TemplateResponse("alerts.html", {
            "request":  request,
            "settings": settings,
            "msg":      msg,
            "error":    error,
        })


    @app.post("/settings/alerts")
    def alerts_save(
        slack_webhook:  str = Form(""),
        webhook_url:    str = Form(""),
        email_to:       str = Form(""),
        smtp_host:      str = Form("smtp.gmail.com"),
        smtp_port:      int = Form(587),
        smtp_user:      str = Form(""),
        smtp_pass:      str = Form(""),
        alert_trigger:  str = Form("any_failure"),
    ):
        conn = get_conn()
        try:
            _ensure_alert_table(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM alert_settings LIMIT 1")
                existing = cur.fetchone()

                if existing:
                    cur.execute("""
                        UPDATE alert_settings SET
                            slack_webhook=%s, webhook_url=%s, email_to=%s,
                            smtp_host=%s, smtp_port=%s, smtp_user=%s,
                            smtp_pass=%s, alert_trigger=%s
                        WHERE id=%s
                    """, (slack_webhook, webhook_url, email_to, smtp_host,
                          smtp_port, smtp_user, smtp_pass or None,
                          alert_trigger, existing["id"]))
                else:
                    cur.execute("""
                        INSERT INTO alert_settings
                            (slack_webhook, webhook_url, email_to, smtp_host,
                             smtp_port, smtp_user, smtp_pass, alert_trigger)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (slack_webhook, webhook_url, email_to, smtp_host,
                          smtp_port, smtp_user, smtp_pass or None, alert_trigger))
            conn.commit()
        finally:
            conn.close()

        return RedirectResponse("/settings/alerts?msg=Ayarlar+kaydedildi", status_code=303)


    @app.post("/settings/alerts/test")
    def alerts_test():
        """Test uyarısı gönder."""
        conn = get_conn()
        try:
            alert = load_alert_manager(conn)
        finally:
            conn.close()

        if not alert:
            return {"message": "Önce uyarı ayarlarını kaydet"}

        fake_results = [{"check_name": "Test check", "passed": False,
                         "value_actual": "0", "expected": "greater_than(0)"}]
        status = alert.send(fake_results, run_id=0,
                            source_name="Test", only_failures=False)

        sent = [k for k, v in status.items() if v]
        if sent:
            return {"message": f"Test gönderildi: {', '.join(sent)}"}
        return {"message": "Hiçbir kanal yapılandırılmamış"}


    # ── Migration ─────────────────────────────────────────────────────────────

    @app.post("/admin/migrate")
    def admin_migrate():
        """test_flag ve non_active_description kolonlarını ekle."""
        conn = get_conn()
        try:
            ok = run_migration(conn)
        finally:
            conn.close()
        return {"success": ok}


def _ensure_alert_table(conn):
    """alert_settings tablosunu oluşturur (yoksa)."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_settings (
                id              INT AUTO_INCREMENT PRIMARY KEY,
                slack_webhook   VARCHAR(500),
                webhook_url     VARCHAR(500),
                email_to        VARCHAR(200),
                smtp_host       VARCHAR(100) DEFAULT 'smtp.gmail.com',
                smtp_port       INT DEFAULT 587,
                smtp_user       VARCHAR(200),
                smtp_pass       VARCHAR(200),
                alert_trigger   VARCHAR(50) DEFAULT 'any_failure',
                updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
