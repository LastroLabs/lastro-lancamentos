// Gera src/data/requisitos.json a partir das páginas do site.
// Uso (dentro de gitpages/): node scripts/gerar-requisitos.mjs
//
// Fontes lidas (nada é transcrito à mão):
//   - src/data/fonte/requisitos-v0.2.md           tabelas dos requisitos (texto original da página)
//   - src/content/docs/decisoes/index.md          coluna "Afeta" de D-01 a D-09
//   - src/content/docs/visao/cenario.md           tabela "Da dor ao requisito"
//   - src/content/docs/home/equipe.mdx            tabela "As frentes da arquitetura"
//   - src/content/docs/arquitetura/visao-geral.mdx  módulos src/lastro/*
//
// O script falha (exit 1) se as contagens não forem 56 Must, 11 Should, 6 Could e 12 Won't.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ler = (p) => fs.readFileSync(path.join(raiz, p), 'utf8');

const FONTES = {
	requisitos: 'src/data/fonte/requisitos-v0.2.md',
	decisoes: 'src/content/docs/decisoes/index.md',
	cenario: 'src/content/docs/visao/cenario.md',
	equipe: 'src/content/docs/home/equipe.mdx',
	arquitetura: 'src/content/docs/arquitetura/visao-geral.mdx',
};

const ESPERADO = { Must: 56, Should: 11, Could: 6, "Won't": 12 };

// ---------------------------------------------------------------- utilitários
const celulas = (linha) => linha.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
const ehSeparador = (linha) => /^\|\s*-{3,}/.test(linha.trim());

