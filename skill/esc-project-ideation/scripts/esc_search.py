#!/usr/bin/env python3
"""Dependency-free CLI adapter for the ESC Supabase search Edge Function.

The HTTP/JSON contract in this file is *provisional*. The repository documents
the database RPC parameters but not the deployed Edge Function request body or
response shape. See references/esc-retrieval-adapter.md for the contract and
the narrow places to adapt it.

Security boundary:
  * HTTPS only; the configured URL must be an origin without userinfo/path.
  * One POST to /functions/v1/<ESC_SEARCH_FUNCTION>; redirects are refused.
  * Authentication comes from environment variables, never command arguments.
  * Service-role credentials and direct table access are not supported.
"""

from __future__ import annotations

import argparse
import http.client
import json
import math
import os
import re
import socket
import ssl
import sys
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, TextIO, Tuple
from urllib.parse import urlsplit, urlunsplit

ADAPTER_NAME = "esc-project-ideation/esc_search.py"
CONTRACT_VERSION = "provisional-v1"
DEFAULT_FUNCTION = "esc-search"
DEFAULT_LIMIT = 5
MIN_LIMIT = 3
MAX_LIMIT = 7
DEFAULT_TIMEOUT = 15.0
MAX_TIMEOUT = 60.0
MAX_QUERY_CHARS = 2000
MAX_FILTER_CHARS = 200
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
FUNCTION_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
REQUIRED_PROVENANCE = ("project_identifier", "project_url")

GERMANY_CONTEXT = (
    "Current corpus coverage is the Germany-coordinated ESC slice (1,000 records "
    "at the 2026-08-09 handoff). Absence from these results is not evidence that "
    "no relevant project exists. A retrieved precedent is not proof of local need, "
    "eligibility, impact, or approval probability."
)
SIMILARITY_NOTE = (
    "Semantic similarity, if the endpoint returns it, is a retrieval rank only; "
    "it is not an evidence-confidence score."
)
ZERO_RECORDS_WARNING = "The endpoint returned zero records for this query and filter set."


