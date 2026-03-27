"""User-configurable settings for the receipt printer."""
from __future__ import annotations

# --- Assistant identity ---
ASSISTANT_NAME = "RASPUTIN"  # Displayed in print_message header
ASSISTANT_CLOSING = "xxx"    # Displayed in print_message footer

# --- Location ---
LOCATION_NAME = "Maastricht"  # Label shown in daily weather section
LATITUDE = 50.8514
LONGITUDE = 5.6910

# --- Scheduler ---
TIMEZONE = "Europe/Amsterdam"
DAILY_PRINT_HOUR = 8
DAILY_PRINT_MINUTE = 0

# --- Greetings ---
MORNING_GREETING = "GOOD MORNING!"
FAREWELL = "Have a great day!"

# --- Hardware ---
BLUETOOTH_DEVICE = "/dev/rfcomm0"
PAPER_WIDTH = 48

# --- Retry logic ---
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 15
