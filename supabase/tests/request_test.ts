import {
  parseSearchRequestBody,
  RequestValidationError,
} from "../functions/esc-search/request.ts";
import {
  buildAdminRequestHeaders,
  resolveAdminKey,
} from "../functions/esc-search/admin.ts";

type TestFunction = () => void | Promise<void>;

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  assert(actualJson === expectedJson, `${message}: ${actualJson} !== ${expectedJson}`);
}

function assertThrows(fn: () => unknown, expectedCode: string): void {
  try {
    fn();
  } catch (error) {
    assert(error instanceof RequestValidationError, "expected request validation error");
    assertEqual(error.code, expectedCode, "unexpected validation code");
    return;
  }
  throw new Error(`expected ${expectedCode} to be thrown`);
}

const tests: Array<[string, TestFunction]> = [
  ["parses and normalizes a complete search request", () => {
    const parsed = parseSearchRequestBody({
      query: "  youth climate action  ",
      match_count: 7,
      filter_country: "  de ",
      filter_action: "Volunteering Projects",
      filter_funding_year: 2024,
    });

    assertEqual(parsed, {
      query: "youth climate action",
      matchCount: 7,
      filterCountry: "DE",
      filterAction: "Volunteering Projects",
      filterFundingYear: 2024,
    }, "complete request normalization");
  }],
  ["applies the default match count and null filters", () => {
    const parsed = parseSearchRequestBody({ query: "inclusion" });
    assertEqual(parsed.matchCount, 10, "default match count");
    assertEqual(parsed.filterCountry, null, "default country");
    assertEqual(parsed.filterAction, null, "default action");
    assertEqual(parsed.filterFundingYear, null, "default year");
  }],
  ["rejects malformed and unsafe request shapes", () => {
    assertThrows(() => parseSearchRequestBody(null), "invalid_body");
    assertThrows(() => parseSearchRequestBody({ query: "" }), "empty_query");
    assertThrows(() => parseSearchRequestBody({ query: "x", match_count: 0 }), "invalid_match_count");
    assertThrows(() => parseSearchRequestBody({ query: "x", match_count: 21 }), "invalid_match_count");
    assertThrows(() => parseSearchRequestBody({ query: "x", filter_country: "Germany" }), "invalid_country");
    assertThrows(() => parseSearchRequestBody({ query: "x", filter_funding_year: 1999 }), "invalid_funding_year");
    assertThrows(() => parseSearchRequestBody({ query: "x", unexpected: true }), "unknown_field");
  }],
  ["prefers the current secret-key JSON dictionary", () => {
    const env = {
      get(name: string): string | undefined {
        return {
          SUPABASE_SECRET_KEYS: JSON.stringify({ default: "current-test-key" }),
          SUPABASE_SERVICE_ROLE_KEY: "legacy-test-key",
        }[name];
      },
    };
    assertEqual(resolveAdminKey(env), "current-test-key", "current key resolution");
  }],
  ["falls back to the legacy service-role variable", () => {
    const env = {
      get(name: string): string | undefined {
        return { SUPABASE_SERVICE_ROLE_KEY: "legacy-test-key" }[name];
      },
    };
    assertEqual(resolveAdminKey(env), "legacy-test-key", "legacy key resolution");
  }],
  ["does not select an arbitrary named secret", () => {
    const env = {
      get(name: string): string | undefined {
        return {
          SUPABASE_SECRET_KEYS: JSON.stringify({ unrelated: "wrong-test-key" }),
          SUPABASE_SERVICE_ROLE_KEY: "legacy-test-key",
        }[name];
      },
    };
    assertEqual(resolveAdminKey(env), "legacy-test-key", "safe named-key fallback");
  }],
  ["rejects an environment with no usable admin key", () => {
    const env = { get: () => undefined };
    let failed = false;
    try {
      resolveAdminKey(env);
    } catch {
      failed = true;
    }
    assert(failed, "missing admin key should fail closed");
  }],
  ["sends modern secret keys only in the apikey header", () => {
    assertEqual(buildAdminRequestHeaders("sb_secret_test"), {
      apikey: "sb_secret_test",
      "Content-Type": "application/json",
    }, "modern secret-key headers");
  }],
  ["keeps legacy service-role JWT authorization compatibility", () => {
    assertEqual(buildAdminRequestHeaders("legacy.jwt.value"), {
      apikey: "legacy.jwt.value",
      "Content-Type": "application/json",
      Authorization: "Bearer legacy.jwt.value",
    }, "legacy service-role headers");
  }],
];

if (typeof Deno !== "undefined") {
  for (const [name, test] of tests) Deno.test(name, test);
} else {
  // The workspace does not necessarily include Deno. This fallback keeps the
  // same no-network test file executable with Node's TypeScript stripping.
  for (const [name, test] of tests) {
    await test();
    console.log(`ok - ${name}`);
  }
}
