import math
import pytest
from unittest.mock import MagicMock
from dq.engine import zscore_anomaly


def make_store(values):
    store = MagicMock()
    store.get_recent_values.return_value = values
    return store


class TestZscoreAnomaly:
    def test_normal_value_passes(self):
        values = [100.0] * 20
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=3.0)
        assert fn(100.0) is True

    def test_anomaly_detected(self):
        values = [100.0 + i * 0.1 for i in range(20)]  # std != 0
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=3.0)
        assert fn(9999.0) is False

    def test_insufficient_samples_passes(self):
        store = make_store([100.0, 200.0])
        fn = zscore_anomaly("m", store, max_zscore=3.0, min_samples=5)
        assert fn(9999.0) is True

    def test_constant_series_passes(self):
        values = [50.0] * 10
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=3.0)
        assert fn(50.0) is True

    def test_exact_threshold_passes(self):
        values = list(range(1, 21))
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=10.0)
        assert fn(10.5) is True

    def test_custom_max_zscore(self):
        values = [100.0 + i * 0.1 for i in range(20)]  # std != 0
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=0.0)
        assert fn(9999.0) is False

    def test_store_called_with_metric_name(self):
        store = make_store([100.0] * 10)
        fn = zscore_anomaly("siparis_sayisi", store, max_zscore=3.0)
        fn(100.0)
        store.get_recent_values.assert_called_once_with("siparis_sayisi", n=100)

    def test_in_assertion_map(self):
        from dq.config import _ASSERTION_MAP
        assert "zscore_anomaly" in _ASSERTION_MAP
