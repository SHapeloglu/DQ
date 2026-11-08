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

    """
    Doğrulama (assertion) fonksiyonlarının tek tek davranışını test eden sınıf.
    Her assertion bir 'fabrika' gibidir: greater_than(0) gibi çağrılır, dönen fonksiyon bir değeri alıp True/False döndürür.
    """
    def test_greater_than_passes(self):
        """greater_than(0): 100 değeri 0'dan büyük olduğu için True döner."""
        assert greater_than(0)(100) is True

    def test_greater_than_fails_on_equal(self):
        """greater_than(100): sınır değeri eşitlik durumunda False olmalı (büyük = katı büyüklük)."""
        assert greater_than(100)(100) is False

    def test_greater_than_fails_below(self):
        """greater_than(50): 10 değeri 50'den küçük olduğu için False döner."""
        assert greater_than(50)(10) is False

    def test_less_than_passes(self):
        """less_than(10): 5.0 değeri 10'dan küçük olduğu için True döner. Ondalıklı sayıyla da çalıştığını gösterir."""
        assert less_than(10)(5.0) is True

    def test_less_than_fails_on_equal(self):
        """less_than(5): eşitlik durumu (5 = 5) False olmalı; 'küçük' katı küçüklüktür."""
        assert less_than(5)(5) is False

    def test_between_passes(self):
        """between(1, 100): 50 aralığın içinde olduğu için True."""
        assert between(1, 100)(50) is True

    def test_between_passes_on_boundary(self):
        """between(1, 100): aralığın iki ucu (1 ve 100) dahildir, ikisi de True olmalı. Sınır hatalarını (off-by-one) yakalamak için yazıldı."""
        assert between(1, 100)(1) is True
        assert between(1, 100)(100) is True

    def test_between_fails_below(self):
        """between(10, 100): 5 alt sınırın altında olduğu için False."""
        assert between(10, 100)(5) is False

    def test_between_fails_above(self):
        """between(10, 100): 200 üst sınırın üstünde olduğu için False."""
        assert between(10, 100)(200) is False

    def test_equals_passes(self):
        """equals('aktif'): aynı metin verildiğinde True."""
        assert equals("aktif")("aktif") is True

    def test_equals_fails(self):
        """equals('aktif'): farklı metin ('pasif') verildiğinde False."""
        assert equals("aktif")("pasif") is False

    def test_row_count_at_least_passes(self):
        """row_count_at_least(1): 10 satır en az 1 olduğu için True."""
        assert row_count_at_least(1)(10) is True

    def test_row_count_at_least_fails(self):
        """row_count_at_least(10): 5 satır en az 10 değil, False."""
        assert row_count_at_least(10)(5) is False

    def test_row_count_between_passes(self):
        """row_count_between(5, 15): 10 satır aralığın içinde, True."""
        assert row_count_between(5, 15)(10) is True

    def test_row_count_between_fails_low(self):
        """row_count_between(5, 15): 3 satır alt sınırın altında, False."""
        assert row_count_between(5, 15)(3) is False

    def test_row_count_between_fails_high(self):
        """row_count_between(5, 15): 20 satır üst sınırın üstünde, False."""
        assert row_count_between(5, 15)(20) is False

    def test_is_not_null_passes(self):
        """is_not_null(42): dolu bir değer için True."""
        assert is_not_null(42) is True

    def test_is_not_null_fails_on_none(self):
        """is_not_null(None): None (boş) için False. Veritabanındaki NULL değerini doğru yakaladığını gösterir."""
        assert is_not_null(None) is False

    def test_is_not_null_fails_on_zero(self):
        """is_not_null(0): 0 de bir değerdir, boş sayılmaz; True dönmeli. 'if not value' gibi yanlış kontrollerin hatasını yakalar."""
        assert is_not_null(0) is False


# ── CheckResult ───────────────────────────────────────────────────────────────

class TestCheckResult:

    """CheckResult (tek bir kontrolün sonucu) nesnesinin durum ve bayrak alanlarını test eden sınıf."""
    def test_status_pass(self):
        """passed=True olan sonucun metinsel durumu 'PASS' olmalı."""
        r = CheckResult("test", True, 10, "greater_than(0)")
        assert r.status == "PASS"

    def test_status_fail(self):
        """passed=False olan sonucun metinsel durumu 'FAIL' olmalı."""
        r = CheckResult("test", False, 0, "greater_than(0)")
        assert r.status == "FAIL"

    def test_passed_field(self):
        """CheckResult.passed alanı, verilen True değerini aynen tutmalı."""
        r = CheckResult("test", True, 10, "greater_than(0)")
        assert r.passed is True


