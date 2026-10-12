"""Entry point.  Run from the desktop-agent folder:  python -m app.main"""
import argparse
import signal
import sys
from dataclasses import replace
from pathlib import Path

from app import __version__
from app.agent import Agent
from app.logging_setup import close_logging, setup_logging
from app.settings import SettingsError, load_settings
from app.tracker import Tracker, TrackerUnavailable, WindowTracker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="attention-agent", description="Attention Platform desktop agent")
    parser.add_argument("--version", action="version", version=f"attention-agent {__version__}")
    parser.add_argument("--data-dir", type=Path, help="folder for config.toml, agent.log, buffer.db")
    parser.add_argument("--debug", action="store_true", help="log everything (DEBUG level)")
    parser.add_argument("--max-ticks", type=int, default=None, help=argparse.SUPPRESS)  # for tests
    return parser


def _install_signal_handlers(agent: Agent) -> dict:
    """Ctrl+C / terminate -> finish the current tick and exit cleanly."""
    previous = {}
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):  # SIGBREAK exists on Windows only
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            previous[sig] = signal.signal(sig, lambda *_: agent.stop())
        except ValueError:  # not the main thread
            pass
    return previous


def main(argv: list[str] | None = None, tracker: Tracker | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(args.data_dir)
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    if args.debug:
        settings = replace(settings, log_level="DEBUG")

    log = setup_logging(settings)
    previous: dict = {}
    try:
        log.info("attention-agent %s starting; data folder: %s", __version__, settings.data_dir)
        if tracker is None:
            try:
                tracker = WindowTracker(include_title=False)  # titles stay off (privacy default)
            except TrackerUnavailable as exc:
                log.error("%s", exc)
                print(f"Error: {exc}", file=sys.stderr)
                return 3
        agent = Agent(settings, tracker)
        previous = _install_signal_handlers(agent)
        try:
            return agent.run(max_ticks=args.max_ticks)
        except KeyboardInterrupt:
            agent.stop()
            return 0
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        close_logging()


if __name__ == "__main__":
    raise SystemExit(main())
