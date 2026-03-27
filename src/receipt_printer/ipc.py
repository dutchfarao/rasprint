"""Unix socket IPC protocol for routing print requests to the running daemon."""
from __future__ import annotations

import socket

SOCKET_PATH = "/tmp/receipt-printer.sock"
_TIMEOUT = 30  # seconds — covers slow Bluetooth writes


def send_print_request(message: str, with_header: bool = True) -> None:
    """Send a print request to the running daemon and wait for acknowledgement.

    Raises RuntimeError if the daemon responds with an error or the connection
    fails.  The caller should fall back to direct printing if the socket does
    not exist at all.
    """
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(_TIMEOUT)
        sock.connect(SOCKET_PATH)
        prefix = "PRINT:" if with_header else "PRINT_RAW:"
        sock.sendall(f"{prefix}{message}\n".encode())
        response = b""
        while b"\n" not in response:
            chunk = sock.recv(256)
            if not chunk:
                break
            response += chunk
    line = response.decode().strip()
    if line.startswith("ERR:"):
        raise RuntimeError(line[4:])
    if line != "OK":
        raise RuntimeError(f"Unexpected daemon response: {line!r}")
