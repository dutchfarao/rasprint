"""APScheduler daily morning receipt job."""
from __future__ import annotations

import logging
import os
import socket
import threading
import time
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from receipt_printer import birthdays, ipc, news, printer, weather

logger = logging.getLogger(__name__)

TIMEZONE = "Europe/Amsterdam"

HEADER_ART = """
██████╗  █████╗ ██╗  ██╗ █████╗
██╔════╝██╔══██╗██║ ██╔╝██╔══██╗
█████╗  ███████║█████╔╝ ███████║
██╔══╝  ██╔══██║██╔═██╗ ██╔══██║
██║     ██║  ██║██║  ██╗██║  ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝

         ██████╗
        ██╔════╝
        ██║  ███╗
        ██║   ██║
        ╚██████╔╝
         ╚═════╝
"""
LOGS_DIR = Path.home() / "receipt_printer" / "logs"
MISSED_LOG = LOGS_DIR / "missed_prints.log"


RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 15

_print_lock = threading.Lock()


def _log_missed(reason: str = "printer unreachable") -> None:
    """Append a timestamped entry to missed_prints.log."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with MISSED_LOG.open("a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().isoformat()}] "
            f"Scheduled print missed — {reason}\n"
        )


def _print_section(p: object, title: str, content: str) -> None:
    """Print a titled section block with separators."""
    printer.print_separator(p)  # type: ignore[arg-type]
    p.set(bold=True, align="left")  # type: ignore[attr-defined]
    p.text(f"{title}\n")  # type: ignore[attr-defined]
    p.set(bold=False, align="left")  # type: ignore[attr-defined]
    printer.print_separator(p)  # type: ignore[arg-type]
    printer.print_wrapped(p, content)  # type: ignore[arg-type]


def _do_print(now: datetime) -> None:
    """Perform the actual print job; raises on any printer error."""
    weather_text = weather.fetch_weather()
    news_text = news.fetch_news()
    birthday_text = birthdays.format_birthdays()

    with printer.open_printer() as p:
        # --- Art header ---
        p.set(align="center", bold=False)
        for line in HEADER_ART.splitlines():
            p.text(line.center(printer.WIDTH) + "\n")

        # --- Header ---
        p.ln(1)
        printer.print_separator(p)
        p.set(bold=True, align="center")
        p.text("GOOD MORNING!\n")
        p.set(bold=False, align="center")
        p.text(now.strftime("%A, %d %B %Y  %H:%M") + "\n")
        printer.print_separator(p)

        # --- Weather ---
        _print_section(p, "WEATHER - Maastricht", weather_text)

        # --- News ---
        printer.print_separator(p)
        _print_section(p, "TOP NEWS", news_text)

        # --- Birthdays ---
        printer.print_separator(p)
        _print_section(p, "BIRTHDAYS", birthday_text)

        # --- Footer ---
        printer.print_separator(p)
        printer.print_centred(p, "Have a great day!")
        printer.print_separator(p)
        p.ln(4)
        p.cut()


def daily_print_job() -> None:
    """Print the daily morning receipt; retries on transient errors before giving up."""
    if not printer.verify_connection():
        logger.warning("Printer not reachable at /dev/rfcomm0 — print job aborted.")
        _log_missed()
        return

    now = datetime.now()

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with _print_lock:
                _do_print(now)
            logger.info("Daily print succeeded on attempt %d.", attempt)
            return
        except Exception as exc:
            logger.warning(
                "Print attempt %d/%d failed: %s", attempt, RETRY_ATTEMPTS, exc
            )
            if attempt < RETRY_ATTEMPTS:
                logger.info("Retrying in %d seconds…", RETRY_DELAY_SECONDS)
                time.sleep(RETRY_DELAY_SECONDS)

    logger.error("All %d print attempts failed — logging as missed.", RETRY_ATTEMPTS)
    _log_missed(reason=f"serial error after {RETRY_ATTEMPTS} attempts")


def _handle_connection(conn: socket.socket) -> None:
    """Handle a single IPC client connection in its own thread."""
    try:
        data = b""
        conn.settimeout(10)
        while b"\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return
            data += chunk
        line = data.decode().strip()
        if not line.startswith("PRINT:"):
            conn.sendall(b"ERR:unknown command\n")
            return
        message = line[len("PRINT:"):]
        with _print_lock:
            printer.print_message(message)
        conn.sendall(b"OK\n")
    except Exception as exc:
        logger.warning("IPC print request failed: %s", exc)
        try:
            conn.sendall(f"ERR:{exc}\n".encode())
        except Exception:
            pass
    finally:
        conn.close()


def _run_socket_server() -> None:
    """Listen on the Unix socket and dispatch incoming print requests."""
    # Remove stale socket from a previous run
    try:
        os.unlink(ipc.SOCKET_PATH)
    except FileNotFoundError:
        pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(ipc.SOCKET_PATH)
    server.listen(5)
    logger.info("IPC socket listening at %s", ipc.SOCKET_PATH)
    while True:
        try:
            conn, _ = server.accept()
        except Exception:
            break
        t = threading.Thread(target=_handle_connection, args=(conn,), daemon=True)
        t.start()


def start_scheduler() -> None:
    """Start the blocking scheduler running daily_print_job at 08:00 Amsterdam time."""
    socket_thread = threading.Thread(target=_run_socket_server, daemon=True)
    socket_thread.start()

    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        daily_print_job,
        trigger=CronTrigger(hour=8, minute=0, timezone=TIMEZONE),
    )
    logger.info("Scheduler started — daily print at 08:00 %s.", TIMEZONE)
    try:
        scheduler.start()
    finally:
        try:
            os.unlink(ipc.SOCKET_PATH)
        except FileNotFoundError:
            pass
