"""HX-11: `tools/project_sync.py` espelha as fichas no Project da organização.

Nada aqui fala com a rede. Os testes usam uma API falsa em memória (`ApiFalsa`) que guarda
issues, itens do Project, colunas, responsáveis, bloqueios, branches e PRs, e registra toda
chamada de escrita em `api.escritas`. Só dados inventados (IDs HX-2x/HX-3x, logins `dev-*`).

Contrato assumido (planos/HX-11/plan.md, D4-D7 e seção 5; tasks T1):
- módulo `tools/project_sync.py`, importado como `project_sync`;
  `main(argv, raiz, api) -> int` não chama sys.exit; `api` é injetada.
- argumentos: `--origem developer|agendada` e `--dry-run`.
  * developer: lê `features/` de `raiz`; cria, atualiza título, move coluna, reconcilia
    responsável e bloqueios, fecha e reabre issues. Só developer cria issue.
  * agendada: NÃO lê `features/` (os testes rodam com uma raiz sem essa pasta); consulta
    branches `feat/<ID>-*` e PRs pela API e só move a coluna (Status) dos cards.
- colunas: A FAZER < FAZENDO < EM REVISÃO < FINALIZADA; REGREDIU fora da ordem.
  Mapa: not_started→A FAZER, in_progress→FAZENDO, passing→FINALIZADA, regressed→REGREDIU;
  blocked não move. Developer nunca recua, salvo: regressed→REGREDIU (reabre o issue) e
  passing→FINALIZADA (fecha o issue), inclusive vindo de REGREDIU.
- agendada: só mexe em cards em A FAZER, FAZENDO e EM REVISÃO. Branch sem PR com card em
  A FAZER → FAZENDO; PR aberto → EM REVISÃO; PR fechado sem merge → FAZENDO; PR com merge
  não é tocado; com mais de um PR na mesma branch vale o mais recente (`criado_em`).
- issue casa com a ficha pelo título `^<ID>: ` (ex.: "HX-20: título"); corpo cita
  `features/<ID>.json`. Título diferente da ficha → `atualizar_titulo`.
- bloqueios usam o campo numérico `id` do issue, não o `numero` (na API falsa, id = numero+1000).
- avisos: uma linha com a palavra AVISO e o ID ou login em questão (stdout ou stderr).
- `--dry-run`: lista cada mudança (com o ID da ficha) e uma linha com "<N> mudanças";
  não chama nenhum método de escrita.
- falha da API: a API levanta `project_sync.FalhaApi(status, mensagem)`. Com 401 o `main`
  devolve 2 e escreve ERRO/MOTIVO/CORREÇÃO em stderr citando APP_CLIENT_ID e APP_PRIVATE_KEY,
  sem imprimir o token (`GH_TOKEN`) e sem escrever em `features/`.

Métodos da API (leitura): listar_issues, listar_itens, listar_branches, listar_prs, login_existe.
Métodos da API (escrita): criar_issue, atualizar_titulo, adicionar_ao_projeto, definir_coluna,
definir_responsaveis, definir_bloqueios, fechar_issue, reabrir_issue.
"""

import copy
import hashlib
import importlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))


def modulo():
    """Importa `project_sync` dentro de cada teste: sem o módulo, cada teste falha sozinho."""
    return importlib.import_module("project_sync")

A_FAZER = "A FAZER"
FAZENDO = "FAZENDO"
EM_REVISAO = "EM REVISÃO"
FINALIZADA = "FINALIZADA"
REGREDIU = "REGREDIU"

TOKEN_FALSO = "token-exemplo-0000"


# ---------------------------------------------------------------------------
# API falsa
# ---------------------------------------------------------------------------


