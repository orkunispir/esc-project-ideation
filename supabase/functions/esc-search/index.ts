import "jsr:@supabase/functions-js/edge-runtime.d.ts";

import { buildAdminRequestHeaders, resolveAdminKey } from "./admin.ts";
import { parseSearchRequestBody, RequestValidationError } from "./request.ts";

const MODEL_NAME = "gte-small";
const embeddingSession = new Supabase.ai.Session(MODEL_NAME);
const EMBEDDING_DIMENSIONS = 384;

type SearchRpcResult = Record<string, unknown>;

class SearchRpcError extends Error {
  readonly status: number;

  constructor(status: number) {
    super("The search RPC failed");
    this.name = "SearchRpcError";
    this.status = status;
  }
}

function requestId(): string {
  return crypto.randomUUID();
}

function headers(): Headers {
  const responseHeaders = new Headers({
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Origin": Deno.env.get("ESC_ALLOWED_ORIGIN") ?? "*",
    "Content-Type": "application/json; charset=utf-8",
    "Vary": "Origin",
  });
  return responseHeaders;
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: headers(),
  });
}

function logServerError(id: string, stage: string, error: unknown): void {
  const record = typeof error === "object" && error !== null
    ? error as Record<string, unknown>
    : {};
  const detail = {
    error_name: error instanceof Error ? error.name : typeof error,
    error_code: typeof record.code === "string" ? record.code : undefined,
    status: typeof record.status === "number" ? record.status : undefined,
  };

  console.error(JSON.stringify({
    event: "esc_search_error",
    request_id: id,
    stage,
    ...detail,
  }));
}

function logServerEvent(id: string, event: string, fields: Record<string, unknown> = {}): void {
  console.info(JSON.stringify({ event, request_id: id, ...fields }));
}

function genericError(id: string, error: "invalid_request" | "service_unavailable" | "method_not_allowed", status: number): Response {
  const messages = {
    invalid_request: "The search request is invalid.",
    service_unavailable: "Search is temporarily unavailable.",
    method_not_allowed: "Only POST requests are supported.",
  } as const;

  return jsonResponse({
    error,
    message: messages[error],
    request_id: id,
  }, status);
}

function embeddingVector(value: unknown): number[] {
  if (!Array.isArray(value)) {
    throw new Error("Embedding model returned a non-array result");
  }

  const vector = value.map((component) => {
    if (typeof component !== "number" || !Number.isFinite(component)) {
      throw new Error("Embedding model returned a non-finite component");
    }
    return component;
  });

  if (vector.length !== EMBEDDING_DIMENSIONS) {
    throw new Error(`Embedding model returned ${vector.length} dimensions`);
  }

  return vector;
}

async function search(request: Request): Promise<Response> {
  const id = requestId();

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: headers() });
  }

  if (request.method !== "POST") {
    logServerEvent(id, "esc_search_rejected_method", { method: request.method });
    return genericError(id, "method_not_allowed", 405);
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch (error) {
    logServerError(id, "parse_json", error);
    return genericError(id, "invalid_request", 400);
  }

  let parsed;
  try {
    parsed = parseSearchRequestBody(body);
  } catch (error) {
    logServerError(id, "validate_request", error);
    if (error instanceof RequestValidationError) {
      return genericError(id, "invalid_request", 400);
    }
    return genericError(id, "service_unavailable", 503);
  }

  let projectUrl: string;
  let adminKey: string;
  try {
    projectUrl = (Deno.env.get("SUPABASE_URL") ?? "").replace(/\/+$/, "");
    if (!projectUrl) throw new Error("SUPABASE_URL is not configured");
    adminKey = resolveAdminKey(Deno.env);
  } catch (error) {
    logServerError(id, "configure_admin_client", error);
    return genericError(id, "service_unavailable", 503);
  }

  let vector: number[];
  try {
    const output = await embeddingSession.run(parsed.query, {
      mean_pool: true,
      normalize: true,
    });
    vector = embeddingVector(output);
  } catch (error) {
    logServerError(id, "generate_embedding", error);
    return genericError(id, "service_unavailable", 503);
  }

  const filterCountry = parsed.filterCountry?.toUpperCase() ?? null;
  try {
    const rpcResponse = await fetch(`${projectUrl}/rest/v1/rpc/search_esc_projects`, {
      method: "POST",
      headers: buildAdminRequestHeaders(adminKey),
      body: JSON.stringify({
        query_embedding: JSON.stringify(vector),
        match_count: parsed.matchCount,
        filter_country: filterCountry,
        filter_action: parsed.filterAction,
        filter_funding_year: parsed.filterFundingYear,
      }),
    });

    if (!rpcResponse.ok) {
      await rpcResponse.body?.cancel();
      throw new SearchRpcError(rpcResponse.status);
    }

    const data: unknown = await rpcResponse.json();
    if (!Array.isArray(data)) throw new Error("search RPC returned a non-array result");

    const results = data as SearchRpcResult[];
    logServerEvent(id, "esc_search_completed", { result_count: results.length });
    return jsonResponse({
      request_id: id,
      query: parsed.query,
      model: MODEL_NAME,
      filters: {
        country: filterCountry,
        action: parsed.filterAction,
        funding_year: parsed.filterFundingYear,
      },
      count: results.length,
      results,
    });
  } catch (error) {
    logServerError(id, "search_rpc", error);
    return genericError(id, "service_unavailable", 503);
  }
}

Deno.serve(search);
