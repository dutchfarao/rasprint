"""ESC/POS printer abstraction and Bluetooth connection verification."""
from __future__ import annotations

import logging
import os
import textwrap
import threading
from contextlib import contextmanager
from typing import Generator

import serial
from escpos.printer import Serial

logger = logging.getLogger(__name__)

DEVICE = "/dev/rfcomm0"
WIDTH = 48


def verify_connection(device: str = DEVICE) -> bool:
    """Return True if the RFCOMM serial device exists and is responsive."""
    if not os.path.exists(device):
        return False

    result: list[bool] = [False]

    def _try_open() -> None:
        try:
            s = serial.Serial(device, timeout=2)
            s.close()
            result[0] = True
        except Exception:
            pass

    thread = threading.Thread(target=_try_open, daemon=True)
    thread.start()
    thread.join(timeout=3)
    return result[0]


@contextmanager
def open_printer(device: str = DEVICE) -> Generator[Serial, None, None]:
    """Open and yield an ESC/POS Serial printer instance."""
    p = Serial(devfile=device, baudrate=9600, timeout=2)
    try:
        yield p
    finally:
        try:
            p.device.close()
        except Exception:
            pass


def print_separator(p: Serial) -> None:
    """Print a full-width dashed separator line."""
    p.set(align="left", bold=False)
    p.text("-" * WIDTH + "\n")


def print_centred(p: Serial, text: str) -> None:
    """Print text centred within WIDTH characters then reset to left-align."""
    p.set(align="center", bold=False)
    p.text(text + "\n")
    p.set(align="left", bold=False)


def print_wrapped(p: Serial, text: str, width: int = WIDTH) -> None:
    """Print text word-wrapped at width characters, preserving newlines."""
    for line in text.splitlines():
        for segment in textwrap.wrap(line, width) or [""]:
            p.text(segment + "\n")


def print_message(message: str, device: str = DEVICE) -> None:
    """Print an on-demand message with a decorative header and footer."""
    with open_printer(device) as p:
        p.ln(2)
        print_separator(p)
        print_centred(p, "[ MESSAGE FROM RASPUTIN ]")
        print_separator(p)
        p.ln(1)
        p.set(align="center", bold=False)
        print_wrapped(p, message)
        p.set(align="left", bold=False)
        p.ln(1)
        print_separator(p)
        print_centred(p, "xxx")
        print_separator(p)
        p.ln(4)
        p.cut()