class ApiFalsa:
    """GitHub em memória. Leituras devolvem cópias; escritas mudam o estado e ficam registradas."""

    def __init__(self, logins=("dev-um", "dev-dois", "dev-tres")):
        self.issues: dict[int, dict] = {}
        self.itens: dict[int, str | None] = {}  # numero do issue -> coluna
        self.branches: list[str] = ["main", "developer"]
        self.prs: list[dict] = []
        self.logins = set(logins)
        self.escritas: list[tuple] = []
        self._proximo = 1

    # -- montagem do cenário (não conta como escrita) --
    def com_issue(self, titulo, coluna=None, responsaveis=(), aberto=True, no_projeto=True):
        numero = self._proximo
        self._proximo += 1
        self.issues[numero] = {
            "numero": numero,
            "id": numero + 1000,
            "titulo": titulo,
            "corpo": "",
            "aberto": aberto,
            "responsaveis": list(responsaveis),
            "bloqueado_por": [],
        }
        if no_projeto:
            self.itens[numero] = coluna
        return numero

    def com_pr(self, branch, aberto, merge=False, criado_em="2026-01-01T00:00:00Z"):
        self.prs.append(
            {"branch": branch, "aberto": aberto, "merge": merge, "criado_em": criado_em}
        )

    # -- leitura --
    def listar_issues(self):
        return copy.deepcopy(list(self.issues.values()))

    def listar_itens(self):
        return [{"numero": n, "status": c} for n, c in self.itens.items()]

    def listar_branches(self):
        return list(self.branches)

    def listar_prs(self):
        return copy.deepcopy(self.prs)

    def login_existe(self, login):
        return login in self.logins

    # -- escrita --
    def criar_issue(self, titulo, corpo):
        self.escritas.append(("criar_issue", titulo))
        numero = self.com_issue(titulo, no_projeto=False)
        self.issues[numero]["corpo"] = corpo
        return numero

    def atualizar_titulo(self, numero, titulo):
        self.escritas.append(("atualizar_titulo", numero, titulo))
        self.issues[numero]["titulo"] = titulo

    def adicionar_ao_projeto(self, numero):
        self.escritas.append(("adicionar_ao_projeto", numero))
        self.itens.setdefault(numero, None)

    def definir_coluna(self, numero, coluna):
        self.escritas.append(("definir_coluna", numero, coluna))
        assert numero in self.itens, "definir_coluna em issue que não está no Project"
        self.itens[numero] = coluna

    def definir_responsaveis(self, numero, logins):
        self.escritas.append(("definir_responsaveis", numero, tuple(logins)))
        desconhecidos = [lg for lg in logins if lg not in self.logins]
        assert not desconhecidos, f"login inexistente enviado à API: {desconhecidos}"
        self.issues[numero]["responsaveis"] = list(logins)

    def definir_bloqueios(self, numero, ids):
        self.escritas.append(("definir_bloqueios", numero, tuple(ids)))
        validos = {i["id"] for i in self.issues.values()}
        assert set(ids) <= validos, "bloqueio deve usar o campo id do issue, não o numero"
        self.issues[numero]["bloqueado_por"] = list(ids)

    def fechar_issue(self, numero):
        self.escritas.append(("fechar_issue", numero))
        self.issues[numero]["aberto"] = False

    def reabrir_issue(self, numero):
        self.escritas.append(("reabrir_issue", numero))
        self.issues[numero]["aberto"] = True

    # -- consultas dos testes --
    def issues_de(self, id_ficha):
        padrao = re.compile(rf"^{re.escape(id_ficha)}: ")
        return [i for i in self.issues.values() if padrao.match(i["titulo"])]

    def issue_de(self, id_ficha):
        achados = self.issues_de(id_ficha)
        assert len(achados) == 1, f"esperava 1 issue de {id_ficha}, achei {len(achados)}"
        return achados[0]

    def coluna_de(self, id_ficha):
        return self.itens.get(self.issue_de(id_ficha)["numero"])


# ---------------------------------------------------------------------------
# Fichas inventadas e execução
# ---------------------------------------------------------------------------


def titulo_de(id_ficha):
    return f"Comportamento inventado {id_ficha}"


def ficha(id_ficha, estado="not_started", responsavel="dev-um", depende_de=(), titulo=None):
    return {
        "id": id_ficha,
        "titulo": titulo or titulo_de(id_ficha),
        "modulo": "ci",
        "requisitos": [],
        "prioridade": "should",
        "onda": 1,
        "essencial": False,
        "estado": estado,
        "responsavel": responsavel,
        "depende_de": list(depende_de),
        "bloqueada_por": "D-99" if estado == "blocked" else None,
        "tipo_verificacao": "comando",
        "criterios": [
            {"id": "c1", "descricao": "critério inventado", "exemplo": {"entrada": "a", "saida": "b"}}
        ],
        "verificacao": [{"criterio": "c1", "comando": "pytest tests/x.py -q"}],
        "evidencia": {"resultado": "ok"} if estado == "passing" else None,
    }


