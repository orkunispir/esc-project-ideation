export type SearchRequest = {
  query: string;
  matchCount: number;
  filterCountry: string | null;
  filterAction: string | null;
  filterFundingYear: number | null;
};

export class RequestValidationError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "RequestValidationError";
    this.code = code;
  }
}

const DEFAULT_MATCH_COUNT = 10;
const MAX_MATCH_COUNT = 20;
const MAX_QUERY_LENGTH = 1000;
const MAX_FILTER_LENGTH = 160;
const MIN_FUNDING_YEAR = 2000;
const MAX_FUNDING_YEAR = 2100;

const allowedFields = new Set([
  "query",
  "match_count",
  "filter_country",
  "filter_action",
  "filter_funding_year",
]);

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readOptionalFilter(
  body: UnknownRecord,
  field: "filter_country" | "filter_action",
): string | null {
  const value = body[field];
  if (value === undefined || value === null) return null;
  if (typeof value !== "string") {
    throw new RequestValidationError("invalid_filter", `${field} must be a string or null`);
  }

  const normalized = value.trim();
  if (normalized.length === 0) return null;
  if (normalized.length > MAX_FILTER_LENGTH) {
    throw new RequestValidationError("invalid_filter", `${field} is too long`);
  }
  return normalized;
}

function readCountryFilter(body: UnknownRecord): string | null {
  const country = readOptionalFilter(body, "filter_country");
  if (country === null) return null;
  if (!/^[A-Za-z]{2}$/.test(country)) {
    throw new RequestValidationError(
      "invalid_country",
      "filter_country must be a two-letter country code",
    );
  }
  return country.toUpperCase();
}

function readOptionalInteger(
  body: UnknownRecord,
  field: "match_count" | "filter_funding_year",
): number | null {
  const value = body[field];
  if (value === undefined || value === null) return null;
  if (typeof value !== "number" || !Number.isFinite(value) || !Number.isInteger(value)) {
    throw new RequestValidationError("invalid_number", `${field} must be an integer or null`);
  }
  return value;
}

export function parseSearchRequestBody(body: unknown): SearchRequest {
  if (!isRecord(body)) {
    throw new RequestValidationError("invalid_body", "body must be a JSON object");
  }

  for (const field of Object.keys(body)) {
    if (!allowedFields.has(field)) {
      throw new RequestValidationError("unknown_field", `unsupported field: ${field}`);
    }
  }

  const rawQuery = body.query;
  if (typeof rawQuery !== "string") {
    throw new RequestValidationError("missing_query", "query must be a string");
  }

  const query = rawQuery.trim();
  if (query.length === 0) {
    throw new RequestValidationError("empty_query", "query must not be empty");
  }
  if (query.length > MAX_QUERY_LENGTH) {
    throw new RequestValidationError("query_too_long", "query is too long");
  }

  const rawMatchCount = readOptionalInteger(body, "match_count");
  const matchCount = rawMatchCount ?? DEFAULT_MATCH_COUNT;
  if (matchCount < 1 || matchCount > MAX_MATCH_COUNT) {
    throw new RequestValidationError(
      "invalid_match_count",
      `match_count must be between 1 and ${MAX_MATCH_COUNT}`,
    );
  }

  const filterFundingYear = readOptionalInteger(body, "filter_funding_year");
  if (
    filterFundingYear !== null &&
    (filterFundingYear < MIN_FUNDING_YEAR || filterFundingYear > MAX_FUNDING_YEAR)
  ) {
    throw new RequestValidationError(
      "invalid_funding_year",
      `filter_funding_year must be between ${MIN_FUNDING_YEAR} and ${MAX_FUNDING_YEAR}`,
    );
  }

  return {
    query,
    matchCount,
    filterCountry: readCountryFilter(body),
    filterAction: readOptionalFilter(body, "filter_action"),
    filterFundingYear,
  };
}
