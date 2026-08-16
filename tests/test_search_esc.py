from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skill" / "esc-project-ideation" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import search_esc  # noqa: E402


ACCESS_TOKEN = "test-access-token"
API_KEY = "test-api-key"
BASE_URL = "https://test-project.supabase.co"
ENDPOINT = f"{BASE_URL}/functions/v1/esc-search"


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body = body
        self.status = status

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False


def response_payload(**result_overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "project_identifier": "TEST-PROJECT-001",
        "project_title": "Community repair workshops",
        "project_summary": "A practical project summary.",
        "results_platform_project_card": "public-card-placeholder",
        "action": "Volunteering Projects",
        "coordinator_country": "DE",
        "funding_year": 2024,
        "funding_amount": 12000,
        "similarity": 0.91,
    }
    result.update(result_overrides)
    return {
        "query": "community repair",
        "model": "test-model",
        "filters": {
            "country": "DE",
            "action": "Volunteering Projects",
            "funding_year": 2024,
        },
        "count": 1,
        "results": [result],
    }


def encoded_response(payload: object) -> FakeResponse:
    return FakeResponse(json.dumps(payload).encode("utf-8"))


class SearchEscTests(unittest.TestCase):
    def run_main(
        self,
        args: list[str],
        *,
        env: dict[str, str],
        response: FakeResponse | None = None,
        side_effect: BaseException | None = None,
    ) -> tuple[int, str, str, object]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        effective_env = {"ESC_SUPABASE_URL": BASE_URL, **env}
        with patch.dict(os.environ, effective_env, clear=True):
            with patch.object(
                search_esc,
                "_open_without_redirects",
                return_value=response,
                side_effect=side_effect,
            ) as opener:
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = search_esc.main(args)
        return exit_code, stdout.getvalue(), stderr.getvalue(), opener

    def test_request_shape_filters_auth_headers_and_pretty_output(self) -> None:
        exit_code, stdout, stderr, opener = self.run_main(
            [
                "--query",
                "  community repair  ",
                "--country",
                " de ",
                "--action",
                " Volunteering Projects ",
                "--year",
                "2024",
                "--limit",
                "7",
                "--timeout",
                "3.5",
                "--pretty",
            ],
            env={
                "ESC_SEARCH_ENDPOINT": ENDPOINT,
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
                "ESC_SUPABASE_API_KEY": API_KEY,
            },
            response=encoded_response(response_payload()),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn('\n  "model"', stdout)
        self.assertEqual(json.loads(stdout), response_payload())
        opener.assert_called_once()
        request = opener.call_args.args[0]
        request_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(
            request_body,
            {
                "query": "community repair",
                "match_count": 7,
                "filter_country": "DE",
                "filter_action": "Volunteering Projects",
                "filter_funding_year": 2024,
            },
        )
        self.assertEqual(request.full_url, ENDPOINT)
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(request.get_header("Authorization"), f"Bearer {ACCESS_TOKEN}")
        self.assertEqual(request.get_header("Apikey"), API_KEY)
        self.assertEqual(opener.call_args.kwargs["timeout"], 3.5)
        self.assertNotIn(ACCESS_TOKEN, stdout + stderr)
        self.assertNotIn(API_KEY, stdout + stderr)

    def test_supabase_url_builds_verified_function_endpoint_and_api_key_is_optional(self) -> None:
        exit_code, stdout, stderr, opener = self.run_main(
            ["--query", "repair"],
            env={
                "ESC_SUPABASE_URL": f"{BASE_URL}/",
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
            },
            response=encoded_response(response_payload()),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["count"], 1)
        request = opener.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://test-project.supabase.co/functions/v1/esc-search",
        )
        self.assertEqual(json.loads(request.data.decode("utf-8"))["match_count"], 5)
        self.assertIsNone(request.get_header("Apikey"))

    def test_empty_result_set_is_valid_and_preserved(self) -> None:
        empty = response_payload()
        empty["count"] = 0
        empty["results"] = []
        exit_code, stdout, stderr, opener = self.run_main(
            ["--query", "rare activity"],
            env={
                "ESC_SEARCH_ENDPOINT": ENDPOINT,
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
            },
            response=encoded_response(empty),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), empty)
        opener.assert_called_once()

    def test_blank_query_and_out_of_range_limit_are_rejected_without_network(self) -> None:
        env = {
            "ESC_SEARCH_ENDPOINT": ENDPOINT,
            "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
        }
        exit_code, stdout, stderr, opener = self.run_main(
            ["--query", "   "], env=env, response=encoded_response(response_payload())
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("must not be empty", stderr)
        opener.assert_not_called()

        with patch.dict(os.environ, {"ESC_SUPABASE_URL": BASE_URL, **env}, clear=True):
            with patch.object(search_esc, "_open_without_redirects") as unopened:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as error_stream:
                    with self.assertRaises(SystemExit) as raised:
                        search_esc.main(["--query", "repair", "--limit", "21"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("limit must be between 1 and 20", error_stream.getvalue())
        unopened.assert_not_called()

    def test_missing_access_token_is_a_clear_configuration_error(self) -> None:
        exit_code, stdout, stderr, opener = self.run_main(
            ["--query", "repair"],
            env={"ESC_SEARCH_ENDPOINT": ENDPOINT},
            response=encoded_response(response_payload()),
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("ESC_SUPABASE_ACCESS_TOKEN is required", stderr)
        opener.assert_not_called()

    def test_unsafe_or_untrusted_endpoints_are_rejected_without_network(self) -> None:
        unsafe_endpoints = (
            "http://test-project.supabase.co/functions/v1/esc-search",
            "https://example.test/functions/v1/esc-search",
            "https://other-project.supabase.co/functions/v1/esc-search",
            "https://test-project.supabase.co/functions/v1/other-function",
        )
        for endpoint in unsafe_endpoints:
            with self.subTest(endpoint=endpoint):
                exit_code, stdout, stderr, opener = self.run_main(
                    ["--query", "repair", "--endpoint", endpoint],
                    env={"ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN},
                    response=encoded_response(response_payload()),
                )
                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout, "")
                self.assertIn("invalid_config", stderr)
                opener.assert_not_called()

    def test_missing_base_url_is_rejected_without_network(self) -> None:
        exit_code, stdout, stderr, opener = self.run_main(
            ["--query", "repair"],
            env={
                "ESC_SUPABASE_URL": "",
                "ESC_SEARCH_ENDPOINT": ENDPOINT,
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
            },
            response=encoded_response(response_payload()),
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("ESC_SUPABASE_URL is required", stderr)
        opener.assert_not_called()

    def test_redirect_handler_refuses_every_redirect(self) -> None:
        handler = search_esc.NoRedirectHandler()
        self.assertIsNone(
            handler.redirect_request(
                object(),
                object(),
                302,
                "Found",
                {},
                "https://other-project.supabase.co/functions/v1/esc-search",
            )
        )

    def test_country_requires_a_two_letter_code(self) -> None:
        exit_code, stdout, stderr, opener = self.run_main(
            ["--query", "repair", "--country", "Germany"],
            env={
                "ESC_SEARCH_ENDPOINT": ENDPOINT,
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
            },
            response=encoded_response(response_payload()),
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("two-letter code", stderr)
        opener.assert_not_called()

    def test_http_error_is_nonzero_and_credentials_are_not_printed(self) -> None:
        http_error = HTTPError(
            ENDPOINT,
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(f"{ACCESS_TOKEN} {API_KEY}".encode("utf-8")),
        )
        exit_code, stdout, stderr, _ = self.run_main(
            ["--query", "repair"],
            env={
                "ESC_SEARCH_ENDPOINT": ENDPOINT,
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
                "ESC_SUPABASE_API_KEY": API_KEY,
            },
            side_effect=http_error,
        )
        self.assertEqual(exit_code, 3)
        self.assertEqual(stdout, "")
        error = json.loads(stderr)
        self.assertEqual(error["code"], "http_error")
        self.assertIn("401", error["error"])
        self.assertNotIn(ACCESS_TOKEN, stderr)
        self.assertNotIn(API_KEY, stderr)

    def test_malformed_json_and_malformed_result_are_rejected(self) -> None:
        exit_code, stdout, stderr, _ = self.run_main(
            ["--query", "repair"],
            env={
                "ESC_SEARCH_ENDPOINT": ENDPOINT,
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
            },
            response=FakeResponse(b"not-json"),
        )
        self.assertEqual(exit_code, 4)
        self.assertEqual(stdout, "")
        self.assertIn("not valid JSON", stderr)

        malformed = response_payload()
        malformed["results"] = [{"project_identifier": "missing-fields"}]
        exit_code, stdout, stderr, _ = self.run_main(
            ["--query", "repair"],
            env={
                "ESC_SEARCH_ENDPOINT": ENDPOINT,
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
            },
            response=encoded_response(malformed),
        )
        self.assertEqual(exit_code, 4)
        self.assertEqual(stdout, "")
        self.assertIn("missing required fields", stderr)

        mismatched_count = response_payload()
        mismatched_count["count"] = 2
        exit_code, stdout, stderr, _ = self.run_main(
            ["--query", "repair"],
            env={
                "ESC_SEARCH_ENDPOINT": ENDPOINT,
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
            },
            response=encoded_response(mismatched_count),
        )
        self.assertEqual(exit_code, 4)
        self.assertEqual(stdout, "")
        self.assertIn("count does not match", stderr)

    def test_success_output_redacts_credentials_even_if_server_echoes_them(self) -> None:
        payload = response_payload(
            project_summary=f"server echoed {ACCESS_TOKEN} and {API_KEY}"
        )
        exit_code, stdout, stderr, _ = self.run_main(
            ["--query", "repair"],
            env={
                "ESC_SEARCH_ENDPOINT": ENDPOINT,
                "ESC_SUPABASE_ACCESS_TOKEN": ACCESS_TOKEN,
                "ESC_SUPABASE_API_KEY": API_KEY,
            },
            response=encoded_response(payload),
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertNotIn(ACCESS_TOKEN, stdout)
        self.assertNotIn(API_KEY, stdout)
        self.assertIn("[REDACTED]", stdout)


if __name__ == "__main__":
    unittest.main()
