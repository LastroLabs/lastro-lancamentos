import { createRootRoute, createRoute, createRouter, Outlet, type RouterHistory } from "@tanstack/react-router";
import { type ApiClient, createApiClient } from "./api/client";
import { Contador } from "./pages/accountant/Contador";
import { Convite } from "./pages/Convite";
import { Envio } from "./pages/client/Envio";
import { Entrar } from "./pages/Entrar";
import { Home } from "./pages/Home";
import { Chefe } from "./pages/manager/Chefe";
import { NaoEncontrada } from "./pages/NaoEncontrada";

export interface AppRouterOptions {
  history?: RouterHistory;
  apiClient?: ApiClient;
}

export function createAppRouter({ history, apiClient }: AppRouterOptions = {}) {
  const client = apiClient ?? createApiClient();
  const rootRoute = createRootRoute({ component: Outlet, notFoundComponent: NaoEncontrada });
  const route = (path: string, component: () => React.JSX.Element) =>
    createRoute({ getParentRoute: () => rootRoute, path, component });

  const routeTree = rootRoute.addChildren([
    route("/", () => <Home apiClient={client} />),
    route("/entrar", Entrar),
    route("/convite/$token", Convite),
    route("/chefe", Chefe),
    route("/contador", Contador),
    route("/enviar/$token", Envio),
  ]);
  return createRouter({ routeTree, ...(history ? { history } : {}) });
}
