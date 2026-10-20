"""Offline tests for the ESC retrieval adapter.

All records and credentials below are synthetic. No test opens a network
connection; tests inject a fake transport into the adapter.
"""

import io
import json
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "esc-project-ideation" / "scripts"))

import esc_search  # noqa: E402  (path is prepared above)


def transport_response(status=200, body=None, reason="OK"):
    if body is None:
        body = b"[]"
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False).encode("utf-8")
    elif isinstance(body, str):
        body = body.encode("utf-8")
    return esc_search.TransportResponse(status=status, reason=reason, body=body)


class FakeTransport:
    def __init__(self, response=None, error=None):
        self.response = response if response is not None else transport_response()
        self.error = error
        self.calls = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout": timeout,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


class FakeHTTPResponse:
    def __init__(self, body=b"[]", status=200, reason="OK", fill_on_read=False, read_error=None):
        self.status = status
        self.reason = reason
        self.body = body
        self.fill_on_read = fill_on_read
        self.read_error = read_error
        self.read_sizes = []

    def read(self, size):
        self.read_sizes.append(size)
        if self.read_error is not None:
            raise self.read_error
        if self.fill_on_read:
            return b"x" * size
        return self.body[:size]


class FakeHTTPSConnection:
    instances = []
    response = FakeHTTPResponse()
    request_error = None
    response_error = None

    @classmethod
    def reset(cls, response=None, request_error=None, response_error=None):
        cls.instances = []
        cls.response = response if response is not None else FakeHTTPResponse()
        cls.request_error = request_error
        cls.response_error = response_error

    def __init__(self, host, port, timeout=None, context=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.requests = []
        self.closed = False
        type(self).instances.append(self)

    def request(self, method, url, body=None, headers=None):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "body": body,
                "headers": dict(headers or {}),
            }
        )
        if type(self).request_error is not None:
            raise type(self).request_error

    def getresponse(self):
        if type(self).response_error is not None:
            raise type(self).response_error
        return type(self).response

    def close(self):
        self.closed = True


def make_config(**overrides):
    values = {
        "base_url": "https://unit-test.supabase.co",
        "anon_key": "synthetic-anon-key",
        "access_token": "synthetic-access-token",
        "function_name": "esc-search",
        "timeout": 5.0,
    }
    values.update(overrides)
    return esc_search.Config(**values)


def valid_environ():
    return {
        "SUPABASE_URL": "https://unit-test.supabase.co",
        "SUPABASE_ANON_KEY": "synthetic-anon-key",
        "SUPABASE_ACCESS_TOKEN": "synthetic-access-token",
    }


def synthetic_record(identifier="SYNTH-DE-0001"):
    return {
        "project_identifier": identifier,
        "title": "Café bridge — 青年 | integration",
        "summary": (
            "Synthetic full summary about refugee and migrant integration through sport.\n"
            "Second line keeps Ünïcode and a | pipe and <script>alert('synthetic')</script>."
        ),
        "project_url": "https://example.invalid/projects/{}".format(identifier),
        "programme": "ESC",
        "action": "Synthetic action",
        "funding_year": 2024,
        "funding_amount": 0,
        "coordinating_organisation": "Synthetic Organisation",
        "coordinator_country": "DE",
        "participating_countries": ["DE", "FR"],
        "similarity": 0.83,
    }


