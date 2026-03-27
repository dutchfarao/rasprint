"""CLI entry point for the receipt-printer tool."""
from __future__ import annotations

import argparse
import logging
import os
import sys

from receipt_printer import config, ipc, printer, scheduler

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _cmd_print(args: argparse.Namespace) -> None:
    """Print an on-demand message, routing through the daemon if it is running."""
    if os.path.exists(ipc.SOCKET_PATH):
        try:
            ipc.send_print_request(args.message, with_header=not args.no_header)
            return
        except Exception as exc:
            print(f"ERROR: Daemon rejected print request — {exc}", file=sys.stderr)
            sys.exit(1)

    # Daemon not running — print directly
    if not printer.verify_connection():
        print(
            f"ERROR: Printer not reachable at {config.BLUETOOTH_DEVICE} — print job aborted.",
            file=sys.stderr,
        )
        sys.exit(1)
    printer.print_message(args.message, with_header=not args.no_header)


def _cmd_start_scheduler(_args: argparse.Namespace) -> None:
    """Start the blocking daily scheduler (runs forever, suitable for systemd)."""
    scheduler.start_scheduler()


def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        prog="receipt-printer",
        description="Epson TM-M30II Bluetooth receipt printer controller",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    print_cmd = subparsers.add_parser("print", help="Print an on-demand message")
    print_cmd.add_argument("message", help="Text to print (supports multi-line)")
    print_cmd.add_argument(
        "--no-header", action="store_true", help="Print without decorative header/footer"
    )
    print_cmd.set_defaults(func=_cmd_print)

    sched_cmd = subparsers.add_parser(
        "start-scheduler", help="Start the daily 08:00 morning receipt scheduler"
    )
    sched_cmd.set_defaults(func=_cmd_start_scheduler)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
