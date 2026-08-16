#!/usr/bin/env python3
"""Small standard-library client for the authenticated ESC search function."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import sys
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, TextIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_TIMEOUT = 30.0
MAX_TIMEOUT = 120.0
DEFAULT_LIMIT = 5
MIN_YEAR = 2000
MAX_YEAR = 2100
MAX_QUERY_LENGTH = 1000
MAX_FILTER_LENGTH = 160
MAX_ENDPOINT_LENGTH = 2048
SEARCH_PATH = "/functions/v1/esc-search"

RESULT_FIELDS = (
    "project_identifier",
    "project_title",
    "project_summary",
    "results_platform_project_card",
    "action",
    "coordinator_country",
    "funding_year",
    "funding_amount",
    "similarity",
)


class SearchClientError(Exception):
    """An expected client, transport, or response error."""

    def __init__(self, message: str, code: str, exit_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


@dataclass(frozen=True)
class ClientConfig:
    base_url: str
    endpoint: str
    access_token: str
    api_key: str | None
    timeout: float


class JsonArgumentParser(argparse.ArgumentParser):
    """Keep command-line failures machine-readable and credential-free."""

    def error(self, message: str) -> None:
        error = {"error": f"invalid arguments: {message}", "code": "invalid_arguments"}
        sys.stderr.write(json.dumps(error, ensure_ascii=False) + "\n")
        raise SystemExit(2)


class NoRedirectHandler(HTTPRedirectHandler):
    """Reject redirects so authorization headers never reach another URL."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _open_without_redirects(request: Request, *, timeout: float) -> Any:
    return build_opener(NoRedirectHandler()).open(request, timeout=timeout)


def _parse_year(value: str) -> int:
    try:
        year = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("year must be an integer") from exc
    if year < MIN_YEAR or year > MAX_YEAR:
        raise argparse.ArgumentTypeError(
            f"year must be between {MIN_YEAR} and {MAX_YEAR}"
        )
    return year


def _parse_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("limit must be an integer") from exc
    if limit < 1 or limit > 20:
        raise argparse.ArgumentTypeError("limit must be between 1 and 20")
    return limit


def _parse_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number") from exc
    if timeout <= 0 or timeout > MAX_TIMEOUT:
        raise argparse.ArgumentTypeError(
            f"timeout must be greater than 0 and at most {MAX_TIMEOUT:g} seconds"
        )
    return timeout


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description="Search authenticated ESC project precedents through Supabase."
    )
    parser.add_argument("--query", required=True, help="Search text.")
    parser.add_argument("--country", help="Optional coordinator country filter.")
    parser.add_argument("--action", help="Optional ESC action filter.")
    parser.add_argument(
        "--year",
        type=_parse_year,
        help=f"Optional funding year ({MIN_YEAR}-{MAX_YEAR}).",
    )
    parser.add_argument(
        "--limit",
        type=_parse_limit,
        default=DEFAULT_LIMIT,
        help="Number of results to request (1-20; default: 5).",
    )
    parser.add_argument(
        "--endpoint",
        help="Override the search endpoint. Credentials are still read from the environment.",
    )
    parser.add_argument(
        "--timeout",
        type=_parse_timeout,
        default=DEFAULT_TIMEOUT,
        help=f"Network timeout in seconds (0-{MAX_TIMEOUT:g}; default: {DEFAULT_TIMEOUT:g}).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print successful JSON output.",
    )
    return parser


