"""
extensions.py — DQ web uygulaması eklentileri.

Bu dosyadaki fonksiyonları main.py'ye ekle:

1. TOML export     → /export/toml/{source_id}
2. active_flag     → checks tablosuna eklendi
3. test_flag       → kural test modunda çalışır, DB'ye yazmaz
4. Uyarı sistemi   → Slack, e-posta, webhook
"""

from __future__ import annotations
import json
import smtplib
import urllib.request
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ── 1. TOML Export ───────────────────────────────────────────────────────────

def checks_to_toml(source: dict, checks: list[dict]) -> str:
    """DB'deki source ve check'leri TOML formatına çevirir."""
    config = json.loads(source["config"]) if isinstance(source["config"], str) else source["config"]

    lines = [
        f"# DQ Export — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"# Kaynak: {source['name']}",
        "",
        "[source]",
        f'type = "{source["type"]}"',
    ]

    for k, v in config.items():
        if isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        else:
            lines.append(f"{k} = {v}")

    lines.append("")

    for c in checks:
        lines.append("[[checks]]")
        lines.append(f'name   = "{c["name"]}"')
        lines.append(f'query  = "{c["query"]}"')
        lines.append(f'assert = "{c["assert_type"]}"')

        val = c["assert_value"]
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                lines.append(f"value  = {val}")
            else:
                lines.append(f"value  = {val}")
        except Exception:
            try:
                lines.append(f"value  = {float(val)}")
            except Exception:
                lines.append(f'value  = "{val}"')

        if c.get("tags"):
            tags = [f'"{t.strip()}"' for t in c["tags"].split(",") if t.strip()]
            lines.append(f"tags   = [{', '.join(tags)}]")

        lines.append("")

    return "\n".join(lines)


# ── 2. active_flag + test_flag SQL migrasyonu ─────────────────────────────────

MIGRATION_SQL = """
-- active_flag: kural aktif mi? (1=aktif, 0=pasif)
-- test_flag: test modunda çalış, DB'ye sonuç yazma (1=test, 0=normal)
-- non_active_description: neden pasif? açıklama

ALTER TABLE checks
    ADD COLUMN IF NOT EXISTS test_flag TINYINT(1) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS non_active_description VARCHAR(500) NULL;
"""


def run_migration(conn) -> bool:
    """Eksik kolonları ekler — idempotent, güvenle tekrar çalıştırılabilir."""
    try:
        with conn.cursor() as cur:
            # MySQL'de IF NOT EXISTS yoksa ayrı kontrol yap
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                AND table_name = 'checks'
                AND column_name = 'test_flag'
            """)
            row = cur.fetchone()
            if (row.get("cnt") or 0) == 0:
                cur.execute("ALTER TABLE checks ADD COLUMN test_flag TINYINT(1) DEFAULT 0")

            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                AND table_name = 'checks'
                AND column_name = 'non_active_description'
            """)
            row = cur.fetchone()
            if (row.get("cnt") or 0) == 0:
                cur.execute(
                    "ALTER TABLE checks ADD COLUMN non_active_description VARCHAR(500) NULL"
                )

        conn.commit()
        return True
    except Exception as e:
        print(f"Migration hatası: {e}")
        return False


# ── 3. Uyarı sistemi ──────────────────────────────────────────────────────────

