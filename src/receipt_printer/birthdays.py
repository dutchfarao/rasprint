"""Birthday file parser and today's birthday checker."""
from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BIRTHDAYS_FILE = Path.home() / "receipt_printer" / "data" / "birthdays.txt"


def _parse_file(path: Path) -> list[tuple[str, date]]:
    """Parse birthdays.txt and return a list of (name, birthdate) tuples."""
    if not path.exists():
        logger.warning("Birthdays file not found: %s", path)
        return []

    entries: list[tuple[str, date]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            name, date_str = line.split(",", 1)
            bday = datetime.strptime(date_str.strip(), "%d-%m-%Y").date()
            entries.append((name.strip(), bday))
        except ValueError:
            logger.warning("Malformed entry on line %d: %r", line_no, line)
    return entries


def get_todays_birthdays(today: date | None = None) -> list[tuple[str, int]]:
    """Return (name, age) pairs for anyone whose birthday is today."""
    today = today or date.today()
    return [
        (name, today.year - bday.year)
        for name, bday in _parse_file(BIRTHDAYS_FILE)
        if bday.month == today.month and bday.day == today.day
    ]


def format_birthdays() -> str:
    """Return a formatted birthday section string for the receipt."""
    people = get_todays_birthdays()
    if not people:
        return "No birthdays today."

    lines: list[str] = []
    for name, age in people:
        lines += [
            "*" * 48,
            f"  Happy Birthday, {name}!".center(48),
            f"  Turning {age} today!".center(48),
            "*" * 48,
        ]
    return "\n".join(lines)
