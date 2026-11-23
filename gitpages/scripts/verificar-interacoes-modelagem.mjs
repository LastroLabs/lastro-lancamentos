import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { stripTypeScriptTypes } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const catalogo = JSON.parse(read('src/data/requisitos.json'));
const dados = JSON.parse(read('src/data/modelagem.json'));
const asJS = (text) => stripTypeScriptTypes(text).replace(/^import .*;\r?$/gm, '').replace(/^export /gm, '');
const api = vm.runInNewContext(`${asJS(read('src/data/modelagem.ts'))}\n({ entidadesDoRequisito, vinculoDoRequisito, decisoesDoRequisito, decisoesModelo, linkEntidade, linkModelagem, linkDecisaoModelo });`, {
  dados, requisitos: catalogo.requisitos, decisoes: catalogo.decisoes,
  link: (p) => `/lastro-lancamentos/${p}`,
});
const fichas = vm.runInNewContext(`${asJS(read('src/data/fichas.ts'))}\nfichas;`);
assert.equal(api.entidadesDoRequisito('RF-CAD-01').length, 2);
assert(api.decisoesDoRequisito('RF-CAD-01').includes('P-02a'));
assert.match(api.decisoesModelo.find((d) => d.id === 'D-08').efeito, /Sem deliberação/);
assert.match(api.decisoesModelo.find((d) => d.id === 'D-06').efeito, /20 MiB/);
assert.equal(api.linkEntidade('sessao'), '/lastro-lancamentos/modelagem/entidades/#sessao');
assert.equal(api.linkModelagem('RF-CAD-01'), '/lastro-lancamentos/modelagem/rastreabilidade/#rf-cad-01');

const normalize = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const itens = catalogo.requisitos.map((r) => {
  const v = api.vinculoDoRequisito(r.id);
  const es = api.entidadesDoRequisito(r.id);
  const fs = fichas.filter((f) => f.requisitos.includes(r.id));
  return { id: r.id.toLowerCase(), hidden: false, open: false,
    dataset: { prioridade: r.prioridade, entidades: es.map((e) => e.id).join(' '),
      vinculo: r.prioridade === "Won't" ? 'fora' : v ? 'documentado' : 'sem',
      busca: normalize(`${r.id} ${r.requisito} ${r.criterio} ${v?.regra ?? ''} ${es.map((e) => e.nome).join(' ')} ${api.decisoesDoRequisito(r.id).join(' ')} ${fs.map((f) => f.id).join(' ')}`) },
    scrollIntoView() {},
  };
});
const campos = {
  busca: { name: 'busca', value: '' },
  prioridade: { name: 'prioridade', value: '', options: ['', 'Must', 'Should', 'Could', "Won't"].map((value) => ({ value })) },
  entidade: { name: 'entidade', value: '', options: ['', ...dados.entidades.map((e) => e.id)].map((value) => ({ value })) },
  vinculo: { name: 'vinculo', value: '', options: ['', 'documentado', 'sem', 'fora'].map((value) => ({ value })) },
};
const events = {};
const windowEvents = {};
const total = { textContent: '' };
const vazio = { hidden: true };
const form = { elements: { namedItem: (name) => campos[name] }, addEventListener: (name, fn) => { events[name] = fn; },
  reset() { Object.values(campos).forEach((c) => { c.value = ''; }); events.reset?.(); },
};
const raiz = { dataset: {}, querySelector: (s) => ({ form, '[data-total]': total, '[data-vazio]': vazio })[s], querySelectorAll: () => itens };
const location = { search: '?prioridade=Must', hash: '' };
const source = read('src/components/ModelagemRastreabilidade.astro').match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInNewContext(stripTypeScriptTypes(source), {
  document: { readyState: 'complete', querySelectorAll: () => [raiz], addEventListener() {} },
  window: { addEventListener: (name, fn) => { windowEvents[name] = fn; } },
  location, URLSearchParams, requestAnimationFrame: (fn) => fn(),
});
const count = () => itens.filter((i) => !i.hidden).length;
assert.equal(count(), 56, 'Link direto com prioridade Must');
campos.entidade.value = 'plano_contas'; events.change();
assert.equal(count(), 3, 'Plano de contas: importação, transitória e sugestão pertencente ao plano');
assert.equal(itens.filter((i) => !i.hidden).map((i) => i.id).sort().join(','), 'rf-cad-03,rf-cad-04,rf-cla-01');
form.reset(); assert.equal(count(), 85);
campos.busca.value = 'CAD-03'; events.input();
assert.equal(count(), 3, 'Busca textual CAD-03 encontra a ficha e o RF de mesmo sufixo');
assert.equal(itens.filter((i) => !i.hidden).map((i) => i.id).sort().join(','), 'rf-aut-03,rf-cad-01,rf-cad-03');
form.reset(); campos.vinculo.value = 'sem'; events.change();
assert.equal(count(), 9, 'Complementares sem vínculo não são apresentados como mapeados');
form.reset(); campos.prioridade.value = "Won't"; events.change();
assert.equal(count(), 12, 'Requisitos fora do escopo');
campos.busca.value = 'sem-correspondencia-na-documentacao'; events.input();
assert.equal(count(), 0); assert.equal(vazio.hidden, false); assert.equal(total.textContent, '0');
location.hash = '#rf-cad-01'; windowEvents.hashchange();
assert.equal(count(), 85, 'Link por hash revela o alvo mesmo com filtros anteriores');
assert.equal(itens.find((i) => i.id === 'rf-cad-01').open, true);
assert.equal(vazio.hidden, true);
form.reset(); assert.equal(count(), 85);
console.log('Interações válidas: consultas, decisões, filtros combinados, busca por ficha, vazio, reset e links diretos.');
