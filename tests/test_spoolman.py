"""Spoolman client: success path, network failure, schema validation."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from print_outline.spoolman import SpoolmanClient, _parse_endpoint, _parse_spool

HTTPS_DEFAULT_PORT = 443
EXAMPLE_HTTP_PORT = 7912
EXAMPLE_SPOOL_ID = 12
NOT_FOUND_STATUS = 404


def _build_response(body: dict[str, Any], status: int = 200) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.read.return_value = json.dumps(body).encode("utf-8")
    return response


def _build_connection(response: MagicMock) -> MagicMock:
    connection = MagicMock()
    connection.getresponse.return_value = response
    return connection


def test_endpoint_parsing_https() -> None:
    endpoint = _parse_endpoint("https://example.com/spoolman/api/v1")
    assert endpoint.use_https is True
    assert endpoint.host == "example.com"
    assert endpoint.port == HTTPS_DEFAULT_PORT
    assert endpoint.base_path == "/spoolman/api/v1"


def test_endpoint_parsing_http_with_port() -> None:
    endpoint = _parse_endpoint(f"http://localhost:{EXAMPLE_HTTP_PORT}/api/v1")
    assert endpoint.use_https is False
    assert endpoint.host == "localhost"
    assert endpoint.port == EXAMPLE_HTTP_PORT


def test_endpoint_rejects_bad_scheme() -> None:
    with pytest.raises(ValueError, match="must use http"):
        _parse_endpoint("file:///etc/passwd")


def test_endpoint_requires_host() -> None:
    with pytest.raises(ValueError, match="no host"):
        _parse_endpoint("https:///nope")


def test_fetch_success() -> None:
    payload = {
        "id": EXAMPLE_SPOOL_ID,
        "filament": {
            "name": "Galaxy Black",
            "material": "PLA",
            "color_hex": "1a1a1a",
            "vendor": {"name": "Bambu Lab"},
        },
    }
    connection = _build_connection(_build_response(payload))
    client = SpoolmanClient("https://example.com/api/v1", timeout_seconds=5)
    with patch.object(client, "_open_connection", return_value=connection):
        spool = client.fetch(EXAMPLE_SPOOL_ID)
    assert spool is not None
    assert spool.spool_id == EXAMPLE_SPOOL_ID
    assert spool.material == "PLA"
    assert spool.vendor_name == "Bambu Lab"
    assert spool.color_hex == "1a1a1a"


def test_fetch_caches_per_run() -> None:
    payload = {"id": 7, "filament": {"name": "x", "material": "PLA"}}
    connection = _build_connection(_build_response(payload))
    client = SpoolmanClient("https://example.com/api/v1", timeout_seconds=5)
    with patch.object(client, "_open_connection", return_value=connection) as opener:
        client.fetch(7)
        client.fetch(7)
        client.fetch(7)
    assert opener.call_count == 1


def test_fetch_handles_timeout_gracefully() -> None:
    client = SpoolmanClient("https://example.com/api/v1", timeout_seconds=1)
    failing_connection = MagicMock()
    failing_connection.request.side_effect = TimeoutError("simulated")
    with patch.object(client, "_open_connection", return_value=failing_connection):
        spool = client.fetch(99)
    assert spool is None


def test_fetch_handles_non_200() -> None:
    client = SpoolmanClient("https://example.com/api/v1", timeout_seconds=1)
    connection = _build_connection(_build_response({}, status=NOT_FOUND_STATUS))
    with patch.object(client, "_open_connection", return_value=connection):
        spool = client.fetch(NOT_FOUND_STATUS)
    assert spool is None


def test_parse_spool_handles_missing_filament() -> None:
    spool = _parse_spool({"id": 1}, fallback_id=1)
    assert spool is not None
    assert spool.material == ""
    assert spool.vendor_name == ""


def test_parse_spool_returns_none_on_garbage() -> None:
    assert _parse_spool("not a dict", fallback_id=1) is None
