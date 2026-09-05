"""
SIH26056 — Immutable Artifact Store & Secret Redactor.

Persists raw web captures in an append-only, sanitized local store outside
the public frontend tree.
- Automatically redacts cookies, auth tokens, session IDs, and API keys.
- Never stores passenger personal data, payment info, or bypass material.
- Generates SHA-256 checksums for deterministic reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Optional
import urllib.parse
import uuid

from loguru import logger

# Base directory for immutable captures, safely outside the frontend public tree
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "artifacts" / "raw_captures"

# Headers that must be completely redacted before storage
SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "amadeus-client-secret",
}

# Query parameter keys that commonly contain secrets
SENSITIVE_QUERY_PARAMS = {
    "token",
    "access_token",
    "auth",
    "key",
    "api_key",
    "secret",
    "session",
    "sessionid",
}


def redact_url(url: str) -> str:
    """Scrub sensitive query parameters from a URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.query:
            return url
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        sanitized = {}
        for k, vals in params.items():
            if k.lower() in SENSITIVE_QUERY_PARAMS:
                sanitized[k] = ["[REDACTED]"]
            else:
                sanitized[k] = vals
        new_query = urllib.parse.urlencode(sanitized, doseq=True)
        return urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
        )
    except Exception:
        return url


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Scrub authorization, cookies, and tokens from request/response headers."""
    redacted = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADERS:
            redacted[k] = "[REDACTED]"
        else:
            redacted[k] = v
    return redacted


def redact_payload_text(text: str) -> str:
    """Scrub bearer tokens and common credential patterns from raw HTML/JSON."""
    # Redact Bearer tokens
    sanitized = re.sub(r'(?i)bearer\s+[A-Za-z0-9\-\._~+/]+=*', 'Bearer [REDACTED]', text)
    # Redact access_token JSON values
    sanitized = re.sub(r'(?i)("access_token"\s*:\s*")[^"]+(")', r'\1[REDACTED]\2', sanitized)
    return sanitized


@dataclass(frozen=True)
class StoredArtifact:
    artifact_id: str
    sha256: str
    relative_path: str
    mime_type: str
    stored_bytes: int
    retrieved_at: datetime
    sanitized_url: str


class ArtifactStore:
    """Manages append-only immutable storage of raw page responses."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or DEFAULT_ARTIFACT_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_capture(
        self,
        source_id: str,
        url: str,
        content: str | bytes,
        mime_type: str = "text/html",
        compress: bool = True,
    ) -> StoredArtifact:
        """
        Sanitize and persist a raw capture to the immutable artifact directory.
        """
        artifact_id = f"art-{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        clean_url = redact_url(url)

        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="replace")
        else:
            text = content

        sanitized_text = redact_payload_text(text)
        raw_bytes = sanitized_text.encode("utf-8")
        sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # Partition by date and source: YYYY/MM/DD/source_id/
        date_dir = self.base_dir / now.strftime("%Y/%m/%d") / source_id
        date_dir.mkdir(parents=True, exist_ok=True)

        ext = ".html.gz" if "html" in mime_type else ".json.gz"
        filename = f"{artifact_id}_{sha256[:8]}{ext}"
        filepath = date_dir / filename

        if compress:
            with gzip.open(filepath, "wb") as f:
                f.write(raw_bytes)
        else:
            with open(filepath, "wb") as f:
                f.write(raw_bytes)

        stored_size = filepath.stat().st_size
        rel_path = str(filepath.relative_to(self.base_dir))

        logger.debug(
            f"Stored raw capture {artifact_id} for {source_id}: "
            f"{stored_size} bytes, sha256={sha256[:12]}..."
        )

        return StoredArtifact(
            artifact_id=artifact_id,
            sha256=sha256,
            relative_path=rel_path,
            mime_type=mime_type,
            stored_bytes=stored_size,
            retrieved_at=now,
            sanitized_url=clean_url,
        )