# ── CheckEngine ───────────────────────────────────────────────────────────────

class TestCheckEngine:

    """CheckEngine (kontrol motoru) ile kontrollerin ekleme, çalıştırma ve etiket filtreleme akışını test eden sınıf."""
    def test_single_check_passes(self, basic_connector):
        """
        Sahte bağlantıda COUNT(*) 100 döndüğünde 'Satır sayısı > 0' kontrolü geçmeli.
        Sonuç adı ve değeri (100) da doğru taşınmalı.
        """
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
        """Boş tabloda (COUNT(*) = 0) aynı kontrol başarısız olmalı ve değer 0 raporlanmalı."""
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
        """sample_checks fixture'ındaki 3 kontrolün hepsi basic_connector ile geçmeli. Birden çok kontrolün birlikte çalıştığını doğrular."""
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
        """Var olmayan bir etiket verilirse hiç kontrol çalışmamalı ve sonuç boş liste olmalı."""
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
        """Hiç kontrol eklenmeden run() çağrılırsa sonuç boş liste dönmeli (hata vermemeli)."""
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
    """referential_integrity (yabancı anahtar bütünlüğü) kuralını test eden sınıf. Argümanlar: tablo adı ve sütun adı; check(orphan_sayısı) kullanılır."""
    def test_passes_when_no_orphans(self):
        """Yetim (eşleşmeyen) kayıt sayısı 0 ise kontrol geçer."""
        from dq.engine import referential_integrity
        check = referential_integrity("orders", "customer_id")
        assert check(0) is True  # eşleşmeyen kayıt yok

    def test_fails_when_orphans_exist(self):
        """5 yetim kayıt varsa kontrol başarısız olur."""
        from dq.engine import referential_integrity
        check = referential_integrity("orders", "customer_id")
        assert check(5) is False  # 5 orphan kayıt var

    def test_fails_on_any_positive(self):
        """1 yetim kayıt bile olsa başarısız olmalı. Sıfır toleransı olduğunu gösterir."""
        from dq.engine import referential_integrity
        check = referential_integrity("a", "b")
        assert check(1) is False

    def test_in_assertion_map(self):
        """_ASSERTION_MAP (kural adı → fonksiyon eşlemesi) içinde 'referential_integrity' kaydının olduğunu ve fabrikanın doğru çalıştığını doğrular. Ayar dosyasından gelen kural adı doğru fonksiyona bağlanmalı."""
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("referential_integrity")
        assert factory is not None
        fn = factory(["ref_table", "ref_col"])
        assert fn(0) is True
        assert fn(3) is False


class TestCompletenessRatio:
    """completeness_ratio (doluluk oranı) kuralını test eden sınıf. Eşik 0.95 = en az %95 dolu olmalı; check(null_oranı) alır."""
    def test_passes_when_null_ratio_below_threshold(self):
        """Null oranı %4 ise (eşik %5 null'a izin verirken) geçer."""
        from dq.engine import completeness_ratio
        fn = completeness_ratio(0.95)  # en az %95 dolu
        assert fn(0.04) is True   # %4 null → geçer

    def test_fails_when_null_ratio_above_threshold(self):
        """Null oranı %6 ise eşik aşılmış olur, kontrol başarısız."""
        from dq.engine import completeness_ratio
        fn = completeness_ratio(0.95)
        assert fn(0.06) is False  # %6 null → geçmez

    def test_exact_boundary(self):
        """Tam sınır: eşik 0.90 iken null oranı 0.10 (tam %10) geçmeli. Sınırın dahil olduğunu gösterir."""
        from dq.engine import completeness_ratio
        fn = completeness_ratio(0.90)
        assert fn(0.10) is True   # tam sınır → geçer

    def test_in_assertion_map(self):
        """'completeness_ratio' kuralının _ASSERTION_MAP kaydını ve fabrikasını doğrular (kural adı ayar dosyasından bağlanır)."""
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("completeness_ratio")
        assert factory is not None
        fn = factory(0.95)
        assert fn(0.03) is True
        assert fn(0.10) is False


