
"""
Windows idle detection utilities.

Uses:
    - GetLastInputInfo: Retrieves the time of the last user input.
    - GetTickCount64: Retrieves the time elapsed since Windows started.

This module does not record keystrokes or mouse-click contents.
It only calculates elapsed time since the last input.
"""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class IdleStatus:
    """Represents the current idle status of the user."""

    idle_seconds: float
    is_idle: bool


def calculate_idle_seconds(
    last_input_tick: int,
    current_tick: int,
) -> float:
    """
    Calculate elapsed seconds since the last input.

    Args:
        last_input_tick: Tick count when the last input occurred.
        current_tick: Current Windows tick count.

    Returns:
        Number of seconds since the last input.

    Raises:
        ValueError: If tick values are negative or current_tick
                    precedes last_input_tick.
    """
    if last_input_tick < 0 or current_tick < 0:
        raise ValueError("Tick values cannot be negative.")

    if current_tick < last_input_tick:
        raise ValueError("Current tick cannot precede last input tick.")

    elapsed_milliseconds = current_tick - last_input_tick

    return elapsed_milliseconds / 1000.0


def is_idle_for_threshold(
    idle_seconds: float,
    threshold_seconds: float,
) -> bool:
    """
    Determine whether the idle duration meets the configured threshold.

    A user is considered idle when idle_seconds >= threshold_seconds.
    """
    if idle_seconds < 0:
        raise ValueError("Idle duration cannot be negative.")

    if threshold_seconds <= 0:
        raise ValueError("Idle threshold must be greater than zero.")

    return idle_seconds >= threshold_seconds


def get_windows_idle_seconds() -> float:
    """
    Return seconds elapsed since the last keyboard or mouse input.

    This function is Windows-specific.

    Raises:
        OSError: If the Windows API call fails.
        RuntimeError: If called on a non-Windows operating system.
    """
    if __import__("sys").platform != "win32":
        raise RuntimeError(
            "Windows idle detection is only available on Windows."
        )

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("dwTime", wintypes.DWORD),
        ]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    get_last_input_info = user32.GetLastInputInfo
    get_last_input_info.argtypes = [
        ctypes.POINTER(LASTINPUTINFO)
    ]
    get_last_input_info.restype = wintypes.BOOL

    get_tick_count64 = kernel32.GetTickCount64
    get_tick_count64.argtypes = []
    get_tick_count64.restype = ctypes.c_ulonglong

    last_input = LASTINPUTINFO()
    last_input.cbSize = ctypes.sizeof(LASTINPUTINFO)

    if not get_last_input_info(ctypes.byref(last_input)):
        error_code = ctypes.get_last_error()

        raise OSError(
            error_code,
            "Windows GetLastInputInfo API call failed.",
        )

    current_tick = int(get_tick_count64())

    # GetLastInputInfo returns a 32-bit tick count.
    # Handle the tick counter wrapping around after approximately
    # 49.7 days by using unsigned 32-bit subtraction.
    elapsed_milliseconds = (
        current_tick - int(last_input.dwTime)
    ) & 0xFFFFFFFF

    return elapsed_milliseconds / 1000.0


def get_idle_status(
    threshold_seconds: float = 60.0,
) -> IdleStatus:
    """
    Return the current idle duration and threshold-based idle status.

    Args:
        threshold_seconds: Minimum idle duration required to classify
                           the user as idle. Defaults to 60 seconds.
    """
    idle_seconds = get_windows_idle_seconds()

    return IdleStatus(
        idle_seconds=idle_seconds,
        is_idle=is_idle_for_threshold(
            idle_seconds,
            threshold_seconds,
        ),
    )


def monitor_idle_status(
    threshold_seconds: float = 60.0,
    poll_interval_seconds: float = 1.0,
    stop_after_seconds: float | None = None,
    idle_seconds_provider: Callable[[], float] | None = None,
) -> None:
    """
    Print idle status periodically.

    This helper is useful for manual verification.

    Args:
        threshold_seconds: Idle threshold in seconds.
        poll_interval_seconds: Delay between checks.
        stop_after_seconds: Optional maximum monitoring duration.
        idle_seconds_provider: Optional injectable idle-time provider.
                               Useful for tests.
    """
    if threshold_seconds <= 0:
        raise ValueError("Idle threshold must be greater than zero.")

    if poll_interval_seconds <= 0:
        raise ValueError("Poll interval must be greater than zero.")

    if stop_after_seconds is not None and stop_after_seconds <= 0:
        raise ValueError("Monitoring duration must be greater than zero.")

    provider = idle_seconds_provider or get_windows_idle_seconds
    start_time = time.monotonic()

    try:
        while True:
            idle_seconds = provider()

            idle = is_idle_for_threshold(
                idle_seconds,
                threshold_seconds,
            )

            status = "IDLE" if idle else "ACTIVE"

            print(
                f"Status: {status} | "
                f"Idle duration: {idle_seconds:.1f}s | "
                f"Threshold: {threshold_seconds:.1f}s"
            )

            if (
                stop_after_seconds is not None
                and time.monotonic() - start_time >= stop_after_seconds
            ):
                break

            time.sleep(poll_interval_seconds)

    except KeyboardInterrupt:
        print("\nIdle monitoring stopped.")
