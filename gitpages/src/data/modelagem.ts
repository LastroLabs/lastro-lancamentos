import dados from './modelagem.json';
import { decisoes, link, requisitos } from './requisitos';

export const entidades = dados.entidades;
export const vinculos = dados.vinculos;
export const vinculoDoRequisito = (id: string) => vinculos.find((v) => v.requisito === id);
export const entidadesDoRequisito = (id: string) => entidades.filter((e) => vinculoDoRequisito(id)?.entidades.includes(e.id));
export const requisitosDaEntidade = (id: string) => requisitos.filter((r) => vinculoDoRequisito(r.id)?.entidades.includes(id));
export const decisoesDoRequisito = (id: string) => [...new Set([
  ...(requisitos.find((r) => r.id === id)?.decisoes ?? []),
  ...(vinculoDoRequisito(id)?.decisoes ?? []),
])];
export const linkEntidade = (id: string) => link(`modelagem/entidades/#${id}`);
export const linkModelagem = (id: string) => link(`modelagem/rastreabilidade/#${id.toLowerCase()}`);
export const linkDecisaoModelo = (id: string) => link(`modelagem/decisoes/#${id.toLowerCase()}`);

export interface DecisaoModelo { id: string; titulo: string; status: string; efeito: string; fonte: string; }
export const decisoesModelo: DecisaoModelo[] = [
  ...decisoes.map((d) => ({ id: d.id, titulo: d.decisao, status: d.status,
    efeito: /^[-—–]$/.test(d.deliberacao.trim()) ? 'Sem deliberação registrada. Não preencher o valor ou ampliar o escopo por conta própria.' : d.deliberacao,
    fonte: link('decisoes/#decisões-dos-requisitos-d-01-a-d-09') })),
  { id: 'ARQ-03', titulo: 'Sessão no servidor', status: 'Aprovada em 18/11', efeito: 'SESSAO preserva validade e encerramento. A atribuição vigente continua sendo consultada em cada operação.', fonte: link('decisoes/arquitetura/') },
  { id: 'ARQ-04', titulo: 'Fila no PostgreSQL com Procrastinate', status: 'Aprovada em 18/11', efeito: 'A fila pertence à infraestrutura aprovada. ARQUIVO registra estado do documento sem substituir o mecanismo de tarefas.', fonte: link('decisoes/arquitetura/') },
  { id: 'ARQ-06', titulo: 'Gateway único de IA', status: 'Aprovada em 18/11', efeito: 'Sanitizar antes da chamada e validar a conta de saída. A entidade SUGESTAO conserva apenas evidência e metadados adequados ao escopo.', fonte: link('decisoes/arquitetura/') },
  { id: 'BD-02', titulo: 'Isolamento por escritório e carteira', status: 'Aprovada em 18/11', efeito: 'Escopo nas FKs, autorização na aplicação e RLS para leitura e escrita.', fonte: link('decisoes/banco-de-dados/') },
  { id: 'BD-03', titulo: 'Arquivos privados', status: 'Aprovada em 18/11', efeito: 'O banco mantém metadados, hash e referência ao objeto privado; o download é autorizado pelo backend.', fonte: link('decisoes/banco-de-dados/') },
  { id: 'BD-04', titulo: 'Versões e histórico auditável', status: 'Aprovada em 18/11', efeito: 'Leitura, revisão, aprendizado e exportação preservam evidência e versão sem event sourcing integral.', fonte: link('decisoes/banco-de-dados/') },
  { id: 'BD-05', titulo: 'Dinheiro em centavos', status: 'Aprovada em 18/11', efeito: 'BIGINT com sinal para valores e saldos; cálculos em inteiros.', fonte: link('decisoes/banco-de-dados/') },
  { id: 'BD-06', titulo: 'Similaridade textual', status: 'Aprovada em 18/11', efeito: 'pg_trgm consulta o histórico do próprio cliente; não introduzir embeddings como condição do MVP.', fonte: link('decisoes/banco-de-dados/') },
  { id: 'P-01', titulo: 'Recusa de acesso', status: 'Aprovada em 18/11', efeito: '401 sem sessão; 403 para papel sem permissão; 404 indistinguível de inexistente para recurso de outro escopo.', fonte: link('decisoes/acesso-e-cadastro/') },
  { id: 'P-02', titulo: 'Cadastro pelo chefe', status: 'Aprovada em 18/11', efeito: 'Somente o chefe cadastra cliente. Papel do membro governa essa ação.', fonte: link('decisoes/acesso-e-cadastro/') },
  { id: 'P-02a', titulo: 'Releitura de RF-CAD-01', status: 'Aprovada em 18/11', efeito: 'O cliente aparece no escritório após o cadastro pelo chefe e, depois de atribuído, na carteira do contador.', fonte: link('decisoes/acesso-e-cadastro/') },
  { id: 'P-09', titulo: 'Ações do chefe sem atribuição', status: 'Pendente', efeito: 'Não presumir permissão para editar cadastro ou gerar link apenas porque o chefe visualiza o escritório inteiro.', fonte: link('decisoes/acesso-e-cadastro/') },
  { id: 'P-10', titulo: 'Cabeçalho da planilha do plano', status: 'Assumida; confirmar com os pilotos', efeito: 'Código e nome na linha 1 são a suposição atual de importação, não evidência de homologação.', fonte: link('decisoes/acesso-e-cadastro/') },
  { id: 'P-11', titulo: 'Substituição do plano vigente', status: 'Assumida; reversível pela liderança', efeito: 'Nova carga substitui o plano atual. Se a transitória não existir no novo plano, o cliente fica sem transitória.', fonte: link('decisoes/acesso-e-cadastro/') },
  { id: 'P-13', titulo: 'Dado inválido: 400 ou 422', status: 'Pendente', efeito: 'Não escolher o status HTTP na especificação do banco; a ficha continua com [definir P-13].', fonte: link('decisoes/acesso-e-cadastro/') },
];

const ids = new Set(entidades.map((e) => e.id));
const rfs = new Set(requisitos.map((r) => r.id));
const ds = new Set(decisoesModelo.map((d) => d.id));
for (const v of vinculos) {
  if (!rfs.has(v.requisito) || v.entidades.some((id) => !ids.has(id)) || v.decisoes.some((id) => !ds.has(id)))
    throw new Error(`Referência inválida na modelagem: ${v.requisito}`);
}
for (const e of entidades) if (e.decisoes.some((id) => !ds.has(id))) throw new Error(`Decisão inválida em ${e.id}`);
for (const r of requisitos.filter((r) => r.prioridade === 'Must')) if (!vinculoDoRequisito(r.id)) throw new Error(`Must sem vínculo: ${r.id}`);
