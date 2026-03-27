Print a message to the thermal receipt printer. Unless the user explicitly says "no art" or "no ascii", always prepend relevant ASCII art to the message.

## Step 1 — Compose the message

Take the user's input from $ARGUMENTS.

Strip any leading `--no-header` or `--no-art` flags before using the text as message content.

Unless `--no-art` was passed, generate a short piece of ASCII art that fits the message theme (a few lines, max ~40 chars wide). Prepend it to the message with a blank line between art and text. Keep it tasteful and receipt-sized.

Example for "Good morning!":
```
   ( (
    ) )
  ........
  |      |]
  \      /
   `----'

Good morning!
```

## Step 2 — Run the CLI

If `--no-header` was passed, use:
```bash
cd /home/dutchfarao/receipt_printer && .venv/bin/receipt-printer print --no-header "<composed message>"
```

Otherwise (default):
```bash
cd /home/dutchfarao/receipt_printer && .venv/bin/receipt-printer print "<composed message>"
```

## Step 3 — Report result

If exit 0: confirm it printed.
If error: show the error and suggest `ls /dev/rfcomm*` to check Bluetooth.

## Flag reference
- `/printer Hello!` — ASCII art + header (RASPUTIN banner)
- `/printer --no-header Hello!` — ASCII art, no header/footer decoration
- `/printer --no-art Hello!` — no ASCII art, with header
- `/printer --no-header --no-art Hello!` — plain text only
