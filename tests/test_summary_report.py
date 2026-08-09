from unittest.mock import MagicMock, patch
from extensions import AlertManager


def make_alert(**kwargs):
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
    def test_returns_true_on_success(self):
        alert = make_alert()
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_smtp.return_value
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = alert.send_summary_report(RESULTS, period="günlük", source_name="orders")
        assert result is True

    def test_returns_false_without_email(self):
        alert = make_alert(email_to=None)
        result = alert.send_summary_report(RESULTS)
        assert result is False

    def test_returns_false_without_smtp_user(self):
        alert = make_alert(smtp_user=None)
        result = alert.send_summary_report(RESULTS)
        assert result is False

    def test_subject_contains_source_name(self):
        alert = make_alert()
        with patch("smtplib.SMTP") as mock_smtp:
            inst = mock_smtp.return_value.__enter__.return_value = MagicMock()
            result = alert.send_summary_report(RESULTS, source_name="siparis")
        assert result is True  # kaynak adı email body HTML'inde geçiyor

    def test_subject_contains_period(self):
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
        alert = make_alert()
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_smtp.return_value
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = alert.send_summary_report([], period="günlük")
        assert result is True

    def test_smtp_error_returns_false(self):
        alert = make_alert()
        with patch("smtplib.SMTP", side_effect=Exception("bağlantı hatası")):
            result = alert.send_summary_report(RESULTS)
        assert result is False

    def test_all_passed(self):
        alert = make_alert()
        all_pass = [{"check_name": f"c{i}", "passed": True, "value_actual": i, "expected": i} for i in range(5)]
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_smtp.return_value
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = alert.send_summary_report(all_pass)
        assert result is True