class AlertManager:
    """
    Başarısız check'leri Slack, e-posta veya webhook'a gönderir.

    Kullanım:
        alert = AlertManager(
            slack_webhook="https://hooks.slack.com/...",
            email_to="team@company.com",
            smtp_host="smtp.gmail.com",
            smtp_user="sender@gmail.com",
            smtp_pass="app_password",
        )
        alert.send(results, run_id=1, source_name="orders")
    """

    def __init__(
        self,
        slack_webhook:  str | None = None,
        webhook_url:    str | None = None,
        email_to:       str | None = None,
        smtp_host:      str = "smtp.gmail.com",
        smtp_port:      int = 587,
        smtp_user:      str | None = None,
        smtp_pass:      str | None = None,
    ):
        self.slack_webhook = slack_webhook
        self.webhook_url   = webhook_url
        self.email_to      = email_to
        self.smtp_host     = smtp_host
        self.smtp_port     = smtp_port
        self.smtp_user     = smtp_user
        self.smtp_pass     = smtp_pass

    def send(self, results: list, run_id: int = 0,
             source_name: str = "", only_failures: bool = True) -> dict:
        """
        Sonuçları yapılandırılmış kanallara gönderir.

        Returns:
            {"slack": bool, "email": bool, "webhook": bool}
        """
        failed = [r for r in results if not r.get("passed", True)]

        if only_failures and not failed:
            return {"slack": False, "email": False, "webhook": False,
                    "reason": "Başarısız check yok"}

        summary = self._build_summary(failed or results, run_id, source_name)
        status  = {}

        if self.slack_webhook:
            status["slack"] = self._send_slack(summary, failed)

        if self.webhook_url:
            status["webhook"] = self._send_webhook(summary, results, failed)

        if self.email_to and self.smtp_user:
            status["email"] = self._send_email(summary, failed)

        return status

    def _build_summary(self, failed: list, run_id: int,
                       source_name: str) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"DQ Uyarı — Run #{run_id}",
            f"Kaynak: {source_name}",
            f"Zaman: {now}",
            f"Başarısız: {len(failed)} check",
            "",
        ]
        for r in failed:
            name = r.get("check_name") or r.get("name", "?")
            val  = r.get("value_actual") or r.get("value", "?")
            exp  = r.get("expected", "?")
            lines.append(f"  ✗ {name}")
            lines.append(f"    Değer: {val} | Beklenen: {exp}")
        return "\n".join(lines)

    def _send_slack(self, summary: str, failed: list) -> bool:
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text",
                             "text": f"⚠️ DQ Uyarı — {len(failed)} check başarısız"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"```{summary}```"}
                }
            ]
            payload = json.dumps({"blocks": blocks}).encode()
            req = urllib.request.Request(
                self.slack_webhook, data=payload,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
            return True
        except Exception as e:
            print(f"Slack uyarı hatası: {e}")
            return False

    def _send_webhook(self, summary: str, all_results: list,
                      failed: list) -> bool:
        try:
            payload = json.dumps({
                "event":   "dq_failure",
                "summary": summary,
                "failed":  len(failed),
                "total":   len(all_results),
                "results": failed,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }).encode()
            req = urllib.request.Request(
                self.webhook_url, data=payload,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
            return True
        except Exception as e:
            print(f"Webhook hatası: {e}")
            return False

    def _send_email(self, summary: str, failed: list) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"⚠️ DQ Uyarı — {len(failed)} check başarısız"
            msg["From"]    = self.smtp_user
            msg["To"]      = self.email_to

            text_part = MIMEText(summary, "plain", "utf-8")

            html_body = f"""
<html><body style="font-family:sans-serif;max-width:600px;margin:auto">
<h2 style="color:#dc2626">⚠️ DQ Uyarı</h2>
<pre style="background:#f9fafb;padding:16px;border-radius:8px;font-size:13px">{summary}</pre>
<p style="color:#6b7280;font-size:12px">DQ — Veri Kalitesi Platformu</p>
</body></html>"""
            html_part = MIMEText(html_body, "html", "utf-8")

            msg.attach(text_part)
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, self.email_to, msg.as_string())
            return True
        except Exception as e:
            print(f"E-posta hatası: {e}")
            return False


    def send_summary_report(
        self,
        results: list,
        period: str = "günlük",
        source_name: str = "",
    ) -> bool:
        """
        Tüm check sonuçlarının özet email raporunu gönderir.
        period: 'günlük' | 'haftalık'
        results: [{"check_name": ..., "passed": ..., "value_actual": ..., "expected": ...}]
        """
        if not self.email_to or not self.smtp_user:
            return False
        total   = len(results)
        passed  = sum(1 for r in results if r.get("passed", False))
        failed  = total - passed
        pct     = round(passed / total * 100, 1) if total else 0
        now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        subject = f"DQ {period.capitalize()} Özet — {source_name or 'Tüm Kaynaklar'} ({pct}% başarı)"
        rows_html = ""
        for r in results:
            name  = r.get("check_name") or r.get("name", "?")
            val   = r.get("value_actual") or r.get("value", "?")
            exp   = r.get("expected", "?")
            ok    = r.get("passed", False)
            color = "#16a34a" if ok else "#dc2626"
            icon  = "✓" if ok else "✗"
            rows_html += (
                f'<tr><td style="padding:4px 8px;color:{color}">{icon}</td>'
                f'<td style="padding:4px 8px">{name}</td>'
                f'<td style="padding:4px 8px">{val}</td>'
                f'<td style="padding:4px 8px">{exp}</td></tr>'
            )
        html_body = f"""
<html><body style="font-family:sans-serif;max-width:700px;margin:auto">
<h2>DQ {period.capitalize()} Özet Raporu</h2>
<p>Kaynak: <b>{source_name or "Tüm"}</b> &nbsp;|&nbsp; Zaman: {now}</p>
<p>Toplam: {total} &nbsp;|&nbsp;
   <span style="color:#16a34a">Geçti: {passed}</span> &nbsp;|&nbsp;
   <span style="color:#dc2626">Başarısız: {failed}</span> &nbsp;|&nbsp;
   Başarı: <b>{pct}%</b></p>
<table border="0" cellspacing="0" style="border-collapse:collapse;width:100%">
<thead><tr style="background:#f3f4f6">
  <th style="padding:6px 8px;text-align:left">Durum</th>
  <th style="padding:6px 8px;text-align:left">Check</th>
  <th style="padding:6px 8px;text-align:left">Değer</th>
  <th style="padding:6px 8px;text-align:left">Beklenen</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
<p style="color:#6b7280;font-size:12px;margin-top:24px">DQ — Veri Kalitesi Platformu</p>
</body></html>"""
        text_body = f"DQ {period} özet\nKaynak: {source_name}\nGeçti: {passed}/{total} ({pct}%)"
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = self.smtp_user
            msg["To"]      = self.email_to
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, self.email_to, msg.as_string())
            return True
        except Exception as e:
            print(f"Özet rapor hatası: {e}")
            return False

# ── AlertManager'ı DB ayarlarından yükle ─────────────────────────────────────

def load_alert_manager(conn) -> AlertManager | None:
    """
    alert_settings tablosundan uyarı ayarlarını yükler.
    Tablo yoksa None döner.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM alert_settings LIMIT 1")
            row = cur.fetchone()
        if not row:
            return None
        return AlertManager(
            slack_webhook = row.get("slack_webhook"),
            webhook_url   = row.get("webhook_url"),
            email_to      = row.get("email_to"),
            smtp_host     = row.get("smtp_host", "smtp.gmail.com"),
            smtp_port     = int(row.get("smtp_port", 587)),
            smtp_user     = row.get("smtp_user"),
            smtp_pass     = row.get("smtp_pass"),
        )
    except Exception:
        return None
