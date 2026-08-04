"""
test_engine.py — CheckEngine ve assertion fonksiyonları için testler.

Çalıştır:
    pytest tests/test_engine.py -v
"""

import pytest
from dq.engine import (
    Check, CheckEngine, CheckResult,
    greater_than, less_than, between, equals,
    row_count_at_least, row_count_between, is_not_null,
)


# ── Assertion fonksiyonları ───────────────────────────────────────────────────

class TestAssertions:

    def test_greater_than_passes(self):
        assert greater_than(0)(100) is True

    def test_greater_than_fails_on_equal(self):
        assert greater_than(100)(100) is False

    def test_greater_than_fails_below(self):
        assert greater_than(50)(10) is False

    def test_less_than_passes(self):
        assert less_than(10)(5.0) is True

    def test_less_than_fails_on_equal(self):
        assert less_than(5)(5) is False

    def test_between_passes(self):
        assert between(1, 100)(50) is True

    def test_between_passes_on_boundary(self):
        assert between(1, 100)(1) is True
        assert between(1, 100)(100) is True

    def test_between_fails_below(self):
        assert between(10, 100)(5) is False

    def test_between_fails_above(self):
        assert between(10, 100)(200) is False

    def test_equals_passes(self):
        assert equals("aktif")("aktif") is True

    def test_equals_fails(self):
        assert equals("aktif")("pasif") is False

    def test_row_count_at_least_passes(self):
        assert row_count_at_least(1)(10) is True

    def test_row_count_at_least_fails(self):
        assert row_count_at_least(10)(5) is False

    def test_row_count_between_passes(self):
        assert row_count_between(5, 15)(10) is True

    def test_row_count_between_fails_low(self):
        assert row_count_between(5, 15)(3) is False

    def test_row_count_between_fails_high(self):
        assert row_count_between(5, 15)(20) is False

    def test_is_not_null_passes(self):
        assert is_not_null(42) is True

    def test_is_not_null_fails_on_none(self):
        assert is_not_null(None) is False

    def test_is_not_null_fails_on_zero(self):
        assert is_not_null(0) is False


# ── CheckResult ───────────────────────────────────────────────────────────────

class TestCheckResult:

    def test_status_pass(self):
        r = CheckResult("test", True, 10, "greater_than(0)")
        assert r.status == "PASS"

    def test_status_fail(self):
        r = CheckResult("test", False, 0, "greater_than(0)")
        assert r.status == "FAIL"

    def test_passed_field(self):
        r = CheckResult("test", True, 10, "greater_than(0)")
        assert r.passed is True


# ── CheckEngine ───────────────────────────────────────────────────────────────

class TestCheckEngine:

    def test_single_check_passes(self, basic_connector):
        check = Check(
            "Satır sayısı > 0",
            "SELECT COUNT(*) FROM source",
            greater_than(0), "greater_than(0)"
        )
        engine = CheckEngine(basic_connector)
        engine.add(check)
        results = engine.run()

        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].name == "Satır sayısı > 0"
        assert results[0].value == 100

    def test_single_check_fails(self, empty_connector):
        check = Check(
            "Satır sayısı > 0",
            "SELECT COUNT(*) FROM source",
            greater_than(0), "greater_than(0)"
        )
        engine = CheckEngine(empty_connector)
        engine.add(check)
        results = engine.run()

        assert results[0].passed is False
        assert results[0].value == 0

    def test_multiple_checks(self, basic_connector, sample_checks):
        engine = CheckEngine(basic_connector)
        engine.add_many(sample_checks)
        results = engine.run()

        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_chaining(self, basic_connector):
        """add() zincirleme çalışmalı."""
        from dq.engine import greater_than
        engine = (
            CheckEngine(basic_connector)
            .add(Check("A", "SELECT COUNT(*) FROM x", greater_than(0), ">0"))
            .add(Check("B", "SELECT SUM(x) FROM x",  greater_than(0), ">0"))
        )
        results = engine.run()
        assert len(results) == 2

    def test_tag_filter_runs_only_matching(self, basic_connector, sample_checks):
        """Sadece belirtilen etiketli check'ler çalışmalı."""
        engine = CheckEngine(basic_connector)
        engine.add_many(sample_checks)
        results = engine.run(tags=["critical"])

        assert len(results) == 1
        assert results[0].name == "Satır sayısı > 0"

    def test_tag_filter_no_match_returns_empty(self, basic_connector, sample_checks):
        engine = CheckEngine(basic_connector)
        engine.add_many(sample_checks)
        results = engine.run(tags=["olmayan_etiket"])

        assert results == []

    def test_connector_opened_and_closed(self, basic_connector):
        """Connector context manager doğru çalışmalı."""
        check = Check("test", "SELECT COUNT(*) FROM x", greater_than(0), ">0")
        engine = CheckEngine(basic_connector)
        engine.add(check)
        engine.run()

        assert basic_connector.connected is True
        assert basic_connector.closed is True

    def test_error_in_query_returns_fail_result(self, error_connector):
        """Connector hata fırlatırsa CheckResult.passed=False olmalı."""
        check = Check("hatalı check", "SELECT COUNT(*) FROM x",
                      greater_than(0), ">0")
        engine = CheckEngine(error_connector)
        engine.add(check)
        results = engine.run()

        assert results[0].passed is False
        assert "Hata" in results[0].message

    def test_empty_check_list_returns_empty(self, basic_connector):
        engine = CheckEngine(basic_connector)
        results = engine.run()
        assert results == []

    def test_query_is_logged(self, basic_connector):
        """Connector execute() doğru sorguyla çağrılmalı."""
        query = "SELECT COUNT(*) FROM orders"
        check = Check("test", query, greater_than(0), ">0")
        engine = CheckEngine(basic_connector)
        engine.add(check)
        engine.run()

        assert query in basic_connector.call_log

# ── referential_integrity testleri ───────────────────────────────────────────
class TestReferentialIntegrity:
    def test_passes_when_no_orphans(self):
        from dq.engine import referential_integrity
        check = referential_integrity("orders", "customer_id")
        assert check(0) is True  # eşleşmeyen kayıt yok

    def test_fails_when_orphans_exist(self):
        from dq.engine import referential_integrity
        check = referential_integrity("orders", "customer_id")
        assert check(5) is False  # 5 orphan kayıt var

    def test_fails_on_any_positive(self):
        from dq.engine import referential_integrity
        check = referential_integrity("a", "b")
        assert check(1) is False

    def test_in_assertion_map(self):
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("referential_integrity")
        assert factory is not None
        fn = factory(["ref_table", "ref_col"])
        assert fn(0) is True
        assert fn(3) is False
