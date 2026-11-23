import accountant from "./accountant.json";
import client from "./client.json";
import general from "./general.json";
import manager from "./manager.json";

/** Every screen text. Each one is also listed in docs/design/microcopy.md. */
export const copy = { general, manager, accountant, client } as const;