class TestStatisticalAnomaly:
    """statistical_anomaly (z-skoru anomali) kuralını test eden sınıf. Eşik z değeridir; z büyükse anomali sayılır."""
    def test_passes_when_zscore_low(self):
        """z=1.5 eşik 3.0'ın altında olduğu için normal kabul edilir (True)."""
        from dq.engine import statistical_anomaly
        fn = statistical_anomaly(3.0)
        assert fn(1.5) is True   # z=1.5 < 3.0 → normal

    def test_fails_when_zscore_high(self):
        """z=4.2 eşik 3.0'ı aştığı için anomali, False."""
        from dq.engine import statistical_anomaly
        fn = statistical_anomaly(3.0)
        assert fn(4.2) is False  # z=4.2 > 3.0 → anomali

    def test_exact_boundary(self):
        """Tam sınır: eşik 2.0 ve z=2.0 geçmeli (sınır dahil)."""
        from dq.engine import statistical_anomaly
        fn = statistical_anomaly(2.0)
        assert fn(2.0) is True   # tam sınır → geçer

    def test_in_assertion_map(self):
        """'statistical_anomaly' kuralının _ASSERTION_MAP kaydını ve fabrikasını doğrular."""
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("statistical_anomaly")
        assert factory is not None
        fn = factory(3.0)
        assert fn(1.0) is True
        assert fn(5.0) is False


class TestSchemaDrift:
    """schema_drift (şema değişikliği) kuralını test eden sınıf. Beklenen kolon sayısı verilir; gerçek sayı farklıysa değişiklik vardır."""
    def test_passes_when_column_count_matches(self):
        """Kolon sayısı beklenenle (10) aynıysa şema değişmemiş, True."""
        from dq.engine import schema_drift
        fn = schema_drift(10)
        assert fn(10) is True

    def test_fails_when_column_added(self):
        """Kolon sayısı 11 olduğunda (kolon eklenmiş) False."""
        from dq.engine import schema_drift
        fn = schema_drift(10)
        assert fn(11) is False  # fazladan kolon eklendi

    def test_fails_when_column_removed(self):
        """Kolon sayısı 9 olduğunda (kolon silinmiş) False. Eklemeyi ve silmeyi ayrı ayrı yakalar."""
        from dq.engine import schema_drift
        fn = schema_drift(10)
        assert fn(9) is False   # kolon silindi

    def test_in_assertion_map(self):
        """'schema_drift' kuralının _ASSERTION_MAP kaydını ve fabrikasını doğrular."""
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("schema_drift")
        assert factory is not None
        fn = factory(5)
        assert fn(5) is True
        assert fn(4) is False


class TestSchemaCheck:
    """schema_check (kolon adı ve tip kontrolü) kuralını test eden sınıf. Beklenen {kolon: tip} sözlüğü verilir; satırlar (kolon_adı, veri_tipi) listesi olarak gelir."""
    def test_passes_when_all_columns_present_with_correct_types(self):
        """Beklenen tüm kolonlar ve tipler doğruysa geçer."""
        from dq.engine import schema_check
        fn = schema_check({"id": "int", "email": "varchar"})
        rows = [
            {"column_name": "id",    "data_type": "int"},
            {"column_name": "email", "data_type": "varchar"},
        ]
        assert fn(rows) is True

    def test_passes_when_type_check_skipped(self):
        """Beklenen tip None ise tip kontrolü atlanır; sadece kolonun varlığına bakılır."""
        from dq.engine import schema_check
        fn = schema_check({"id": None, "email": None})
        rows = [
            {"column_name": "id",    "data_type": "bigint"},
            {"column_name": "email", "data_type": "text"},
        ]
        assert fn(rows) is True

    def test_fails_when_column_missing(self):
        """Beklenen 'phone' kolonu yoksa başarısız olur (eksik kolon)."""
        from dq.engine import schema_check
        fn = schema_check({"id": "int", "phone": "varchar"})
        rows = [{"column_name": "id", "data_type": "int"}]
        assert fn(rows) is False

    def test_fails_when_type_mismatch(self):
        """Kolon var ama tipi farklı (beklenen int, gelen varchar) ise başarısız olur."""
        from dq.engine import schema_check
        fn = schema_check({"id": "int"})
        rows = [{"column_name": "id", "data_type": "varchar"}]
        assert fn(rows) is False

    def test_passes_with_json_string_input(self):
        """Satırlar liste yerine JSON metni olarak gelirse de doğru çalışmalı. Veri kaynağının iki biçimde gelebildiğini gösterir."""
        import json
        from dq.engine import schema_check
        fn = schema_check({"id": "int"})
        rows_json = json.dumps([{"column_name": "id", "data_type": "int"}])
        assert fn(rows_json) is True

    def test_fails_on_none_input(self):
        """Veri hiç gelmezse (None) False döner. Hata vermeden başarısız saymalı."""
        from dq.engine import schema_check
        fn = schema_check({"id": "int"})
        assert fn(None) is False

    def test_case_insensitive_column_and_type(self):
        """Kolon adı ve tip büyük/küçük harf farkı yüzünden reddedilmemeli ('ID' ile 'id', 'INT' ile 'int' eşleşir)."""
        from dq.engine import schema_check
        fn = schema_check({"ID": "INT"})
        rows = [{"column_name": "id", "data_type": "int"}]
        assert fn(rows) is True

    def test_in_assertion_map(self):
        """'schema_check' kuralının _ASSERTION_MAP kaydını ve fabrikasını doğrular."""
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("schema_check")
        assert factory is not None
        fn = factory({"id": "int"})
        rows = [{"column_name": "id", "data_type": "int"}]
        assert fn(rows) is True


