import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import type { ApiClient } from "../api/client";
import { copy } from "../copy";

type Saude = "verificando" | "no_ar" | "fora_do_ar";

function consultarSaude(apiClient: ApiClient): Promise<Saude> {
  return apiClient
    .GET("/api/v1/health")
    .then(({ data }): Saude => (data?.api === "up" && data.database === "connected" ? "no_ar" : "fora_do_ar"))
    .catch((): Saude => "fora_do_ar");
}

export function Home({ apiClient }: { apiClient: ApiClient }) {
  const [saude, setSaude] = useState<Saude>("verificando");

  useEffect(() => {
    let ativo = true;
    consultarSaude(apiClient).then((resultado) => {
      if (ativo) setSaude(resultado);
    });
    return () => {
      ativo = false;
    };
  }, [apiClient]);

  const texto = {
    verificando: copy.geral.saudeVerificando,
    no_ar: copy.geral.saudeNoAr,
    fora_do_ar: copy.geral.saudeForaDoAr,
  }[saude];

  return (
    <main>
      <p>{texto}</p>
      <Link to="/entrar">{copy.geral.irParaEntrar}</Link>
    </main>
  );
}