def gravar_fichas(raiz, *fichas):
    pasta = raiz / "features"
    pasta.mkdir(parents=True, exist_ok=True)
    for f in fichas:
        texto = json.dumps(f, indent=2, ensure_ascii=False) + "\n"
        (pasta / f"{f['id']}.json").write_text(texto, encoding="utf-8")
    return raiz


def issue_igual(api, f, coluna, aberto=True):
    """Issue já sincronizado com a ficha `f` (título e responsável certos)."""
    return api.com_issue(
        f"{f['id']}: {f['titulo']}", coluna=coluna, responsaveis=[f["responsavel"]], aberto=aberto
    )


def rodar(raiz, api, origem, *extra):
    return modulo().main(["--origem", origem, *extra], raiz=raiz, api=api)


def saida(capsys):
    lida = capsys.readouterr()
    return lida.out + lida.err


def linhas_de_aviso(texto):
    return [linha for linha in texto.splitlines() if "AVISO" in linha]


def hash_da_pasta(pasta):
    h = hashlib.sha256()
    for arq in sorted(pasta.rglob("*")):
        h.update(arq.relative_to(pasta).as_posix().encode())
        if arq.is_file():
            h.update(arq.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# c1 · cria issue para ficha sem item, sem duplicar
# ---------------------------------------------------------------------------


def test_cria_issue_para_ficha_sem_item(tmp_path):
    hx20 = ficha("HX-20", "not_started", "dev-um")
    hx21 = ficha("HX-21", "in_progress", "dev-dois")
    hx22 = ficha("HX-22", "not_started", "dev-tres")
    raiz = gravar_fichas(tmp_path, hx20, hx21, hx22)
    api = ApiFalsa()
    issue_igual(api, hx20, A_FAZER)

    assert rodar(raiz, api, "developer") == 0

    criados = sorted(e[1] for e in api.escritas if e[0] == "criar_issue")
    assert criados == [f"HX-21: {hx21['titulo']}", f"HX-22: {hx22['titulo']}"]
    assert len(api.issues_de("HX-20")) == 1

    novo = api.issue_de("HX-21")
    assert api.coluna_de("HX-21") == FAZENDO
    assert novo["responsaveis"] == ["dev-dois"]
    assert "features/HX-21.json" in novo["corpo"]
    assert api.coluna_de("HX-22") == A_FAZER
    assert api.issue_de("HX-22")["responsaveis"] == ["dev-tres"]


def test_nao_duplica_e_segunda_execucao_nao_altera(tmp_path):
    hx2 = ficha("HX-2", "not_started", "dev-um")
    hx20 = ficha("HX-20", "in_progress", "dev-um", titulo="Título novo inventado")
    hx21 = ficha("HX-21", "in_progress", "dev-dois")
    raiz = gravar_fichas(tmp_path, hx2, hx20, hx21)
    api = ApiFalsa()
    # issue antigo de HX-20 com o título velho; "HX-20: ..." não pode ser tomado como HX-2
    api.com_issue("HX-20: Título velho inventado", coluna=FAZENDO, responsaveis=["dev-um"])
    # issue de HX-21 existe, mas está fora do Project: só entra no Project
    api.com_issue(f"HX-21: {hx21['titulo']}", responsaveis=["dev-dois"], no_projeto=False)

    assert rodar(raiz, api, "developer") == 0

    assert len(api.issues_de("HX-2")) == 1, "HX-2 deve ganhar um issue próprio"
    assert len(api.issues_de("HX-20")) == 1
    assert len(api.issues_de("HX-21")) == 1
    assert api.issue_de("HX-20")["titulo"] == "HX-20: Título novo inventado"
    assert api.coluna_de("HX-21") == FAZENDO
    assert not any(e[0] == "criar_issue" and e[1].startswith("HX-20:") for e in api.escritas)
    assert not any(e[0] == "criar_issue" and e[1].startswith("HX-21:") for e in api.escritas)

    api.escritas.clear()
    assert rodar(raiz, api, "developer") == 0
    assert api.escritas == [], f"a segunda execução não deveria escrever: {api.escritas}"


def test_responsavel_desconhecido_avisa_sem_falhar(tmp_path, capsys):
    hx21 = ficha("HX-21", "in_progress", "login-inexistente-xyz")
    raiz = gravar_fichas(tmp_path, hx21)
    api = ApiFalsa()

    assert rodar(raiz, api, "developer") == 0

    novo = api.issue_de("HX-21")
    assert api.coluna_de("HX-21") == FAZENDO
    assert novo["responsaveis"] == []
    avisos = linhas_de_aviso(saida(capsys))
    assert any("login-inexistente-xyz" in linha for linha in avisos), avisos


# ---------------------------------------------------------------------------
# c2 · coluna conforme a origem (agendada consulta branches e PRs; developer só avança)
# ---------------------------------------------------------------------------


def test_branch_move_so_o_proprio_card(tmp_path, capsys):
    raiz = tmp_path  # sem features/: a agendada não pode ler fichas
    api = ApiFalsa()
    api.com_issue("HX-20: Inventado vinte", coluna=A_FAZER)
    api.com_issue("HX-21: Inventado vinte e um", coluna=A_FAZER)  # sem branch
    api.com_issue("HX-24: Inventado vinte e quatro", coluna=FINALIZADA, aberto=False)
    api.com_issue("HX-25: Inventado vinte e cinco", coluna=REGREDIU)
    api.com_issue("HX-26: Inventado vinte e seis", coluna=EM_REVISAO)
    api.branches += [
        "feat/HX-20-algo-inventado",
        "docs/HX-21-fora-do-padrao",
        "feat/HX-23-sem-card",
        "feat/HX-24-branch-esquecida",
        "feat/HX-25-branch-esquecida",
        "feat/HX-26-sem-pr",
    ]

    assert rodar(raiz, api, "agendada") == 0

    assert api.coluna_de("HX-20") == FAZENDO
    assert api.coluna_de("HX-21") == A_FAZER
    assert api.coluna_de("HX-24") == FINALIZADA
    assert api.coluna_de("HX-25") == REGREDIU
    assert api.coluna_de("HX-26") == EM_REVISAO
    numero_hx20 = api.issue_de("HX-20")["numero"]
    assert api.escritas == [("definir_coluna", numero_hx20, FAZENDO)]
    assert not api.issues_de("HX-23"), "a agendada nunca cria issue"
    assert any("HX-23" in linha for linha in linhas_de_aviso(saida(capsys)))


def test_pr_aberto_vai_para_em_revisao(tmp_path):
    raiz = tmp_path  # sem features/
    api = ApiFalsa()
    api.com_issue("HX-20: Inventado vinte", coluna=FAZENDO)
    api.com_issue("HX-21: Inventado vinte e um", coluna=EM_REVISAO)
    api.com_issue("HX-22: Inventado vinte e dois", coluna=EM_REVISAO)
    api.com_issue("HX-24: Inventado vinte e quatro", coluna=FINALIZADA, aberto=False)
    api.com_issue("HX-25: Inventado vinte e cinco", coluna=FAZENDO)
    api.com_issue("HX-26: Inventado vinte e seis", coluna=A_FAZER)
    api.branches += [
        "feat/HX-20-a",
        "feat/HX-21-b",
        "feat/HX-22-c",
        "feat/HX-24-d",
        "feat/HX-25-e",
        "feat/HX-26-f",
    ]
    api.com_pr("feat/HX-20-a", aberto=True)
    api.com_pr("feat/HX-21-b", aberto=False, merge=False)  # fechado sem merge
    api.com_pr("feat/HX-22-c", aberto=False, merge=True)  # com merge: developer resolve
    api.com_pr("feat/HX-24-d", aberto=True)  # FINALIZADA: a agendada não toca
    api.com_pr("feat/HX-25-e", aberto=False, merge=False, criado_em="2026-01-01T00:00:00Z")
    api.com_pr("feat/HX-25-e", aberto=True, criado_em="2026-01-02T00:00:00Z")  # mais recente
    api.com_pr("feat/HX-26-f", aberto=True)

    assert rodar(raiz, api, "agendada") == 0

    assert api.coluna_de("HX-20") == EM_REVISAO
    assert api.coluna_de("HX-21") == FAZENDO
    assert api.coluna_de("HX-22") == EM_REVISAO
    assert api.coluna_de("HX-24") == FINALIZADA
    assert api.coluna_de("HX-25") == EM_REVISAO
    assert api.coluna_de("HX-26") == EM_REVISAO
    so_colunas = {e[0] for e in api.escritas}
    assert so_colunas == {"definir_coluna"}, f"a agendada só move colunas: {api.escritas}"


def test_developer_nunca_recua_status(tmp_path):
    fichas = {
        "HX-22": (ficha("HX-22", "not_started"), FAZENDO, FAZENDO),
        "HX-26": (ficha("HX-26", "in_progress"), EM_REVISAO, EM_REVISAO),
        "HX-27": (ficha("HX-27", "in_progress"), A_FAZER, FAZENDO),
        "HX-28": (ficha("HX-28", "in_progress"), REGREDIU, REGREDIU),
        "HX-29": (ficha("HX-29", "in_progress"), FINALIZADA, FINALIZADA),
        "HX-31": (ficha("HX-31", "blocked"), FAZENDO, FAZENDO),
        "HX-34": (ficha("HX-34", "blocked"), A_FAZER, A_FAZER),
    }
    raiz = gravar_fichas(tmp_path, *(f for f, _, _ in fichas.values()))
    api = ApiFalsa()
    for f, antes, _ in fichas.values():
        issue_igual(api, f, antes, aberto=antes != FINALIZADA)
    # regressed: exceção explícita ao "nunca recua"
    hx30 = ficha("HX-30", "regressed")
    gravar_fichas(raiz, hx30)
    issue_igual(api, hx30, FINALIZADA, aberto=False)

    assert rodar(raiz, api, "developer") == 0

    for id_ficha, (_, _, depois) in fichas.items():
        assert api.coluna_de(id_ficha) == depois, id_ficha
    assert api.coluna_de("HX-30") == REGREDIU
    assert api.issue_de("HX-30")["aberto"] is True
    reabertos = [e[1] for e in api.escritas if e[0] == "reabrir_issue"]
    assert reabertos == [api.issue_de("HX-30")["numero"]]


def test_passing_em_developer_finaliza_e_fecha_issue(tmp_path):
    hx23 = ficha("HX-23", "passing")
    hx32 = ficha("HX-32", "passing")
    hx33 = ficha("HX-33", "passing")
    raiz = gravar_fichas(tmp_path, hx23, hx32, hx33)
    api = ApiFalsa()
    issue_igual(api, hx23, EM_REVISAO)
    issue_igual(api, hx32, REGREDIU)  # voltou a passing depois de regredir
    issue_igual(api, hx33, FINALIZADA, aberto=False)  # já está certo

    assert rodar(raiz, api, "developer") == 0

    for id_ficha in ("HX-23", "HX-32", "HX-33"):
        assert api.coluna_de(id_ficha) == FINALIZADA, id_ficha
        assert api.issue_de(id_ficha)["aberto"] is False, id_ficha
    numero_hx33 = api.issue_de("HX-33")["numero"]
    assert not [e for e in api.escritas if len(e) > 1 and e[1] == numero_hx33]


# ---------------------------------------------------------------------------
# c3 · reconciliação de responsável e bloqueios; ficha apagada não apaga issue
# ---------------------------------------------------------------------------


def test_reconcilia_responsavel(tmp_path):
    hx20 = ficha("HX-20", "in_progress", "dev-dois")
    hx21 = ficha("HX-21", "in_progress", "dev-dois")
    raiz = gravar_fichas(tmp_path, hx20, hx21)
    api = ApiFalsa()
    api.com_issue(f"HX-20: {hx20['titulo']}", coluna=FAZENDO, responsaveis=["dev-um"])
    api.com_issue(
        f"HX-21: {hx21['titulo']}", coluna=FAZENDO, responsaveis=["dev-um", "dev-dois"]
    )

    assert rodar(raiz, api, "developer") == 0

    assert api.issue_de("HX-20")["responsaveis"] == ["dev-dois"]
    assert api.issue_de("HX-21")["responsaveis"] == ["dev-dois"]


def test_reconcilia_bloqueios(tmp_path):
    hx01 = ficha("HX-01", "passing")
    hx02 = ficha("HX-02", "in_progress")
    hx20 = ficha("HX-20", "not_started", depende_de=["HX-02"])
    hx21 = ficha("HX-21", "not_started", depende_de=["HX-01", "HX-02"])
    raiz = gravar_fichas(tmp_path, hx01, hx02, hx20, hx21)
    api = ApiFalsa()
    issue_igual(api, hx01, FINALIZADA, aberto=False)
    issue_igual(api, hx02, FAZENDO)
    n20 = issue_igual(api, hx20, A_FAZER)
    issue_igual(api, hx21, A_FAZER)
    id_hx01 = api.issue_de("HX-01")["id"]
    id_hx02 = api.issue_de("HX-02")["id"]
    api.issues[n20]["bloqueado_por"] = [id_hx01]  # bloqueio antigo

    assert rodar(raiz, api, "developer") == 0

    assert api.issue_de("HX-20")["bloqueado_por"] == [id_hx02]
    assert sorted(api.issue_de("HX-21")["bloqueado_por"]) == sorted([id_hx01, id_hx02])
    assert api.issue_de("HX-02")["bloqueado_por"] == []


def test_ficha_removida_nao_apaga_issue(tmp_path, capsys):
    hx20 = ficha("HX-20", "in_progress")
    raiz = gravar_fichas(tmp_path, hx20)
    api = ApiFalsa()
    issue_igual(api, hx20, FAZENDO)
    n23 = api.com_issue("HX-23: Ficha que foi removida", coluna=FAZENDO, responsaveis=["dev-um"])

    assert rodar(raiz, api, "developer") == 0

    issue = api.issues[n23]
    assert issue["aberto"] is True
    assert api.itens[n23] == FAZENDO
    assert issue["responsaveis"] == ["dev-um"]
    assert not [e for e in api.escritas if len(e) > 1 and e[1] == n23]
    assert any("HX-23" in linha for linha in linhas_de_aviso(saida(capsys)))


# ---------------------------------------------------------------------------
# c4 · --dry-run não escreve; falha da API dá código 2 sem tocar nas fichas
# ---------------------------------------------------------------------------


def test_dry_run_nao_escreve(tmp_path, capsys):
    hx30 = ficha("HX-30", "not_started", titulo="Título novo inventado")
    hx31 = ficha("HX-31", "in_progress")
    raiz = gravar_fichas(tmp_path, hx30, hx31)
    api = ApiFalsa()
    api.com_issue("HX-30: Título velho inventado", coluna=A_FAZER, responsaveis=["dev-um"])
    issue_igual(api, hx31, A_FAZER)

    assert rodar(raiz, api, "developer", "--dry-run") == 0

    assert api.escritas == []
    texto = saida(capsys)
    assert "HX-30" in texto and "HX-31" in texto
    assert re.search(r"\b2 mudanças\b", texto), texto
    assert api.issue_de("HX-30")["titulo"] == "HX-30: Título velho inventado"
    assert api.coluna_de("HX-31") == A_FAZER

    # sem --dry-run, as mesmas 2 mudanças são aplicadas
    assert rodar(raiz, api, "developer") == 0
    assert api.issue_de("HX-30")["titulo"] == "HX-30: Título novo inventado"
    assert api.coluna_de("HX-31") == FAZENDO


class ApiRecusaCredencial(ApiFalsa):
    """Responde 401 em qualquer chamada, como o GitHub com token inválido."""

    def __getattribute__(self, nome):
        if nome.startswith(("listar_", "login_", "criar_", "atualizar_", "adicionar_", "definir_",
                            "fechar_", "reabrir_")):
            def recusar(*_args, **_kwargs):
                raise modulo().FalhaApi(401, "Bad credentials")
            return recusar
        return super().__getattribute__(nome)


def test_falha_api_exit_2_sem_tocar_fichas(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", TOKEN_FALSO)
    raiz = gravar_fichas(
        tmp_path, ficha("HX-20", "in_progress"), ficha("HX-21", "passing", depende_de=["HX-20"])
    )
    antes = hash_da_pasta(raiz / "features")

    codigo = rodar(raiz, ApiRecusaCredencial(), "developer")

    lida = capsys.readouterr()
    assert codigo == 2
    for rotulo in ("ERRO:", "MOTIVO:", "CORREÇÃO:"):
        assert rotulo in lida.err, lida.err
    assert "APP_CLIENT_ID" in lida.err
    assert "APP_PRIVATE_KEY" in lida.err
    assert TOKEN_FALSO not in lida.out + lida.err
    assert hash_da_pasta(raiz / "features") == antes
