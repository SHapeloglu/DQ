from dq.engine import distribution_check


class TestDistributionCheck:
    def test_mean_only_pass(self):
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn("100.0") is True

    def test_mean_only_fail(self):
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn("120.0") is False

    def test_mean_and_std_pass(self):
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn("100.0,10.0") is True

    def test_mean_and_std_fail_on_std(self):
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=5.0)
        assert fn("100.0,15.0") is False

    def test_mean_and_std_fail_on_mean(self):
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=5.0)
        assert fn("90.0,10.0") is False

    def test_tolerance_boundary_pass(self):
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn("110.0,11.0") is True

    def test_none_value_fails(self):
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn(None) is False

    def test_zero_expected_mean(self):
        fn = distribution_check(expected_mean=0.0, expected_std=1.0, tolerance_pct=10.0)
        assert fn("0.0,1.0") is True