/** Linhas de tabela (sem cabeçalho e separador) dentro da seção que começa com `titulo`. */
function tabelaDaSecao(md, titulo) {
	const linhas = md.split('\n');
	const ini = linhas.findIndex((l) => l.startsWith(titulo));
	if (ini < 0) throw new Error(`Seção não encontrada: ${titulo}`);
	const nivel = titulo.match(/^#+/)[0].length;
	const rows = [];
	let viuCabecalho = false;
	for (let i = ini + 1; i < linhas.length; i++) {
		const l = linhas[i];
		const h = l.match(/^(#+)\s/);
		if (h && h[1].length <= nivel) break;
		if (!l.trim().startsWith('|')) {
			if (rows.length) break; // fim da primeira tabela da seção
			continue;
		}
		if (ehSeparador(l)) { viuCabecalho = true; continue; }
		if (!viuCabecalho) continue; // linha de cabeçalho
		rows.push(celulas(l));
	}
	return rows;
}

// ---------------------------------------------------------------- 1. requisitos
const mdReq = ler(FONTES.requisitos);
const requisitos = [];
let prioridade = null;
let area = null;
for (const linha of mdReq.split('\n')) {
	const h2 = linha.match(/^## (.+)/);
	if (h2) {
		const t = h2[1].trim();
		prioridade = t === 'Must' ? 'Must' : t === 'Should' ? 'Should' : t === 'Could' ? 'Could' : t.startsWith("Won't") ? "Won't" : null;
		area = null;
		continue;
	}
	const h3 = linha.match(/^### (.+)/);
	if (h3) { area = h3[1].trim(); continue; }
	if (!prioridade || !linha.trim().startsWith('| RF-')) continue;
	const [idCel, requisito, criterio, origem] = celulas(linha);
	const m = idCel.match(/^(RF-[A-Z]+-[0-9]+[a-z]?)(?:\s*\((NOVO|AJUSTADO)\))?$/);
	if (!m) throw new Error(`ID não reconhecido: ${idCel}`);
	requisitos.push({ id: m[1], selo: m[2] ?? null, prioridade, areaMust: prioridade === 'Must' ? area : null, requisito, criterio, origem });
}

// ---------------------------------------------------------------- contagens
const contagem = Object.fromEntries(Object.keys(ESPERADO).map((p) => [p, requisitos.filter((r) => r.prioridade === p).length]));
const ids = requisitos.map((r) => r.id);
const duplicados = ids.filter((id, i) => ids.indexOf(id) !== i);
const diferencas = Object.entries(ESPERADO).filter(([p, n]) => contagem[p] !== n);
if (diferencas.length || duplicados.length || requisitos.length !== 85) {
	console.error('Contagens não batem com o esperado.');
	console.error('Esperado:', ESPERADO, '| obtido:', contagem, '| total:', requisitos.length);
	if (duplicados.length) console.error('IDs duplicados:', duplicados);
	process.exit(1);
}

// ---------------------------------------------------------------- 2. área
const prefixo = (id) => id.split('-')[1];
// Área pelo subtítulo ### dos Must; para os demais, pela área Must do mesmo prefixo.
const areaPorPrefixo = {};
for (const r of requisitos) if (r.areaMust) areaPorPrefixo[prefixo(r.id)] ??= r.areaMust;
// Prefixos que não têm requisito Must: rótulo tirado do próprio texto do requisito.
const AREA_SEM_MUST = {
	MAQ: 'Maquininha', PAI: 'Carteira', REG: 'Regras', DOC: 'Arquivos originais', OBS: 'Observabilidade',
	REL: 'Resumo mensal', IMP: 'Impostos e parcelamentos', BAN: 'Open Finance', CHAT: 'Chatbot',
	COB: 'Cobrança', CON: 'Consultoria', INF: 'Informais', TRI: 'Tributação',
};
for (const r of requisitos) {
	const p = prefixo(r.id);
	r.area = r.areaMust ?? (r.prioridade !== 'Must' && p === 'MAQ' ? AREA_SEM_MUST.MAQ : areaPorPrefixo[p]) ?? AREA_SEM_MUST[p];
	if (!r.area) throw new Error(`Sem área para ${r.id}`);
	delete r.areaMust;
}

// ---------------------------------------------------------------- 3. decisões
const expandeRFs = (texto) => {
	// "RF-VAL-01 a 04" → VAL-01..04 | "RF-APR" → todos do prefixo | "RF-ENV-01" → ele mesmo
	const out = new Set();
	for (const m of texto.matchAll(/RF-([A-Z]+)(?:-([0-9]+[a-z]?)(?:\s+a\s+([0-9]+))?)?/g)) {
		const [, p, num, ate] = m;
		if (!num) { requisitos.filter((r) => prefixo(r.id) === p).forEach((r) => out.add(r.id)); continue; }
		if (ate) {
			for (let n = Number(num); n <= Number(ate); n++) out.add(`RF-${p}-${String(n).padStart(2, '0')}`);
			continue;
		}
		out.add(`RF-${p}-${num}`);
	}
	for (const id of out) if (!ids.includes(id)) throw new Error(`Referência a requisito inexistente: ${id} em "${texto}"`);
	return [...out];
};

const decisoesCatalogo = [];
for (const [id, decisao, afeta, recomendacao, status, deliberacao] of tabelaDaSecao(ler(FONTES.decisoes), '## Decisões dos requisitos')) {
	if (!/^D-0\d$/.test(id)) continue;
	decisoesCatalogo.push({ id, decisao, afeta: expandeRFs(afeta), recomendacao, status, deliberacao });
}
if (decisoesCatalogo.length !== 9) throw new Error(`Esperava D-01 a D-09, achei ${decisoesCatalogo.length}`);
for (const r of requisitos) {
	const ds = new Set(decisoesCatalogo.filter((d) => d.afeta.includes(r.id)).map((d) => d.id));
	for (const m of `${r.requisito} ${r.criterio} ${r.origem}`.matchAll(/D-0\d/g)) ds.add(m[0]);
	r.decisoes = [...ds].sort();
	r.aDefinir = /\[definir\]/.test(`${r.requisito} ${r.criterio}`);
}

// ---------------------------------------------------------------- 4. dores
const doresCatalogo = tabelaDaSecao(ler(FONTES.cenario), '## Da dor ao requisito').map(([dor, relatou, resposta]) => ({
	dor, relatou, resposta, requisitos: expandeRFs(resposta),
}));
for (const r of requisitos) r.dores = doresCatalogo.filter((d) => d.requisitos.includes(r.id)).map((d) => d.dor);

// ---------------------------------------------------------------- 5. frente
const frentesCatalogo = tabelaDaSecao(ler(FONTES.equipe), '## As frentes da arquitetura').map(([frente, modulos, entregas]) => ({
	frente, prefixos: [...new Set([...entregas.matchAll(/RF-([A-Z]+)/g)].map((m) => m[1]))],
}));
for (const r of requisitos) r.frente = frentesCatalogo.find((f) => f.prefixos.includes(prefixo(r.id)))?.frente ?? null;

// ---------------------------------------------------------------- 6. módulo (mapeamento proposto)
const modulosExistentes = [...new Set([...ler(FONTES.arquitetura).matchAll(/src\/lastro\/([a-z]+)\//g)].map((m) => m[1]))];
// Proposta por prefixo. Won't fica sem módulo (fora desta versão). AVI é transversal.
const MODULO_POR_PREFIXO = {
	AUT: 'acesso', SEG: 'acesso', CAD: 'cadastro', ENV: 'envio', LEI: 'leitura', VAL: 'validacao',
	CLA: 'classificacao', MAQ: 'classificacao', PER: 'perguntas', APR: 'revisao', REV: 'revisao',
	EXP: 'exportacao', PAI: 'envio', REG: 'classificacao', DOC: 'envio', OBS: 'observabilidade', AVI: null,
};
// Exceções por ID, quando o texto do requisito aponta para outro módulo descrito na arquitetura.
const MODULO_POR_ID = { 'RF-SEG-02': 'nucleo', 'RF-SEG-03': 'ia' };
for (const r of requisitos) {
	r.modulo = r.prioridade === "Won't" ? null : (MODULO_POR_ID[r.id] ?? MODULO_POR_PREFIXO[prefixo(r.id)] ?? null);
	if (r.modulo && !modulosExistentes.includes(r.modulo)) throw new Error(`Módulo ${r.modulo} não existe em ${FONTES.arquitetura}`);
}

// ---------------------------------------------------------------- saída
const ordem = ['id', 'selo', 'prioridade', 'area', 'requisito', 'criterio', 'origem', 'decisoes', 'aDefinir', 'dores', 'frente', 'modulo'];
const saida = {
	_aviso: 'Arquivo gerado por scripts/gerar-requisitos.mjs. Não edite à mão: altere as fontes e rode o script de novo.',
	versaoRequisitos: 'v0.2 (07/11/2026)',
	fontes: FONTES,
	notas: {
		criterio: "Nos Won't, o campo criterio guarda o Motivo.",
		modulo: 'Módulos aprovados com a ARQ-01 (18/11/2026). O vínculo requisito → módulo é por prefixo do ID, com exceções RF-SEG-02 → nucleo e RF-SEG-03 → ia; AVI é transversal; Won\'t sem módulo. Quando há ficha, vale o módulo da ficha.',
		frente: 'Pela tabela de frentes da equipe; prefixos que a tabela não cita ficam com frente null.',
		area: 'Must: subtítulo da seção. Demais: área Must do mesmo prefixo ou rótulo tirado do texto do requisito.',
	},
	contagem: { ...contagem, total: requisitos.length },
	decisoes: decisoesCatalogo,
	dores: doresCatalogo,
	frentes: frentesCatalogo,
	modulos: modulosExistentes,
	requisitos: requisitos.map((r) => Object.fromEntries(ordem.map((k) => [k, r[k]]))),
};
fs.writeFileSync(path.join(raiz, 'src/data/requisitos.json'), JSON.stringify(saida, null, '\t') + '\n');
console.log('OK requisitos.json', saida.contagem);
console.log('   com decisão:', requisitos.filter((r) => r.decisoes.length).length,
	'| [definir]:', requisitos.filter((r) => r.aDefinir).length,
	'| NOVO:', requisitos.filter((r) => r.selo === 'NOVO').length,
	'| AJUSTADO:', requisitos.filter((r) => r.selo === 'AJUSTADO').length,
	'| com dor:', requisitos.filter((r) => r.dores.length).length,
	'| sem frente:', [...new Set(requisitos.filter((r) => !r.frente).map((r) => prefixo(r.id)))].join(' '));
