"""Harness do Lastro (`hx`). Só biblioteca padrão; Python 3.11+.

Fase 0 (HX-01): esqueleto, erros padronizados e códigos de saída.
Fase A (HX-02, HX-03): allowlist de comandos, gravação atômica de fichas e `hx state`.
Fase B (HX-04, HX-05): `hx check-clean` (CPF/CNPJ, segredos e nomes proibidos; nunca imprime o valor).
Fase C (HX-06): `hx verify` (ruff e pytest no container Docker).
Fase D (HX-07): `hx feature verify <ID>` (roda a ficha no container e grava estado e evidência).
Fase E (HX-08, HX-09): `hx feature start <ID>` (valida, cria branch e progress, commita e dá push).

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


def _carregar_fichas_validas(raiz: Path, erro: str, correcao: str) -> list[dict]:
    """Carrega todas as fichas e falha com HarnessErro se qualquer uma tiver problema."""
    fichas = carregar_fichas(raiz)
    problemas = validar_fichas(fichas)
    if problemas:
        raise HarnessErro(
            erro=erro,
            motivo=f"{len(problemas)} problema(s) encontrado(s):\n"
            + "\n".join(f"- {p}" for p in problemas),
            correcao=correcao,
        )
    return fichas


def cmd_state(args: argparse.Namespace, raiz: Path) -> int:
    fichas = _carregar_fichas_validas(
        raiz,
        erro="as fichas de features têm problemas e não consigo montar o painel.",
        correcao="edite o arquivo indicado e rode hx state de novo.",
    )

    fichas = sorted(fichas, key=lambda f: _chave_natural(f["id"]))
    linhas = [
        (f["id"], f["estado"], _texto(f["responsavel"]), _texto(f["prioridade"]), f["titulo"])
        for f in fichas
    ]
    cabecalho = ("ID", "Estado", "Resp.", "Prior.", "Título")
    larguras = [max(len(c), *(len(linha[i]) for linha in linhas)) for i, c in enumerate(cabecalho[:-1])]

    def formatar(campos: tuple[str, ...]) -> str:
        colunas = [c.ljust(w) for c, w in zip(campos[:-1], larguras)]
        return "  ".join([*colunas, campos[-1]]).rstrip()

    print("Lastro — estado das features")
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
_CNPJ = re.compile(
    r"\b(?:[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}|[0-9]{14})\b", re.ASCII
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
    """True se `texto` (com ou sem pontuação) é um CNPJ de DV correto e não repetido."""
    d = _digitos(texto)
    if len(d) != 14 or len(set(d)) == 1:
        return False
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
    if any(not _eh_placeholder(m.group(1)) for m in _SEGREDO.finditer(linha)):
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


def varrer(raiz: Path, nomes: list[str]) -> list[tuple[str, int, str]]:
    """Achados como (arquivo, linha, tipo), em ordem. Sem valores."""
    raiz = Path(raiz)
    achados: list[tuple[str, int, str]] = []
    for relativo in _listar_arquivos(raiz):
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
    """WIP=1: o dev não pode ter outra branch feat/* ainda fora da main. Checagem local."""
    codigo, saida = _git(["branch", "--list", "feat/*", "--no-merged", "origin/main"], raiz)
    if codigo != 0:
        raise HarnessErro(
            erro="não consegui conferir se você tem outra feature aberta.",
            motivo=f"'git branch --no-merged origin/main' falhou: {saida.strip() or 'sem saída'}",
            correcao="rode git fetch origin (para existir origin/main) e tente de novo.",
        )
    abertas = [linha.strip().lstrip("*+").strip() for linha in saida.splitlines() if linha.strip()]
    if abertas:
        raise HarnessErro(
            erro="você já tem uma feature aberta (uma por pessoa e por sessão).",
            motivo="branch ainda fora da main: " + ", ".join(abertas) + ".",
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


def cmd_feature_start(args: argparse.Namespace, raiz: Path) -> int:
    """Valida (barato → caro, rede por último), cria a branch, o progress e a ficha in_progress."""
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
    _git_ou_erro(
        ["switch", "-c", branch, "origin/main"],
        raiz,
        erro=f"não consegui criar a branch {branch}.",
        correcao="confira se a branch já existe localmente (git branch) e se origin/main está atualizada.",
    )

    if template is not None:
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


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hx", description="Harness do Lastro.")
    sub = parser.add_subparsers(dest="comando", required=True, metavar="<comando>")
    p_state = sub.add_parser(
        "state", help="painel de features e quem está com cada uma"
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
        "start", help="abre a feature: valida, cria branch e progress, commita e dá push"
    )
    p_fstart.add_argument("id", help="ID da feature (ex.: HX-08)")
    p_fstart.set_defaults(func=cmd_feature_start)
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
