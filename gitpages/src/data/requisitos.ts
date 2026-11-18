// Tipos e helpers sobre src/data/requisitos.json.
// O JSON é gerado por scripts/gerar-requisitos.mjs; não edite o JSON à mão.
import dados from './requisitos.json';

export type Prioridade = 'Must' | 'Should' | 'Could' | "Won't";
export type Selo = 'NOVO' | 'AJUSTADO' | null;

export interface Requisito {
	id: string;
	selo: Selo;
	prioridade: Prioridade;
	area: string;
	requisito: string;
	/** Critério de aceitação; nos Won't, o motivo. */
	criterio: string;
	origem: string;
	decisoes: string[];
	aDefinir: boolean;
	dores: string[];
	/** Frente da equipe, pela tabela de frentes; null quando a fonte não cita o prefixo. */
	frente: string | null;
	/** Módulo src/lastro/<modulo>/: módulos aprovados (ARQ-01); vínculo pelo prefixo do ID. Quando há ficha, vale o módulo da ficha. */
	modulo: string | null;
}

export interface Decisao { id: string; decisao: string; afeta: string[]; recomendacao: string; status: string; deliberacao: string }
export interface Dor { dor: string; relatou: string; resposta: string; requisitos: string[] }

export const requisitos = dados.requisitos as Requisito[];
export const decisoes = dados.decisoes as Decisao[];
export const dores = dados.dores as Dor[];
export const frentes = dados.frentes as { frente: string; prefixos: string[] }[];
export const notas = dados.notas;
export const versaoRequisitos = dados.versaoRequisitos;

export const PRIORIDADES: Prioridade[] = ['Must', 'Should', 'Could', "Won't"];

export const DESCRICAO_PRIORIDADE: Record<Prioridade, string> = {
	Must: 'Sem isso o MVP não funciona',
	Should: 'Importante, com contorno manual',
	Could: 'Só se sobrar tempo',
	"Won't": 'Fora desta versão',
};

/** Classe CSS por prioridade (cores definidas em custom.css). */
export const classePrioridade = (p: Prioridade) => `req-prio--${p === "Won't" ? 'wont' : p.toLowerCase()}`;

export const porPrioridade = (p: Prioridade) => requisitos.filter((r) => r.prioridade === p);

/** Áreas na ordem em que aparecem nos requisitos (ordem do documento). */
export function areas(p?: Prioridade): string[] {
	return [...new Set((p ? porPrioridade(p) : requisitos).map((r) => r.area))];
}

export const porArea = (area: string, p?: Prioridade) =>
	requisitos.filter((r) => r.area === area && (!p || r.prioridade === p));

export const prefixo = (id: string) => id.split('-')[1];

/** Prefixos e a área de cada um, na ordem do documento. */
export function prefixos(): { prefixo: string; area: string; total: number }[] {
	const mapa = new Map<string, { area: string; total: number }>();
	for (const r of requisitos) {
		const p = prefixo(r.id);
		const atual = mapa.get(p);
		if (atual) atual.total++;
		else mapa.set(p, { area: r.area, total: 1 });
	}
	return [...mapa].map(([p, v]) => ({ prefixo: p, ...v }));
}

/**
 * Fontes citadas na coluna Origem, sem o comentário entre parênteses.
 * Ex.: "v2 (passo 1), Esc.2 (confiança leva cerca de 3 meses)" → ["v2", "Esc.2"].
 */
export function origens(r: Requisito): string[] {
	const partes: string[] = [];
	let nivel = 0;
	let atual = '';
	for (const c of r.origem) {
		if (c === '(') nivel++;
		if (c === ')') nivel--;
		if (c === ',' && nivel === 0) { partes.push(atual); atual = ''; continue; }
		atual += c;
	}
	partes.push(atual);
	return [...new Set(partes.map((p) => p.replace(/\(.*\)/, '').trim()).filter(Boolean))];
}

/** Ordem fixa das fontes, como na legenda da página de requisitos. */
export const FONTES_ORDEM = ['v2', 'Esc.1', 'Esc.2', 'Ata', 'Proposta', 'Equipe'];

export const ancora = (id: string) => id.toLowerCase();

const BASE = import.meta.env.BASE_URL.replace(/\/?$/, '/');
export const linkRequisito = (id: string) => `${BASE}visao/requisitos/#${ancora(id)}`;
export const linkDecisoes = () => `${BASE}decisoes/#decisões-dos-requisitos-d-01-a-d-09`;
export const link = (caminho: string) => `${BASE}${caminho.replace(/^\//, '')}`;

export function contagem() {
	const porP = Object.fromEntries(PRIORIDADES.map((p) => [p, porPrioridade(p).length])) as Record<Prioridade, number>;
	return {
		...porP,
		total: requisitos.length,
		novo: requisitos.filter((r) => r.selo === 'NOVO').length,
		ajustado: requisitos.filter((r) => r.selo === 'AJUSTADO').length,
		aDefinir: requisitos.filter((r) => r.aDefinir).length,
		comDecisao: requisitos.filter((r) => r.decisoes.length).length,
	};
}