class RequestContractTests(unittest.TestCase):
    def test_posts_provisional_contract_headers_and_body(self):
        record = synthetic_record()
        fake = FakeTransport(transport_response(body=[record]))

        result = esc_search.execute_search(
            make_config(),
            "refugee integration through sport",
            country="DE",
            action="Volunteering | local",
            funding_year=2024,
            limit=5,
            http_post=fake,
        )

        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], "https://unit-test.supabase.co/functions/v1/esc-search")
        self.assertEqual(call["headers"]["apikey"], "synthetic-anon-key")
        self.assertEqual(call["headers"]["Authorization"], "Bearer synthetic-access-token")
        self.assertEqual(call["headers"]["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(call["headers"]["Accept"], "application/json")
        self.assertEqual(call["timeout"], 5.0)
        self.assertEqual(
            json.loads(call["body"].decode("utf-8")),
            {
                "query": "refugee integration through sport",
                "match_count": 5,
                "filter_country": "DE",
                "filter_action": "Volunteering | local",
                "filter_funding_year": 2024,
            },
        )
        self.assertEqual(result["records"], [record])
        self.assertEqual(result["returned"], 1)
        self.assertFalse(result["adapter"]["live_verified"])

    def test_omits_absent_optional_filters(self):
        fake = FakeTransport(transport_response(body=[]))
        esc_search.execute_search(make_config(), "youth climate action", http_post=fake)

        body = json.loads(fake.calls[0]["body"].decode("utf-8"))
        self.assertEqual(set(body), {"query", "match_count"})
        self.assertEqual(body["match_count"], 5)

    def test_uses_configured_function_name_path(self):
        fake = FakeTransport(transport_response(body=[]))
        esc_search.execute_search(
            make_config(function_name="esc-search-v2"), "query", http_post=fake
        )
        self.assertEqual(
            fake.calls[0]["url"],
            "https://unit-test.supabase.co/functions/v1/esc-search-v2",
        )

    def test_rejects_invalid_limit_query_and_year(self):
        cases = [
            ({"query": "valid", "limit": 2}, "limit"),
            ({"query": "valid", "limit": 8}, "limit"),
            ({"query": "   "}, "query"),
            ({"query": "valid", "funding_year": 1999}, "funding_year"),
            ({"query": "valid", "funding_year": 2101}, "funding_year"),
        ]
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                fake = FakeTransport()
                with self.assertRaises(esc_search.EscSearchError) as caught:
                    esc_search.execute_search(make_config(), http_post=fake, **kwargs)
                self.assertEqual(caught.exception.code, "invalid_arguments")
                self.assertIn(expected, caught.exception.message)
                self.assertEqual(fake.calls, [])

    def test_rejects_empty_filter_values(self):
        for name in ("country", "action"):
            with self.subTest(name=name):
                with self.assertRaises(esc_search.EscSearchError) as caught:
                    esc_search.execute_search(
                        make_config(), "query", http_post=FakeTransport(), **{name: "  "}
                    )
                self.assertEqual(caught.exception.code, "invalid_arguments")

    def test_rejects_insecure_or_credentialed_base_url(self):
        for base_url in (
            "http://unit-test.supabase.co",
            "https://user:pass@unit-test.supabase.co",
            "https://unit-test.supabase.co/extra",
            "https://unit-test.supabase.co?token=leak",
            "https://[invalid",
            "https://unit-test.supabase.co:not-a-port",
        ):
            with self.subTest(base_url=base_url):
                environ = valid_environ()
                environ["SUPABASE_URL"] = base_url
                with self.assertRaises(esc_search.EscSearchError) as caught:
                    esc_search.load_config(environ)
                self.assertEqual(caught.exception.code, "invalid_config")
                self.assertNotIn("pass", caught.exception.message)

    def test_rejects_unsafe_function_name(self):
        for name in ("../esc-search", "esc/search", "esc search", "   "):
            with self.subTest(name=name):
                environ = valid_environ()
                environ["ESC_SEARCH_FUNCTION"] = name
                with self.assertRaises(esc_search.EscSearchError) as caught:
                    esc_search.load_config(environ)
                self.assertEqual(caught.exception.code, "invalid_config")

    def test_accepts_safe_custom_function_name(self):
        environ = valid_environ()
        environ["ESC_SEARCH_FUNCTION"] = "esc_search-2"
        config = esc_search.load_config(environ)
        self.assertEqual(
            config.endpoint,
            "https://unit-test.supabase.co/functions/v1/esc_search-2",
        )


class ResponseContractTests(unittest.TestCase):
    def test_accepts_results_wrapper_and_preserves_fields(self):
        first = synthetic_record("SYNTH-DE-0001")
        second = synthetic_record("SYNTH-DE-0002")
        second["funding_amount"] = 12500.5
        second["summary"] = "Zweite synthetische Zusammenfassung — 日本語"
        fake = FakeTransport(
            transport_response(body={"results": [first, second], "total": 2})
        )

        result = esc_search.execute_search(make_config(), "synthetic query", http_post=fake)

        self.assertEqual(result["records"], [first, second])
        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["records"][0]["funding_amount"], 0)
        self.assertEqual(result["records"][0]["summary"], first["summary"])
        self.assertIn("日本語", result["records"][1]["summary"])
        self.assertNotIn("confidence", json.dumps(result["records"][0]).lower())
        self.assertEqual(result["records"][0]["similarity"], 0.83)

    def test_accepts_direct_list_and_fewer_than_limit(self):
        records = [synthetic_record("SYNTH-DE-0001"), synthetic_record("SYNTH-DE-0002")]
        fake = FakeTransport(transport_response(body=records))

        result = esc_search.execute_search(make_config(), "synthetic query", limit=5, http_post=fake)

        self.assertEqual(result["records"], records)
        self.assertEqual(result["returned"], 2)
        self.assertFalse(any("only the first" in warning for warning in result["warnings"]))

    def test_zero_records_is_success_not_a_provenance_error(self):
        for body in ([], {"results": []}):
            with self.subTest(body=body):
                fake = FakeTransport(transport_response(body=body))
                result = esc_search.execute_search(make_config(), "no match query", http_post=fake)
                self.assertTrue(result["ok"])
                self.assertEqual(result["returned"], 0)
                self.assertEqual(result["records"], [])
                self.assertTrue(
                    any("zero records" in warning for warning in result["warnings"])
                )

    def test_missing_provenance_is_explicit_error(self):
        for missing in ("project_identifier", "project_url"):
            with self.subTest(missing=missing):
                record = synthetic_record()
                del record[missing]
                fake = FakeTransport(transport_response(body=[record]))
                with self.assertRaises(esc_search.EscSearchError) as caught:
                    esc_search.execute_search(make_config(), "query", http_post=fake)
                self.assertEqual(caught.exception.code, "invalid_response")
                self.assertIn(missing, caught.exception.message)
                self.assertIn("Record 1", caught.exception.message)
                self.assertNotIn("zero records", caught.exception.message)

    def test_unsupported_shapes_and_malformed_json_fail_explicitly(self):
        cases = [
            (b"{", "not valid UTF-8 JSON"),
            (b"\xff", "not valid UTF-8 JSON"),
            (b"null", "Response must be a JSON array"),
            (b'"text"', "Response must be a JSON array"),
            (b'{"records": []}', "must contain a 'results' array"),
            (b'{"results": {}}', "'results' value must be an array"),
            (b"[1]", "Record 1 must be a JSON object"),
        ]
        for body, expected in cases:
            with self.subTest(body=body):
                fake = FakeTransport(transport_response(body=body))
                with self.assertRaises(esc_search.EscSearchError) as caught:
                    esc_search.execute_search(make_config(), "query", http_post=fake)
                self.assertEqual(caught.exception.code, "invalid_response")
                self.assertIn(expected, caught.exception.message)

    def test_rejects_non_finite_numbers_without_echoing_values(self):
        base = (
            '{"project_identifier":"SYNTH-1",'
            '"project_url":"https://example.invalid/1",'
            '"funding_amount":%s}'
        )
        cases = [
            base % "NaN",
            base % "Infinity",
            base % "-Infinity",
            base % "1e999",
            base % "-1e999",
        ]
        cases.append('{"results": [%s]}' % (base % "1e999"))
        for body in cases:
            with self.subTest(body=body):
                fake = FakeTransport(transport_response(body=body))
                with self.assertRaises(esc_search.EscSearchError) as caught:
                    esc_search.execute_search(make_config(), "query", http_post=fake)
                self.assertEqual(caught.exception.code, "invalid_response")
                self.assertEqual(caught.exception.exit_code, 3)
                self.assertIn("non-finite", caught.exception.message)
                for raw_value in ("NaN", "Infinity", "1e999", "SYNTH-1"):
                    self.assertNotIn(raw_value, caught.exception.message)

    def test_render_json_is_strict_about_non_finite_values(self):
        with self.assertRaises(ValueError):
            esc_search.render_json({"ok": True, "value": float("nan")})

    def test_valid_source_urls_are_preserved_exactly(self):
        for url in (
            "http://example.invalid/projects/1?x=1&y=2#part",
            "https://example.invalid",
            "https://example.invalid:443/project?id=synthetic",
        ):
            with self.subTest(url=url):
                record = synthetic_record()
                record["project_url"] = url
                fake = FakeTransport(transport_response(body=[record]))
                result = esc_search.execute_search(make_config(), "query", http_post=fake)
                self.assertEqual(result["records"][0]["project_url"], url)

    def test_rejects_invalid_source_urls_without_echoing_values(self):
        invalid_urls = (
            "not a URL",
            "/projects/1",
            "projects/1",
            "//example.invalid/1",
            "javascript:alert(1)",
            "ftp://example.invalid/1",
            "mailto:test@example.invalid",
            "https:///missing-host",
            "https://user:pass@example.invalid/1",
            "https://user@example.invalid/1",
            "https://example.invalid:notaport/1",
            "https://example.invalid:70000/1",
            "https://example.invalid:0/1",
            "https://example.invalid/1 with space",
            "https://example.invalid/1\n",
            "https://example.invalid\\path",
        )
        for url in invalid_urls:
            with self.subTest(url=url):
                record = synthetic_record()
                record["project_url"] = url
                fake = FakeTransport(transport_response(body=[record]))
                with self.assertRaises(esc_search.EscSearchError) as caught:
                    esc_search.execute_search(make_config(), "query", http_post=fake)
                self.assertEqual(caught.exception.code, "invalid_response")
                self.assertEqual(caught.exception.exit_code, 3)
                self.assertIn("Record 1", caught.exception.message)
                self.assertIn("project_url", caught.exception.message)
                self.assertNotIn(url, caught.exception.message)

    def test_only_selected_records_are_url_validated_when_truncated(self):
        records = [synthetic_record("SYNTH-{:04d}".format(index)) for index in range(1, 5)]
        records[3]["project_url"] = "not a URL"
        fake = FakeTransport(transport_response(body=records))

        result = esc_search.execute_search(make_config(), "query", limit=3, http_post=fake)

        self.assertEqual(result["returned"], 3)
        self.assertTrue(any("4 records; only the first 3" in warning for warning in result["warnings"]))

    def test_absent_optional_fields_are_not_fabricated(self):
        record = synthetic_record()
        del record["title"]
        del record["summary"]
        del record["funding_amount"]
        fake = FakeTransport(transport_response(body=[record]))

        result = esc_search.execute_search(make_config(), "query", http_post=fake)

        output_record = result["records"][0]
        self.assertNotIn("title", output_record)
        self.assertNotIn("summary", output_record)
        self.assertNotIn("funding_amount", output_record)
        markdown = esc_search.render_markdown(result)
        self.assertIn("#### 1. SYNTH-DE-0001", markdown)
        self.assertIn("**Funding amount:** null", markdown)
        self.assertIn("> null", markdown)

    def test_truncates_to_limit_with_warning(self):
        records = [synthetic_record("SYNTH-{:04d}".format(index)) for index in range(1, 5)]
        fake = FakeTransport(transport_response(body=records))

        result = esc_search.execute_search(make_config(), "query", limit=3, http_post=fake)

        self.assertEqual(result["returned"], 3)
        self.assertEqual([record["project_identifier"] for record in result["records"]], [
            "SYNTH-0001",
            "SYNTH-0002",
            "SYNTH-0003",
        ])
        self.assertTrue(any("4 records; only the first 3" in warning for warning in result["warnings"]))
        self.assertIn(
            "**Note:** The endpoint returned 4 records; only the first 3 are shown.",
            esc_search.render_markdown(result),
        )


class ErrorHandlingTests(unittest.TestCase):
    def test_http_status_errors_are_mapped(self):
        cases = [
            (400, "http_error"),
            (401, "authentication_failed"),
            (403, "forbidden"),
            (429, "rate_limited"),
            (500, "server_error"),
            (503, "server_error"),
        ]
        for status, code in cases:
            with self.subTest(status=status):
                fake = FakeTransport(transport_response(status=status, body=b"ignored"))
                with self.assertRaises(esc_search.EscSearchError) as caught:
                    esc_search.execute_search(make_config(), "query", http_post=fake)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(caught.exception.exit_code, 4)

    def test_redirect_is_refused_and_not_followed(self):
        fake = FakeTransport(
            transport_response(
                status=302,
                reason="Found",
                body=b'{"url": "https://elsewhere.invalid"}',
            )
        )
        with self.assertRaises(esc_search.EscSearchError) as caught:
            esc_search.execute_search(make_config(), "query", http_post=fake)
        self.assertEqual(caught.exception.code, "redirect_refused")
        self.assertIn("redirect", caught.exception.message)
        self.assertEqual(len(fake.calls), 1)

    def test_timeout_is_reported(self):
        fake = FakeTransport(error=TimeoutError("synthetic timeout"))
        with self.assertRaises(esc_search.EscSearchError) as caught:
            esc_search.execute_search(make_config(), "query", http_post=fake)
        self.assertEqual(caught.exception.code, "timeout")
        self.assertIn("timed out", caught.exception.message)

    def test_socket_timeout_is_reported(self):
        fake = FakeTransport(error=socket.timeout("synthetic timeout"))
        with self.assertRaises(esc_search.EscSearchError) as caught:
            esc_search.execute_search(make_config(), "query", http_post=fake)
        self.assertEqual(caught.exception.code, "timeout")

    def test_transport_error_does_not_echo_exception_text(self):
        fake = FakeTransport(error=OSError("leaked synthetic-access-token"))
        with self.assertRaises(esc_search.EscSearchError) as caught:
            esc_search.execute_search(make_config(), "query", http_post=fake)
        self.assertEqual(caught.exception.code, "transport_error")
        self.assertNotIn("synthetic-access-token", caught.exception.message)

    def test_http_error_diagnostics_are_secret_free(self):
        out = io.StringIO()
        err = io.StringIO()
        fake = FakeTransport(
            transport_response(
                status=401,
                reason="Unauthorized",
                body=b"server echoed synthetic-access-token and synthetic-anon-key",
            )
        )

        code = esc_search.main(
            ["synthetic query"],
            environ=valid_environ(),
            http_post=fake,
            stdout=out,
            stderr=err,
        )

        self.assertEqual(code, 4)
        self.assertEqual(out.getvalue(), "")
        diagnostic = err.getvalue()
        self.assertIn('"authentication_failed"', diagnostic)
        self.assertNotIn("synthetic-access-token", diagnostic)
        self.assertNotIn("synthetic-anon-key", diagnostic)
        self.assertNotIn("Traceback", diagnostic)

    def test_missing_settings_fail_usefully_without_secrets(self):
        out = io.StringIO()
        err = io.StringIO()

        code = esc_search.main(
            ["synthetic query"],
            environ={"SUPABASE_ANON_KEY": "orphan-synthetic-anon-key"},
            http_post=FakeTransport(),
            stdout=out,
            stderr=err,
        )

        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        diagnostic = json.loads(err.getvalue())
        self.assertEqual(diagnostic["error"]["code"], "missing_config")
        self.assertIn("SUPABASE_URL", diagnostic["error"]["message"])
        self.assertIn("SUPABASE_ACCESS_TOKEN", diagnostic["error"]["message"])
        self.assertNotIn("orphan-synthetic-anon-key", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_invalid_timeout_is_a_usage_error(self):
        out = io.StringIO()
        err = io.StringIO()
        code = esc_search.main(
            ["synthetic query", "--timeout", "0"],
            environ=valid_environ(),
            http_post=FakeTransport(),
            stdout=out,
            stderr=err,
        )
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(err.getvalue())["error"]["code"], "invalid_arguments")

    def test_cli_invalid_limit_returns_json_usage_error(self):
        out = io.StringIO()
        err = io.StringIO()
        code = esc_search.main(
            ["synthetic query", "--limit", "2"],
            environ=valid_environ(),
            http_post=FakeTransport(),
            stdout=out,
            stderr=err,
        )
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        diagnostic = json.loads(err.getvalue())
        self.assertEqual(diagnostic["error"]["code"], "invalid_arguments")
        self.assertIn("invalid choice", diagnostic["error"]["message"])
        self.assertNotIn("Traceback", err.getvalue())

    def test_cli_missing_query_returns_json_usage_error(self):
        out = io.StringIO()
        err = io.StringIO()
        code = esc_search.main(
            [],
            environ=valid_environ(),
            http_post=FakeTransport(),
            stdout=out,
            stderr=err,
        )
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        diagnostic = json.loads(err.getvalue())
        self.assertEqual(diagnostic["error"]["code"], "invalid_arguments")
        self.assertIn("required: query", diagnostic["error"]["message"])

    def test_main_returns_json_success(self):
        out = io.StringIO()
        err = io.StringIO()
        record = synthetic_record()
        fake = FakeTransport(transport_response(body=[record]))

        code = esc_search.main(
            ["synthetic query"],
            environ=valid_environ(),
            http_post=fake,
            stdout=out,
            stderr=err,
        )

        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), "")
        output = json.loads(out.getvalue())
        self.assertTrue(output["ok"])
        self.assertEqual(output["records"], [record])


