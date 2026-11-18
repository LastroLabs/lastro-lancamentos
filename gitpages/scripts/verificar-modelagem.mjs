import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const modelo = JSON.parse(read('src/data/modelagem.json'));
const catalogo = JSON.parse(read('src/data/requisitos.json'));
const requisitos = new Map(catalogo.requisitos.map((r) => [r.id, r]));
const entidades = new Map(modelo.entidades.map((e) => [e.id, e]));
const vinculos = new Map(modelo.vinculos.map((v) => [v.requisito, v]));
const slug = (s) => s.trim().toLowerCase().replace(/[^\p{L}\p{N}_\s-]/gu, '').replace(/\s/g, '-');
assert.equal(entidades.size, 27);
assert.equal(entidades.size, modelo.entidades.length, 'Entidade duplicada');
assert.equal(vinculos.size, modelo.vinculos.length, 'Requisito duplicado na modelagem');
for (const v of modelo.vinculos) {
  assert(requisitos.has(v.requisito), `Requisito desconhecido: ${v.requisito}`);
  assert.notEqual(requisitos.get(v.requisito).prioridade, "Won't");
  assert(v.regra.trim());
  for (const id of v.entidades) assert(entidades.has(id), `Entidade desconhecida: ${id}`);
}
const must = [...requisitos.values()].filter((r) => r.prioridade === 'Must');
assert.equal(must.length, 56);
for (const r of must) assert(vinculos.has(r.id), `Must sem vínculo: ${r.id}`);
assert.match(requisitos.get('RF-CAD-01').requisito, /chefe/i, 'A modelagem exige a releitura vigente de RF-CAD-01');
for (const d of catalogo.decisoes) {
  assert(d.status && d.deliberacao, `Decisão sem status/deliberação do Pages: ${d.id}`);
}
assert.match(catalogo.decisoes.find((d) => d.id === 'D-03').status, /Aprovada/);
assert.match(catalogo.decisoes.find((d) => d.id === 'D-08').status, /Pendente/);
assert.match(catalogo.decisoes.find((d) => d.id === 'D-06').deliberacao, /7 dias/);
assert.match(catalogo.decisoes.find((d) => d.id === 'D-06').deliberacao, /20 MiB/);

const docs = path.join(root, 'src/content/docs');
const files = fs.readdirSync(docs, { recursive: true }).filter((p) => /\.mdx?$/.test(p));
const anchors = (text) => new Set([
  ...[...text.matchAll(/^#{1,6}\s+(.+)$/gm)].map((m) => slug(m[1])),
  ...[...text.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]),
]);
for (const name of ['entidades', 'modelo-logico']) {
  const ids = anchors(read(`src/content/docs/modelagem/${name}.md`));
  for (const e of modelo.entidades) assert(ids.has(e.id), `Âncora de ${e.nome} ausente em ${name}`);
}
let links = 0;
const prefix = '/lastro-lancamentos/';
for (const file of files) {
  const text = fs.readFileSync(path.join(docs, file), 'utf8');
  const isModel = file.replaceAll('\\', '/').startsWith('modelagem/');
  for (const [, href] of text.matchAll(/(?:\]\(|href=")([^\s"\)]+)(?:\)|")/g)) {
    if (!href.startsWith(prefix) || (!isModel && !href.includes('/modelagem/'))) continue;
    const url = new URL(href, 'https://lastrolabs.github.io');
    const route = decodeURIComponent(url.pathname.slice(prefix.length)).replace(/\/$/, '');
    const target = [`${route}.md`, `${route}.mdx`, `${route}/index.md`, `${route}/index.mdx`].find((p) => fs.existsSync(path.join(docs, p)));
    assert(target, `Página inexistente: ${href} em ${file}`);
    const hash = decodeURIComponent(url.hash.slice(1));
    if (hash && route === 'visao/requisitos') assert([...requisitos.keys()].some((id) => id.toLowerCase() === hash), `RF inexistente: ${href}`);
    else if (hash && route === 'modelagem/rastreabilidade') assert([...requisitos.keys()].some((id) => id.toLowerCase() === hash), `RF inexistente: ${href}`);
    else if (hash) assert(anchors(fs.readFileSync(path.join(docs, target), 'utf8')).has(hash), `Âncora ausente: ${href} em ${file}`);
    const entity = url.searchParams.get('entidade');
    if (entity) assert(entidades.has(entity), `Filtro de entidade inexistente: ${href}`);
    links++;
  }
}

if (process.argv.includes('--dist')) {
  const dist = path.join(root, 'dist');
  for (const file of fs.readdirSync(dist, { recursive: true }).filter((p) => /\.html$/.test(p))) {
    const html = fs.readFileSync(path.join(dist, file), 'utf8');
    const isModel = file.replaceAll('\\', '/').startsWith('modelagem/');
    for (const [, raw] of html.matchAll(/href="([^"]+)"/g)) {
      const href = raw.replaceAll('&amp;', '&');
      if (!href.startsWith(prefix) || (!isModel && !href.includes('/modelagem/'))) continue;
      const url = new URL(href, 'https://lastrolabs.github.io');
      const route = decodeURIComponent(url.pathname.slice(prefix.length));
      const target = path.join(dist, route.endsWith('/') ? `${route}index.html` : route);
      assert(fs.existsSync(target), `Destino renderizado ausente: ${href} em ${file}`);
      if (url.hash && target.endsWith('.html')) assert(fs.readFileSync(target, 'utf8').includes(`id="${decodeURIComponent(url.hash.slice(1))}"`), `Fragmento renderizado ausente: ${href} em ${file}`);
    }
  }
}
console.log(`Modelagem: ${entidades.size} entidades, ${must.length} Must, ${vinculos.size} vínculos e ${links} links válidos.`);