def _env_value(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _credential_values() -> tuple[str, ...]:
    values = []
    for name in ("ESC_SUPABASE_ACCESS_TOKEN", "ESC_SUPABASE_API_KEY"):
        value = _env_value(name)
        if value:
            values.append(value)
    return tuple(values)


def redact_text(text: str, secrets: Sequence[str]) -> str:
    """Replace configured credential values before anything reaches a stream."""

    redacted = text
    for secret in sorted({secret for secret in secrets if secret}, key=len, reverse=True):
        candidates = {
            secret,
            json.dumps(secret, ensure_ascii=False)[1:-1],
            json.dumps(secret)[1:-1],
        }
        for candidate in sorted(candidates, key=len, reverse=True):
            if candidate:
                redacted = redacted.replace(candidate, "[REDACTED]")
    return redacted


def _validate_text(value: Any, name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise SearchClientError(f"{name} must be text.", "invalid_input", 2)
    if not value.strip():
        raise SearchClientError(f"{name} must not be empty.", "invalid_input", 2)
    if len(value) > max_length:
        raise SearchClientError(
            f"{name} must be at most {max_length} characters.", "invalid_input", 2
        )
    if any(ord(character) < 32 and character not in "\t" for character in value):
        raise SearchClientError(
            f"{name} contains an unsupported control character.", "invalid_input", 2
        )
    return value.strip()


def _validate_optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _validate_text(value, name, MAX_FILTER_LENGTH)


def _validate_country(value: Any) -> str | None:
    if value is None:
        return None
    country = _validate_text(value, "country", MAX_FILTER_LENGTH).upper()
    if len(country) != 2 or not country.isascii() or not country.isalpha():
        raise SearchClientError(
            "country must be a two-letter code such as DE.",
            "invalid_input",
            2,
        )
    return country


def _validate_limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 20:
        raise SearchClientError("limit must be an integer between 1 and 20.", "invalid_input", 2)
    return value


def _validate_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise SearchClientError("year must be an integer.", "invalid_input", 2)
    if value < MIN_YEAR or value > MAX_YEAR:
        raise SearchClientError(
            f"year must be between {MIN_YEAR} and {MAX_YEAR}.", "invalid_input", 2
        )
    return value


def _validate_timeout(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SearchClientError("timeout must be a number.", "invalid_input", 2)
    timeout = float(value)
    if timeout <= 0 or timeout > MAX_TIMEOUT:
        raise SearchClientError(
            f"timeout must be greater than 0 and at most {MAX_TIMEOUT:g} seconds.",
            "invalid_input",
            2,
        )
    return timeout


def _is_loopback_host(hostname: str) -> bool:
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _validate_url(value: Any, name: str, *, base: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SearchClientError(f"{name} must be a non-empty URL.", "invalid_config", 2)
    value = value.strip()
    if len(value) > MAX_ENDPOINT_LENGTH:
        raise SearchClientError(
            f"{name} is too long.", "invalid_config", 2
        )
    if any(character.isspace() for character in value):
        raise SearchClientError(f"{name} must not contain whitespace.", "invalid_config", 2)
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError as exc:
        raise SearchClientError(f"{name} is not a valid URL.", "invalid_config", 2) from exc
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not hostname:
        raise SearchClientError(
            f"{name} must use an http or https URL.", "invalid_config", 2
        )
    if parsed.username is not None or parsed.password is not None:
        raise SearchClientError(
            f"{name} must not include credentials in the URL.", "invalid_config", 2
        )
    if parsed.query or parsed.fragment:
        raise SearchClientError(
            f"{name} must not include a query string or fragment.", "invalid_config", 2
        )
    loopback = _is_loopback_host(hostname)
    if parsed.scheme == "http" and not loopback:
        raise SearchClientError(
            f"{name} must use HTTPS outside local loopback development.",
            "invalid_config",
            2,
        )
    if not loopback and not hostname.lower().endswith(".supabase.co"):
        raise SearchClientError(
            f"{name} must use a Supabase project host.",
            "invalid_config",
            2,
        )
    if base and parsed.path not in {"", "/"}:
        raise SearchClientError(
            f"{name} must be a Supabase project URL without a path.", "invalid_config", 2
        )
    if not base and parsed.path != SEARCH_PATH:
        raise SearchClientError(
            f"{name} must point to {SEARCH_PATH}.",
            "invalid_config",
            2,
        )
    return value.rstrip("/")


def _validate_endpoint_for_base(endpoint: str, name: str, base_url: str) -> str:
    endpoint = _validate_url(endpoint, name)
    endpoint_parts = urlsplit(endpoint)
    base_parts = urlsplit(base_url)
    if (
        endpoint_parts.scheme != base_parts.scheme
        or endpoint_parts.hostname != base_parts.hostname
        or endpoint_parts.port != base_parts.port
    ):
        raise SearchClientError(
            f"{name} must use the same origin as ESC_SUPABASE_URL.",
            "invalid_config",
            2,
        )
    return endpoint


def _resolve_endpoint(cli_endpoint: str | None, base_url: str) -> str:
    if cli_endpoint is not None:
        return _validate_endpoint_for_base(cli_endpoint, "--endpoint", base_url)

    configured_endpoint = _env_value("ESC_SEARCH_ENDPOINT")
    if configured_endpoint:
        return _validate_endpoint_for_base(
            configured_endpoint,
            "ESC_SEARCH_ENDPOINT",
            base_url,
        )

    return f"{base_url}{SEARCH_PATH}"


def _resolve_config(args: argparse.Namespace) -> ClientConfig:
    base_url_value = _env_value("ESC_SUPABASE_URL")
    if not base_url_value:
        raise SearchClientError(
            "ESC_SUPABASE_URL is required.", "invalid_config", 2
        )
    base_url = _validate_url(base_url_value, "ESC_SUPABASE_URL", base=True)
    access_token = _env_value("ESC_SUPABASE_ACCESS_TOKEN")
    if not access_token:
        raise SearchClientError(
            "ESC_SUPABASE_ACCESS_TOKEN is required.", "missing_access_token", 2
        )
    api_key = _env_value("ESC_SUPABASE_API_KEY")
    return ClientConfig(
        base_url=base_url,
        endpoint=_resolve_endpoint(args.endpoint, base_url),
        access_token=access_token,
        api_key=api_key,
        timeout=_validate_timeout(args.timeout),
    )


def _build_payload(
    *,
    query: str,
    country: str | None,
    action: str | None,
    year: int | None,
    limit: int,
) -> dict[str, Any]:
    return {
        "query": _validate_text(query, "query", MAX_QUERY_LENGTH),
        "match_count": _validate_limit(limit),
        "filter_country": _validate_country(country),
        "filter_action": _validate_optional_text(action, "action"),
        "filter_funding_year": _validate_year(year),
    }


def _response_status(response: Any) -> int:
    status = getattr(response, "status", None)
    if status is None:
        getcode = getattr(response, "getcode", None)
        status = getcode() if callable(getcode) else None
    if isinstance(status, bool) or not isinstance(status, int):
        raise SearchClientError("The search response had no valid HTTP status.", "http_error", 3)
    return status


def _reject_nonstandard_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _validate_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SearchClientError("The search response must be a JSON object.", "malformed_response", 4)

    required = {"query", "model", "filters", "count", "results"}
    missing = sorted(required.difference(payload))
    if missing:
        raise SearchClientError(
            "The search response is missing required fields: " + ", ".join(missing) + ".",
            "malformed_response",
            4,
        )
    if not isinstance(payload["query"], str):
        raise SearchClientError("The search response has an invalid query field.", "malformed_response", 4)
    if not isinstance(payload["model"], str):
        raise SearchClientError("The search response has an invalid model field.", "malformed_response", 4)
    if not isinstance(payload["filters"], dict):
        raise SearchClientError("The search response has invalid filters.", "malformed_response", 4)
    count = payload["count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise SearchClientError("The search response has an invalid count.", "malformed_response", 4)

    results = payload["results"]
    if not isinstance(results, list):
        raise SearchClientError("The search response results must be a list.", "malformed_response", 4)
    if count != len(results):
        raise SearchClientError(
            "The search response count does not match its results.",
            "malformed_response",
            4,
        )
    for index, result in enumerate(results):
        if not isinstance(result, dict):
            raise SearchClientError(
                f"The search response result at index {index} is not an object.",
                "malformed_response",
                4,
            )
        missing_result_fields = [field for field in RESULT_FIELDS if field not in result]
        if missing_result_fields:
            raise SearchClientError(
                f"The search response result at index {index} is missing required fields: "
                + ", ".join(missing_result_fields)
                + ".",
                "malformed_response",
                4,
            )
    return payload


def search_esc(
    *,
    base_url: str,
    endpoint: str,
    access_token: str,
    api_key: str | None,
    query: str,
    country: str | None = None,
    action: str | None = None,
    year: int | None = None,
    limit: int = DEFAULT_LIMIT,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Execute one authenticated search request and validate its JSON shape."""

    base_url = _validate_url(base_url, "base_url", base=True)
    endpoint = _validate_endpoint_for_base(endpoint, "endpoint", base_url)
    access_token = _validate_text(access_token, "access token", MAX_ENDPOINT_LENGTH)
    if api_key is not None:
        api_key = _validate_text(api_key, "API key", MAX_ENDPOINT_LENGTH)
    timeout = _validate_timeout(timeout)
    request_payload = _build_payload(
        query=query,
        country=country,
        action=action,
        year=year,
        limit=limit,
    )
    encoded_payload = json.dumps(
        request_payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    if api_key:
        headers["apikey"] = api_key

    request = Request(endpoint, data=encoded_payload, headers=headers, method="POST")
    try:
        with _open_without_redirects(request, timeout=timeout) as response:
            status = _response_status(response)
            raw_body = response.read()
    except HTTPError as exc:
        raise SearchClientError(
            f"The search request failed with HTTP status {exc.code}.", "http_error", 3
        ) from None
    except (socket.timeout, TimeoutError):
        raise SearchClientError("The search request timed out.", "timeout", 3) from None
    except (URLError, OSError):
        raise SearchClientError("The search request could not reach the endpoint.", "network_error", 3) from None

    if status < 200 or status >= 300:
        raise SearchClientError(
            f"The search request failed with HTTP status {status}.", "http_error", 3
        )
    if not isinstance(raw_body, bytes):
        raise SearchClientError("The search response body was not bytes.", "malformed_response", 4)
    try:
        decoded_body = raw_body.decode("utf-8")
        decoded_payload = json.loads(
            decoded_body, parse_constant=_reject_nonstandard_json_constant
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        raise SearchClientError("The search response was not valid JSON.", "malformed_response", 4) from None
    return _validate_response(decoded_payload)


def _write_json(
    value: Mapping[str, Any],
    stream: TextIO,
    *,
    pretty: bool,
    secrets: Sequence[str],
) -> None:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        allow_nan=False,
    )
    stream.write(redact_text(serialized, secrets) + "\n")


def _write_error(error: SearchClientError, secrets: Sequence[str]) -> None:
    _write_json(
        {"error": str(error), "code": error.code},
        sys.stderr,
        pretty=False,
        secrets=secrets,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    secrets = _credential_values()
    try:
        config = _resolve_config(args)
        response = search_esc(
            base_url=config.base_url,
            endpoint=config.endpoint,
            access_token=config.access_token,
            api_key=config.api_key,
            query=args.query,
            country=args.country,
            action=args.action,
            year=args.year,
            limit=args.limit,
            timeout=config.timeout,
        )
    except SearchClientError as error:
        _write_error(error, secrets)
        return error.exit_code

    _write_json(response, sys.stdout, pretty=args.pretty, secrets=secrets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
