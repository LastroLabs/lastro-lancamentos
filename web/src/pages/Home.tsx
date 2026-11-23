import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import type { ApiClient } from "../api/client";
import { copy } from "../copy";

type HealthState = "checking" | "up" | "down";

function fetchHealth(apiClient: ApiClient): Promise<HealthState> {
  return apiClient
    .GET("/api/v1/health")
    .then(({ data }): HealthState => (data?.api === "up" && data.database === "connected" ? "up" : "down"))
    .catch((): HealthState => "down");
}

export function Home({ apiClient }: { apiClient: ApiClient }) {
  const [health, setHealth] = useState<HealthState>("checking");

  useEffect(() => {
    let active = true;
    fetchHealth(apiClient).then((result) => {
      if (active) setHealth(result);
    });
    return () => {
      active = false;
    };
  }, [apiClient]);

  const text = {
    checking: copy.general.healthChecking,
    up: copy.general.healthUp,
    down: copy.general.healthDown,
  }[health];

  return (
    <main>
      <p>{text}</p>
      <Link to="/entrar">{copy.general.goToSignIn}</Link>
    </main>
  );
}
