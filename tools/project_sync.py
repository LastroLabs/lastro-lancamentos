"""Sync das fichas com o Project da organização (HX-11). Só biblioteca padrão.

Uso:
    python tools/project_sync.py --origem developer [--dry-run]
    python tools/project_sync.py --origem agendada [--dry-run]

- `developer`: lê `features/*.json` e reconcilia os issues `<ID>: <título>`: cria o que falta,
  atualiza título, avança a coluna (Status), reconcilia responsável e bloqueios, fecha e reabre.
  É a única origem que cria issue.
- `agendada`: NÃO lê `features/`. Consulta pela API as branches `feat/<ID>-*` e seus PRs e só
  move a coluna dos cards que estão em A FAZER, FAZENDO ou EM REVISÃO.
- `--dry-run`: só lista as mudanças; não chama nenhuma escrita.

O script nunca escreve em `features/`. Primeiro decide (lista de mudanças), depois aplica.
Códigos de saída: 0 = ok · 2 = erro de uso, de ambiente ou da API (ERRO/MOTIVO/CORREÇÃO).
`main` nunca chama sys.exit. Decisões: planos/HX-11/plan.md (D1, D3, D5, D6, D7 e seção 5).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from harness import RAIZ_PADRAO, HarnessErro, carregar_fichas, mostrar_erro

# ---------------------------------------------------------------------------
# Colunas e regras de movimento
# ---------------------------------------------------------------------------

A_FAZER = "A FAZER"
FAZENDO = "FAZENDO"
EM_REVISAO = "EM REVISÃO"
FINALIZADA = "FINALIZADA"
REGREDIU = "REGREDIU"

ORDEM = (A_FAZER, FAZENDO, EM_REVISAO, FINALIZADA)  # REGREDIU fica fora da ordem
MAPA_ESTADO = {
    "not_started": A_FAZER,
    "in_progress": FAZENDO,
    "passing": FINALIZADA,
    "regressed": REGREDIU,
}  # `blocked` não move o card: o bloqueio nativo do issue já aparece
COLUNAS_DA_AGENDADA = (None, A_FAZER, FAZENDO, EM_REVISAO)  # None = card sem Status

_ID = r"[A-Z]+-\d+"
_TITULO_DO_ISSUE = re.compile(rf"^({_ID}): ")
_BRANCH_DE_FEATURE = re.compile(rf"^feat/({_ID})-")


def coluna_developer(estado: str, atual: str | None) -> str | None:
    """Coluna do card em developer: só avança; exceções `passing` e `regressed`."""
    if estado == "passing":
        return FINALIZADA
    if estado == "regressed":
        return REGREDIU
    desejada = MAPA_ESTADO.get(estado)
    if atual is None:
        return desejada or A_FAZER
    if desejada is None or atual not in ORDEM:
        return atual  # blocked não move; REGREDIU só sai com passing
    return desejada if ORDEM.index(desejada) > ORDEM.index(atual) else atual


def coluna_agendada(atual: str | None, pr: dict | None) -> str | None:
    """Coluna do card pela branch e pelo PR mais recente (só A FAZER, FAZENDO, EM REVISÃO)."""
    if pr is None:
        return FAZENDO if atual in (None, A_FAZER) else atual
    if pr.get("aberto"):
        return EM_REVISAO
    if not pr.get("merge") and atual == EM_REVISAO:
        return FAZENDO
    return atual  # PR com merge: quem resolve é o push em developer


# ---------------------------------------------------------------------------
# Plano de mudanças
# ---------------------------------------------------------------------------


class FalhaApi(Exception):
    """A API do GitHub respondeu com erro."""

    def __init__(self, status: int, mensagem: str) -> None:
        super().__init__(f"{status}: {mensagem}")
        self.status = status
        self.mensagem = mensagem


@dataclass
class Mudanca:
    id_ficha: str
    descricao: str
    aplicar: Callable[[Contexto], None]
    criacao: bool = False


@dataclass
class Contexto:
    """Estado remoto lido no começo; atualizado durante a aplicação."""

    api: object
    issues: dict[str, dict] = field(default_factory=dict)  # ID da ficha -> issue
    itens: dict[int, str | None] = field(default_factory=dict)  # número do issue -> coluna
    avisos: list[str] = field(default_factory=list)

    def ler(self) -> None:
        self.issues = indexar_issues(self.api.listar_issues(), self.avisos)
        self.itens = {i["numero"]: i.get("status") for i in self.api.listar_itens()}

    def avisar(self, texto: str) -> None:
        self.avisos.append(f"AVISO: {texto}")

    def numero_de(self, id_ficha: str) -> int:
        return self.issues[id_ficha]["numero"]


def indexar_issues(issues: list[dict], avisos: list[str]) -> dict[str, dict]:
    """ID da ficha -> issue, casando o título com `^<ID>: ` (D5). Fica o de menor número."""
    por_id: dict[str, dict] = {}
    for issue in sorted(issues, key=lambda i: i["numero"]):
        achado = _TITULO_DO_ISSUE.match(issue.get("titulo") or "")
        if not achado:
            continue
        id_ficha = achado.group(1)
        if id_ficha in por_id:
            avisos.append(
                f"AVISO: {id_ficha} tem mais de um issue (#{por_id[id_ficha]['numero']} e "
                f"#{issue['numero']}); uso o #{por_id[id_ficha]['numero']}."
            )
            continue
        por_id[id_ficha] = issue
    return por_id


def corpo_do_issue(id_ficha: str) -> str:
    return (
        f"Ficha: features/{id_ficha}.json\n\n"
        "Issue mantido por tools/project_sync.py: altere a ficha, não este issue."
    )


def _responsaveis(ficha: dict, ctx: Contexto, cache: dict[str, bool]) -> list[str]:
    login = ficha.get("responsavel")
    if not isinstance(login, str) or not login.strip():
        return []
    login = login.strip()
    if login not in cache:
        cache[login] = bool(ctx.api.login_existe(login))
        if not cache[login]:
            ctx.avisar(
                f"{ficha['id']}: o responsável '{login}' não existe no GitHub; "
                "o issue fica sem responsável. Corrija o login na ficha."
            )
    return [login] if cache[login] else []


def planejar_developer(raiz: Path, ctx: Contexto) -> list[Mudanca]:
    fichas = carregar_fichas(raiz)
    ctx.ler()
    ids_fichas = {f["id"] for f in fichas}
    logins: dict[str, bool] = {}
    criacoes: list[Mudanca] = []
    demais: list[Mudanca] = []

    for ficha in fichas:
        id_ficha = ficha["id"]
        estado = ficha.get("estado")
        titulo = f"{id_ficha}: {ficha.get('titulo', '')}"
        responsaveis = _responsaveis(ficha, ctx, logins)
        issue = ctx.issues.get(id_ficha)

        if issue is None:
            coluna = coluna_developer(estado, None)
            criacoes.append(
                Mudanca(
                    id_ficha,
                    f"criar issue '{titulo}' em {coluna}",
                    _criar(id_ficha, titulo, coluna, responsaveis, fechar=estado == "passing"),
                    criacao=True,
                )
            )
        else:
            demais.extend(_ajustes(ficha, issue, titulo, responsaveis, ctx))

        bloqueio = _bloqueios(ficha, issue, ids_fichas, ctx)
        if bloqueio:
            demais.append(bloqueio)

    for id_ficha, issue in sorted(ctx.issues.items()):
        if id_ficha not in ids_fichas:
            ctx.avisar(
                f"{id_ficha}: o issue #{issue['numero']} não tem ficha em features/; "
                "não foi alterado. Feche à mão se a feature foi descartada."
            )
    return criacoes + demais


def _criar(id_ficha, titulo, coluna, responsaveis, fechar) -> Callable[[Contexto], None]:
    def aplicar(ctx: Contexto) -> None:
        api = ctx.api
        numero = api.criar_issue(titulo, corpo_do_issue(id_ficha))
        api.adicionar_ao_projeto(numero)
        api.definir_coluna(numero, coluna)
        if responsaveis:
            api.definir_responsaveis(numero, responsaveis)
        if fechar:
            api.fechar_issue(numero)
        ctx.issues[id_ficha] = {"numero": numero, "titulo": titulo}
        ctx.itens[numero] = coluna

    return aplicar


def _ajustes(ficha, issue, titulo, responsaveis, ctx: Contexto) -> list[Mudanca]:
    id_ficha = ficha["id"]
    estado = ficha.get("estado")
    numero = issue["numero"]
    mudancas: list[Mudanca] = []

    if issue.get("titulo") != titulo:
        mudancas.append(
            Mudanca(
                id_ficha,
                f"atualizar título do #{numero} para '{titulo}'",
                lambda c: c.api.atualizar_titulo(numero, titulo),
            )
        )

    no_projeto = numero in ctx.itens
    atual = ctx.itens.get(numero)
    nova = coluna_developer(estado, atual)
    if not no_projeto:
        mudancas.append(
            Mudanca(
                id_ficha,
                f"adicionar o #{numero} ao Project em {nova}",
                lambda c: (c.api.adicionar_ao_projeto(numero), c.api.definir_coluna(numero, nova)),
            )
        )
    elif nova != atual:
        mudancas.append(
            Mudanca(
                id_ficha,
                f"mover o #{numero} de {atual or 'sem coluna'} para {nova}",
                lambda c: c.api.definir_coluna(numero, nova),
            )
        )

    aberto = issue.get("aberto", True)
    if estado == "passing" and aberto:
        mudancas.append(
            Mudanca(id_ficha, f"fechar o #{numero}", lambda c: c.api.fechar_issue(numero))
        )
    elif estado == "regressed" and not aberto:
        mudancas.append(
            Mudanca(id_ficha, f"reabrir o #{numero}", lambda c: c.api.reabrir_issue(numero))
        )

    if sorted(issue.get("responsaveis") or []) != sorted(responsaveis):
        texto = ", ".join(responsaveis) or "ninguém"
        mudancas.append(
            Mudanca(
                id_ficha,
                f"responsável do #{numero}: {texto}",
                lambda c: c.api.definir_responsaveis(numero, responsaveis),
            )
        )
    return mudancas


def _bloqueios(ficha, issue, ids_fichas, ctx: Contexto) -> Mudanca | None:
    """Bloqueado exatamente pelos issues de `depende_de` (D3). Usa o `id`, não o número."""
    id_ficha = ficha["id"]
    deps: list[str] = []
    pendente = False  # dependência cujo issue só nasce nesta execução
    for dep in ficha.get("depende_de") or []:
        if dep in ctx.issues:
            deps.append(dep)
        elif dep in ids_fichas:
            deps.append(dep)
            pendente = True
        else:
            ctx.avisar(f"{id_ficha}: a dependência {dep} não tem ficha nem issue; ignorada.")

    if issue is None and not deps:
        return None
    atuais = set((issue or {}).get("bloqueado_por") or [])
    if issue is not None and not pendente and {ctx.issues[d]["id"] for d in deps} == atuais:
        return None

    def aplicar(c: Contexto) -> None:
        ids = [c.issues[d]["id"] for d in deps]
        c.api.definir_bloqueios(c.numero_de(id_ficha), ids)

    texto = ", ".join(deps) or "nada"
    return Mudanca(id_ficha, f"bloqueado por: {texto}", aplicar)


def planejar_agendada(ctx: Contexto) -> list[Mudanca]:
    """Não lê `features/`: só branches e PRs pela API, e só move colunas."""
    ctx.ler()
    ids: set[str] = set()
    for branch in ctx.api.listar_branches():
        achado = _BRANCH_DE_FEATURE.match(branch)
        if achado:
            ids.add(achado.group(1))

    ultimo_pr: dict[str, dict] = {}
    for pr in ctx.api.listar_prs():
        achado = _BRANCH_DE_FEATURE.match(pr.get("branch") or "")
        if not achado:
            continue
        id_ficha = achado.group(1)
        ids.add(id_ficha)
        anterior = ultimo_pr.get(id_ficha)
        if anterior is None or (pr.get("criado_em") or "") > (anterior.get("criado_em") or ""):
            ultimo_pr[id_ficha] = pr

    mudancas: list[Mudanca] = []
    for id_ficha in sorted(ids):
        issue = ctx.issues.get(id_ficha)
        if issue is None or issue["numero"] not in ctx.itens:
            ctx.avisar(
                f"{id_ficha}: há branch ou PR, mas não há card no Project; "
                "só o push em developer cria o card."
            )
            continue
        numero = issue["numero"]
        atual = ctx.itens[numero]
        if atual not in COLUNAS_DA_AGENDADA:
            continue  # FINALIZADA e REGREDIU só mudam em developer
        nova = coluna_agendada(atual, ultimo_pr.get(id_ficha))
        if nova != atual:
            mudancas.append(
                Mudanca(
                    id_ficha,
                    f"mover o #{numero} de {atual or 'sem coluna'} para {nova}",
                    lambda c, n=numero, col=nova: c.api.definir_coluna(n, col),
                )
            )
    return mudancas


def aplicar(mudancas: list[Mudanca], ctx: Contexto) -> None:
    criacoes = [m for m in mudancas if m.criacao]
    for m in criacoes:
        m.aplicar(ctx)
        print(f"- {m.id_ficha}: {m.descricao}")
    if criacoes:
        ctx.issues = indexar_issues(ctx.api.listar_issues(), [])  # `id` dos issues novos
    for m in mudancas:
        if not m.criacao:
            m.aplicar(ctx)
            print(f"- {m.id_ficha}: {m.descricao}")


def _resumo(n: int, verbo: str) -> str:
    """Ex.: '1 mudança pendente', '2 mudanças pendentes'."""
    return f"{n} mudança {verbo}" if n == 1 else f"{n} mudanças {verbo}s"


# ---------------------------------------------------------------------------
# Cliente real do GitHub (urllib; transporte trocável)
# ---------------------------------------------------------------------------

API = "https://api.github.com"
ORG_PADRAO = "LastroLabs"
PAUSA_ENTRE_ESCRITAS = 0.5  # segundos: limite secundário de taxa

Transporte = Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, str], bytes]]


def transporte_urllib(metodo, url, cabecalhos, corpo):
    pedido = urllib.request.Request(url, data=corpo, headers=cabecalhos, method=metodo)
    try:
        with urllib.request.urlopen(pedido, timeout=30) as resposta:
            return resposta.status, dict(resposta.headers), resposta.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read() or b""
    except urllib.error.URLError as e:
        raise FalhaApi(0, f"sem conexão com o GitHub ({e.reason})") from e


_PROXIMA_PAGINA = re.compile(r'<([^>]+)>;\s*rel="next"')

_Q_PROJETO = """
query($org: String!, $num: Int!, $depois: String) {
  organization(login: $org) {
    projectV2(number: $num) {
      id
      field(name: "Status") { ... on ProjectV2SingleSelectField { id options { id name } } }
      items(first: 100, after: $depois) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content { ... on Issue { number repository { nameWithOwner } } }
          fieldValueByName(name: "Status") {
            ... on ProjectV2ItemFieldSingleSelectValue { name }
          }
        }
      }
    }
  }
}"""

_M_ADICIONAR = """
mutation($projeto: ID!, $conteudo: ID!) {
  addProjectV2ItemById(input: {projectId: $projeto, contentId: $conteudo}) { item { id } }
}"""

_M_COLUNA = """
mutation($projeto: ID!, $item: ID!, $campo: ID!, $opcao: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projeto, itemId: $item, fieldId: $campo,
    value: {singleSelectOptionId: $opcao}
  }) { projectV2Item { id } }
}"""


class GitHubApi:
    """Issues e bloqueios por REST; itens e colunas do Project por GraphQL (2 passos)."""

    def __init__(
        self,
        token: str,
        repo: str,
        org: str,
        numero_projeto: int,
        transporte: Transporte = transporte_urllib,
        com_bloqueios: bool = True,
        pausa: float = PAUSA_ENTRE_ESCRITAS,
    ) -> None:
        self._token = token
        self.repo = repo
        self.org = org
        self.numero_projeto = numero_projeto
        self._transporte = transporte
        self._com_bloqueios = com_bloqueios
        self._pausa = pausa
        self._node_ids: dict[int, str] = {}
        self._item_ids: dict[int, str] = {}
        self._projeto: dict | None = None

    @classmethod
    def do_ambiente(cls, com_bloqueios: bool) -> GitHubApi:
        faltando = [v for v in ("GH_TOKEN", "GITHUB_REPOSITORY", "PROJECT_NUMBER") if not os.environ.get(v)]
        if faltando:
            raise HarnessErro(
                erro="não consegui falar com o GitHub.",
                motivo=f"falta a variável de ambiente {', '.join(faltando)}.",
                correcao=(
                    "defina GH_TOKEN (token do GitHub App), GITHUB_REPOSITORY (dono/repo) e "
                    "PROJECT_NUMBER (número do Project) e rode de novo."
                ),
            )
        try:
            numero = int(os.environ["PROJECT_NUMBER"])
        except ValueError as e:
            raise HarnessErro(
                erro="não consegui achar o Project.",
                motivo="PROJECT_NUMBER não é um número inteiro.",
                correcao="use o número que aparece na URL do Project (…/projects/<número>).",
            ) from e
        return cls(
            token=os.environ["GH_TOKEN"],
            repo=os.environ["GITHUB_REPOSITORY"],
            org=os.environ.get("PROJECT_ORG") or ORG_PADRAO,
            numero_projeto=numero,
            com_bloqueios=com_bloqueios,
        )

    # -- transporte --
    def _pedir(self, metodo: str, url: str, dados: object = None) -> tuple[dict[str, str], object]:
        if not url.startswith("http"):
            url = API + url
        cabecalhos = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lastro-project-sync",
        }
        corpo = None
        if dados is not None:
            corpo = json.dumps(dados).encode("utf-8")
            cabecalhos["Content-Type"] = "application/json"
        if metodo != "GET" and self._pausa:
            time.sleep(self._pausa)
        status, resp_cab, bruto = self._transporte(metodo, url, cabecalhos, corpo)
        try:
            conteudo = json.loads(bruto) if bruto else None
        except json.JSONDecodeError:
            conteudo = None
        if status >= 400:
            mensagem = conteudo.get("message") if isinstance(conteudo, dict) else None
            raise FalhaApi(status, mensagem or f"{metodo} {url.split('?')[0]} falhou")
        return {k.lower(): v for k, v in resp_cab.items()}, conteudo

    def _paginar(self, caminho: str) -> list[dict]:
        url: str | None = caminho
        tudo: list[dict] = []
        while url:
            cab, pagina = self._pedir("GET", url)
            tudo.extend(pagina or [])
            achado = _PROXIMA_PAGINA.search(cab.get("link", ""))
            url = achado.group(1) if achado else None
        return tudo

    def _graphql(self, consulta: str, variaveis: dict) -> dict:
        _, resposta = self._pedir("POST", "/graphql", {"query": consulta, "variables": variaveis})
        if not isinstance(resposta, dict):
            raise FalhaApi(0, "resposta vazia do GraphQL")
        if resposta.get("errors"):
            erro = resposta["errors"][0]
            raise FalhaApi(403 if erro.get("type") == "FORBIDDEN" else 422, erro.get("message", "?"))
        return resposta["data"]

    # -- leitura --
    def listar_issues(self) -> list[dict]:
        issues = []
        for bruto in self._paginar(f"/repos/{self.repo}/issues?state=all&per_page=100"):
            if "pull_request" in bruto:
                continue
            numero = bruto["number"]
            self._node_ids[numero] = bruto["node_id"]
            issue = {
                "numero": numero,
                "id": bruto["id"],
                "titulo": bruto["title"],
                "corpo": bruto.get("body") or "",
                "aberto": bruto["state"] == "open",
                "responsaveis": [a["login"] for a in bruto.get("assignees") or []],
                "bloqueado_por": [],
            }
            if self._com_bloqueios and _TITULO_DO_ISSUE.match(issue["titulo"]):
                issue["bloqueado_por"] = self._bloqueado_por(numero)
            issues.append(issue)
        return issues

    def _bloqueado_por(self, numero: int) -> list[int]:
        caminho = f"/repos/{self.repo}/issues/{numero}/dependencies/blocked_by?per_page=100"
        return [b["id"] for b in self._paginar(caminho)]

    def _carregar_projeto(self, depois: str | None = None) -> dict:
        dados = self._graphql(
            _Q_PROJETO, {"org": self.org, "num": self.numero_projeto, "depois": depois}
        )
        projeto = (dados.get("organization") or {}).get("projectV2")
        if not projeto:
            raise FalhaApi(404, f"Project {self.numero_projeto} não encontrado em {self.org}")
        if self._projeto is None:
            campo = projeto.get("field") or {}
            if not campo.get("id"):
                raise FalhaApi(404, "o Project não tem o campo 'Status'")
            self._projeto = {
                "id": projeto["id"],
                "campo": campo["id"],
                "opcoes": {o["name"]: o["id"] for o in campo.get("options") or []},
            }
        return projeto["items"]

    def listar_itens(self) -> list[dict]:
        itens: list[dict] = []
        depois = None
        while True:
            pagina = self._carregar_projeto(depois)
            for no in pagina["nodes"]:
                conteudo = no.get("content") or {}
                repo = (conteudo.get("repository") or {}).get("nameWithOwner", "")
                if "number" not in conteudo or repo.lower() != self.repo.lower():
                    continue
                self._item_ids[conteudo["number"]] = no["id"]
                status = (no.get("fieldValueByName") or {}).get("name")
                itens.append({"numero": conteudo["number"], "status": status})
            if not pagina["pageInfo"]["hasNextPage"]:
                return itens
            depois = pagina["pageInfo"]["endCursor"]

    def listar_branches(self) -> list[str]:
        return [b["name"] for b in self._paginar(f"/repos/{self.repo}/branches?per_page=100")]

    def listar_prs(self) -> list[dict]:
        caminho = f"/repos/{self.repo}/pulls?state=all&per_page=100&sort=created&direction=desc"
        return [
            {
                "branch": pr["head"]["ref"],
                "aberto": pr["state"] == "open",
                "merge": bool(pr.get("merged_at")),
                "criado_em": pr["created_at"],
            }
            for pr in self._paginar(caminho)
        ]

    def login_existe(self, login: str) -> bool:
        try:
            self._pedir("GET", f"/users/{urllib.parse.quote(login)}")
        except FalhaApi as e:
            if e.status == 404:
                return False
            raise
        return True

    # -- escrita --
    def criar_issue(self, titulo: str, corpo: str) -> int:
        _, issue = self._pedir("POST", f"/repos/{self.repo}/issues", {"title": titulo, "body": corpo})
        self._node_ids[issue["number"]] = issue["node_id"]
        return issue["number"]

    def _editar(self, numero: int, dados: dict) -> None:
        self._pedir("PATCH", f"/repos/{self.repo}/issues/{numero}", dados)

    def atualizar_titulo(self, numero: int, titulo: str) -> None:
        self._editar(numero, {"title": titulo})

    def definir_responsaveis(self, numero: int, logins: list[str]) -> None:
        self._editar(numero, {"assignees": list(logins)})

    def fechar_issue(self, numero: int) -> None:
        self._editar(numero, {"state": "closed"})

    def reabrir_issue(self, numero: int) -> None:
        self._editar(numero, {"state": "open"})

    def definir_bloqueios(self, numero: int, ids: list[int]) -> None:
        base = f"/repos/{self.repo}/issues/{numero}/dependencies/blocked_by"
        atuais = set(self._bloqueado_por(numero))
        for issue_id in sorted(set(ids) - atuais):
            self._pedir("POST", base, {"issue_id": issue_id})
        for issue_id in sorted(atuais - set(ids)):
            self._pedir("DELETE", f"{base}/{issue_id}")

    def adicionar_ao_projeto(self, numero: int) -> None:
        if self._projeto is None:
            self._carregar_projeto()
        if numero not in self._node_ids:
            _, issue = self._pedir("GET", f"/repos/{self.repo}/issues/{numero}")
            self._node_ids[numero] = issue["node_id"]
        dados = self._graphql(
            _M_ADICIONAR, {"projeto": self._projeto["id"], "conteudo": self._node_ids[numero]}
        )
        self._item_ids[numero] = dados["addProjectV2ItemById"]["item"]["id"]

    def definir_coluna(self, numero: int, coluna: str) -> None:
        if self._projeto is None:
            self._carregar_projeto()
        opcao = self._projeto["opcoes"].get(coluna)
        if opcao is None:
            raise FalhaApi(422, f"o campo Status não tem a opção '{coluna}'")
        if numero not in self._item_ids:
            raise FalhaApi(404, f"o issue #{numero} não está no Project")
        self._graphql(
            _M_COLUNA,
            {
                "projeto": self._projeto["id"],
                "item": self._item_ids[numero],
                "campo": self._projeto["campo"],
                "opcao": opcao,
            },
        )


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------


def _erro_da_api(e: FalhaApi) -> HarnessErro:
    if e.status in (401, 403):
        return HarnessErro(
            erro="o GitHub recusou a credencial do sync; nada foi alterado em features/.",
            motivo=f"a API respondeu {e.status} ({e.mensagem}).",
            correcao=(
                "confira os segredos APP_CLIENT_ID e APP_PRIVATE_KEY do Environment project-sync "
                "e se o GitHub App está instalado na organização com acesso a Issues e Projects."
            ),
        )
    return HarnessErro(
        erro="a API do GitHub falhou no meio do sync; nada foi alterado em features/.",
        motivo=f"a API respondeu {e.status} ({e.mensagem}).",
        correcao=(
            "rode de novo daqui a alguns minutos: o sync retoma de onde parou. "
            "Se repetir, confira PROJECT_NUMBER e o campo Status do Project."
        ),
    )


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project_sync", description="Espelha as fichas no Project da organização."
    )
    parser.add_argument("--origem", required=True, choices=("developer", "agendada"))
    parser.add_argument("--dry-run", action="store_true", help="só lista; não escreve nada")
    return parser


def main(argv: list[str] | None = None, raiz: Path | None = None, api: object = None) -> int:
    """Ponto de entrada testável. Devolve o código de saída; não chama sys.exit."""
    raiz = Path(raiz) if raiz is not None else RAIZ_PADRAO
    args = _criar_parser().parse_args(argv)  # uso incorreto: argparse aborta com 2
    ctx = Contexto(api=api)
    try:
        if ctx.api is None:
            ctx.api = GitHubApi.do_ambiente(com_bloqueios=args.origem == "developer")
        if args.origem == "developer":
            mudancas = planejar_developer(raiz, ctx)
        else:
            mudancas = planejar_agendada(ctx)
        for aviso in ctx.avisos:
            print(aviso)
        if args.dry_run:
            for m in mudancas:
                print(f"- {m.id_ficha}: {m.descricao}")
            print(f"{_resumo(len(mudancas), 'pendente')} (dry-run: nada foi escrito).")
            return 0
        aplicar(mudancas, ctx)
        print(f"{_resumo(len(mudancas), 'aplicada')}.")
        return 0
    except FalhaApi as e:
        mostrar_erro(_erro_da_api(e))
        return 2
    except HarnessErro as e:
        mostrar_erro(e)
        return 2


if __name__ == "__main__":
    for _fluxo in (sys.stdout, sys.stderr):
        _fluxo.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