class TestDuplicateRow:
    """duplicate_row (tekrarlanan satır) kuralını test eden sınıf. Eşik: izin verilen en fazla tekrar sayısı (varsayılan 0)."""
    def test_passes_when_no_duplicates(self):
        """Tekrar sayısı 0 ise geçer."""
        from dq.engine import duplicate_row
        fn = duplicate_row(0)
        assert fn(0) is True  # tekrar yok

    def test_fails_when_duplicates_exist(self):
        """5 tekrarlı satır varsa başarısız olur."""
        from dq.engine import duplicate_row
        fn = duplicate_row(0)
        assert fn(5) is False  # 5 tekrar eden satır

    def test_passes_with_threshold(self):
        """Eşik 3 iken: 3 tekrar (tam sınır) geçer, 4 tekrar (sınır aşıldı) kalır."""
        from dq.engine import duplicate_row
        fn = duplicate_row(3)
        assert fn(3) is True   # tam sınır → geçer
        assert fn(4) is False  # sınır aşıldı

    def test_default_threshold_is_zero(self):
        """duplicate_row() argümansız çağrılırsa eşik 0'dır: 0 geçer, 1 kalır."""
        from dq.engine import duplicate_row
        fn = duplicate_row()
        assert fn(0) is True
        assert fn(1) is False

    def test_in_assertion_map(self):
        """'duplicate_row' kuralının _ASSERTION_MAP kaydını ve fabrikasını doğrular."""
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("duplicate_row")
        assert factory is not None
        fn = factory(0)
        assert fn(0) is True
        assert fn(1) is False


class TestCustomSql:
    """custom_sql (kullanıcının yazdığı SQL'in sonucunu kontrol eder) kuralını test eden sınıf. Beklenen değer tek sayı, aralık ([min, max]) veya None olabilir."""
    def test_passes_when_value_equals_expected(self):
        """Beklenen değer 0 ve sonuç 0 ise geçer."""
        from dq.engine import custom_sql
        fn = custom_sql(0)
        assert fn(0) is True

    def test_fails_when_value_not_equal(self):
        """Beklenen 0, sonuç 5 ise başarısız."""
        from dq.engine import custom_sql
        fn = custom_sql(0)
        assert fn(5) is False

    def test_passes_with_range(self):
        """Aralık [10, 100] verildiğinde 50 geçer; sınırlar 10 ve 100 de geçer (aralık dahildir)."""
        from dq.engine import custom_sql
        fn = custom_sql([10, 100])
        assert fn(50) is True
        assert fn(10) is True
        assert fn(100) is True

    def test_fails_outside_range(self):
        """Aralık dışındaki değerler (5 ve 101) başarısız olur."""
        from dq.engine import custom_sql
        fn = custom_sql([10, 100])
        assert fn(5) is False
        assert fn(101) is False

    def test_passes_when_expected_none_and_value_exists(self):
        """Beklenen None iken sonuç bir değer taşıyorsa geçer (sadece 'bir sonuç var' kontrolü)."""
        from dq.engine import custom_sql
        fn = custom_sql(None)
        assert fn(42) is True

    def test_fails_when_expected_none_and_value_is_none(self):
        """Beklenen None iken sonuç da None ise başarısız. Yani sonucun gerçekten dolu olması gerekir."""
        from dq.engine import custom_sql
        fn = custom_sql(None)
        assert fn(None) is False

    def test_in_assertion_map(self):
        """'custom_sql' kuralının _ASSERTION_MAP kaydını ve fabrikasını doğrular."""
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("custom_sql")
        assert factory is not None
        fn = factory(0)
        assert fn(0) is True
        assert fn(1) is False


