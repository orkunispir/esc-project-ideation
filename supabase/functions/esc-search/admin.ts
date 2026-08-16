export type EnvironmentReader = {
  get(name: string): string | undefined;
};

export class AdminKeyConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AdminKeyConfigurationError";
  }
}

export function buildAdminRequestHeaders(key: string): Record<string, string> {
  const headers: Record<string, string> = {
    apikey: key,
    "Content-Type": "application/json",
  };

  // Modern Supabase secret keys are not JWTs and must not be placed in an
  // Authorization: Bearer header. Legacy service-role keys remain JWT-based.
  if (!key.startsWith("sb_secret_")) {
    headers.Authorization = `Bearer ${key}`;
  }

  return headers;
}

function firstSecretValue(value: unknown): string | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;

  const record = value as Record<string, unknown>;
  const preferredNames = ["default", "service_role"];
  for (const name of preferredNames) {
    const candidate = record[name];
    if (typeof candidate === "string" && candidate.trim().length > 0) {
      return candidate.trim();
    }
  }

  return null;
}

/**
 * Resolve the server-only admin key. New projects expose a JSON dictionary in
 * SUPABASE_SECRET_KEYS; older deployments expose SUPABASE_SERVICE_ROLE_KEY.
 */
export function resolveAdminKey(env: EnvironmentReader): string {
  const secretKeysJson = env.get("SUPABASE_SECRET_KEYS");
  if (secretKeysJson && secretKeysJson.trim().length > 0) {
    try {
      const key = firstSecretValue(JSON.parse(secretKeysJson));
      if (key) return key;
    } catch {
      // Fall through to the legacy variable. The caller logs only a generic
      // configuration failure and never logs the secret value.
    }
  }

  const legacyKey = env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (legacyKey && legacyKey.trim().length > 0) return legacyKey.trim();

  throw new AdminKeyConfigurationError(
    "No Supabase secret key is configured for server-side search",
  );
}