class EscSearchError(Exception):
    """A user-facing adapter error with a stable code and process exit code."""

    def __init__(self, code: str, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


class ClientArgumentParser(argparse.ArgumentParser):
    """Keep argument failures in the same JSON-on-stderr shape as other errors."""

    def error(self, message: str) -> None:
        raise EscSearchError(
            "invalid_arguments",
            "Invalid arguments: {}. Run --help for usage.".format(message),
        )


@dataclass(frozen=True)
class Config:
    base_url: str
    anon_key: str
    access_token: str
    function_name: str = DEFAULT_FUNCTION
    timeout: float = DEFAULT_TIMEOUT

    @property
    def endpoint(self) -> str:
        parts = urlsplit(self.base_url)
        base_path = parts.path.rstrip("/")
        path = "{}/functions/v1/{}".format(base_path, self.function_name)
        return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


@dataclass(frozen=True)
class TransportResponse:
    status: int
    reason: str
    body: bytes


Transport = Callable[[str, str, Mapping[str, str], bytes, float], TransportResponse]


def _validate_base_url(value: str) -> None:
    try:
        parts = urlsplit(value)
    except ValueError:
        raise EscSearchError("invalid_config", "SUPABASE_URL is not a valid URL.") from None
    if parts.scheme.lower() != "https":
        raise EscSearchError(
            "invalid_config",
            "SUPABASE_URL must use https:// so credentials are never sent over a clear connection.",
        )
    if not parts.hostname:
        raise EscSearchError("invalid_config", "SUPABASE_URL must include a valid host.")
    if any(character.isspace() for character in parts.netloc):
        raise EscSearchError("invalid_config", "SUPABASE_URL must not contain whitespace.")
    if parts.username is not None or parts.password is not None:
        raise EscSearchError(
            "invalid_config", "SUPABASE_URL must not contain embedded credentials."
        )
    try:
        parts.port
    except ValueError:
        raise EscSearchError("invalid_config", "SUPABASE_URL contains an invalid port.") from None
    if parts.query or parts.fragment:
        raise EscSearchError(
            "invalid_config", "SUPABASE_URL must not contain a query string or fragment."
        )
    if parts.path not in ("", "/"):
        raise EscSearchError(
            "invalid_config", "SUPABASE_URL must be an origin without an extra path."
        )


def load_config(environ: Mapping[str, str]) -> Config:
    required = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_ACCESS_TOKEN")
    missing = [name for name in required if not (environ.get(name) or "").strip()]
    if missing:
        raise EscSearchError(
            "missing_config",
            "Missing required environment variable(s): {}. See references/esc-retrieval-adapter.md "
            "or docs/CONFIG.example.md.".format(", ".join(missing)),
        )

    base_url = environ["SUPABASE_URL"].strip()
    _validate_base_url(base_url)

    function_name = (environ.get("ESC_SEARCH_FUNCTION") or DEFAULT_FUNCTION).strip()
    if not FUNCTION_NAME_RE.fullmatch(function_name):
        raise EscSearchError(
            "invalid_config",
            "ESC_SEARCH_FUNCTION must contain only letters, digits, underscores, and hyphens.",
        )

    return Config(
        base_url=base_url,
        anon_key=environ["SUPABASE_ANON_KEY"].strip(),
        access_token=environ["SUPABASE_ACCESS_TOKEN"].strip(),
        function_name=function_name,
    )


def _clean_filter(name: str, value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EscSearchError("invalid_arguments", "{} must be a string.".format(name))
    cleaned = value.strip()
    if not cleaned:
        raise EscSearchError("invalid_arguments", "{} must not be empty.".format(name))
    if len(cleaned) > MAX_FILTER_CHARS:
        raise EscSearchError(
            "invalid_arguments", "{} must be at most {} characters.".format(name, MAX_FILTER_CHARS)
        )
    return cleaned


def validate_search_args(
    query: str,
    country: Optional[str],
    action: Optional[str],
    funding_year: Optional[int],
    limit: int,
) -> Tuple[str, Optional[str], Optional[str], Optional[int]]:
    if not isinstance(query, str) or not query.strip():
        raise EscSearchError("invalid_arguments", "query must be a non-empty string.")
    query = query.strip()
    if len(query) > MAX_QUERY_CHARS:
        raise EscSearchError(
            "invalid_arguments", "query must be at most {} characters.".format(MAX_QUERY_CHARS)
        )

    if isinstance(limit, bool) or not isinstance(limit, int) or not MIN_LIMIT <= limit <= MAX_LIMIT:
        raise EscSearchError(
            "invalid_arguments",
            "limit must be an integer from {} to {}.".format(MIN_LIMIT, MAX_LIMIT),
        )

    country = _clean_filter("country", country)
    action = _clean_filter("action", action)

    if funding_year is not None:
        if isinstance(funding_year, bool) or not isinstance(funding_year, int):
            raise EscSearchError("invalid_arguments", "funding_year must be an integer.")
        if not 2000 <= funding_year <= 2100:
            raise EscSearchError(
                "invalid_arguments", "funding_year must be a four-digit year from 2000 to 2100."
            )

    return query, country, action, funding_year


def build_payload(
    query: str,
    country: Optional[str],
    action: Optional[str],
    funding_year: Optional[int],
    limit: int,
) -> Dict[str, Any]:
    """Map CLI arguments to the provisional Edge Function body.

    This is intentionally the only request-field mapping. If the deployed
    function uses different parameter names, change this function and the
    response extraction below, then update the contract reference.
    """
    payload: Dict[str, Any] = {
        "query": query,
        "match_count": limit,
    }
    if country is not None:
        payload["filter_country"] = country
    if action is not None:
        payload["filter_action"] = action
    if funding_year is not None:
        payload["filter_funding_year"] = funding_year
    return payload


def build_headers(config: Config) -> Dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "apikey": config.anon_key,
        "Authorization": "Bearer {}".format(config.access_token),
        "User-Agent": "esc-project-ideation-retrieval/{}".format(CONTRACT_VERSION),
    }


def _default_http_post(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout: float,
) -> TransportResponse:
    if method != "POST":
        raise ValueError("the adapter only issues POST requests")

    parts = urlsplit(url)
    if parts.scheme.lower() != "https" or not parts.hostname:
        raise ValueError("the adapter only posts to an https endpoint")

    connection = http.client.HTTPSConnection(
        parts.hostname,
        parts.port,
        timeout=timeout,
        context=ssl.create_default_context(),
    )
    try:
        connection.request(
            "POST",
            urlunsplit(("", "", parts.path or "/", parts.query, "")),
            body=body,
            headers=dict(headers),
        )
        response = connection.getresponse()
        response_body = response.read(MAX_RESPONSE_BYTES + 1)
        return TransportResponse(
            status=response.status,
            reason=response.reason or "",
            body=response_body,
        )
    finally:
        connection.close()


def _http_error(status: int) -> EscSearchError:
    if 300 <= status < 400:
        return EscSearchError(
            "redirect_refused",
            "Search request refused a redirect (HTTP {}). Credentials are sent only to the "
            "configured endpoint.".format(status),
            4,
        )
    if status == 401:
        return EscSearchError(
            "authentication_failed",
            "Authentication failed (HTTP 401). Check SUPABASE_ACCESS_TOKEN and SUPABASE_ANON_KEY.",
            4,
        )
    if status == 403:
        return EscSearchError(
            "forbidden",
            "Search request was forbidden (HTTP 403). The access token may lack permission.",
            4,
        )
    if status == 429:
        return EscSearchError(
            "rate_limited",
            "Search service rate-limited the request (HTTP 429). Retry later.",
            4,
        )
    if 500 <= status < 600:
        return EscSearchError(
            "server_error",
            "Search service failed (HTTP {}). Retry later or check the deployment.".format(status),
            4,
        )
    return EscSearchError(
        "http_error",
        "Search request failed (HTTP {}).".format(status),
        4,
    )


def _is_valid_source_url(value: Any) -> bool:
    """Return true for an absolute HTTP(S) URL with safe, useful provenance."""
    if not isinstance(value, str) or not value:
        return False
    if any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in value
    ):
        return False
    if "\\" in value:
        return False
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ("http", "https"):
            return False
        if not parts.hostname:
            return False
        if parts.username is not None or parts.password is not None:
            return False
        if "@" in parts.netloc:
            return False
        port = parts.port
    except ValueError:
        return False
    return port != 0