class TestVolumeAnomaly:
    """volume_anomaly (satır sayısı değişimi) kuralını test eden sınıf. baseline: önceki dönemin satır sayısı; max_pct_change: izin verilen en büyük yüzde değişim."""
    def test_passes_when_change_within_threshold(self):
        """Baseline 1000, değer 1100 (%10 artış), eşik %20: geçer."""
        from dq.engine import volume_anomaly
        fn = volume_anomaly(max_pct_change=20.0, baseline=1000)
        assert fn(1100) is True   # %10 artış → geçer

    def test_fails_when_change_exceeds_threshold(self):
        """Baseline 1000, değer 1300 (%30 artış), eşik %20: başarısız."""
        from dq.engine import volume_anomaly
        fn = volume_anomaly(max_pct_change=20.0, baseline=1000)
        assert fn(1300) is False  # %30 artış → geçmez

    def test_passes_on_decrease_within_threshold(self):
        """Baseline 1000, değer 900 (%10 azalış): azalış da eşik içindeyse geçer. Artış ve azalışın ikisi de kontrol edilir."""
        from dq.engine import volume_anomaly
        fn = volume_anomaly(max_pct_change=20.0, baseline=1000)
        assert fn(900) is True    # %10 azalış → geçer

    def test_fails_on_large_decrease(self):
        """Baseline 1000, değer 500 (%50 azalış): büyük azalış başarısız olur."""
        from dq.engine import volume_anomaly
        fn = volume_anomaly(max_pct_change=20.0, baseline=1000)
        assert fn(500) is False   # %50 azalış → geçmez

    def test_passes_without_baseline(self):
        """Baseline verilmezse sadece değer > 0 kontrol edilir: 100 geçer."""
        from dq.engine import volume_anomaly
        fn = volume_anomaly()
        assert fn(100) is True    # baseline yok, değer > 0 → geçer

    def test_fails_on_zero_without_baseline(self):
        """Baseline yokken değer 0 (boş tablo) başarısız olur."""
        from dq.engine import volume_anomaly
        fn = volume_anomaly()
        assert fn(0) is False     # boş tablo → geçmez

    def test_passes_exact_boundary(self):
        """Tam sınır: eşik %10 iken %10 artış (1100) geçer."""
        from dq.engine import volume_anomaly
        fn = volume_anomaly(max_pct_change=10.0, baseline=1000)
        assert fn(1100) is True   # tam %10 → geçer

    def test_in_assertion_map(self):
        """'volume_anomaly' kuralının _ASSERTION_MAP kaydını ve fabrikasını doğrular."""
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("volume_anomaly")
        assert factory is not None
        fn = factory(50.0)
        assert fn(100) is True

class TestRowCondition:
    """row_condition (satır bazlı SQL koşulu, ihlal sayısı) kuralını test eden sınıf. Argüman: kural koşulu metni; check(ihlal_sayısı) alır."""
    def test_passes_when_no_violations(self):
        """İhlal sayısı 0 ise geçer."""
        from dq.engine import row_condition
        fn = row_condition("age > 0 AND age < 150")
        assert fn(0) is True   # ihlal yok → geçer
    def test_fails_when_violations_exist(self):
        """5 satır ihlal ederse başarısız."""
        from dq.engine import row_condition
        fn = row_condition("age > 0 AND age < 150")
        assert fn(5) is False  # 5 satır ihlal → geçmez
    def test_in_assertion_map(self):
        """'row_condition' kuralının _ASSERTION_MAP kaydını ve fabrikasını doğrular."""
        from dq.config import _ASSERTION_MAP
        factory = _ASSERTION_MAP.get("row_condition")
        assert factory is not None
        fn = factory("status IN ('active', 'pending')")
        assert fn(0) is True
