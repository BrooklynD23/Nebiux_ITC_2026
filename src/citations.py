"""Citation URL normalization utilities.

Handles common URL inconsistencies found in the corpus index.json:
- ``http`` -> ``https``
- Percent-encoded tilde (``%7e`` / ``%7E``) -> ``~``
- Trailing-slash normalization (strip trailing ``/``)
- Lowercase scheme and host for canonical form
"""

from __future__ import annotations

from urllib.parse import unquote, urlparse, urlunparse


def normalize_url(raw_url: str) -> str:
    """Return a canonical form of *raw_url*.

    Parameters
    ----------
    raw_url:
        The URL as it appears in the corpus index.

    Returns
    -------
    str
        A normalized, canonical URL string.

    Examples
    --------
    >>> normalize_url("http://www.cpp.edu/path/")
    'https://www.cpp.edu/path'
    >>> normalize_url("https://www.cpp.edu/%7Efaculty/page")
    'https://www.cpp.edu/~faculty/page'
    """
    if not raw_url or not raw_url.strip():
        return raw_url

    # Decode percent-encoding first so %7e becomes ~
    decoded = unquote(raw_url.strip())

    parsed = urlparse(decoded)

    # Force https
    scheme = "https"

    # Lowercase the hostname
    netloc = (parsed.hostname or "").lower()
    if parsed.port and parsed.port not in (80, 443):
        netloc = f"{netloc}:{parsed.port}"

    # Strip trailing slash from path (but keep "/" for root)
    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"

    # Reassemble without query/fragment for canonical form
    canonical = urlunparse((scheme, netloc, path, "", parsed.query, ""))

    return canonical
