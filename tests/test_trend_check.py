from unittest.mock import MagicMock
from dq.engine import trend_check


def make_store(values):
    store = MagicMock()
    store.get_recent_values.return_value = values
    return store


class TestTrendCheck:
    def test_stable_trend_passes(self):
        values = [100.0] * 14
        store = make_store(values)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(100.0) is True

    def test_large_increase_fails(self):
        prev = [100.0] * 7
        curr = [150.0] * 7  # %50 artış
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(150.0) is False

    def test_large_decrease_fails(self):
        prev = [100.0] * 7
        curr = [50.0] * 7  # %50 düşüş
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(50.0) is False

    def test_insufficient_history_passes(self):
        store = make_store([100.0] * 5)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(100.0) is True

    def test_direction_up_increase_fails(self):
        prev = [100.0] * 7
        curr = [130.0] * 7  # %30 artış — up modunda kötü
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0, direction="up")
        assert fn(130.0) is False

    def test_direction_up_decrease_passes(self):
        prev = [100.0] * 7
        curr = [70.0] * 7  # düşüş — up modunda normal
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0, direction="up")
        assert fn(70.0) is True

    def test_direction_down_decrease_fails(self):
        prev = [100.0] * 7
        curr = [60.0] * 7  # %40 düşüş — down modunda kötü
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0, direction="down")
        assert fn(60.0) is False

    def test_zero_prev_avg_zero_curr_passes(self):
        store = make_store([0.0] * 14)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(0.0) is True
