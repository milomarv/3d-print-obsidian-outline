"""Tiny stdlib client for the Spoolman REST API.

Built on `http.client` rather than `urllib.request` so the scheme is
explicitly chosen (HTTP vs HTTPS) — there is no path through which a
file:// or other unexpected scheme could reach a network call.

Per-run in-process cache so the same spool ID is not fetched twice.
Network failures are non-fatal — they degrade the rendered table to a
bare ID list rather than aborting the run.
"""

from __future__ import annotations

import http.client
import json
import logging
import urllib.parse
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_HTTP_OK = 200


@dataclass(frozen=True)
class Spool:
    """Subset of a Spoolman spool record needed to render a Filaments table."""

    spool_id: int
    material: str
    color_hex: str
    filament_name: str
    vendor_name: str

    @property
    def display_name(self) -> str:
        parts = [self.vendor_name, self.material, self.filament_name]
        return " — ".join(p for p in parts if p)


@dataclass(frozen=True)
class _Endpoint:
    use_https: bool
    host: str
    port: int
    base_path: str


class SpoolmanClient:
    """Single-run client. Holds an in-memory cache keyed by spool ID."""

    def __init__(self, base_url: str, *, timeout_seconds: int) -> None:
        self._endpoint = _parse_endpoint(base_url)
        self._timeout = timeout_seconds
        self._cache: dict[int, Spool | None] = {}

    def fetch(self, spool_id: int) -> Spool | None:
        """Return the spool, or None when unreachable / not found."""
        if spool_id in self._cache:
            return self._cache[spool_id]
        result = self._fetch_uncached(spool_id)
        self._cache[spool_id] = result
        return result

    def _fetch_uncached(self, spool_id: int) -> Spool | None:
        path = f"{self._endpoint.base_path}/spool/{spool_id}"
        connection = self._open_connection()
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            if response.status != _HTTP_OK:
                logger.info("spoolman returned status=%d for id=%s", response.status, spool_id)
                return None
            raw = response.read().decode("utf-8")
        except (TimeoutError, OSError, http.client.HTTPException) as exc:
            logger.info("spoolman fetch failed for id=%s: %s", spool_id, exc)
            return None
        finally:
            connection.close()
        try:
            payload: object = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.info("spoolman returned non-JSON for id=%s: %s", spool_id, exc)
            return None
        return _parse_spool(payload, spool_id)

    def _open_connection(self) -> http.client.HTTPConnection:
        if self._endpoint.use_https:
            return http.client.HTTPSConnection(
                self._endpoint.host,
                self._endpoint.port,
                timeout=self._timeout,
            )
        return http.client.HTTPConnection(
            self._endpoint.host,
            self._endpoint.port,
            timeout=self._timeout,
        )


def _parse_endpoint(base_url: str) -> _Endpoint:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        msg = f"spoolman base_url must use http(s); got: {parsed.scheme!r}"
        raise ValueError(msg)
    if not parsed.hostname:
        msg = f"spoolman base_url has no host: {base_url!r}"
        raise ValueError(msg)
    use_https = parsed.scheme == "https"
    port = parsed.port if parsed.port is not None else (443 if use_https else 80)
    base_path = parsed.path.rstrip("/")
    return _Endpoint(use_https=use_https, host=parsed.hostname, port=port, base_path=base_path)


def _parse_spool(payload: object, fallback_id: int) -> Spool | None:
    if not isinstance(payload, dict):
        return None
    filament_raw = payload.get("filament")
    filament: dict[str, object] = filament_raw if isinstance(filament_raw, dict) else {}
    vendor_raw = filament.get("vendor")
    vendor: dict[str, object] = vendor_raw if isinstance(vendor_raw, dict) else {}
    spool_id_raw = payload.get("id", fallback_id)
    spool_id = int(spool_id_raw) if isinstance(spool_id_raw, int) else fallback_id
    return Spool(
        spool_id=spool_id,
        material=str(filament.get("material") or ""),
        color_hex=str(filament.get("color_hex") or ""),
        filament_name=str(filament.get("name") or ""),
        vendor_name=str(vendor.get("name") or ""),
    )
