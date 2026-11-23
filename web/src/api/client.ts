import createClient from "openapi-fetch";
import type { paths } from "./schema";

export type ApiClientOptions = {
  /** API base address; empty means a path relative to the site. Default: VITE_API_URL. */
  baseUrl?: string;
  /** Replaces the network (used in tests). */
  fetch?: (request: Request) => Promise<Response>;
};

/**
 * HTTP client typed by the generated OpenAPI (schema.d.ts).
 * The /api/v1 prefix is already part of the generated paths (e.g. "/api/v1/health"), so the
 * base address is only VITE_API_URL (empty = path relative to the site itself).
 */
export function createApiClient(options: ApiClientOptions = {}) {
  const base = (options.baseUrl ?? import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");
  return createClient<paths>({
    baseUrl: base,
    ...(options.fetch ? { fetch: options.fetch } : {}),
  });
}

export type ApiClient = ReturnType<typeof createApiClient>;
