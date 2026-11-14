"""Fase E do harness: HX-08 e HX-09 (`hx feature start <ID>`).

Nenhum teste chama git de verdade nem usa rede: `harness._executar` é sempre trocado por um
`GitFalso`, que registra as chamadas e responde por prefixo do comando. Cada teste monta fichas
e o template do progress em tmp_path. Só dados sintéticos.

Contrato assumido (plano, fase e):
- `harness.slug(titulo)` devolve o slug do título (minúsculas, sem acento, só [a-z0-9] e "-",
  hífens colapsados, no máximo 40 caracteres, sem hífen no fim).
- o comando é `harness.main(["feature", "start", ID], raiz=...)`; a identidade do dev vem de
  HX_USUARIO (ou de `git config user.name`), comparada de forma normalizada com `responsavel`.
- a data do progress (DD/MM/AAAA) vem de `harness._agora()`.
- ordem das checagens: fichas válidas → ID existe → responsável → estado → dependências →
  WIP (`git branch`) → `git fetch` → `git ls-remote` → `git status`. Só então escreve.
- execução: `git switch -c <branch> origin/main` → progress → ficha → `git add` →
  `git commit -m "chore(<ID>): inicia feature"` → `git push -u origin <branch>`.
- falha de HarnessErro vira exit 2 com ERRO / MOTIVO / CORREÇÃO em stderr.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import harness  # precisa vir depois do ajuste do sys.path

AGORA = "2026-11-13T14:02:11Z"
ID = "HAR-02"
TITULO = "Conferir saldo do extrato"
BRANCH = "feat/HAR-02-conferir-saldo-do-extrato"
DATA = "13/11/2026"
TEMPLATE = harness.RAIZ_PADRAO / "docs" / "templates" / "progress.md"

REDE = {"fetch", "ls-remote", "push"}
ESCRITA = {"switch", "add", "commit", "push"}

EVIDENCIA = {
    "verificado_em": "2026-11-01T08:00:00Z",
    "commit": "000000000000",
    "resultados": [{"criterio": "c1", "comando": "pytest tests/x.py::test_a -q", "resultado": "ok"}],
}


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def _ficha(id_=ID, estado="not_started", titulo=TITULO, **override):
    """Ficha sintética válida. `override` troca campos."""
    ficha = {
        "id": id_,
        "titulo": titulo,
        "modulo": "harness",
        "requisitos": [],
        "prioridade": "must",
        "onda": 1,
        "essencial": False,
        "estado": estado,
        "responsavel": "caio",
        "depende_de": [],
        "bloqueada_por": None,
        "tipo_verificacao": "comando",
        "criterios": [
            {"id": "c1", "descricao": "Faz a", "exemplo": {"entrada": "x", "saida": "y"}},
        ],
        "verificacao": [{"criterio": "c1", "comando": "pytest tests/x.py::test_a -q"}],
        "evidencia": None,
    }
    if estado == "passing":
        ficha["evidencia"] = copy.deepcopy(EVIDENCIA)
    ficha.update(override)
    return ficha


def _gravar(raiz, ficha):
    pasta = Path(raiz) / "features"
    pasta.mkdir(exist_ok=True)
    caminho = pasta / f"{ficha['id']}.json"
    harness.salvar_ficha(caminho, ficha)
    return caminho


def _ler(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def _sem_opcoes_globais(cmd):
    """Tira `git` e as opções globais (`-c k=v`, `-C dir`) do começo: sobra verbo + argumentos."""
    args = list(cmd[1:])
    while len(args) >= 2 and args[0] in ("-c", "-C"):
        args = args[2:]
    return args


class GitFalso:
    """Substitui `_executar`: registra as chamadas e responde por prefixo do comando.

    `respostas` mapeia um prefixo (tupla de tokens depois do `git`) para (código, saída).
    Vale o prefixo mais longo. Comando sem resposta programada derruba o teste.
    `ao_chamar` mapeia um verbo para uma função chamada no momento da chamada (para olhar o
    disco naquele instante).
    """

    PADRAO = {
        ("config", "user.name"): (0, "Caio\n"),
        ("branch",): (0, ""),
        ("fetch",): (0, ""),
        ("ls-remote",): (0, "1111111111111111111111111111111111111111\trefs/heads/main\n"),
        ("status",): (0, ""),
        ("switch",): (0, "Switched to a new branch\n"),
        ("add",): (0, ""),
        ("commit",): (0, "[ok] chore\n"),
        ("push",): (0, ""),
    }

    def __init__(self, respostas=None):
        self.respostas = {**self.PADRAO, **(respostas or {})}
        self.ao_chamar = {}
        self.chamadas = []  # lista de (argumentos sem `git` e sem opções globais, cwd)

    def __call__(self, cmd, cwd):
        assert cmd[0] == "git", f"só git passa por aqui nesta fase: {cmd}"
        args = _sem_opcoes_globais(cmd)
        prefixos = [p for p in self.respostas if tuple(args[: len(p)]) == p]
        if not prefixos:
            raise AssertionError(f"chamada git inesperada: {cmd}")
        resposta = self.respostas[max(prefixos, key=len)]
        self.chamadas.append((args, cwd))
        if args[0] in self.ao_chamar:
            self.ao_chamar[args[0]]()
        return resposta

    @property
    def verbos(self):
        return [args[0] for args, _ in self.chamadas]

    @property
    def ordem(self):
        """Verbos na ordem da primeira chamada de cada um."""
        return list(dict.fromkeys(self.verbos))

    def chamada(self, verbo):
        """Argumentos da primeira chamada do verbo (ou falha mostrando o que houve)."""
        for args, _ in self.chamadas:
            if args[0] == verbo:
                return args
        raise AssertionError(f"git {verbo} não foi chamado; chamadas: {self.verbos}")


@pytest.fixture
def preparar(tmp_path, monkeypatch):
    """Monta fichas, template e progress/ em tmp_path e troca `_executar` por um GitFalso.

    Devolve `preparar(fichas=None, usuario="Caio", respostas=None) -> GitFalso`.
    """

    def _preparar(fichas=None, usuario="Caio", respostas=None):
        for ficha in fichas if fichas is not None else [_ficha()]:
            _gravar(tmp_path, ficha)
        (tmp_path / "docs" / "templates").mkdir(parents=True)
        (tmp_path / "docs" / "templates" / "progress.md").write_text(
            TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (tmp_path / "progress").mkdir()
        monkeypatch.setenv("HX_USUARIO", usuario)
        monkeypatch.setattr(harness, "_agora", lambda: AGORA)
        git = GitFalso(respostas)
        monkeypatch.setattr(harness, "_executar", git)
        return git

    return _preparar


def _iniciar(tmp_path, capsys, id_=ID):
    codigo = harness.main(["feature", "start", id_], raiz=tmp_path)
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


def _confere_erro(err):
    assert "ERRO:" in err
    assert "MOTIVO:" in err
    assert "CORREÇÃO:" in err


def _recusou_sem_rede_nem_escrita(codigo, err, git):
    assert codigo == 2
    _confere_erro(err)
    assert not (set(git.verbos) & (REDE | ESCRITA)), f"chamadas indevidas: {git.verbos}"


# ---------------------------------------------------------------------------
# HX-09 c1: slug
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("titulo", "esperado"),
    [
        pytest.param("Conferir saldo do extrato", "conferir-saldo-do-extrato", id="simples"),
        pytest.param("Validação à vista: Ação Única", "validacao-a-vista-acao-unica", id="acento"),
        pytest.param("  Leitura   de   OFX  ", "leitura-de-ofx", id="espacos"),
        pytest.param("Saldo (R$) & juros — 100%", "saldo-r-juros-100", id="simbolos"),
        pytest.param("Exportar o extrato conferido para o Excel do Domínio",
                     "exportar-o-extrato-conferido-para-o-exce", id="40_caracteres"),  # fmt: skip
        pytest.param("a" * 50, "a" * 40, id="corta_em_40"),
        pytest.param("a" * 39 + " b", "a" * 39, id="hifen_final_depois_do_corte"),
        pytest.param("Relatório final!!!", "relatorio-final", id="simbolo_no_fim"),
    ],
)
def test_slug(titulo, esperado):
    resultado = harness.slug(titulo)

    assert resultado == esperado
    assert len(resultado) <= 40
    assert not resultado.endswith("-")
    assert "--" not in resultado


# ---------------------------------------------------------------------------
# HX-08 c1: ficha inexistente e responsável diferente (sem tocar a rede)
# ---------------------------------------------------------------------------


def test_ficha_inexistente(tmp_path, capsys, preparar):
    git = preparar([_ficha("HAR-01"), _ficha("HAR-02")])

    codigo, _, err = _iniciar(tmp_path, capsys, "ZZ-99")

    _recusou_sem_rede_nem_escrita(codigo, err, git)
    assert "ZZ-99" in err


def test_responsavel_diferente_recusa(tmp_path, capsys, preparar):
    git = preparar(usuario="ana")  # a ficha é de "caio"
    caminho = tmp_path / "features" / f"{ID}.json"
    antes = caminho.read_bytes()

    codigo, _, err = _iniciar(tmp_path, capsys)

    _recusou_sem_rede_nem_escrita(codigo, err, git)
    assert "HX_USUARIO" in err  # a correção cita a variável
    assert caminho.read_bytes() == antes


# ---------------------------------------------------------------------------
# HX-08 c2: estado permitido e dependências
# ---------------------------------------------------------------------------


def test_blocked_recusa(tmp_path, capsys, preparar):
    git = preparar([_ficha(estado="blocked", bloqueada_por="D-05")])

    codigo, _, err = _iniciar(tmp_path, capsys)

    _recusou_sem_rede_nem_escrita(codigo, err, git)
    assert "D-05" in err  # cita bloqueada_por


def test_in_progress_recusa(tmp_path, capsys, preparar):
    git = preparar([_ficha(estado="in_progress")])

    codigo, _, err = _iniciar(tmp_path, capsys)

    _recusou_sem_rede_nem_escrita(codigo, err, git)
    assert "in_progress" in err


def test_passing_recusa(tmp_path, capsys, preparar):
    git = preparar([_ficha(estado="passing")])

    codigo, _, err = _iniciar(tmp_path, capsys)

    _recusou_sem_rede_nem_escrita(codigo, err, git)
    assert "passing" in err


def test_dependencia_nao_passing_recusa(tmp_path, capsys, preparar):
    git = preparar(
        [
            _ficha("HAR-00", estado="passing"),
            _ficha("HAR-01", estado="in_progress", responsavel="ana"),
            _ficha("HAR-04", estado="not_started", responsavel="ana"),
            _ficha("HAR-02", depende_de=["HAR-00", "HAR-01", "HAR-04"]),
        ]
    )

    codigo, _, err = _iniciar(tmp_path, capsys)

    _recusou_sem_rede_nem_escrita(codigo, err, git)
    assert "HAR-01" in err and "HAR-04" in err  # lista todas as pendentes
    assert "HAR-00" not in err  # a que já está passing não aparece


def test_regressed_pode_reiniciar(tmp_path, capsys, preparar):
    git = preparar([_ficha(estado="regressed", evidencia=copy.deepcopy(EVIDENCIA))])

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 0, err
    depois = _ler(tmp_path / "features" / f"{ID}.json")
    assert depois["estado"] == "in_progress"
    assert depois["evidencia"] == EVIDENCIA  # a evidência antiga fica
    assert "push" in git.verbos


# ---------------------------------------------------------------------------
# HX-08 c3: WIP e branch remota
# ---------------------------------------------------------------------------


def test_wip_recusa_com_branch_aberta(tmp_path, capsys, preparar):
    git = preparar(respostas={("branch",): (0, "  feat/HAR-03-x\n")})

    codigo, _, err = _iniciar(tmp_path, capsys)

    _recusou_sem_rede_nem_escrita(codigo, err, git)
    assert "feat/HAR-03-x" in err  # cita a branch aberta
    consulta = git.chamada("branch")
    assert "--list" in consulta and "feat/*" in consulta
    assert "--no-merged" in consulta and "origin/main" in consulta
    assert not (set(git.verbos) & {"fetch", "ls-remote"})  # a checagem é local


def test_branch_remota_existente_recusa(tmp_path, capsys, preparar):
    git = preparar(
        respostas={
            ("ls-remote",): (
                0,
                "2222222222222222222222222222222222222222\trefs/heads/feat/HAR-02-qualquer\n",
            )
        }
    )

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 2
    _confere_erro(err)
    assert not (set(git.verbos) & ESCRITA), f"escreveu antes de recusar: {git.verbos}"
    assert "feat/HAR-02-qualquer" in err
    assert "fetch" in git.verbos and "ls-remote" in git.verbos


def test_ls_remote_filtra_em_python(tmp_path, capsys, preparar):
    # Outras branches, inclusive HAR-020 (começa com "HAR-02" mas não com "HAR-02-"):
    # o filtro tem de ser pelo prefixo refs/heads/feat/HAR-02-, e não deixa passar nem barrar errado.
    outras = (
        "1111111111111111111111111111111111111111\trefs/heads/main\n"
        "3333333333333333333333333333333333333333\trefs/heads/feat/HAR-03-x\n"
        "4444444444444444444444444444444444444444\trefs/heads/feat/HAR-020-outra\n"
    )
    git = preparar(respostas={("ls-remote",): (0, outras)})

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 0, err  # nenhuma das linhas é do HAR-02
    chamada = git.chamada("ls-remote")
    assert "--heads" in chamada and "origin" in chamada
    assert not any("*" in token for token in chamada), f"padrão com asterisco: {chamada}"


# ---------------------------------------------------------------------------
# HX-08 c4: árvore suja e ordem das verificações
# ---------------------------------------------------------------------------


def test_arvore_suja_recusa(tmp_path, capsys, preparar):
    git = preparar(respostas={("status",): (0, " M README.md\n")})

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 2
    _confere_erro(err)
    assert "porcelain" in " ".join(git.chamada("status"))
    assert not (set(git.verbos) & ESCRITA)  # nada foi criado
    assert not (tmp_path / "progress" / f"{ID}.md").exists()
    assert _ler(tmp_path / "features" / f"{ID}.json")["estado"] == "not_started"


CENARIOS_SEM_REDE = {
    "ficha_inexistente": dict(pedido="ZZ-99"),
    "ficha_invalida_em_outra": dict(
        fichas=[_ficha(), _ficha("HAR-05", estado="estado_que_nao_existe")]
    ),
    "responsavel_diferente": dict(usuario="ana"),
    "bloqueada": dict(fichas=[_ficha(estado="blocked", bloqueada_por="D-05")]),
    "in_progress": dict(fichas=[_ficha(estado="in_progress")]),
    "passing": dict(fichas=[_ficha(estado="passing")]),
    "dependencia_pendente": dict(
        fichas=[_ficha("HAR-01", estado="in_progress", responsavel="ana"),
                _ficha(depende_de=["HAR-01"])]  # fmt: skip
    ),
    "wip": dict(respostas={("branch",): (0, "  feat/HAR-03-x\n")}),
}


@pytest.mark.parametrize("cenario", sorted(CENARIOS_SEM_REDE))
def test_ordem_das_verificacoes_sem_rede_primeiro(tmp_path, capsys, preparar, cenario):
    opcoes = dict(CENARIOS_SEM_REDE[cenario])
    pedido = opcoes.pop("pedido", ID)
    git = preparar(**opcoes)

    codigo, _, err = _iniciar(tmp_path, capsys, pedido)

    assert codigo == 2, err
    assert not (set(git.verbos) & {"fetch", "ls-remote"}), (
        f"chamou a rede antes de uma checagem local falhar: {git.verbos}"
    )


def test_ordem_das_verificacoes_no_caminho_feliz(tmp_path, capsys, preparar):
    git = preparar()

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 0, err
    # WIP (local) → fetch → ls-remote → status → só então escreve (switch, add, commit, push)
    ordem = [v for v in git.ordem if v != "config"]
    assert ordem == ["branch", "fetch", "ls-remote", "status", "switch", "add", "commit", "push"]


# ---------------------------------------------------------------------------
# HX-09 c2: branch e progress
# ---------------------------------------------------------------------------


def test_cria_branch_a_partir_de_origin_main(tmp_path, capsys, preparar):
    git = preparar()

    codigo, out, err = _iniciar(tmp_path, capsys)

    assert codigo == 0, err
    assert git.chamada("switch") == ["switch", "-c", BRANCH, "origin/main"]
    # mensagem final: branch, caminho do progress e próximo passo
    assert BRANCH in out
    assert "progress/HAR-02.md" in out
    assert "teste" in out.lower()  # escreva os testes primeiro


def test_cria_progress_com_substituicoes(tmp_path, capsys, preparar):
    preparar()
    template = TEMPLATE.read_text(encoding="utf-8")
    assert "{{ID}}" in template  # o template de verdade tem os marcadores

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 0, err
    texto = (tmp_path / "progress" / f"{ID}.md").read_text(encoding="utf-8")
    assert "{{" not in texto and "}}" not in texto
    assert f"# {ID} · {TITULO}" in texto
    assert "Responsável: caio" in texto  # o da ficha, não o texto digitado em HX_USUARIO
    assert f"`{BRANCH}`" in texto
    assert f"Início: {DATA}" in texto
    esperado = (
        template.replace("{{ID}}", ID)
        .replace("{{TITULO}}", TITULO)
        .replace("{{RESPONSAVEL}}", "caio")
        .replace("{{BRANCH}}", BRANCH)
        .replace("{{DATA}}", DATA)
    )
    assert texto == esperado  # o resto do template fica intacto


def test_nao_sobrescreve_progress_existente(tmp_path, capsys, preparar):
    preparar([_ficha(estado="regressed", evidencia=copy.deepcopy(EVIDENCIA))])
    progress = tmp_path / "progress" / f"{ID}.md"
    progress.write_text("# anotações da sessão anterior\n- 10/11 · S1 · feito\n", encoding="utf-8")
    antes = progress.read_bytes()

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 0, err
    assert progress.read_bytes() == antes


# ---------------------------------------------------------------------------
# HX-09 c3: estado da ficha, commit e push
# ---------------------------------------------------------------------------


def test_ficha_vira_in_progress(tmp_path, capsys, preparar):
    preparar()
    caminho = tmp_path / "features" / f"{ID}.json"
    antes = _ler(caminho)

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 0, err
    depois = _ler(caminho)
    assert depois["estado"] == "in_progress"
    assert list(depois) == list(antes)  # mesmas chaves, na mesma ordem
    assert {k for k in antes if antes[k] != depois[k]} == {"estado"}


def test_commit_e_push_na_ordem(tmp_path, capsys, preparar):
    git = preparar()
    no_add = {}

    def olhar_disco():
        no_add["estado"] = _ler(tmp_path / "features" / f"{ID}.json")["estado"]
        no_add["progress"] = (tmp_path / "progress" / f"{ID}.md").exists()

    git.ao_chamar["add"] = olhar_disco

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 0, err
    # ficha e progress já estavam gravados quando o add rodou
    assert no_add == {"estado": "in_progress", "progress": True}
    escritas = [v for v in git.verbos if v in ("add", "commit", "push")]
    assert escritas == ["add", "commit", "push"]
    add = git.chamada("add")
    assert "progress/HAR-02.md" in add and "features/HAR-02.json" in add
    commit = git.chamada("commit")
    assert commit[commit.index("-m") + 1] == "chore(HAR-02): inicia feature"
    assert git.chamada("push") == ["push", "-u", "origin", BRANCH]


# ---------------------------------------------------------------------------
# HX-09 c4: falha no push
# ---------------------------------------------------------------------------


def test_falha_no_push_mantem_branch_e_orienta(tmp_path, capsys, preparar):
    git = preparar(respostas={("push",): (1, "fatal: unable to access 'origin'\n")})

    codigo, _, err = _iniciar(tmp_path, capsys)

    assert codigo == 2
    _confere_erro(err)
    correcao = err[err.index("CORREÇÃO:") :]
    assert f"git push -u origin {BRANCH}" in correcao
    # depois do switch só houve add, commit e push: a branch local não foi apagada nem trocada
    assert git.verbos[git.verbos.index("switch") :] == ["switch", "add", "commit", "push"]
    # o trabalho local ficou: ficha in_progress e progress criado
    assert _ler(tmp_path / "features" / f"{ID}.json")["estado"] == "in_progress"
    assert (tmp_path / "progress" / f"{ID}.md").exists()
