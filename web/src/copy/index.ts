import chefe from "./chefe.json";
import cliente from "./cliente.json";
import contador from "./contador.json";
import geral from "./geral.json";

/** Todos os textos de tela. Cada texto também está em docs/design/microcopy.md. */
export const copy = { geral, chefe, contador, cliente } as const;
