"""Network helpers for resolving client IP and host."""

import socket


def get_local_ip() -> str:
    """Best-effort local machine IP (used when no HTTP client is available)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def get_hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"


def extract_client_ip_from_headers(headers: dict[str, str], direct_client: str | None) -> str:
    forwarded = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = headers.get("x-real-ip") or headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if direct_client:
        return direct_client
    return get_local_ip()
