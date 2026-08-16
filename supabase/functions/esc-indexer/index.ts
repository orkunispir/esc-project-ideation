import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const disabledResponse = {
  error: "indexer_disabled",
  message: "The one-time ESC embedding import is complete.",
};

function responseHeaders(): Headers {
  return new Headers({
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Origin": "*",
    "Content-Type": "application/json; charset=utf-8",
  });
}

// This function remains checked in to mirror the deployed state, but it is
// intentionally inert. It must never perform ingestion or call the database.
Deno.serve(() => new Response(JSON.stringify(disabledResponse), {
  status: 410,
  headers: responseHeaders(),
}));