def _extract_records(document: Any, limit: int) -> Tuple[List[Dict[str, Any]], int, bool]:
    if isinstance(document, list):
        records: Any = document
    elif isinstance(document, dict):
        if "results" not in document:
            raise EscSearchError(
                "invalid_response",
                "Response object must contain a 'results' array (provisional contract).",
                3,
            )
        records = document["results"]
        if not isinstance(records, list):
            raise EscSearchError(
                "invalid_response", "Response 'results' value must be an array.", 3
            )
    else:
        raise EscSearchError(
            "invalid_response",
            "Response must be a JSON array of records or an object with a 'results' array.",
            3,
        )

    original_count = len(records)
    selected = records[:limit]
    for index, record in enumerate(selected, start=1):
        if not isinstance(record, dict):
            raise EscSearchError(
                "invalid_response",
                "Record {} must be a JSON object.".format(index),
                3,
            )
        missing = [
            field
            for field in REQUIRED_PROVENANCE
            if not isinstance(record.get(field), str) or not record[field].strip()
        ]
        if missing:
            raise EscSearchError(
                "invalid_response",
                "Record {} is missing required provenance: {}.".format(index, ", ".join(missing)),
                3,
            )
        if not _is_valid_source_url(record.get("project_url")):
            raise EscSearchError(
                "invalid_response",
                "Record {} has an invalid project_url; expected an absolute HTTP(S) URL.".format(
                    index
                ),
                3,
            )
    return selected, original_count, original_count > limit


class _NonFiniteJSONNumber(ValueError):
    pass


def _reject_json_constant(value: str) -> Any:
    raise _NonFiniteJSONNumber(value)


def _parse_json_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise _NonFiniteJSONNumber(value)
    return number