class DefaultTransportTests(unittest.TestCase):
    def setUp(self):
        self.context = object()
        FakeHTTPSConnection.reset()
        self.connection_patch = patch.object(
            esc_search.http.client, "HTTPSConnection", FakeHTTPSConnection
        )
        self.context_patch = patch.object(
            esc_search.ssl, "create_default_context", return_value=self.context
        )
        self.connection_patch.start()
        self.context_patch.start()
        self.addCleanup(self.connection_patch.stop)
        self.addCleanup(self.context_patch.stop)

    def test_main_uses_default_transport_with_expected_request_and_timeout(self):
        record = synthetic_record()
        FakeHTTPSConnection.reset(
            response=FakeHTTPResponse(body=json.dumps([record]).encode("utf-8"))
        )
        out = io.StringIO()
        err = io.StringIO()

        code = esc_search.main(
            [
                "synthetic query",
                "--country",
                "DE",
                "--action",
                "Synthetic action",
                "--funding-year",
                "2024",
                "--limit",
                "5",
                "--timeout",
                "7.5",
            ],
            environ=valid_environ(),
            stdout=out,
            stderr=err,
        )

        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(len(FakeHTTPSConnection.instances), 1)
        connection = FakeHTTPSConnection.instances[0]
        self.assertEqual(connection.host, "unit-test.supabase.co")
        self.assertIsNone(connection.port)
        self.assertEqual(connection.timeout, 7.5)
        self.assertIs(connection.context, self.context)
        self.assertEqual(len(connection.requests), 1)
        request = connection.requests[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["url"], "/functions/v1/esc-search")
        self.assertEqual(request["headers"]["apikey"], "synthetic-anon-key")
        self.assertEqual(request["headers"]["Authorization"], "Bearer synthetic-access-token")
        self.assertEqual(request["headers"]["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(
            json.loads(request["body"].decode("utf-8")),
            {
                "query": "synthetic query",
                "match_count": 5,
                "filter_country": "DE",
                "filter_action": "Synthetic action",
                "filter_funding_year": 2024,
            },
        )
        self.assertTrue(connection.closed)
        self.assertEqual(
            FakeHTTPSConnection.response.read_sizes,
            [esc_search.MAX_RESPONSE_BYTES + 1],
        )
        self.assertEqual(json.loads(out.getvalue())["records"], [record])

    def test_default_transport_closes_connection_on_transport_error(self):
        FakeHTTPSConnection.reset(request_error=OSError("synthetic connection failure"))

        with self.assertRaises(esc_search.EscSearchError) as caught:
            esc_search.execute_search(make_config(), "query")

        self.assertEqual(caught.exception.code, "transport_error")
        self.assertEqual(len(FakeHTTPSConnection.instances), 1)
        self.assertTrue(FakeHTTPSConnection.instances[0].closed)

    def test_default_transport_propagates_timeout_and_closes(self):
        FakeHTTPSConnection.reset(response_error=TimeoutError("synthetic timeout"))

        with self.assertRaises(esc_search.EscSearchError) as caught:
            esc_search.execute_search(make_config(), "query")

        self.assertEqual(caught.exception.code, "timeout")
        self.assertEqual(len(FakeHTTPSConnection.instances), 1)
        self.assertTrue(FakeHTTPSConnection.instances[0].closed)

    def test_default_transport_refuses_redirect_without_second_request(self):
        FakeHTTPSConnection.reset(
            response=FakeHTTPResponse(status=302, reason="Found", body=b"")
        )

        with self.assertRaises(esc_search.EscSearchError) as caught:
            esc_search.execute_search(make_config(), "query")

        self.assertEqual(caught.exception.code, "redirect_refused")
        self.assertEqual(len(FakeHTTPSConnection.instances), 1)
        connection = FakeHTTPSConnection.instances[0]
        self.assertEqual(len(connection.requests), 1)
        self.assertTrue(connection.closed)

    def test_default_transport_bounds_read_and_rejects_oversized_body(self):
        with patch.object(esc_search, "MAX_RESPONSE_BYTES", 16):
            FakeHTTPSConnection.reset(response=FakeHTTPResponse(fill_on_read=True))

            with self.assertRaises(esc_search.EscSearchError) as caught:
                esc_search.execute_search(make_config(), "query")

        self.assertEqual(caught.exception.code, "response_too_large")
        self.assertEqual(caught.exception.exit_code, 3)
        self.assertEqual(FakeHTTPSConnection.instances[0].response.read_sizes, [17])
        self.assertTrue(FakeHTTPSConnection.instances[0].closed)


class MarkdownTests(unittest.TestCase):
    def test_markdown_escapes_untrusted_values_and_preserves_zero(self):
        record = synthetic_record()
        record["title"] = "Bad | Title\n## forged <script>alert(1)</script>"
        record["summary"] = (
            "Line one | pipe\nLine two <b>bold</b> *stars* [link](https://example.invalid)"
        )
        fake = FakeTransport(transport_response(body=[record]))
        result = esc_search.execute_search(make_config(), "query", http_post=fake)

        markdown = esc_search.render_markdown(result)

        self.assertIn("| 1 | Bad \\| Title ## forged &lt;script&gt;", markdown)
        self.assertIn("\\|", markdown)
        self.assertIn("&lt;script&gt;", markdown)
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("\n## forged", markdown)
        self.assertIn("| 0 |", markdown)
        self.assertIn("**Funding amount:** 0", markdown)

    def test_markdown_zero_records_is_honest(self):
        fake = FakeTransport(transport_response(body=[]))
        result = esc_search.execute_search(make_config(), "query", http_post=fake)

        markdown = esc_search.render_markdown(result)

        self.assertIn("**Returned:** 0 of up to 5", markdown)
        self.assertIn("No matching records were returned.", markdown)
        self.assertIn("not evidence that no relevant project exists", markdown)


if __name__ == "__main__":
    unittest.main()
