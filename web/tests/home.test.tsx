// @vitest-environment jsdom
/**
 * WEB-01 c4: the home page asks the API health through the generated client.
 *
 * Contract the implementation must follow (plan D5, T4, T5):
 *  - `web/src/api/client.ts` exports `createApiClient({ baseUrl?, fetch? })` (openapi-fetch,
 *    prefix /api/v1; the injected `fetch` replaces the network);
 *  - `web/src/router.tsx` exports `createAppRouter({ history, apiClient? })`; `/` is the home.
 * Only invented answers.
 */
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { createApiClient } from "../src/api/client";
import { createAppRouter } from "../src/router";

const UP = "Sistema no ar.";
const DOWN = "O sistema está fora do ar. Tente de novo em alguns minutos.";
const TECHNICAL = /503|200|\bapi\b|health|saude|status|http|fetch|network|rede|json|banco|database|erro/i;

type FakeFetch = (request: Request) => Promise<Response>;

function renderHome(fakeFetch: FakeFetch) {
  const apiClient = createApiClient({ baseUrl: "http://api.test", fetch: fakeFetch });
  const history = createMemoryHistory({ initialEntries: ["/"] });
  const router = createAppRouter({ history, apiClient });
  return render(<RouterProvider router={router} />);
}

afterEach(cleanup);

describe("health on the home page", () => {
  test("200 with api up and database connected shows the system is up", async () => {
    const requested: string[] = [];
    const { container } = renderHome(async (request) => {
      requested.push(new URL(request.url).pathname);
      return Response.json({ api: "up", database: "connected" });
    });
    await screen.findByText(UP);
    expect(requested).toContain("/api/v1/health");
    expect(container.textContent).not.toContain(DOWN);
    expect(container.textContent).not.toMatch(TECHNICAL);
  });

  test("503 shows the system is down, without technical terms", async () => {
    const { container } = renderHome(async () =>
      Response.json(
        {
          type: "about:blank",
          title: "Serviço indisponível",
          status: 503,
          detail: "Texto inventado do problema.",
        },
        { status: 503, headers: { "content-type": "application/problem+json" } },
      ),
    );
    await screen.findByText(DOWN);
    expect(container.textContent).not.toContain(UP);
    expect(container.textContent).not.toMatch(TECHNICAL);
    expect(container.textContent).not.toContain("Serviço indisponível");
  });

  test("network failure shows the system is down, without technical terms", async () => {
    const { container } = renderHome(async () => {
      throw new TypeError("Failed to fetch");
    });
    await screen.findByText(DOWN);
    expect(container.textContent).not.toContain(UP);
    expect(container.textContent).not.toMatch(TECHNICAL);
    expect(container.textContent).not.toContain("Failed");
  });

  test("200 with an unexpected body counts as down", async () => {
    renderHome(async () => Response.json({ qualquer: "coisa" }));
    await screen.findByText(DOWN);
    expect(screen.queryByText(UP)).toBeNull();
  });
});
