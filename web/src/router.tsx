import { createRootRoute, createRoute, createRouter, Outlet, type RouterHistory } from "@tanstack/react-router";
import { type ApiClient, createApiClient } from "./api/client";
import { AccountantHome } from "./pages/accountant/AccountantHome";
import { ClientUpload } from "./pages/client/ClientUpload";
import { Home } from "./pages/Home";
import { Invitation } from "./pages/Invitation";
import { ManagerHome } from "./pages/manager/ManagerHome";
import { NotFound } from "./pages/NotFound";
import { SignIn } from "./pages/SignIn";

export interface AppRouterOptions {
  history?: RouterHistory;
  apiClient?: ApiClient;
}

export function createAppRouter({ history, apiClient }: AppRouterOptions = {}) {
  const client = apiClient ?? createApiClient();
  const rootRoute = createRootRoute({ component: Outlet, notFoundComponent: NotFound });
  const route = (path: string, component: () => React.JSX.Element) =>
    createRoute({ getParentRoute: () => rootRoute, path, component });

  const routeTree = rootRoute.addChildren([
    route("/", () => <Home apiClient={client} />),
    route("/entrar", SignIn),
    route("/convite/$token", Invitation),
    route("/chefe", ManagerHome),
    route("/contador", AccountantHome),
    route("/enviar/$token", ClientUpload),
  ]);
  return createRouter({ routeTree, ...(history ? { history } : {}) });
}
