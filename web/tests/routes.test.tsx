// @vitest-environment jsdom
/**
 * WEB-01 c2: the routes of the three roles, the invite and the unknown address.
 *
 * Contract the implementation must follow (plan T3): `web/src/router.tsx` exports
 * `createAppRouter({ history })`, a TanStack Router built from code. The tests open each
 * address with an in-memory history. Only invented data (the token `abc123`).
 */
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { createAppRouter } from "../src/router";

const NOT_FOUND = "Página não encontrada. Confira o endereço ou volte ao início.";

const ROUTES: ReadonlyArray<readonly [string, string]> = [
  ["/entrar", "Entrar"],
  ["/convite/abc123", "Criar sua senha"],
  ["/chefe", "Área do chefe"],
  ["/contador", "Área do contador"],
  ["/enviar/abc123", "Envio do extrato"],
  ["/qualquer-coisa", NOT_FOUND],
];

function open(path: string) {
  const history = createMemoryHistory({ initialEntries: [path] });
  const router = createAppRouter({ history });
  return render(<RouterProvider router={router} />);
}

afterEach(cleanup);

describe("routes of the roles", () => {
  test.each(ROUTES)("route %s shows %s", async (path, text) => {
    open(path);
    const found = await screen.findAllByText(text);
    expect(found.length).toBeGreaterThan(0);
  });

  test("unknown address shows only the not-found message", async () => {
    const { container } = open("/qualquer-coisa");
    await screen.findByText(NOT_FOUND);
    for (const [, title] of ROUTES.slice(0, 5)) {
      expect(container.textContent).not.toContain(title);
    }
  });

  test("role routes do not show the not-found message", async () => {
    const { container } = open("/chefe");
    await screen.findByText("Área do chefe");
    expect(container.textContent).not.toContain(NOT_FOUND);
  });

  test("home has a link to /entrar", async () => {
    const { container } = open("/");
    await screen.findByRole("link");
    expect(container.querySelector('a[href="/entrar"]')).not.toBeNull();
  });
});
