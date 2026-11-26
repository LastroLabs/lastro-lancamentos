"""Harness do Lastro (`hx`). Só biblioteca padrão; Python 3.11+.

Fase 0 (HX-01): esqueleto, erros padronizados e códigos de saída.
Fase A (HX-02, HX-03): allowlist de comandos, gravação atômica de fichas e `hx state`.
Fase B (HX-04, HX-05): `hx check-clean` (CPF/CNPJ, segredos e nomes proibidos; nunca imprime o valor).
Fase C (HX-06): `hx verify` (ruff e pytest no container Docker).
Fase D (HX-07): `hx feature verify <ID>` (roda a ficha no container e grava estado e evidência).
Fase E (HX-08, HX-09): `hx feature start <ID>` (valida, pergunta se cria a branch a partir de
origin/developer, cria progress, muda a ficha e, se criou a branch, commita e dá push).

Códigos de saída: 0 = ok · 1 = falha esperada (ex.: teste vermelho) · 2 = erro de uso ou de ambiente.
`main` nunca chama sys.exit: só o bloco `if __name__ == "__main__"` faz isso.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

RAIZ_PADRAO = Path(__file__).resolve().parents[1]


class HarnessErro(Exception):
    """Erro de negócio do harness: o que houve, por quê e como corrigir."""

    def __init__(self, erro: str, motivo: str, correcao: str) -> None:
        super().__init__(erro)
        self.erro = erro
        self.motivo = motivo
        self.correcao = correcao


def mostrar_erro(e: HarnessErro) -> None:
    """Imprime as 3 linhas do erro em stderr."""
    print(f"ERRO: {e.erro}", file=sys.stderr)
    print(f"MOTIVO: {e.motivo}", file=sys.stderr)
    print(f"CORREÇÃO: {e.correcao}", file=sys.stderr)


def _executar(cmd: list[str], cwd: Path) -> tuple[int, str]:
    """Roda `cmd` sem shell e devolve (código, stdout + stderr).

    Comando inexistente levanta FileNotFoundError; quem chama decide o que fazer.
    É a única porta de entrada para git e docker nas outras fases.
    """
    resultado = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return resultado.returncode, (resultado.stdout or "") + (resultado.stderr or "")


# ---------------------------------------------------------------------------
# HX-02: allowlist de comandos e gravação de fichas
# ---------------------------------------------------------------------------

_CAMINHO = re.compile(r"^[\w./-]+(::[\w\[\]-]+)*$")
_EXPRESSAO_K = re.compile(r"^[\w ]+$")
_LETRA_DE_DRIVE = re.compile(r"^[A-Za-z]:")


def _motivo_caminho(token: str) -> str | None:
    """Devolve o motivo de recusa de um caminho (ou id de teste pytest), ou None se ok."""
    if token.startswith("/") or _LETRA_DE_DRIVE.match(token):
        return f"o caminho '{token}' não é relativo"
    if ".." in token:
        return f"o caminho '{token}' usa '..'"
    if not _CAMINHO.match(token):
        return f"'{token}' não é um caminho válido (só letras, números, _, ., / e -)"
    return None


def validar_comando(cmd: str) -> str | None:
    """Confere o comando da ficha contra a lista de permitidos. None = ok; senão, o motivo.

    Não usa shell: quebra com shlex e valida cada argumento. Só `pytest` e `ruff check`.
    """
    if any(c in cmd for c in "\n\r\0"):
        return "o comando não pode ter quebra de linha"
    try:
        argv = shlex.split(cmd)
    except ValueError as e:
        return f"não consegui interpretar o comando ({e})"
    if not argv:
        return "o comando está vazio"

    programa, args = argv[0], argv[1:]
    if programa not in ("pytest", "ruff"):
        return f"só 'pytest' e 'ruff' são permitidos, mas o comando começa com '{programa}'"

    if programa == "ruff":
        if not args or args[0] != "check":
            return "o ruff só é permitido como 'ruff check <caminho>'"
        caminhos = args[1:]
        if not caminhos:
            return "'ruff check' exige ao menos um caminho"
        for token in caminhos:
            if token.startswith("-"):
                return f"a opção '{token}' não é permitida no ruff"
            if (motivo := _motivo_caminho(token)) is not None:
                return motivo
        return None

    i = 0
    while i < len(args):
        token = args[i]
        if token in ("-q", "-x"):
            i += 1
        elif token == "-k":
            if i + 1 >= len(args):
                return "a opção '-k' exige uma expressão"
            expressao = args[i + 1]
            if not expressao.strip() or not _EXPRESSAO_K.match(expressao):
                return (
                    f"a expressão do -k ('{expressao}') só pode ter letras, números, "
                    "_ e espaço"
                )
            i += 2
        elif token.startswith("-"):
            return f"a opção '{token}' não é permitida no pytest (só -q, -x e -k)"
        else:
            if (motivo := _motivo_caminho(token)) is not None:
                return motivo
            i += 1
    return None


def salvar_ficha(caminho: Path, ficha: dict) -> None:
    """Grava a ficha em JSON (UTF-8, LF, ordem das chaves mantida) de forma atômica."""
    caminho = Path(caminho)
    texto = json.dumps(ficha, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=caminho.parent, prefix=f".{caminho.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, caminho)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# HX-03: carregar, validar e listar fichas
# ---------------------------------------------------------------------------

ESTADOS = ("not_started", "in_progress", "passing", "blocked", "regressed")
CAMPOS_OBRIGATORIOS = (
    "id",
    "titulo",
    "modulo",
    "requisitos",
    "prioridade",
    "onda",
    "essencial",
    "estado",
    "responsavel",
    "depende_de",
    "bloqueada_por",
    "tipo_verificacao",
    "criterios",
    "verificacao",
    "evidencia",
)


class Ficha(dict):
    """Ficha lida de disco: um dict comum que lembra de qual arquivo veio."""

    arquivo: Path | None = None


def _vazio(valor: object) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, (list, dict)):
        return not valor
    return False


def carregar_fichas(raiz: Path) -> list[dict]:
    """Lê features/*.json em ordem alfabética. Falha com HarnessErro se não houver ficha."""
    pasta = Path(raiz) / "features"
    if not pasta.is_dir():
        raise HarnessErro(
            erro="não consegui ler as features.",
            motivo=f"a pasta 'features/' não existe em {raiz}.",
            correcao="rode o comando na raiz do repositório do Lastro.",
        )
    arquivos = sorted(pasta.glob("*.json"), key=lambda p: p.name)
    if not arquivos:
        raise HarnessErro(
            erro="não encontrei nenhuma ficha de feature.",
            motivo=f"a pasta '{pasta}' não tem nenhum arquivo .json.",
            correcao=(
                "crie as fichas em features/<ID>.json (modelo em "
                "docs/templates/feature_template.md) ou rode na raiz do repositório."
            ),
        )

    fichas: list[dict] = []
    falhas: list[str] = []
    for arquivo in arquivos:
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            falhas.append(f"- {arquivo.name}: linha {e.lineno}, coluna {e.colno}: {e.msg}")
            continue
        except (UnicodeDecodeError, OSError) as e:
            falhas.append(f"- {arquivo.name}: não consegui ler o arquivo ({e})")
            continue
        if not isinstance(dados, dict):
            falhas.append(f"- {arquivo.name}: a ficha deve ser um objeto JSON ({{...}})")
            continue
        ficha = Ficha(dados)
        ficha.arquivo = arquivo
        fichas.append(ficha)

    if falhas:
        raise HarnessErro(
            erro="há ficha com JSON inválido.",
            motivo="\n".join(falhas),
            correcao="edite o arquivo indicado, na linha apontada, e rode hx state de novo.",
        )
    return fichas


def _id_da_ficha(ficha: dict) -> str:
    """ID de referência: o nome do arquivo (a fonte de verdade), ou o campo id."""
    arquivo = getattr(ficha, "arquivo", None)
    if arquivo is not None:
        return arquivo.stem
    valor = ficha.get("id")
    return valor if isinstance(valor, str) and valor else "?"


def _problemas_da_ficha(ficha: dict, ids: set[str]) -> list[str]:
    pid = _id_da_ficha(ficha)
    problemas: list[str] = []

    def add(texto: str) -> None:
        problemas.append(f"{pid}: {texto}")

    for campo in CAMPOS_OBRIGATORIOS:
        if campo not in ficha:
            add(f"campo obrigatório '{campo}' ausente")

    if "id" in ficha and ficha["id"] != pid:
        add(f"o campo id ('{ficha['id']}') é diferente do nome do arquivo ('{pid}.json')")

    estado = ficha.get("estado")
    estado_valido = isinstance(estado, str) and estado in ESTADOS
    if "estado" in ficha and not estado_valido:
        add(f"estado '{estado}' inválido; use um de: {', '.join(ESTADOS)}")

    # critérios
    ids_criterios: set[str] = set()
    criterios_ok = False
    if "criterios" in ficha:
        criterios = ficha["criterios"]
        if not isinstance(criterios, list) or not criterios:
            add("criterios deve ser uma lista com ao menos um critério")
        else:
            criterios_ok = True
            for criterio in criterios:
                cid = criterio.get("id") if isinstance(criterio, dict) else None
                if not isinstance(cid, str) or not cid.strip():
                    add("todo critério precisa de um id (texto não vazio)")
                elif cid in ids_criterios:
                    add(f"o id de critério '{cid}' está repetido")
                else:
                    ids_criterios.add(cid)

    # verificações
    if "verificacao" in ficha:
        verificacoes = ficha["verificacao"]
        if not isinstance(verificacoes, list):
            add("verificacao deve ser uma lista")
        else:
            cobertos: set[str] = set()
            for item in verificacoes:
                if not isinstance(item, dict):
                    add("cada item de verificacao deve ser um objeto com 'criterio' e 'comando'")
                    continue
                alvo = item.get("criterio")
                if criterios_ok and alvo not in ids_criterios:
                    add(f"verificação aponta para o critério '{alvo}', que não existe")
                elif isinstance(alvo, str):
                    cobertos.add(alvo)
                comando = item.get("comando")
                if not isinstance(comando, str):
                    add(f"a verificação do critério '{alvo}' não tem 'comando' (texto)")
                elif (motivo := validar_comando(comando)) is not None:
                    add(f"comando '{comando}' recusado: {motivo}")
            if criterios_ok:
                for cid in sorted(ids_criterios - cobertos):
                    add(f"o critério {cid} não tem nenhuma verificação")

    # dependências
    deps = ficha.get("depende_de")
    if "depende_de" in ficha:
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            add("depende_de deve ser uma lista de IDs")
        else:
            for dep in deps:
                if dep == pid:
                    add("depende de si mesma (ciclo de dependência)")
                elif dep not in ids:
                    add(f"depende_de cita '{dep}', que não existe em features/")

    # coerência entre estado e demais campos
    if estado_valido:
        if estado == "blocked" and _vazio(ficha.get("bloqueada_por")):
            add("estado blocked exige bloqueada_por preenchido (ex.: a decisão D-xx)")
        if estado == "in_progress" and _vazio(ficha.get("responsavel")):
            add("estado in_progress exige responsavel preenchido")
        if estado == "passing" and _vazio(ficha.get("evidencia")):
            add("estado passing exige evidencia preenchida")
        if estado == "not_started" and not _vazio(ficha.get("evidencia")):
            add("estado not_started exige evidencia vazia (null)")

    return problemas


def _ciclos(grafo: dict[str, list[str]]) -> list[tuple[str, ...]]:
    """Ciclos do grafo (cada um uma vez, começando pelo menor ID)."""
    achados: set[tuple[str, ...]] = set()
    cor: dict[str, int] = {}  # ausente = não visitado · 1 = na pilha · 2 = concluído
    pilha: list[str] = []

    def visitar(no: str) -> None:
        cor[no] = 1
        pilha.append(no)
        for vizinho in grafo.get(no, []):
            if cor.get(vizinho) == 1:
                ciclo = pilha[pilha.index(vizinho):]
                k = ciclo.index(min(ciclo))
                achados.add(tuple(ciclo[k:] + ciclo[:k]))
            elif vizinho not in cor:
                visitar(vizinho)
        pilha.pop()
        cor[no] = 2

    for no in sorted(grafo):
        if no not in cor:
            visitar(no)
    return sorted(achados)


def validar_fichas(fichas: list[dict]) -> list[str]:
    """Aplica todas as regras e acumula os problemas. Lista vazia = ok."""
    ids = {_id_da_ficha(f) for f in fichas}
    problemas: list[str] = []
    grafo: dict[str, list[str]] = {}
    for ficha in fichas:
        problemas.extend(_problemas_da_ficha(ficha, ids))
        deps = ficha.get("depende_de")
        if isinstance(deps, list):
            pid = _id_da_ficha(ficha)
            grafo[pid] = [d for d in deps if isinstance(d, str) and d in ids and d != pid]
    for ciclo in _ciclos(grafo):
        caminho = " → ".join((*ciclo, ciclo[0]))
        problemas.append(f"{ciclo[0]}: ciclo de dependência: {caminho}")
    return problemas


def _chave_natural(id_: str) -> list[object]:
    """Ordena HX-2 antes de HX-10."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", id_)]


def _texto(valor: object) -> str:
    return "-" if _vazio(valor) else str(valor)


# ---------------------------------------------------------------------------
# HAR-04: regras de 18/11 (só valem se a raiz tiver o equipe.ts; plan D4, opção A)
# ---------------------------------------------------------------------------

EQUIPE_TS = Path("gitpages") / "src" / "data" / "equipe.ts"
PADRAO_ID = re.compile(r"^[A-Z]{2,4}-\d{2}$")
MODULOS = (
    "core",
    "access",
    "registry",
    "uploads",
    "parsing",
    "validation",
    "classification",
    "questions",
    "review",
    "export",
    "ai",
    "observability",
    "api",
    "worker",
    "harness",
    "ci",
    "web",
)
PRIORIDADES = ("must", "should", "could")
ONDAS = range(1, 5)
_HANDLE_GITHUB = re.compile(r"""\bgithub\s*:\s*['"]([^'"]+)['"]""")
_NOME_DE_TESTE = re.compile(r"::(\S+)")
_CAMPO_DO_PROBLEMA = re.compile(r"^\S+ \((\w+)\):")
DICAS_POR_CAMPO = {
    "id": "o id segue o padrão AAA-00 (2 a 4 letras maiúsculas, hífen e 2 dígitos).",
    "modulo": f"o modulo é um destes: {', '.join(MODULOS)}.",
    "prioridade": f"a prioridade é uma destas: {', '.join(PRIORIDADES)}.",
    "onda": "a onda é um número inteiro de 1 a 4.",
    "responsavel": f"o responsavel é um handle do GitHub listado em {EQUIPE_TS.as_posix()}.",
    "verificacao": "cada nome de teste (depois de '::') pertence a uma só ficha.",
}


def ler_handles_da_equipe(raiz: Path) -> set[str]:
    """Handles (campo `github`) do equipe.ts, em minúsculas. Nenhum lido → HarnessErro."""
    caminho = Path(raiz) / EQUIPE_TS
    try:
        texto = caminho.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        raise HarnessErro(
            erro="não consegui ler a lista da equipe.",
            motivo=f"falha ao ler {EQUIPE_TS.as_posix()} ({e}).",
            correcao="confira se o arquivo existe e está em UTF-8.",
        ) from e
    handles = {h.strip().casefold() for h in _HANDLE_GITHUB.findall(texto) if h.strip()}
    if not handles:
        raise HarnessErro(
            erro="não encontrei nenhum handle na lista da equipe.",
            motivo=f"{EQUIPE_TS.as_posix()} não tem nenhuma linha no formato github: '<handle>'.",
            correcao="preencha o campo github de quem é da equipe, ou corrija o formato do arquivo.",
        )
    return handles


def _problemas_de_regra(ficha: dict, handles: set[str]) -> list[str]:
    pid = _id_da_ficha(ficha)
    problemas: list[str] = []

    def add(campo: str, texto: str) -> None:
        problemas.append(f"{pid} ({campo}): {texto}")

    for campo in ficha:
        if campo not in CAMPOS_OBRIGATORIOS:
            add(campo, f"campo '{campo}' não faz parte da ficha; remova-o")

    if "id" in ficha and not (isinstance(ficha["id"], str) and PADRAO_ID.match(ficha["id"])):
        add("id", f"o id '{ficha['id']}' não segue o padrão AAA-00")
    if "modulo" in ficha and ficha["modulo"] not in MODULOS:
        add("modulo", f"módulo '{ficha['modulo']}' desconhecido")
    if "prioridade" in ficha and ficha["prioridade"] not in PRIORIDADES:
        add("prioridade", f"prioridade '{ficha['prioridade']}' inválida")
    if "onda" in ficha:
        onda = ficha["onda"]
        if isinstance(onda, bool) or not isinstance(onda, int) or onda not in ONDAS:
            add("onda", f"onda '{onda}' inválida")
    if "essencial" in ficha and ficha["essencial"] is not False:
        add("essencial", "essencial deve ser false")
    if "tipo_verificacao" in ficha and ficha["tipo_verificacao"] != "comando":
        add("tipo_verificacao", "tipo_verificacao deve ser 'comando'")
    if ficha.get("estado") != "blocked" and not _vazio(ficha.get("bloqueada_por")):
        add("bloqueada_por", "bloqueada_por só é preenchido quando o estado é blocked")

    responsavel = ficha.get("responsavel")
    if not _vazio(responsavel) and (
        not isinstance(responsavel, str) or responsavel.strip().casefold() not in handles
    ):
        add("responsavel", f"'{responsavel}' não é um handle da equipe")
    return problemas


def _nomes_de_teste(ficha: dict) -> set[str]:
    verificacoes = ficha.get("verificacao")
    if not isinstance(verificacoes, list):
        return set()
    nomes: set[str] = set()
    for item in verificacoes:
        comando = item.get("comando") if isinstance(item, dict) else None
        if isinstance(comando, str):
            nomes.update(_NOME_DE_TESTE.findall(comando))
    return nomes


def validar_regras_do_projeto(fichas: list[dict], raiz: Path) -> list[str]:
    """Regras de 18/11 (HAR-04). Problemas no formato '<ID> (<campo>): <texto>'."""
    handles = ler_handles_da_equipe(raiz)
    problemas: list[str] = []
    donos: dict[str, list[str]] = {}
    for ficha in fichas:
        problemas.extend(_problemas_de_regra(ficha, handles))
        for nome in _nomes_de_teste(ficha):
            donos.setdefault(nome, []).append(_id_da_ficha(ficha))
    for nome, ids in sorted(donos.items()):
        if len(ids) > 1:
            ids = sorted(ids, key=_chave_natural)
            problemas.append(
                f"{ids[0]} (verificacao): o teste '{nome}' aparece em {' e '.join(ids)}"
            )
    return problemas


def _carregar_fichas_validas(raiz: Path, erro: str, correcao: str) -> list[dict]:
    """Carrega todas as fichas e falha com HarnessErro se qualquer uma tiver problema."""
    fichas = carregar_fichas(raiz)
    problemas = validar_fichas(fichas)
    if (Path(raiz) / EQUIPE_TS).is_file():
        problemas += validar_regras_do_projeto(fichas, raiz)
    if problemas:
        campos = {m.group(1) for p in problemas if (m := _CAMPO_DO_PROBLEMA.match(p))}
        dicas = [DICAS_POR_CAMPO[c] for c in DICAS_POR_CAMPO if c in campos]
        raise HarnessErro(
            erro=erro,
            motivo=f"{len(problemas)} problema(s) encontrado(s):\n"
            + "\n".join(f"- {p}" for p in problemas),
            correcao=" ".join([correcao, *(f"Lembre: {d}" for d in dicas)]),
        )
    return fichas


ESTADOS_ATENCAO = ("blocked", "regressed")


def _estados_do_filtro(args: argparse.Namespace) -> tuple[str, ...] | None:
    """Valida as flags do `hx state` e devolve os estados a mostrar (None = todos)."""
    pedidos = getattr(args, "estado", None) or []
    if getattr(args, "atencao", False):
        if pedidos:
            raise HarnessErro(
                erro="--atencao e --estado foram usados juntos.",
                motivo="--atencao já escolhe os estados blocked e regressed.",
                correcao="use só --atencao, ou só --estado com os estados que quer ver.",
            )
        return ESTADOS_ATENCAO
    for estado in pedidos:
        if estado not in ESTADOS:
            raise HarnessErro(
                erro=f"estado '{estado}' não existe.",
                motivo="--estado só aceita os estados das fichas.",
                correcao=f"use um destes: {', '.join(ESTADOS)}.",
            )
    return tuple(pedidos) or None


def cmd_state(args: argparse.Namespace, raiz: Path) -> int:
    filtro = _estados_do_filtro(args)
    fichas = _carregar_fichas_validas(
        raiz,
        erro="as fichas de features têm problemas e não consigo montar o painel.",
        correcao="edite o arquivo indicado e rode hx state de novo.",
    )

    fichas = sorted(fichas, key=lambda f: _chave_natural(f["id"]))
    visiveis = fichas if filtro is None else [f for f in fichas if f["estado"] in filtro]
    linhas = [
        (f["id"], f["estado"], _texto(f["responsavel"]), _texto(f["prioridade"]), f["titulo"])
        for f in visiveis
    ]
    cabecalho = ("ID", "Estado", "Resp.", "Prior.", "Título")
    larguras = [
        max([len(c), *(len(linha[i]) for linha in linhas)]) for i, c in enumerate(cabecalho[:-1])
    ]

    def formatar(campos: tuple[str, ...]) -> str:
        colunas = [c.ljust(w) for c, w in zip(campos[:-1], larguras)]
        return "  ".join([*colunas, campos[-1]]).rstrip()

    print("Lastro — estado das features")
    if getattr(args, "atencao", False) and not linhas:
        print("Nada pede atenção.")
    else:
        print(formatar(cabecalho))
        for linha in linhas:
            print(formatar(linha))
    ordem_do_resumo = ("passing", "in_progress", "not_started", "blocked", "regressed")
    contagem = {e: sum(1 for f in fichas if f["estado"] == e) for e in ordem_do_resumo}
    print("Resumo: " + " · ".join(f"{contagem[e]} {e}" for e in ordem_do_resumo))
    return 0


# ---------------------------------------------------------------------------
# HX-04: detectores (devolvem só o TIPO do achado, nunca o valor)
# ---------------------------------------------------------------------------

VARIAVEL_NOMES = "LASTRO_NOMES_PROIBIDOS"
AVISO_SEM_NOMES = "AVISO: verificação de nomes pulada (variável não definida)"

TIPO_CPF = "CPF com dígito verificador válido"
TIPO_CNPJ = "CNPJ com dígito verificador válido"
TIPO_CHAVE_SK = "chave de API (prefixo sk-)"
TIPO_CHAVE_AWS = "chave de acesso AWS"
TIPO_TOKEN_GITHUB = "token do GitHub"
TIPO_CHAVE_PRIVADA = "chave criptográfica (cabeçalho PEM)"  # sem repetir trechos do cabeçalho
TIPO_SEGREDO = "possível segredo (atribuição)"
TIPO_NOME = "nome proibido"

_CPF = re.compile(r"\b(?:[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}|[0-9]{11})\b", re.ASCII)
# HAR-04: as 12 primeiras posições aceitam letras (CNPJ alfanumérico); os 2 DVs são dígitos.
_CNPJ = re.compile(
    r"\b(?:[0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-[0-9]{2}|[0-9A-Z]{12}[0-9]{2})\b",
    re.ASCII | re.IGNORECASE,
)
_CHAVE_SK = re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}")
_CHAVE_AWS = re.compile(r"(?<![A-Za-z0-9])AKIA[A-Z0-9]{16}")
_TOKEN_GITHUB = re.compile(r"(?<![A-Za-z0-9])ghp_[A-Za-z0-9]{30,}")
_CHAVE_PRIVADA = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
# `\w{0,40}` (e não `\w*`) evita custo quadrático em linhas enormes.
_SEGREDO = re.compile(
    r"(?:api[_-]?key|secret|token|passw(?:or)?d|senha)\w{0,40}[\"']?\s*[=:]\s*[\"']?"
    r"([^\s\"']{16,})",
    re.IGNORECASE,
)
_MARCAS_DE_PLACEHOLDER = ("changeme", "xxx", "exemplo")
# Valor sem aspas que é código (chamada ou índice), não segredo literal: `password =
# secrets.token_urlsafe(12)` ou `"password": pessoas[login]` (CAD-03).
_EXPRESSAO_DE_CODIGO = re.compile(r"[A-Za-z_][\w.]*[(\[]")

_PESOS_CNPJ_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_CNPJ_2 = (6, *_PESOS_CNPJ_1)


def _digitos(texto: str) -> list[int]:
    return [int(c) for c in texto if "0" <= c <= "9"]


def _digito_verificador(digitos: list[int], pesos: tuple[int, ...] | range) -> int:
    resto = sum(d * p for d, p in zip(digitos, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(texto: str) -> bool:
    """True se `texto` (com ou sem pontuação) é um CPF de DV correto e não repetido."""
    d = _digitos(texto)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    return (
        _digito_verificador(d[:9], range(10, 1, -1)) == d[9]
        and _digito_verificador(d[:10], range(11, 1, -1)) == d[10]
    )


def cnpj_valido(texto: str) -> bool:
    """True se `texto` (com ou sem pontuação, numérico ou alfanumérico) é um CNPJ de DV correto.

    Cada caractere vale ord(c) - 48 depois de passar para maiúscula (0 = 0, A = 17); no CNPJ
    numérico isso é o próprio dígito. Os 2 últimos são sempre dígitos. Todos iguais → False.
    """
    chars = [c for c in texto.upper() if c.isascii() and c.isalnum()]
    if len(chars) != 14 or not all(c.isdigit() for c in chars[12:]) or len(set(chars)) == 1:
        return False
    d = [ord(c) - 48 for c in chars]
    return (
        _digito_verificador(d[:12], _PESOS_CNPJ_1) == d[12]
        and _digito_verificador(d[:13], _PESOS_CNPJ_2) == d[13]
    )


def _normalizar(texto: str) -> str:
    """Sem acento, sem diferença de caixa e com espaços colapsados (para comparar nomes)."""
    decomposto = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.casefold().split())


def _nomes_proibidos() -> list[str]:
    """Nomes de LASTRO_NOMES_PROIBIDOS (separados por ;), já normalizados. Vazio se ausente."""
    bruto = os.environ.get(VARIAVEL_NOMES, "")
    return [n for n in (_normalizar(p) for p in bruto.split(";")) if n]


def _eh_placeholder(valor: str) -> bool:
    baixo = valor.lower()
    return baixo.startswith(("<", "${")) or any(m in baixo for m in _MARCAS_DE_PLACEHOLDER)


def _eh_segredo(achado: re.Match[str]) -> bool:
    """True se o valor atribuído parece segredo: nem placeholder, nem expressão de código."""
    valor = achado.group(1)
    if _eh_placeholder(valor):
        return False
    entre_aspas = achado.string[achado.start(1) - 1] in "\"'"
    return entre_aspas or not _EXPRESSAO_DE_CODIGO.match(valor)


def tipos_da_linha(linha: str, nomes: list[str]) -> list[str]:
    """Tipos de achado em uma linha. Nunca devolve (nem guarda) o valor encontrado."""
    tipos: list[str] = []
    if any(cpf_valido(m.group()) for m in _CPF.finditer(linha)):
        tipos.append(TIPO_CPF)
    if any(cnpj_valido(m.group()) for m in _CNPJ.finditer(linha)):
        tipos.append(TIPO_CNPJ)
    if _CHAVE_SK.search(linha):
        tipos.append(TIPO_CHAVE_SK)
    if _CHAVE_AWS.search(linha):
        tipos.append(TIPO_CHAVE_AWS)
    if _TOKEN_GITHUB.search(linha):
        tipos.append(TIPO_TOKEN_GITHUB)
    if _CHAVE_PRIVADA.search(linha):
        tipos.append(TIPO_CHAVE_PRIVADA)
    if any(_eh_segredo(m) for m in _SEGREDO.finditer(linha)):
        tipos.append(TIPO_SEGREDO)
    if nomes:
        normal = _normalizar(linha)
        if any(n in normal for n in nomes):
            tipos.append(TIPO_NOME)
    return tipos


# ---------------------------------------------------------------------------
# HX-05: varredura dos arquivos e relatório
# ---------------------------------------------------------------------------

PASTAS_IGNORADAS = frozenset({".git", "node_modules", "__pycache__", ".venv", ".pytest_cache"})
PASTA_FIXTURES = "fixtures"
LIMITE_BYTES = 1024 * 1024
BYTES_PARA_DETECTAR_BINARIO = 8 * 1024
_COMANDO_GIT = ["git", "-c", "core.quotepath=off", "ls-files", "--cached", "--others", "--exclude-standard"]


def _percorrer_arvore(raiz: Path) -> list[str]:
    """Sem git: caminhos relativos (com `/`) de todos os arquivos, pulando as pastas ignoradas."""
    achados: list[str] = []
    for pasta, subpastas, nomes in os.walk(raiz):
        subpastas[:] = [d for d in subpastas if d not in PASTAS_IGNORADAS]
        for nome in nomes:
            if nome not in PASTAS_IGNORADAS:
                achados.append(os.path.relpath(os.path.join(pasta, nome), raiz).replace(os.sep, "/"))
    return achados


def _listar_arquivos(raiz: Path) -> list[str]:
    """`git ls-files` quando o git responde com sucesso; senão percorre a árvore."""
    try:
        codigo, saida = _executar(_COMANDO_GIT, raiz)
    except OSError:  # inclui FileNotFoundError: git não instalado
        codigo, saida = 1, ""
    if codigo == 0:
        return sorted({linha for linha in saida.splitlines() if linha.strip()})
    return sorted(_percorrer_arvore(raiz))


def _ler_texto(caminho: Path) -> str | None:
    """Texto do arquivo, ou None se for link, binário, grande demais ou ilegível."""
    try:
        if caminho.is_symlink() or not caminho.is_file():
            return None
        with caminho.open("rb") as f:
            dados = f.read(LIMITE_BYTES + 1)
    except OSError:
        return None
    if len(dados) > LIMITE_BYTES or b"\x00" in dados[:BYTES_PARA_DETECTAR_BINARIO]:
        return None
    return dados.decode("utf-8", errors="replace")


def _arquivos_de_fixtures(raiz: Path) -> list[str]:
    """HAR-03: arquivos de fixtures/ (com o prefixo), mesmo fora do Git (.gitignore)."""
    pasta = raiz / PASTA_FIXTURES
    if not pasta.is_dir():
        return []
    return [f"{PASTA_FIXTURES}/{relativo}" for relativo in _percorrer_arvore(pasta)]


def varrer(raiz: Path, nomes: list[str]) -> list[tuple[str, int, str]]:
    """Achados como (arquivo, linha, tipo), em ordem. Sem valores.

    Além do que o git lista, varre fixtures/, que fica no .gitignore (HAR-03).
    """
    raiz = Path(raiz)
    achados: list[tuple[str, int, str]] = []
    arquivos = sorted({*_listar_arquivos(raiz), *_arquivos_de_fixtures(raiz)})
    for relativo in arquivos:
        texto = _ler_texto(raiz / relativo)
        if texto is None:
            continue
        for numero, linha in enumerate(texto.split("\n"), start=1):
            for tipo in tipos_da_linha(linha, nomes):
                achados.append((relativo, numero, tipo))
    return achados


def cmd_check_clean(args: argparse.Namespace, raiz: Path) -> int:
    """Relata arquivo, linha e tipo de cada achado. Nunca o valor: logs do CI são públicos."""
    nomes = _nomes_proibidos()
    if not nomes:
        print(AVISO_SEM_NOMES, file=sys.stderr)
    achados = varrer(raiz, nomes)

    print(f"check-clean: {len(achados)} achado(s)")
    largura = max((len(f"{arquivo}:{linha}") for arquivo, linha, _ in achados), default=0)
    for arquivo, linha, tipo in achados:
        print(f"  {f'{arquivo}:{linha}'.ljust(largura)}  {tipo}")
    print("RESULTADO: FALHOU" if achados else "RESULTADO: OK")
    return 1 if achados else 0


# ---------------------------------------------------------------------------
# HX-06: `hx verify` (ruff e pytest no container)
# ---------------------------------------------------------------------------

LINHAS_DA_CAUDA = 40
CODIGO_PYTEST_SEM_TESTES = 5
_PASSOS_DE_VERIFICACAO = (["ruff", "check", "."], ["pytest", "-q"])
_PASSOS_PULADOS = ("Arquitetura", "E2E")


def montar_comando_docker(
    cmd: list[str], posix: bool, uid: int | None = None, gid: int | None = None
) -> list[str]:
    """Monta `docker compose run` para o serviço `dev`. Função pura (não lê o ambiente).

    `-T` desliga o pseudo-TTY (obrigatório em CI e com a saída capturada). Em POSIX passa
    `--user uid:gid` para não criar arquivos de root no host.
    """
    base = ["docker", "compose", "run", "--rm", "-T"]
    if posix and uid is not None:
        base += ["--user", f"{uid}:{gid}"]
    return base + ["dev"] + list(cmd)


def _erro_docker() -> HarnessErro:
    return HarnessErro(
        erro="Docker indisponível",
        motivo="o comando 'docker info' falhou (daemon desligado ou docker fora do PATH)",
        correcao="abra o Docker Desktop (ou inicie o serviço) e rode hx verify de novo",
    )


def _exigir_docker(raiz: Path) -> None:
    """Falha com HarnessErro (exit 2) se o docker não está no PATH ou o daemon não responde."""
    if shutil.which("docker") is None:
        raise _erro_docker()
    try:
        codigo, _ = _executar(["docker", "info"], raiz)
    except OSError:
        raise _erro_docker() from None
    if codigo != 0:
        raise _erro_docker()


def _comando_no_container(cmd: list[str]) -> list[str]:
    posix = hasattr(os, "getuid")
    uid, gid = (os.getuid(), os.getgid()) if posix else (None, None)
    return montar_comando_docker(cmd, posix, uid, gid)


def _cauda(saida: str) -> str:
    return "\n".join(saida.splitlines()[-LINHAS_DA_CAUDA:])


def cmd_verify(args: argparse.Namespace, raiz: Path) -> int:
    """Roda ruff e pytest no container; os dois rodam mesmo que o primeiro falhe."""
    _exigir_docker(raiz)

    total = len(_PASSOS_DE_VERIFICACAO)
    falhas: list[tuple[str, str, str]] = []  # (passo, saída, aviso)
    for numero, passo in enumerate(_PASSOS_DE_VERIFICACAO, start=1):
        nome = " ".join(passo)
        try:
            codigo, saida = _executar(_comando_no_container(passo), raiz)
        except OSError as e:
            codigo, saida = 127, f"não consegui executar o comando ({e})"
        aviso = ""
        if passo[0] == "pytest" and codigo == CODIGO_PYTEST_SEM_TESTES:
            aviso = "nenhum teste foi coletado (pytest código 5); isso conta como falha"
        ok = codigo == 0
        print(f"[{numero}/{total}] {nome.ljust(15)}{'OK' if ok else 'FALHOU'}")
        if not ok:
            falhas.append((nome, saida, aviso))

    for nome in _PASSOS_PULADOS:
        print(f"{nome}: PULADO (ainda não implementado)")

    for nome, saida, aviso in falhas:
        print()
        print(f"--- {nome}: últimas {LINHAS_DA_CAUDA} linhas da saída ---")
        if aviso:
            print(f"AVISO: {aviso}")
        cauda = _cauda(saida)
        if cauda:
            print(cauda)

    print("RESULTADO: FALHOU" if falhas else "RESULTADO: OK")
    return 1 if falhas else 0


# ---------------------------------------------------------------------------
# HX-07: `hx feature verify <ID>` (único jeito legítimo de marcar uma feature como pronta)
# ---------------------------------------------------------------------------

_ESTADOS_VERIFICAVEIS = ("in_progress", "regressed", "passing")
_LINHAS_DE_ARVORE_SUJA = 10


def _agora() -> str:
    """Instante atual em UTC, ISO 8601 com Z. Função à parte para os testes fixarem o relógio."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _exigir_arvore_limpa(raiz: Path, comando: str = "hx feature verify") -> None:
    """Falha com HarnessErro se `git status --porcelain` não está vazio (ou o git não responde).

    `comando` só entra na mensagem de correção ("... e rode <comando> de novo").
    """
    try:
        codigo, saida = _executar(["git", "status", "--porcelain"], raiz)
    except OSError:
        codigo, saida = 1, "git não encontrado"
    if codigo != 0:
        raise HarnessErro(
            erro="não consegui consultar o git.",
            motivo=f"'git status --porcelain' falhou: {saida.strip() or 'sem saída'}",
            correcao="rode o comando dentro do repositório git do Lastro, com o git instalado.",
        )
    linhas = [linha for linha in saida.splitlines() if linha.strip()]
    if linhas:
        mostradas = linhas[:_LINHAS_DE_ARVORE_SUJA]
        resto = len(linhas) - len(mostradas)
        if resto > 0:
            mostradas.append(f"... e mais {resto} arquivo(s)")
        raise HarnessErro(
            erro="a árvore de trabalho tem alterações não commitadas.",
            motivo="evidência de árvore suja não é reproduzível:\n" + "\n".join(mostradas),
            correcao=f"faça commit (ou guarde com git stash) e rode {comando} de novo.",
        )


def _commit_atual(raiz: Path) -> str:
    """Hash curto (12 caracteres) do HEAD."""
    try:
        codigo, saida = _executar(["git", "rev-parse", "--short=12", "HEAD"], raiz)
    except OSError:
        codigo, saida = 1, "git não encontrado"
    commit = saida.strip()
    if codigo != 0 or not commit:
        raise HarnessErro(
            erro="não consegui descobrir o commit atual.",
            motivo=f"'git rev-parse --short=12 HEAD' falhou: {commit or 'sem saída'}",
            correcao="faça ao menos um commit no repositório e rode hx feature verify de novo.",
        )
    return commit


def _escolher_ficha(fichas: list[dict], id_: str) -> dict:
    for ficha in fichas:
        if _id_da_ficha(ficha) == id_:
            return ficha
    disponiveis = ", ".join(sorted((_id_da_ficha(f) for f in fichas), key=_chave_natural))
    raise HarnessErro(
        erro=f"a feature '{id_}' não existe.",
        motivo=f"não há features/{id_}.json. IDs disponíveis: {disponiveis}.",
        correcao="confira o ID (hx state lista todas) e rode o comando de novo.",
    )


def _exigir_estado_verificavel(ficha: dict, id_: str) -> None:
    estado = ficha["estado"]
    if estado in _ESTADOS_VERIFICAVEIS:
        return
    if estado == "blocked":
        raise HarnessErro(
            erro=f"a feature {id_} está bloqueada.",
            motivo=f"estado blocked, bloqueada_por: {ficha['bloqueada_por']}.",
            correcao="resolva o bloqueio (decisão em docs/decisoes/DECISIONS.md) antes de verificar.",
        )
    raise HarnessErro(
        erro=f"a feature {id_} ainda não foi iniciada.",
        motivo=f"estado {estado}: só in_progress, regressed e passing podem ser verificadas.",
        correcao=f"rode hx feature start {id_} --owner <nome>.",
    )


def cmd_feature_verify(args: argparse.Namespace, raiz: Path) -> int:
    """Roda as verificações da ficha no container e grava `estado` e `evidencia`."""
    fichas = _carregar_fichas_validas(
        raiz,
        erro="as fichas de features têm problemas e não consigo verificar.",
        correcao="edite o arquivo indicado e rode hx feature verify de novo.",
    )
    id_ = args.id
    ficha = _escolher_ficha(fichas, id_)
    _exigir_estado_verificavel(ficha, id_)
    _exigir_arvore_limpa(raiz)
    commit = _commit_atual(raiz)
    _exigir_docker(raiz)

    # Defesa em profundidade: revalida tudo antes de executar qualquer coisa.
    itens = ficha["verificacao"]
    for item in itens:
        if (motivo := validar_comando(item["comando"])) is not None:
            raise HarnessErro(
                erro="comando da ficha recusado.",
                motivo=f"{id_}, critério {item['criterio']}: '{item['comando']}': {motivo}",
                correcao="corrija o comando na ficha para um permitido (pytest ou ruff check).",
            )

    resultados: list[dict] = []
    falhas: list[tuple[str, str, str]] = []  # (critério, comando, saída)
    for item in itens:
        criterio, comando = item["criterio"], item["comando"]
        try:
            codigo, saida = _executar(_comando_no_container(shlex.split(comando)), raiz)
        except OSError as e:
            codigo, saida = 127, f"não consegui executar o comando ({e})"
        ok = codigo == 0
        print(f"[{criterio}] {comando} → {'OK' if ok else 'FALHOU'}")
        resultados.append({"criterio": criterio, "comando": comando, "resultado": "ok" if ok else "falhou"})
        if not ok:
            falhas.append((criterio, comando, saida))

    nome_do_arquivo = f"features/{ficha.arquivo.name}" if getattr(ficha, "arquivo", None) else f"features/{id_}.json"

    if falhas:
        for criterio, comando, saida in falhas:
            print()
            print(f"--- [{criterio}] {comando}: últimas {LINHAS_DA_CAUDA} linhas da saída ---")
            cauda = _cauda(saida)
            if cauda:
                print(cauda)
        print()
        print("Critérios que falharam: " + ", ".join(dict.fromkeys(c for c, _, _ in falhas)))
        if ficha["estado"] == "passing":
            ficha["estado"] = "regressed"  # a evidência antiga fica, para auditoria
            salvar_ficha(ficha.arquivo, ficha)
            print(f"{id_} voltou para regressed. Faça commit de {nome_do_arquivo}.")
        else:
            print(f"{id_} continua {ficha['estado']}; a ficha não foi alterada.")
        print("RESULTADO: FALHOU")
        return 1

    ficha["estado"] = "passing"
    ficha["evidencia"] = {"verificado_em": _agora(), "commit": commit, "resultados": resultados}
    salvar_ficha(ficha.arquivo, ficha)
    print(f"Ficha atualizada. Faça commit de {nome_do_arquivo}.")
    print("RESULTADO: OK")
    return 0


# ---------------------------------------------------------------------------
# HX-08, HX-09: `hx feature start <ID>` (abre a feature de forma padronizada)
# ---------------------------------------------------------------------------

LIMITE_DO_SLUG = 40
BASE_REMOTA = "origin/developer"  # base das branches de feature (entrega da sprint)
VARIAVEL_USUARIO = "HX_USUARIO"
_MARCADORES_DO_PROGRESS = re.compile(r"\{\{(ID|TITULO|RESPONSAVEL|BRANCH|DATA)\}\}")


def slug(titulo: str) -> str:
    """Título → trecho da branch: minúsculas, sem acento, só [a-z0-9] e '-', até 40 caracteres.

    Função pura: não lê ambiente, disco nem relógio.
    """
    decomposto = unicodedata.normalize("NFKD", titulo)
    ascii_puro = decomposto.encode("ascii", "ignore").decode("ascii").lower()
    colapsado = re.sub(r"[^a-z0-9]+", "-", ascii_puro).strip("-")
    return colapsado[:LIMITE_DO_SLUG].rstrip("-")


def _git(args: list[str], raiz: Path) -> tuple[int, str]:
    """Roda `git <args>` pela porta única `_executar`; git ausente vira código 127."""
    try:
        return _executar(["git", *args], raiz)
    except OSError as e:
        return 127, f"git não encontrado ({e})"


def _identidade_do_dev(raiz: Path) -> str:
    """HX_USUARIO, ou `git config user.name`. Falha se nenhum dos dois existe."""
    usuario = os.environ.get(VARIAVEL_USUARIO, "").strip()
    if usuario:
        return usuario
    codigo, saida = _git(["config", "user.name"], raiz)
    nome = saida.strip()
    if codigo != 0 or not nome:
        raise HarnessErro(
            erro="não sei quem você é.",
            motivo=f"a variável {VARIAVEL_USUARIO} está vazia e 'git config user.name' não devolveu nome.",
            correcao=f"defina {VARIAVEL_USUARIO} com o seu nome da ficha (ou rode git config user.name).",
        )
    return nome


def _exigir_responsavel(ficha: dict, id_: str, raiz: Path) -> None:
    dev = _identidade_do_dev(raiz)
    responsavel = ficha["responsavel"]
    if _normalizar(dev) != _normalizar(str(responsavel)):
        raise HarnessErro(
            erro=f"a feature {id_} não é sua.",
            motivo=f"a ficha está com '{responsavel}' e você é '{dev}'.",
            correcao=(
                f"peça para reatribuir a ficha em PR ou ajuste {VARIAVEL_USUARIO} "
                f"(ex.: {VARIAVEL_USUARIO}={responsavel})."
            ),
        )


def _exigir_estado_iniciavel(ficha: dict, id_: str) -> None:
    estado = ficha["estado"]
    if estado in ("not_started", "regressed"):
        return
    if estado == "blocked":
        raise HarnessErro(
            erro=f"a feature {id_} está bloqueada.",
            motivo=f"estado blocked, bloqueada_por: {ficha['bloqueada_por']}.",
            correcao="resolva o bloqueio (decisão em docs/decisoes/DECISIONS.md) antes de iniciar.",
        )
    if estado == "in_progress":
        correcao = f"continue de onde parou (progress/{id_}.md) e use hx feature verify {id_} ao terminar."
    else:
        correcao = "a feature já foi entregue; se algo quebrou, hx feature verify a marca como regressed."
    raise HarnessErro(
        erro=f"a feature {id_} não pode ser iniciada.",
        motivo=f"estado {estado}: só not_started e regressed podem ser iniciadas.",
        correcao=correcao,
    )


def _exigir_dependencias_prontas(ficha: dict, id_: str, fichas: list[dict]) -> None:
    por_id = {_id_da_ficha(f): f for f in fichas}
    pendentes = [
        f"{dep} ({por_id[dep]['estado']})"
        for dep in ficha["depende_de"]
        if por_id[dep]["estado"] != "passing"
    ]
    if pendentes:
        raise HarnessErro(
            erro=f"a feature {id_} depende de features que ainda não estão passing.",
            motivo="pendentes: " + ", ".join(pendentes) + ".",
            correcao="espere (ou ajude a terminar) as dependências e rode o comando de novo.",
        )


def _exigir_sem_wip(raiz: Path) -> None:
    """WIP=1: o dev não pode ter outra branch feat/* ainda fora da developer. Checagem local."""
    codigo, saida = _git(["branch", "--list", "feat/*", "--no-merged", BASE_REMOTA], raiz)
    if codigo != 0:
        raise HarnessErro(
            erro="não consegui conferir se você tem outra feature aberta.",
            motivo=f"'git branch --no-merged {BASE_REMOTA}' falhou: {saida.strip() or 'sem saída'}",
            correcao=f"rode git fetch origin (para existir {BASE_REMOTA}) e tente de novo.",
        )
    abertas = [linha.strip().lstrip("*+").strip() for linha in saida.splitlines() if linha.strip()]
    if abertas:
        raise HarnessErro(
            erro="você já tem uma feature aberta (uma por pessoa e por sessão).",
            motivo=f"branch ainda fora da {BASE_REMOTA.split('/')[-1]}: " + ", ".join(abertas) + ".",
            correcao="termine essa feature (PR aprovado e mergeado) ou apague a branch, e rode de novo.",
        )


def _exigir_rede_ok(args: list[str], raiz: Path, o_que: str) -> str:
    codigo, saida = _git(args, raiz)
    if codigo != 0:
        raise HarnessErro(
            erro=f"não consegui {o_que}.",
            motivo=f"'git {' '.join(args)}' falhou: {saida.strip() or 'sem saída'}",
            correcao="resolva a rede/permissão e rode o comando de novo.",
        )
    return saida


def _exigir_sem_branch_remota(id_: str, raiz: Path) -> None:
    """Nenhuma branch feat/<ID>-* em origin. O filtro é em Python (sem glob, sem aspas)."""
    saida = _exigir_rede_ok(["ls-remote", "--heads", "origin"], raiz, "consultar as branches do origin")
    prefixo = f"refs/heads/feat/{id_}-"
    existentes = []
    for linha in saida.splitlines():
        partes = linha.split()
        if partes and partes[-1].startswith(prefixo):
            existentes.append(partes[-1].removeprefix("refs/heads/"))
    if existentes:
        raise HarnessErro(
            erro=f"a feature {id_} já tem branch no origin.",
            motivo="branch remota: " + ", ".join(existentes) + ".",
            correcao=f"retome essa branch (git switch ...) ou combine com quem a criou; não crie outra para {id_}.",
        )


def _data_br(instante: str) -> str:
    """'2026-11-13T14:02:11Z' → '13/11/2026'."""
    return datetime.strptime(instante, "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")


def _ler_template_do_progress(raiz: Path) -> str:
    caminho = raiz / "docs" / "templates" / "progress.md"
    try:
        return caminho.read_text(encoding="utf-8")
    except OSError as e:
        raise HarnessErro(
            erro="não consegui ler o template do progress.",
            motivo=f"{caminho}: {e}",
            correcao="confira se docs/templates/progress.md existe e rode o comando na raiz do repositório.",
        ) from None


def _git_ou_erro(args: list[str], raiz: Path, erro: str, correcao: str) -> None:
    codigo, saida = _git(args, raiz)
    if codigo != 0:
        raise HarnessErro(
            erro=erro,
            motivo=f"'git {' '.join(args)}' falhou: {saida.strip() or 'sem saída'}",
            correcao=correcao,
        )


def _terminal_interativo() -> bool:
    """True se há um terminal para perguntar. Função à parte para os testes a trocarem."""
    entrada = sys.stdin
    return entrada is not None and entrada.isatty()


def _ler_resposta(pergunta: str) -> str:
    """Mostra a pergunta e lê a resposta. Função à parte para os testes a trocarem."""
    return input(pergunta)


def _confirmar_criacao_da_branch(branch: str) -> bool:
    """Pergunta se deve criar `branch` a partir da base. Fora de terminal assume sim.

    Vazio e EOF contam como não (o padrão é [s/N]); resposta que não é sim nem não repete a pergunta.
    """
    if not _terminal_interativo():
        return True
    pergunta = f"Criar a branch {branch} a partir de {BASE_REMOTA}? [s/N] "
    while True:
        try:
            resposta = _normalizar(_ler_resposta(pergunta))
        except EOFError:
            return False
        if resposta in ("s", "sim", "y", "yes"):
            return True
        if resposta in ("", "n", "nao", "no"):
            return False
        print("Responda s (sim) ou n (não).")


def _desfazer_branch(branch: str, raiz: Path) -> bool:
    """Volta para a branch anterior e apaga `branch` (que ainda não tem commits). True se deu certo."""
    codigo, _ = _git(["switch", "-"], raiz)
    if codigo != 0:
        return False
    codigo, _ = _git(["branch", "-d", branch], raiz)
    return codigo == 0


def cmd_feature_start(args: argparse.Namespace, raiz: Path) -> int:
    """Valida (barato → caro, rede por último), confirma a branch, cria o progress e a ficha in_progress."""
    id_ = args.id
    fichas = _carregar_fichas_validas(
        raiz,
        erro="as fichas de features têm problemas e não consigo iniciar.",
        correcao="edite o arquivo indicado e rode hx feature start de novo.",
    )
    ficha = _escolher_ficha(fichas, id_)

    # Sem rede.
    _exigir_responsavel(ficha, id_, raiz)
    _exigir_estado_iniciavel(ficha, id_)
    _exigir_dependencias_prontas(ficha, id_, fichas)
    progress = raiz / "progress" / f"{id_}.md"
    template = None if progress.exists() else _ler_template_do_progress(raiz)
    _exigir_sem_wip(raiz)

    # Rede.
    _exigir_rede_ok(["fetch", "origin"], raiz, "atualizar o origin")
    _exigir_sem_branch_remota(id_, raiz)
    _exigir_arvore_limpa(raiz, comando="hx feature start")

    # Escrita.
    branch = f"feat/{id_}-{slug(ficha['titulo'])}"
    criar_branch = not args.sem_branch and _confirmar_criacao_da_branch(branch)

    if criar_branch:
        _git_ou_erro(
            ["switch", "-c", branch, BASE_REMOTA],
            raiz,
            erro=f"não consegui criar a branch {branch}.",
            correcao=f"confira se a branch já existe localmente (git branch) e se {BASE_REMOTA} está atualizada.",
        )
        if not ficha.arquivo.is_file():
            # A ficha só existia na árvore anterior: a base ainda não a tem.
            desfeito = _desfazer_branch(branch, raiz)
            raise HarnessErro(
                erro=f"a ficha {id_} não existe na {BASE_REMOTA}.",
                motivo=f"depois de criar {branch} a partir de {BASE_REMOTA}, features/{ficha.arquivo.name} "
                "sumiu: a ficha (e o harness) ainda não foram mergeados nessa branch.",
                correcao=(
                    f"faça o merge da ficha na {BASE_REMOTA.split('/')[-1]} (PR) e rode o comando de novo. "
                    + (
                        "A branch criada foi desfeita."
                        if desfeito
                        else f"Volte para a sua branch com git switch - e apague {branch} com git branch -d {branch}."
                    )
                ),
            )

    if template is not None:
        progress.parent.mkdir(parents=True, exist_ok=True)
        valores = {
            "ID": id_,
            "TITULO": ficha["titulo"],
            "RESPONSAVEL": str(ficha["responsavel"]),
            "BRANCH": branch,
            "DATA": _data_br(_agora()),
        }
        texto = _MARCADORES_DO_PROGRESS.sub(lambda m: valores[m.group(1)], template)
        with progress.open("w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    ficha["estado"] = "in_progress"
    salvar_ficha(ficha.arquivo, ficha)

    nome_da_ficha = f"features/{ficha.arquivo.name}"
    if not criar_branch:
        print(f"Feature {id_} iniciada sem branch: nada foi commitado nem enviado.")
        print(f"Progress: progress/{id_}.md · Ficha: {nome_da_ficha} (in_progress, só no seu disco)")
        print(f"Próximo passo: crie a sua branch (sugestão de nome: {branch}) e faça o primeiro commit")
        print("com esses dois arquivos; depois escreva os testes primeiro (regra 3 do AGENTS.md).")
        return 0

    _git_ou_erro(
        ["add", f"progress/{id_}.md", nome_da_ficha],
        raiz,
        erro="não consegui preparar o commit.",
        correcao=f"rode: git add progress/{id_}.md {nome_da_ficha} e depois git commit e git push -u origin {branch}.",
    )
    _git_ou_erro(
        ["commit", "-m", f"chore({id_}): inicia feature"],
        raiz,
        erro="não consegui criar o commit.",
        correcao=f"resolva o problema do git (hooks, identidade) e rode: git commit; git push -u origin {branch}.",
    )
    _git_ou_erro(
        ["push", "-u", "origin", branch],
        raiz,
        erro=f"a branch {branch} foi criada só localmente.",
        correcao=f"resolva a rede/permissão e rode: git push -u origin {branch}.",
    )

    print(f"Branch criada: {branch}")
    print(f"Progress: progress/{id_}.md")
    print("Próximo passo: escreva os testes primeiro (regra 3 do AGENTS.md).")
    return 0


# ---------------------------------------------------------------------------
# HAR-03: `hx fixtures build [--semente N] [--check]`
# ---------------------------------------------------------------------------

ARQUIVOS_PRESERVADOS = frozenset({".gitkeep"})


def _semente(texto: str) -> int:
    """Tipo do argparse para --semente: inteiro ≥ 0 (Random trata -N como N)."""
    try:
        valor = int(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"valor inválido {texto!r}: use um inteiro ≥ 0") from None
    if valor < 0:
        raise argparse.ArgumentTypeError(f"valor inválido {texto!r}: use um inteiro ≥ 0")
    return valor


def _arquivos_em_disco(pasta: Path) -> set[str]:
    """Caminhos relativos (com /) dos arquivos de fixtures/, sem os preservados."""
    if not pasta.is_dir():
        return set()
    return {r for r in _percorrer_arvore(pasta) if r.rsplit("/", 1)[-1] not in ARQUIVOS_PRESERVADOS}


def _exigir_sem_documentos(arquivos: dict[str, bytes], membros_xlsx) -> None:
    """D7: aborta se alguma linha gerada tiver achado do check-clean (antes de gravar)."""
    nomes = _nomes_proibidos()
    achados: list[str] = []
    for relativo, dados in arquivos.items():
        if relativo.endswith(".xlsx"):
            textos = {f"{relativo}!{m}": t for m, t in membros_xlsx(dados).items()}
        else:
            textos = {relativo: dados.decode("utf-8", errors="replace")}
        for onde, texto in textos.items():
            for numero, linha in enumerate(texto.split("\n"), start=1):
                achados += [f"{onde}:{numero} ({tipo})" for tipo in tipos_da_linha(linha, nomes)]
    if achados:
        raise HarnessErro(
            "o gerador produziu linha com documento ou segredo; nada foi gravado",
            f"{len(achados)} achado(s): " + "; ".join(achados[:10]),
            "corrija tools/fixtures_sinteticas.py (ou rode com outra --semente) e rode "
            "hx fixtures build de novo",
        )


def _gravar_fixtures(pasta: Path, arquivos: dict[str, bytes]) -> int:
    """Grava o mapa e apaga o que o gerador não gera (exceto .gitkeep). Devolve quantos apagou."""
    sobras = sorted(_arquivos_em_disco(pasta) - set(arquivos))
    for relativo, dados in arquivos.items():
        destino = pasta / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(dados)
    for relativo in sobras:
        (pasta / relativo).unlink()
    for subpasta in sorted({(pasta / r).parent for r in sobras}, key=lambda p: -len(p.parts)):
        if subpasta != pasta and subpasta.is_dir() and not any(subpasta.iterdir()):
            subpasta.rmdir()
    return len(sobras)


def _divergencias(pasta: Path, arquivos: dict[str, bytes]) -> list[str]:
    """Só lê o disco: arquivos alterados, ausentes e a mais em relação ao mapa gerado."""
    em_disco = _arquivos_em_disco(pasta)
    linhas = []
    for relativo, dados in arquivos.items():
        if relativo not in em_disco:
            linhas.append(f"ausente: {PASTA_FIXTURES}/{relativo}")
        elif (pasta / relativo).read_bytes() != dados:
            linhas.append(f"alterado: {PASTA_FIXTURES}/{relativo}")
    linhas += [f"a mais: {PASTA_FIXTURES}/{r}" for r in sorted(em_disco - set(arquivos))]
    return linhas


def cmd_fixtures_build(args: argparse.Namespace, raiz: Path) -> int:
    """Gera fixtures/ pela semente (função pura do gerador); com --check, só confere."""
    import fixtures_sinteticas as gerador  # D1: só aqui, para o hx não depender dele ao abrir

    semente = gerador.SEMENTE_PADRAO if args.semente is None else args.semente
    arquivos = gerador.gerar_arquivos(semente)
    pasta = raiz / PASTA_FIXTURES
    comando = "hx fixtures build" + ("" if args.semente is None else f" --semente {semente}")

    if args.check:
        divergencias = _divergencias(pasta, arquivos)
        if divergencias:
            mostrar_erro(HarnessErro(
                f"{PASTA_FIXTURES}/ não está em dia com a semente {semente} "
                f"({len(divergencias)} divergência(s)); nada foi gravado",
                "; ".join(divergencias),
                f"rode {comando} para gerar a pasta de novo e repita o --check",
            ))
            return 1
        print(f"fixtures em dia: {len(arquivos)} arquivo(s) iguais aos da semente {semente}")
        return 0

    _exigir_sem_documentos(arquivos, gerador.membros_xlsx)
    apagados = _gravar_fixtures(pasta, arquivos)
    print(
        f"fixtures: {len(arquivos)} arquivo(s) gravado(s) em {PASTA_FIXTURES}/ "
        f"(semente {semente}); {apagados} arquivo(s) antigo(s) apagado(s)"
    )
    return 0


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hx", description="Harness do Lastro.")
    sub = parser.add_subparsers(dest="comando", required=True, metavar="<comando>")
    p_state = sub.add_parser(
        "state", help="painel de features e quem está com cada uma"
    )
    p_state.add_argument(
        "--estado",
        action="append",
        metavar="ESTADO",
        help="mostra só as fichas deste estado (pode repetir): " + ", ".join(ESTADOS),
    )
    p_state.add_argument(
        "--atencao",
        action="store_true",
        help="mostra só as fichas blocked e regressed",
    )
    p_state.set_defaults(func=cmd_state)
    p_clean = sub.add_parser(
        "check-clean", help="procura dado real e segredo no repositório (nunca mostra o valor)"
    )
    p_clean.set_defaults(func=cmd_check_clean)
    p_verify = sub.add_parser("verify", help="roda ruff e pytest no container Docker")
    p_verify.set_defaults(func=cmd_verify)
    p_feature = sub.add_parser("feature", help="comandos de uma feature")
    sub_feature = p_feature.add_subparsers(dest="acao", required=True, metavar="<ação>")
    p_fverify = sub_feature.add_parser(
        "verify", help="roda as verificações da ficha e grava estado e evidência"
    )
    p_fverify.add_argument("id", help="ID da feature (ex.: HX-07)")
    p_fverify.set_defaults(func=cmd_feature_verify)
    p_fstart = sub_feature.add_parser(
        "start",
        help=f"abre a feature: valida, pergunta se cria a branch a partir de {BASE_REMOTA}, cria o progress",
    )
    p_fstart.add_argument("id", help="ID da feature (ex.: HX-08)")
    p_fstart.add_argument(
        "--sem-branch",
        action="store_true",
        help="não cria branch nem commita: só muda a ficha e cria o progress (você cria a sua branch)",
    )
    p_fstart.set_defaults(func=cmd_feature_start)
    p_fixtures = sub.add_parser(
        "fixtures", help="dados sintéticos de teste (cadastro, OFX, planilhas e gabarito)"
    )
    sub_fixtures = p_fixtures.add_subparsers(dest="acao", required=True, metavar="<ação>")
    p_fbuild = sub_fixtures.add_parser(
        "build",
        help=(
            f"gera {PASTA_FIXTURES}/ a partir de uma semente fixa e apaga dela o que o "
            "gerador não produz (exceto .gitkeep)"
        ),
        description=(
            f"Gera {PASTA_FIXTURES}/ a partir de uma semente fixa (mesma semente, mesmos bytes). "
            f"Atenção: sem --check, apaga de {PASTA_FIXTURES}/ os arquivos que o gerador não "
            "produz (exceto .gitkeep)."
        ),
    )
    p_fbuild.add_argument(
        "--semente", type=_semente, default=None, metavar="N",
        help="semente do sorteio, inteiro ≥ 0 (padrão: 1)",
    )
    p_fbuild.add_argument(
        "--check",
        action="store_true",
        help=f"só confere se {PASTA_FIXTURES}/ está em dia com a semente; não grava nada",
    )
    p_fbuild.set_defaults(func=cmd_fixtures_build)
    return parser


def main(argv: list[str] | None = None, raiz: Path | None = None) -> int:
    """Ponto de entrada testável. Devolve o código de saída; não chama sys.exit."""
    raiz = Path(raiz) if raiz is not None else RAIZ_PADRAO
    args = _criar_parser().parse_args(argv)  # uso incorreto: argparse aborta com 2
    try:
        return int(args.func(args, raiz))
    except HarnessErro as e:
        mostrar_erro(e)
        return 2


if __name__ == "__main__":
    for _fluxo in (sys.stdout, sys.stderr):
        _fluxo.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
