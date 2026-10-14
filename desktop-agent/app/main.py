
"""Entry point. Run from the desktop-agent folder:

    python -m app.main login      # store login in Windows Credential Manager
    python -m app.main            # run the agent (Ctrl+C to stop)
    python -m app.main status     # login, server and upload queue
    python -m app.main logout
"""

import argparse
import getpass
import signal
import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable

from app import __version__
from app.account_cli import run_account_command
from app.agent import Agent
from app.api_client import ApiClient
from app.idle import get_windows_idle_seconds
from app.logging_setup import close_logging, setup_logging
from app.settings import SettingsError, load_settings
from app.token_store import TokenStore, TokenStoreUnavailable
from app.tracker import Tracker, TrackerUnavailable, WindowTracker


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="attention-agent",
        description="Attention Platform desktop agent",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "login", "logout", "status"],
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"attention-agent {__version__}",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="folder for config.toml, agent.log, buffer.db",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="log everything (DEBUG level)",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--show-password",
        action="store_true",
        help="show the password while typing (login only)",
    )

    return parser


def _install_signal_handlers(agent: Agent) -> dict:
    """Ctrl+C or terminate asks the agent to stop cleanly."""

    previous = {}

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)

        if sig is None:
            continue

        try:
            previous[sig] = signal.signal(
                sig,
                lambda *_: agent.stop(),
            )
        except ValueError:
            # Signal handlers can only be installed from the main thread.
            pass

    return previous


def main(
    argv: list[str] | None = None,
    tracker: Tracker | None = None,
    token_store: TokenStore | None = None,
    input_fn: Callable[[str], str] = input,
    password_fn: Callable[[str], str] = getpass.getpass,
) -> int:
    """Run a CLI command or start the desktop activity agent."""

    args = build_parser().parse_args(argv)

    try:
        settings = load_settings(args.data_dir)
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.debug:
        settings = replace(settings, log_level="DEBUG")

    # Login/logout/status print their own messages.
    log = setup_logging(
        settings,
        console=args.command == "run",
    )

    previous: dict = {}

    try:
        log.info(
            "attention-agent %s starting; data folder: %s",
            __version__,
            settings.data_dir,
        )

        if args.command != "run":
            return run_account_command(
                args.command,
                settings,
                token_store,
                input_fn,
                input_fn if args.show_password else password_fn,
            )

        if tracker is None:
            try:
                # Read window titles only when explicitly enabled in config.
                tracker = WindowTracker(
                    include_title=settings.store_window_titles
                )
            except TrackerUnavailable as exc:
                log.error("%s", exc)
                print(f"Error: {exc}", file=sys.stderr)
                return 3

        # Connect the authenticated API client to the agent's sync worker.
        api_client = None

        try:
            store = (
                token_store
                if token_store is not None
                else TokenStore()
            )
            api_client = ApiClient(settings.api_base_url, store)
        except TokenStoreUnavailable as exc:
            log.warning(
                "Secure token storage unavailable; "
                "running in local-only mode: %s",
                exc,
            )

        agent = Agent(
            settings,
            tracker,
            idle_provider=get_windows_idle_seconds,
            api_client=api_client,
        )

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
