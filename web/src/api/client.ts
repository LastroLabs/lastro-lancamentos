import createClient from "openapi-fetch";
import type { paths } from "./schema";

export type ApiClientOptions = {
  /** Endereço base da API; vazio usa caminho relativo. Padrão: VITE_API_URL. */
  baseUrl?: string;
  /** Substitui a rede (usado nos testes). */
  fetch?: (request: Request) => Promise<Response>;
};

/**
 * Cliente HTTP tipado pelo OpenAPI gerado (schema.d.ts).
 * O prefixo /api/v1 já faz parte dos caminhos gerados (ex.: "/api/v1/health"); por isso o
 * endereço base é só o de VITE_API_URL (vazio = caminho relativo ao próprio site).
 */
export function createApiClient(options: ApiClientOptions = {}) {
  const base = (options.baseUrl ?? import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");
  return createClient<paths>({
    baseUrl: base,
    ...(options.fetch ? { fetch: options.fetch } : {}),
  });
}

export type ApiClient = ReturnType<typeof createApiClient>;
