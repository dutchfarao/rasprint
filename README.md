# receipt-printer

Epson TM-M30II Bluetooth thermal receipt printer controller for Raspberry Pi 5.

Prints a daily morning receipt at 08:00 (Amsterdam time) containing weather,
top news, and birthday alerts. Also supports on-demand printing from the CLI.

---

## Hardware prerequisites

- Raspberry Pi 5 running Raspberry Pi OS (Debian Bookworm, ARM64)
- Epson TM-M30II printer paired and trusted via `bluetoothctl`
- RFCOMM binding configured (`/dev/rfcomm0` pointing to the printer's MAC)
- `rfcomm.service` systemd unit enabled (see the Bluetooth setup guide)

---

## Installation

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # or open a new terminal
```

### 2. Clone / copy the project

```bash
cd ~/receipt_printer   # project must live here (paths are anchored to ~/)
```

### 3. Create the virtual environment and install

```bash
uv venv
uv pip install -e .
```

### 4. (Optional) Set a NewsAPI key for better news coverage

```bash
echo "NEWS_API_KEY=your_key_here" >> ~/.env
```

If the variable is absent the scheduler falls back to Google News RSS (no key needed).

---

## Usage

### On-demand print

```bash
.venv/bin/receipt-printer print "Your message here"
```

Multi-line messages work too:

```bash
.venv/bin/receipt-printer print $'Line one\nLine two\nLine three'
```

The command verifies the Bluetooth connection before sending. If the printer
is unreachable it exits with a non-zero code and prints an error to stderr.

### Start the daily scheduler (foreground)

```bash
.venv/bin/receipt-printer start-scheduler
```

Prints a morning receipt every day at 08:00 Europe/Amsterdam. If the printer
is unreachable at trigger time, the missed print is logged to
`~/receipt_printer/logs/missed_prints.log`.

---

## Adding birthdays

Edit `~/receipt_printer/data/birthdays.txt`. One entry per line:

```
Name, DD-MM-YYYY
```

Example:

```
Test Friend, 26-03-1997
Alice Smith, 01-01-1990
```

The scheduler checks this file every morning and prints a celebratory banner
if today matches anyone's birthday (month and day only; year is used for age).

---

## Setting up the systemd service

Install the unit file and enable it:

```bash
sudo cp ~/receipt_printer/receipt-printer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable receipt-printer
sudo systemctl start receipt-printer
```

Check status and logs:

```bash
sudo systemctl status receipt-printer
journalctl -u receipt-printer -f
```

---

## Troubleshooting the Bluetooth connection

**Check if the printer is paired and trusted:**

```bash
bluetoothctl info 00:01:90:6D:80:A2
```

Look for `Paired: yes`, `Trusted: yes`.

**Check the RFCOMM binding:**

```bash
rfcomm show rfcomm0
```

Should show `connected` or `clean` (clean means bound and ready to connect on demand).

**Manually rebind if /dev/rfcomm0 is missing:**

```bash
sudo rfcomm bind 0 00:01:90:6D:80:A2 1
```

**Check the rfcomm.service is running:**

```bash
sudo systemctl status rfcomm
```

**Test the connection directly:**

```bash
printf "\x1b\x40Hello\n\n\n\x1d\x56\x00" > /dev/rfcomm0
```

If nothing prints or the command hangs, the printer is off or out of Bluetooth range.

**Missed print log:**

```bash
cat ~/receipt_printer/logs/missed_prints.log
```
