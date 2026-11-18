// Fichas do primeiro lote (onda S1), copiadas de features/*.json da branch fichas/onda-s1 em 18/11/2026.
// Estão EM REVISÃO: ainda não foram mescladas na developer. Atualize por PR quando entrarem.
// Só metadados; critérios e testes ficam nas fichas.

export interface Ficha {
	id: string;
	titulo: string;
	modulo: string;
	requisitos: string[];
	onda: number;
	estado: string;
	responsavel: string | null;
	dependeDe: string[];
	/** true enquanto a ficha só existe na branch de revisão. */
	emRevisao: boolean;
}

export const fichas: Ficha[] = [
	{ id: "ACE-01", titulo: "Entrar com login individual e encerrar a sessão", modulo: "acesso", requisitos: ["RF-AUT-01"], onda: 2, estado: "not_started", responsavel: "arthurlleite", dependeDe: ["NUC-01"], emRevisao: true },
	{ id: "ACE-02", titulo: "Cadastrar contador e atribuir cliente pelo chefe", modulo: "acesso", requisitos: ["RF-AUT-03"], onda: 2, estado: "not_started", responsavel: "camposs04", dependeDe: ["ACE-01", "CAD-03"], emRevisao: true },
	{ id: "ACE-03", titulo: "Mostrar a cada contador só os clientes da sua carteira", modulo: "acesso", requisitos: ["RF-AUT-02", "RF-SEG-02"], onda: 2, estado: "not_started", responsavel: "RaissaOliveira19", dependeDe: ["ACE-02", "NUC-02"], emRevisao: true },
	{ id: "ACE-04", titulo: "Revogar acesso do contador anterior ao reatribuir cliente", modulo: "acesso", requisitos: ["RF-AUT-04"], onda: 2, estado: "not_started", responsavel: "arthurlleite", dependeDe: ["ACE-02", "ACE-03"], emRevisao: true },
	{ id: "ACE-05", titulo: "Gerar link do cliente com validade e permitir invalidar", modulo: "acesso", requisitos: ["RF-SEG-01"], onda: 2, estado: "not_started", responsavel: "arthurlleite", dependeDe: ["ACE-02", "NUC-02"], emRevisao: true },
	{ id: "CAD-01", titulo: "Validar CNPJ numérico e alfanumérico do cliente", modulo: "cadastro", requisitos: ["RF-CAD-01"], onda: 1, estado: "not_started", responsavel: "marrathomaz", dependeDe: [], emRevisao: true },
	{ id: "CAD-02", titulo: "Ler a planilha do plano de contas e apontar linha inválida", modulo: "cadastro", requisitos: ["RF-CAD-03"], onda: 1, estado: "not_started", responsavel: "camposs04", dependeDe: [], emRevisao: true },
	{ id: "CAD-03", titulo: "Cadastrar cliente com nome e CNPJ", modulo: "cadastro", requisitos: ["RF-CAD-01", "RF-AUT-03"], onda: 2, estado: "not_started", responsavel: "guin409", dependeDe: ["CAD-01", "ACE-01", "NUC-02"], emRevisao: true },
	{ id: "CAD-04", titulo: "Informar as contas bancárias do cliente com banco e apelido", modulo: "cadastro", requisitos: ["RF-CAD-02"], onda: 2, estado: "not_started", responsavel: "marrathomaz", dependeDe: ["ACE-02", "NUC-02"], emRevisao: true },
	{ id: "CAD-05", titulo: "Carregar o plano de contas do cliente por planilha", modulo: "cadastro", requisitos: ["RF-CAD-03"], onda: 2, estado: "not_started", responsavel: "marrathomaz", dependeDe: ["CAD-02", "HAR-03", "ACE-02", "NUC-02"], emRevisao: true },
	{ id: "CAD-06", titulo: "Indicar a conta transitória do cliente dentre as do plano", modulo: "cadastro", requisitos: ["RF-CAD-04"], onda: 2, estado: "not_started", responsavel: "RaissaOliveira19", dependeDe: ["CAD-05"], emRevisao: true },
	{ id: "CAD-07", titulo: "Cadastrar os sócios do cliente e mostrá-los na ficha", modulo: "cadastro", requisitos: ["RF-CAD-06"], onda: 2, estado: "not_started", responsavel: "marrathomaz", dependeDe: ["ACE-02", "NUC-02"], emRevisao: true },
	{ id: "HAR-02", titulo: "Filtrar hx state por estado e resumir só o que pede atenção", modulo: "harness", requisitos: [], onda: 1, estado: "passing", responsavel: "caio-nascime", dependeDe: [], emRevisao: false },
	{ id: "HAR-03", titulo: "Gerar fixtures e gabarito sintéticos por semente fixa", modulo: "harness", requisitos: ["BD-07"], onda: 2, estado: "not_started", responsavel: "caio-nascime", dependeDe: ["HAR-04"], emRevisao: true },
	{ id: "HAR-04", titulo: "Alinhar validação de fichas e check-clean às decisões de 18/11", modulo: "harness", requisitos: [], onda: 1, estado: "not_started", responsavel: "caio-nascime", dependeDe: [], emRevisao: true },
	{ id: "HX-10", titulo: "Rodar verify e check-clean na CI a cada push e pull request", modulo: "ci", requisitos: [], onda: 1, estado: "passing", responsavel: "caio-nascime", dependeDe: [], emRevisao: false },
	{ id: "IA-01", titulo: "Remover CPF, CNPJ, agência, conta e nomes de descrições", modulo: "ia", requisitos: ["RF-SEG-03"], onda: 1, estado: "not_started", responsavel: "arthurlleite", dependeDe: [], emRevisao: true },
	{ id: "IA-02", titulo: "Enviar ao serviço de IA só descrições anonimizadas", modulo: "ia", requisitos: ["RF-SEG-03"], onda: 2, estado: "not_started", responsavel: "camposs04", dependeDe: ["IA-01", "HAR-03"], emRevisao: true },
	{ id: "NUC-01", titulo: "Responder a saúde da API com o banco e as migrações", modulo: "nucleo", requisitos: ["ARQ-01", "ARQ-08", "BD-01"], onda: 1, estado: "not_started", responsavel: "guin409", dependeDe: [], emRevisao: true },
	{ id: "NUC-02", titulo: "Decidir o acesso por escritório, papel e carteira", modulo: "nucleo", requisitos: ["BD-02"], onda: 1, estado: "not_started", responsavel: "RaissaOliveira19", dependeDe: [], emRevisao: true },
	{ id: "NUC-03", titulo: "Isolar no banco os dados de cada escritório", modulo: "nucleo", requisitos: ["RF-SEG-02", "BD-02"], onda: 2, estado: "not_started", responsavel: "RaissaOliveira19", dependeDe: ["NUC-01", "CAD-03"], emRevisao: true },
];

/** Fichas que citam o requisito em `requisitos`. */
export const fichasDoRequisito = (id: string) => fichas.filter((f) => f.requisitos.includes(id));
