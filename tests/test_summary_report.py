# Bu dosya: dq/extensions.py içindeki e-posta özet raporunun (send_summary_report) testlerini içerir. SMTP sunucusu patch ile taklit edilir; gerçek e-posta gönderilmez.
# patch: test süresince bir nesneyi sahte olanla değiştirir, test bitince eski haline döndürür.
# MagicMock: her çağrıyı kaydeden esnek sahte nesne. Testler pytest ile çalışır.
from unittest.mock import MagicMock, patch
from extensions import AlertManager


def make_alert(**kwargs):
    """
    Test için AlertManager (e-posta uyarı yöneticisi) oluşturur. Varsayılan SMTP bilgileri sahte değerlerdir; gerçek bir sunucuya bağlanılmaz (smtplib.SMTP ayrıca patch ile taklit edilir).
    kwargs ile belirli bir ayar değiştirilebilir (örn. email_to=None).
    """
    defaults = dict(
        email_to="test@example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="sender@example.com",
        smtp_pass="pass",
    )
    defaults.update(kwargs)
    return AlertManager(**defaults)


RESULTS = [
    {"check_name": "row_count", "passed": True,  "value_actual": 100, "expected": 100},
    {"check_name": "null_check", "passed": False, "value_actual": 5,   "expected": 0},
    {"check_name": "fresh",      "passed": True,  "value_actual": 1,   "expected": 1},
]


class TestSendSummaryReport:
    """send_summary_report (günlük/haftalık özet e-postası) fonksiyonunun testleri. SMTP sunucusu taklit edildiği için gerçek e-posta gitmez."""
    def test_returns_true_on_success(self):
        """E-posta gönderimi başarılıysa fonksiyon True döner."""
        alert = make_alert()
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_smtp.return_value
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = alert.send_summary_report(RESULTS, period="günlük", source_name="orders")
        assert result is True

    def test_returns_false_without_email(self):
        """Alıcı adresi (email_to) yoksa e-posta gönderilmeden False döner."""
        alert = make_alert(email_to=None)
        result = alert.send_summary_report(RESULTS)
        assert result is False

    def test_returns_false_without_smtp_user(self):
        """SMTP kullanıcısı yoksa gönderim yapılmadan False döner."""
        alert = make_alert(smtp_user=None)
        result = alert.send_summary_report(RESULTS)
        assert result is False

    def test_subject_contains_source_name(self):
        """DİKKAT: Bu test konu satırında kaynak adının olduğunu DOĞRULAMAZ; sadece True döndüğünü kontrol eder. Yorum 'body'de geçiyor diyor ama assert bunu sınamıyor. (TODO(kontrol))"""
        alert = make_alert()
        with patch("smtplib.SMTP") as mock_smtp:
            inst = mock_smtp.return_value.__enter__.return_value = MagicMock()
            result = alert.send_summary_report(RESULTS, source_name="siparis")
        assert result is True  # kaynak adı email body HTML'inde geçiyor

    def test_subject_contains_period(self):
        """DİKKAT: Bu test de periyodun (haftalık) konuda olduğunu doğrulamaz; sadece True döndüğünü kontrol eder. (TODO(kontrol))"""
        alert = make_alert()
        subjects = []
        original_init = __import__("email.mime.multipart", fromlist=["MIMEMultipart"]).MIMEMultipart
        with patch("smtplib.SMTP") as mock_smtp:
            with patch("extensions.MIMEMultipart", wraps=original_init) as mock_mime:
                mock_mime.return_value = original_init("alternative")
                inst = mock_smtp.return_value.__enter__.return_value = MagicMock()
                result = alert.send_summary_report(RESULTS, period="haftalık")
        assert result is True

    def test_empty_results(self):
        """Hiç sonuç yokken de e-posta gönderilebilmeli ve True dönmeli (boş rapor da hata değildir)."""
        alert = make_alert()
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_smtp.return_value
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = alert.send_summary_report([], period="günlük")
        assert result is True

    def test_smtp_error_returns_false(self):
        """SMTP bağlantısı hata verirse (Exception) fonksiyon çökmez ve False döner. Uyarı sistemi, mail sunucusu düştüğünde DQ işini durdurmamalı."""
        alert = make_alert()
        with patch("smtplib.SMTP", side_effect=Exception("bağlantı hatası")):
            result = alert.send_summary_report(RESULTS)
        assert result is False

    def test_all_passed(self):
        """Tüm kontroller başarılıysa (5 adet) da rapor gönderilip True dönmeli."""
        alert = make_alert()
        all_pass = [{"check_name": f"c{i}", "passed": True, "value_actual": i, "expected": i} for i in range(5)]
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_smtp.return_value
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = alert.send_summary_report(all_pass)
        assert result is True
