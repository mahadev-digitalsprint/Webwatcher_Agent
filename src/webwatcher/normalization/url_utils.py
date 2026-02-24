from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

TRACKING_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
}


def normalize_url(raw_url: str, base_url: str | None = None) -> str:
    url = raw_url.strip()
    if base_url:
        url = urljoin(base_url, url)
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    query_params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in TRACKING_KEYS]
    query = urlencode(sorted(query_params))
    fragment = ""
    return urlunparse((scheme, netloc, path.rstrip("/") or "/", "", query, fragment))


def same_domain(url_a: str, url_b: str) -> bool:
    return urlparse(url_a).netloc.lower() == urlparse(url_b).netloc.lower()

