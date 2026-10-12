
"""Unit tests for desktop-agent idle detection."""

import pytest

from app.idle import (
    calculate_idle_seconds,
    get_idle_status,
    is_idle_for_threshold,
    monitor_idle_status,
)


class TestCalculateIdleSeconds:
    def test_calculates_elapsed_seconds(self):
        result = calculate_idle_seconds(
            last_input_tick=10_000,
            current_tick=15_000,
        )

        assert result == 5.0

    def test_returns_zero_when_ticks_are_equal(self):
        result = calculate_idle_seconds(
            last_input_tick=10_000,
            current_tick=10_000,
        )

        assert result == 0.0

    def test_handles_large_elapsed_duration(self):
        result = calculate_idle_seconds(
            last_input_tick=1_000,
            current_tick=121_000,
        )

        assert result == 120.0

    @pytest.mark.parametrize(
        ("last_input_tick", "current_tick"),
        [
            (-1, 1000),
            (1000, -1),
            (-1, -1),
        ],
    )
    def test_rejects_negative_ticks(
        self,
        last_input_tick,
        current_tick,
    ):
        with pytest.raises(ValueError):
            calculate_idle_seconds(
                last_input_tick,
                current_tick,
            )

    def test_rejects_current_tick_before_last_input(self):
        with pytest.raises(ValueError):
            calculate_idle_seconds(
                last_input_tick=5000,
                current_tick=4000,
            )


class TestIdleThreshold:
    def test_active_below_threshold(self):
        assert is_idle_for_threshold(29.9, 30.0) is False

    def test_idle_at_threshold(self):
        assert is_idle_for_threshold(30.0, 30.0) is True

    def test_idle_above_threshold(self):
        assert is_idle_for_threshold(45.0, 30.0) is True

    def test_rejects_negative_idle_duration(self):
        with pytest.raises(ValueError):
            is_idle_for_threshold(-1.0, 30.0)

    @pytest.mark.parametrize("threshold", [0, -1, -10.0])
    def test_rejects_invalid_threshold(self, threshold):
        with pytest.raises(ValueError):
            is_idle_for_threshold(10.0, threshold)


def test_get_idle_status_uses_provider(monkeypatch):
    monkeypatch.setattr(
        "app.idle.get_windows_idle_seconds",
        lambda: 45.0,
    )

    result = get_idle_status(threshold_seconds=30.0)

    assert result.idle_seconds == 45.0
    assert result.is_idle is True


def test_get_idle_status_reports_active(monkeypatch):
    monkeypatch.setattr(
        "app.idle.get_windows_idle_seconds",
        lambda: 10.0,
    )

    result = get_idle_status(threshold_seconds=30.0)

    assert result.idle_seconds == 10.0
    assert result.is_idle is False


def test_monitor_idle_status_stops_after_duration(
    monkeypatch,
    capsys,
):
    readings = iter([2.0, 40.0])

    monkeypatch.setattr(
        "app.idle.time.sleep",
        lambda _: None,
    )

    monitor_idle_status(
        threshold_seconds=30.0,
        poll_interval_seconds=1.0,
        stop_after_seconds=0.000001,
        idle_seconds_provider=lambda: next(readings),
    )

    output = capsys.readouterr().out

    assert "Status: ACTIVE" in output
    assert "Idle duration: 2.0s" in output
