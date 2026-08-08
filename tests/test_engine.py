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


class TestCompletenessRatio:
    def test_passes_when_null_ratio_below_threshold(self):
        from dq.engine import completeness_ratio
        fn = completeness_ratio(0.95)  # en az %95 dolu
        assert fn(0.04) is True   # %4 null → geçer

    def test_fails_when_null_ratio_above_threshold(self):
        from dq.engine import completeness_ratio
        fn = completeness_ratio(0.95)
        assert fn(0.06) is False  # %6 null → geçmez

    def test_exact_boundary(self):
        from dq.engine import completeness_ratio
        fn = completeness_ratio(0.90)
        assert fn(0.10) is True   # tam sınır → geçer

    def test_in_assertion_map(self):
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("completeness_ratio")
        assert factory is not None
        fn = factory(0.95)
        assert fn(0.03) is True
        assert fn(0.10) is False


class TestStatisticalAnomaly:
    def test_passes_when_zscore_low(self):
        from dq.engine import statistical_anomaly
        fn = statistical_anomaly(3.0)
        assert fn(1.5) is True   # z=1.5 < 3.0 → normal

    def test_fails_when_zscore_high(self):
        from dq.engine import statistical_anomaly
        fn = statistical_anomaly(3.0)
        assert fn(4.2) is False  # z=4.2 > 3.0 → anomali

    def test_exact_boundary(self):
        from dq.engine import statistical_anomaly
        fn = statistical_anomaly(2.0)
        assert fn(2.0) is True   # tam sınır → geçer

    def test_in_assertion_map(self):
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("statistical_anomaly")
        assert factory is not None
        fn = factory(3.0)
        assert fn(1.0) is True
        assert fn(5.0) is False


class TestSchemaDrift:
    def test_passes_when_column_count_matches(self):
        from dq.engine import schema_drift
        fn = schema_drift(10)
        assert fn(10) is True

    def test_fails_when_column_added(self):
        from dq.engine import schema_drift
        fn = schema_drift(10)
        assert fn(11) is False  # fazladan kolon eklendi

    def test_fails_when_column_removed(self):
        from dq.engine import schema_drift
        fn = schema_drift(10)
        assert fn(9) is False   # kolon silindi

    def test_in_assertion_map(self):
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("schema_drift")
        assert factory is not None
        fn = factory(5)
        assert fn(5) is True
        assert fn(4) is False


class TestSchemaCheck:
    def test_passes_when_all_columns_present_with_correct_types(self):
        from dq.engine import schema_check
        fn = schema_check({"id": "int", "email": "varchar"})
        rows = [
            {"column_name": "id",    "data_type": "int"},
            {"column_name": "email", "data_type": "varchar"},
        ]
        assert fn(rows) is True

    def test_passes_when_type_check_skipped(self):
        from dq.engine import schema_check
        fn = schema_check({"id": None, "email": None})
        rows = [
            {"column_name": "id",    "data_type": "bigint"},
            {"column_name": "email", "data_type": "text"},
        ]
        assert fn(rows) is True

    def test_fails_when_column_missing(self):
        from dq.engine import schema_check
        fn = schema_check({"id": "int", "phone": "varchar"})
        rows = [{"column_name": "id", "data_type": "int"}]
        assert fn(rows) is False

    def test_fails_when_type_mismatch(self):
        from dq.engine import schema_check
        fn = schema_check({"id": "int"})
        rows = [{"column_name": "id", "data_type": "varchar"}]
        assert fn(rows) is False

    def test_passes_with_json_string_input(self):
        import json
        from dq.engine import schema_check
        fn = schema_check({"id": "int"})
        rows_json = json.dumps([{"column_name": "id", "data_type": "int"}])
        assert fn(rows_json) is True

    def test_fails_on_none_input(self):
        from dq.engine import schema_check
        fn = schema_check({"id": "int"})
        assert fn(None) is False

    def test_case_insensitive_column_and_type(self):
        from dq.engine import schema_check
        fn = schema_check({"ID": "INT"})
        rows = [{"column_name": "id", "data_type": "int"}]
        assert fn(rows) is True

    def test_in_assertion_map(self):
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("schema_check")
        assert factory is not None
        fn = factory({"id": "int"})
        rows = [{"column_name": "id", "data_type": "int"}]
        assert fn(rows) is True


class TestDuplicateRow:
    def test_passes_when_no_duplicates(self):
        from dq.engine import duplicate_row
        fn = duplicate_row(0)
        assert fn(0) is True  # tekrar yok

    def test_fails_when_duplicates_exist(self):
        from dq.engine import duplicate_row
        fn = duplicate_row(0)
        assert fn(5) is False  # 5 tekrar eden satır

    def test_passes_with_threshold(self):
        from dq.engine import duplicate_row
        fn = duplicate_row(3)
        assert fn(3) is True   # tam sınır → geçer
        assert fn(4) is False  # sınır aşıldı

    def test_default_threshold_is_zero(self):
        from dq.engine import duplicate_row
        fn = duplicate_row()
        assert fn(0) is True
        assert fn(1) is False

    def test_in_assertion_map(self):
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("duplicate_row")
        assert factory is not None
        fn = factory(0)
        assert fn(0) is True
        assert fn(1) is False
