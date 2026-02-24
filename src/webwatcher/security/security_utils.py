import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


def validate_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.scheme in ALLOWED_SCHEMES and parsed.netloc)


def enforce_domain(url: str, allowed_domain: str) -> bool:
    return urlparse(url).netloc.lower().endswith(allowed_domain.lower())


def _is_private_or_local_ip(ip: str) -> bool:
    parsed_ip = ipaddress.ip_address(ip)
    return (
        parsed_ip.is_private
        or parsed_ip.is_loopback
        or parsed_ip.is_link_local
        or parsed_ip.is_multicast
        or parsed_ip.is_reserved
    )


def prevent_ssrf(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = info[4][0]
        if _is_private_or_local_ip(ip):
            return False
    return True


def validate_file_size(size_bytes: int | None, max_mb: int) -> bool:
    if size_bytes is None:
        return True
    return size_bytes <= max_mb * 1024 * 1024


def validate_content_type(content_type: str | None, allow: set[str]) -> bool:
    if not content_type:
        return False
    normalized = content_type.split(";")[0].strip().lower()
    return normalized in {item.lower() for item in allow}

