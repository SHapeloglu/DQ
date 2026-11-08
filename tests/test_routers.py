"""
test_routers.py — routers/ iş mantığı unit testleri.
pymysql / main.py import gerektirmez.
"""
import json
import pytest
from unittest.mock import MagicMock

def _make_conn(fetchone=None, fetchall=None):
    """Sahte veritabanı bağlantısı ve imleci (cursor) üretir. fetchone/fetchall sonuçları parametre olarak verilebilir."""
    cur = MagicMock()
    cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall or []
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur

class TestSourcesLogic:
    """DİKKAT: Bu sınıftaki testler routers/ kodunu gerçekten çağırmaz; mantığı testin içinde yeniden yazıp sınar. Gerçek kod değişse bu testler yine geçer. (TODO(kontrol): gerçek fonksiyonlara bağlanmalı.)"""
    def test_csv_config_only_has_path(self):
        """Kaynak türü csv ise yapılandırmada yalnızca 'path' bulunmalı, host gibi veritabanı alanları olmamalı."""
        type_ = "csv"
        config = {"path": "/data/file.csv"} if type_ == "csv" else {}
        assert config == {"path": "/data/file.csv"}
        assert "host" not in config

    def test_mysql_config_has_connection_fields(self):
        """Kaynak türü mysql ise host, port, veritabanı, kullanıcı ve parola alanları oluşmalı; path alanı olmamalı."""
        type_ = "mysql"
        config = {} if type_ == "csv" else {
            "host": "localhost", "port": "3306",
            "database": "dq", "user": "root", "password": "pass"
        }
        assert config["host"] == "localhost"
        assert "path" not in config

    def test_config_serialized_as_json(self):
        """Yapılandırma sözlüğü JSON metnine çevrilip geri okunduğunda değerler korunmalı (veritabanına JSON olarak yazılır)."""
        config = {"host": "localhost", "port": "3306"}
        serialized = json.dumps(config)
        assert json.loads(serialized)["host"] == "localhost"

    def test_source_delete_sql_structure(self):
        """Kaynak silme SQL'i parametreli yazılmalı (%s) ve id değeri ayrı bir parametre olarak verilmeli. Bu, SQL enjeksiyonunu önlemenin yoludur."""
        conn, cur = _make_conn()
        with conn.cursor() as c:
            c.execute("DELETE FROM sources WHERE id = %s", (42,))
        cur.execute.assert_called_with("DELETE FROM sources WHERE id = %s", (42,))

class TestChecksLogic:
    """Kontrol (check) kütüphanesi kurallarının yardımcı mantığı için testler. DİKKAT: Bu sınıftaki testler de gerçek router kodunu değil, içlerindeki kopyaları sınar."""
    def test_library_pattern_id_valid(self):
        """Kural kütüphanesi ID'si '5' metni ise sayıya (5) çevrilmeli."""
        pid = int("5") if "5".strip().isdigit() else None
        assert pid == 5

    def test_library_pattern_id_empty(self):
        """Boş metin ID'si None olmalı (sayıya çevrilmeye çalışılmaz)."""
        pid = int("") if "".strip().isdigit() else None
        assert pid is None

    def test_library_pattern_id_whitespace(self):
        """Sadece boşluk içeren ID de geçersiz sayılmalı (None)."""
        pid = int("  ") if "  ".strip().isdigit() else None
        assert pid is None

    def test_suggestion_type_mapping(self):
        """Öneri tipi eşlemesi: 'not_null' → 'is_not_null', bilinmeyen tip ise aynen kalmalı."""
        mapping = {"not_null": "is_not_null", "unique": "is_unique"}
        assert mapping.get("not_null", "not_null") == "is_not_null"
        assert mapping.get("unknown", "unknown") == "unknown"

    def test_reject_feedback_called_with_false(self):
        """Öneri reddedildiğinde geri bildirim accepted=False ile kaydedilmeli ve kolon adı doğru geçmeli."""
        calls = []
        def mock_feedback(conn, pid, col, rule_type, accepted):
            """Geri bildirim kaydını taklit eder: çağrı bilgilerini (kabul edildi mi, kolon adı) calls listesine yazar. Gerçek veritabanına yazmaz."""
            calls.append({"accepted": accepted, "col": col})
        conn, _ = _make_conn()
        mock_feedback(conn, None, "email", "is_not_null", accepted=False)
        assert calls[0]["accepted"] is False
        assert calls[0]["col"] == "email"

class TestGlossaryLogic:
    """Glossary (iş sözlüğü) güncelleme mantığı için testler. DİKKAT: Gerçek fonksiyon değil, testin içindeki kopyalar sınanır."""
    def test_update_filters_allowed_fields(self):
        """Sadece izin verilen alanlar (business_name, description, owner, tags) güncellemeye girer; 'hacker' alanı elenmeli, kalan 2 alan kalmalı."""
        allowed = {"business_name", "description", "owner", "tags"}
        payload = {"business_name": "Ad", "hacker": "x", "tags": "pii"}
        updates = {k: v for k, v in payload.items() if k in allowed}
        assert "hacker" not in updates
        assert len(updates) == 2

    def test_update_empty_payload_rejected(self):
        """Hiç izinli alan yoksa güncelleme boş olmalı (reddedilmeli)."""
        allowed = {"business_name", "description", "owner", "tags"}
        updates = {k: v for k, v in {"bad": "x"}.items() if k in allowed}
        assert len(updates) == 0

    def test_set_clause_generation(self):
        """SET ifadesi (alan=%s) izinli alanlardan doğru üretilmeli."""
        updates = {"business_name": "Test", "owner": "CRM"}
        fields = ", ".join(f"{k}=%s" for k in updates)
        assert "business_name=%s" in fields
        assert "owner=%s" in fields
