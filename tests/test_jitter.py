import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implant"))


class TestJitter:
    def test_jitter_range_50_percent(self):
        """Con ±50%, el sleep debe estar entre 15s y 45s (base=30)."""
        from implant import calculate_jitter_sleep

        results = []
        for _ in range(100):
            sleep_time = calculate_jitter_sleep(30, 50)
            results.append(sleep_time)

        assert all(1 <= s <= 60 for s in results), f"Sleep fuera de rango: {min(results)}-{max(results)}"
        assert min(results) >= 15, f"Sleep mínimo muy bajo: {min(results)}"
        assert max(results) <= 45, f"Sleep máximo muy alto: {max(results)}"

    def test_jitter_range_20_percent(self):
        """Con ±20%, el sleep debe estar entre 24s y 36s (base=30)."""
        from implant import calculate_jitter_sleep

        results = []
        for _ in range(100):
            sleep_time = calculate_jitter_sleep(30, 20)
            results.append(sleep_time)

        assert all(20 <= s <= 40 for s in results), f"Sleep fuera de rango: {min(results)}-{max(results)}"

    def test_jitter_range_100_percent(self):
        """Con ±100%, el sleep debe estar entre 0s y 60s (base=30), mínimo 1s."""
        from implant import calculate_jitter_sleep

        results = []
        for _ in range(100):
            sleep_time = calculate_jitter_sleep(30, 100)
            results.append(sleep_time)

        assert all(1 <= s <= 60 for s in results), f"Sleep fuera de rango: {min(results)}-{max(results)}"

    def test_jitter_always_positive(self):
        """El sleep siempre debe ser >= 1 segundo."""
        from implant import calculate_jitter_sleep

        for _ in range(100):
            sleep_time = calculate_jitter_sleep(30, 50)
            assert sleep_time >= 1

    def test_jitter_is_integer(self):
        """El sleep debe ser un entero."""
        from implant import calculate_jitter_sleep

        sleep_time = calculate_jitter_sleep(30, 50)
        assert isinstance(sleep_time, int)

    def test_zero_jitter_returns_base(self):
        """Con jitter 0%, el sleep debe ser exactamente el base."""
        from implant import calculate_jitter_sleep

        for _ in range(10):
            sleep_time = calculate_jitter_sleep(30, 0)
            assert sleep_time == 30
