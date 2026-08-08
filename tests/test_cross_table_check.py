from unittest.mock import MagicMock, patch
from dq.engine import cross_table_check


def make_connector(return_value):
    conn = MagicMock()
    conn.execute.return_value = [{"val": return_value}]
    conn.__enter__ = lambda s: conn
    conn.__exit__ = MagicMock(return_value=False)
    return conn


class TestCrossTableCheck:
    def test_equals_pass(self):
        conn_b = make_connector(100)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="equals")
        assert fn(100) is True

    def test_equals_fail(self):
        conn_b = make_connector(200)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="equals")
        assert fn(100) is False

    def test_less_than_pass(self):
        conn_b = make_connector(200)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="less_than")
        assert fn(100) is True

    def test_less_than_fail(self):
        conn_b = make_connector(50)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="less_than")
        assert fn(100) is False

    def test_greater_than_pass(self):
        conn_b = make_connector(50)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="greater_than")
        assert fn(100) is True

    def test_within_pct_pass(self):
        conn_b = make_connector(100)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="within_pct", tolerance=5.0)
        assert fn(104) is True

    def test_within_pct_fail(self):
        conn_b = make_connector(100)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="within_pct", tolerance=5.0)
        assert fn(110) is False

    def test_empty_result_fails(self):
        conn_b = MagicMock()
        conn_b.execute.return_value = []
        conn_b.__enter__ = lambda s: conn_b
        conn_b.__exit__ = MagicMock(return_value=False)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="equals")
        assert fn(100) is False
