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
from escpos.printer import Serial

from receipt_printer import birthdays, config, ipc, news, printer, weather

logger = logging.getLogger(__name__)

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

_print_lock = threading.Lock()


def _log_missed(reason: str = "printer unreachable") -> None:
    """Append a timestamped entry to missed_prints.log."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with MISSED_LOG.open("a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().isoformat()}] "
            f"Scheduled print missed — {reason}\n"
        )


def _print_section(p: Serial, title: str, content: str) -> None:
    """Print a titled section block with separators."""
    printer.print_separator(p)
    p.set(bold=True, align="left")
    p.text(f"{title}\n")
    p.set(bold=False, align="left")
    printer.print_separator(p)
    printer.print_wrapped(p, content)


def _do_print(now: datetime, weather_text: str, news_text: str, birthday_text: str) -> None:
    """Perform the actual print job; raises on any printer error."""
    with printer.open_printer() as p:
        # --- Art header ---
        p.set(align="center", bold=False)
        for line in HEADER_ART.splitlines():
            p.text(line.center(config.PAPER_WIDTH) + "\n")

        # --- Header ---
        p.ln(1)
        printer.print_separator(p)
        p.set(bold=True, align="center")
        p.text(f"{config.MORNING_GREETING}\n")
        p.set(bold=False, align="center")
        p.text(now.strftime("%A, %d %B %Y  %H:%M") + "\n")
        printer.print_separator(p)

        # --- Weather ---
        _print_section(p, f"WEATHER - {config.LOCATION_NAME}", weather_text)

        # --- News ---
        _print_section(p, "TOP NEWS", news_text)

        # --- Birthdays ---
        _print_section(p, "BIRTHDAYS", birthday_text)

        # --- Footer ---
        printer.print_separator(p)
        printer.print_centred(p, config.FAREWELL)
        printer.print_separator(p)
        p.ln(4)
        p.cut()


def daily_print_job() -> None:
    """Print the daily morning receipt; retries connection failures before giving up."""
    now = datetime.now()

    # Fetch data once, outside the retry loop — these handle their own exceptions
    # and must not re-run on retry (stale data is fine; duplicate prints are not).
    weather_text = weather.fetch_weather()
    news_text = news.fetch_news()
    birthday_text = birthdays.format_birthdays()

    for attempt in range(1, config.RETRY_ATTEMPTS + 1):
        if not printer.verify_connection():
            logger.warning(
                "Printer not reachable at %s (attempt %d/%d).",
                config.BLUETOOTH_DEVICE, attempt, config.RETRY_ATTEMPTS,
            )
            if attempt < config.RETRY_ATTEMPTS:
                logger.info("Retrying in %d seconds…", config.RETRY_DELAY_SECONDS)
                time.sleep(config.RETRY_DELAY_SECONDS)
                continue
            _log_missed()
            return

        try:
            with _print_lock:
                _do_print(now, weather_text, news_text, birthday_text)
            logger.info("Daily print succeeded on attempt %d.", attempt)
            return
        except Exception as exc:
            # Do NOT retry after printing has started — ESC/POS data already sent
            # to the printer cannot be recalled; retrying would duplicate the output.
            logger.error("Print failed on attempt %d: %s — aborting to avoid duplicates.", attempt, exc)
            _log_missed(reason=f"print error: {exc}")
            return

    _log_missed(reason="printer unreachable after all attempts")


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
        if line.startswith("PRINT_RAW:"):
            message = line[len("PRINT_RAW:"):]
            with_header = False
        elif line.startswith("PRINT:"):
            message = line[len("PRINT:"):]
            with_header = True
        else:
            conn.sendall(b"ERR:unknown command\n")
            return
        with _print_lock:
            printer.print_message(message, with_header=with_header)
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
    """Start the blocking scheduler running daily_print_job at the configured time."""
    socket_thread = threading.Thread(target=_run_socket_server, daemon=True)
    socket_thread.start()

    scheduler = BlockingScheduler(timezone=config.TIMEZONE)
    scheduler.add_job(
        daily_print_job,
        trigger=CronTrigger(
            hour=config.DAILY_PRINT_HOUR,
            minute=config.DAILY_PRINT_MINUTE,
            timezone=config.TIMEZONE,
        ),
    )
    logger.info(
        "Scheduler started — daily print at %02d:%02d %s.",
        config.DAILY_PRINT_HOUR,
        config.DAILY_PRINT_MINUTE,
        config.TIMEZONE,
    )
    try:
        scheduler.start()
    finally:
        try:
            os.unlink(ipc.SOCKET_PATH)
        except FileNotFoundError:
            pass