def execute_search(
    config: Config,
    query: str,
    *,
    country: Optional[str] = None,
    action: Optional[str] = None,
    funding_year: Optional[int] = None,
    limit: int = DEFAULT_LIMIT,
    http_post: Optional[Transport] = None,
) -> Dict[str, Any]:
    query, country, action, funding_year = validate_search_args(
        query, country, action, funding_year, limit
    )
    payload = build_payload(query, country, action, funding_year, limit)
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    transport = http_post or _default_http_post

    try:
        response = transport("POST", config.endpoint, build_headers(config), body, config.timeout)
    except (TimeoutError, socket.timeout):
        raise EscSearchError(
            "timeout",
            "Search request timed out after {:g} seconds.".format(config.timeout),
            4,
        ) from None
    except (OSError, http.client.HTTPException):
        raise EscSearchError(
            "transport_error",
            "Network error while contacting the configured search function.",
            4,
        ) from None

    if not isinstance(response, TransportResponse):
        raise EscSearchError(
            "transport_error", "Search transport returned an unsupported response.", 4
        )
    if not 200 <= response.status < 300:
        raise _http_error(response.status)
    if len(response.body) > MAX_RESPONSE_BYTES:
        raise EscSearchError(
            "response_too_large",
            "Search response exceeded the {} byte limit.".format(MAX_RESPONSE_BYTES),
            3,
        )

    try:
        document = json.loads(
            response.body.decode("utf-8"),
            parse_constant=_reject_json_constant,
            parse_float=_parse_json_float,
        )
    except _NonFiniteJSONNumber:
        raise EscSearchError(
            "invalid_response",
            "Response contained a non-finite number, which is not supported.",
            3,
        ) from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise EscSearchError("invalid_response", "Response was not valid UTF-8 JSON.", 3) from None

    records, original_count, truncated = _extract_records(document, limit)
    warnings = [GERMANY_CONTEXT, SIMILARITY_NOTE]
    if not records:
        warnings.append(ZERO_RECORDS_WARNING)
    if truncated:
        warnings.append(
            "The endpoint returned {} records; only the first {} are shown.".format(
                original_count, limit
            )
        )

    return {
        "ok": True,
        "adapter": {
            "name": ADAPTER_NAME,
            "contract": CONTRACT_VERSION,
            "live_verified": False,
        },
        "query": query,
        "filters": {
            "country": country,
            "action": action,
            "funding_year": funding_year,
        },
        "limit": limit,
        "returned": len(records),
        "records": records,
        "warnings": warnings,
    }


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _md_text(value: Any) -> str:
    """Escape untrusted text for inline Markdown and blockquotes."""
    text = _format_value(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    escaped = []
    for character in text:
        if character in "\\`*_[]|#":
            escaped.append("\\" + character)
        elif character == "\n":
            escaped.append("\n")
        elif ord(character) < 32 and character != "\t":
            escaped.append(" ")
        else:
            escaped.append(character)
    return "".join(escaped)


def _md_cell(value: Any) -> str:
    """Escape untrusted text for a Markdown table cell."""
    text = _format_value(value)
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    return "".join(
        character if character == "\t" or ord(character) >= 32 else " " for character in text
    )


def render_json(result: Mapping[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def render_markdown(result: Mapping[str, Any]) -> str:
    records = result["records"]
    filters = result["filters"]
    lines = [
        "## ESC retrieval evidence",
        "",
        "> " + GERMANY_CONTEXT,
        ">",
        "> " + SIMILARITY_NOTE,
        "",
        "**Query:** " + _md_text(result["query"]),
        "**Filters:** country={}; action={}; funding_year={}".format(
            _md_text(filters["country"]),
            _md_text(filters["action"]),
            _md_text(filters["funding_year"]),
        ),
        "**Returned:** {} of up to {}".format(result["returned"], result["limit"]),
        "**Contract:** {} (provisional; not live-verified)".format(result["adapter"]["contract"]),
        "",
    ]

    extra_warnings = [
        warning
        for warning in result["warnings"]
        if warning not in (GERMANY_CONTEXT, SIMILARITY_NOTE, ZERO_RECORDS_WARNING)
    ]
    for warning in extra_warnings:
        lines.append("**Note:** " + _md_text(warning))
    if extra_warnings:
        lines.append("")

    if not records:
        lines.append(
            "No matching records were returned. This is not evidence that no relevant project exists."
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "| # | Title | Identifier | Action | Year | Funding | URL |",
            "|---:|---|---|---|---:|---:|---|",
        ]
    )
    for index, record in enumerate(records, start=1):
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} |".format(
                index,
                _md_cell(record.get("title")),
                _md_cell(record.get("project_identifier")),
                _md_cell(record.get("action")),
                _md_cell(record.get("funding_year")),
                _md_cell(record.get("funding_amount")),
                _md_cell(record.get("project_url")),
            )
        )

    lines.extend(["", "### Record details", ""])
    detail_fields = (
        ("Identifier", "project_identifier"),
        ("URL", "project_url"),
        ("Programme", "programme"),
        ("Action", "action"),
        ("Funding year", "funding_year"),
        ("Funding amount", "funding_amount"),
        ("Coordinating organisation", "coordinating_organisation"),
        ("Coordinator country", "coordinator_country"),
        ("Participating countries", "participating_countries"),
    )
    for index, record in enumerate(records, start=1):
        title = record.get("title")
        heading = title if isinstance(title, str) and title.strip() else record["project_identifier"]
        lines.append("#### {}. {}".format(index, _md_text(heading)))
        for label, key in detail_fields:
            lines.append("- **{}:** {}".format(label, _md_text(record.get(key))))
        lines.extend(["", "**Summary:**", ""])
        summary = _md_text(record.get("summary"))
        lines.extend("> " + line for line in summary.split("\n"))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = ClientArgumentParser(
        prog="esc_search.py",
        description=(
            "Search the ESC Supabase Edge Function and print provenance-preserving results. "
            "The HTTP contract is provisional and the adapter has not been live-verified."
        ),
        epilog=(
            "Required environment: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_ACCESS_TOKEN. "
            "Optional: ESC_SEARCH_FUNCTION (default esc-search). "
            "Credentials are never accepted as command arguments."
        ),
    )
    parser.add_argument("query", help="plain-language need, target group, place, activity, or outcome")
    parser.add_argument("--country", metavar="COUNTRY", help="optional country filter (surrounding whitespace is trimmed)")
    parser.add_argument("--action", metavar="ACTION", help="optional action filter (surrounding whitespace is trimmed)")
    parser.add_argument("--funding-year", type=int, metavar="YEAR", help="optional four-digit funding year")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        choices=range(MIN_LIMIT, MAX_LIMIT + 1),
        metavar="{}-{}".format(MIN_LIMIT, MAX_LIMIT),
        help="maximum records to return (default {})".format(DEFAULT_LIMIT),
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="output format (default json)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help="network timeout in seconds, up to {:g} (default {:g})".format(
            MAX_TIMEOUT, DEFAULT_TIMEOUT
        ),
    )
    return parser


def _error_json(error: EscSearchError) -> str:
    return json.dumps(
        {
            "ok": False,
            "error": {
                "code": error.code,
                "message": error.message,
            },
        },
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    environ: Optional[Mapping[str, str]] = None,
    http_post: Optional[Transport] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
) -> int:
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr

    try:
        args = build_parser().parse_args(argv)
        if not 0 < args.timeout <= MAX_TIMEOUT:
            raise EscSearchError(
                "invalid_arguments", "timeout must be greater than 0 and at most {:g} seconds.".format(MAX_TIMEOUT)
            )
        config = replace(load_config(environ if environ is not None else os.environ), timeout=args.timeout)
        result = execute_search(
            config,
            args.query,
            country=args.country,
            action=args.action,
            funding_year=args.funding_year,
            limit=args.limit,
            http_post=http_post,
        )
        out.write(render_markdown(result) if args.format == "markdown" else render_json(result))
        return 0
    except EscSearchError as error:
        err.write(_error_json(error))
        return error.exit_code
    except Exception as error:  # Never expose a traceback or interpolate untrusted values.
        err.write(
            _error_json(
                EscSearchError(
                    "internal_error",
                    "Unexpected adapter error ({}).".format(type(error).__name__),
                    1,
                )
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
