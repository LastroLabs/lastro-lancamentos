"""Fase B do harness: HX-04 (detectores) e HX-05 (varredura e relatório) do `hx check-clean`.

Cada teste monta um mini-repo em tmp_path e chama main(["check-clean"], raiz=tmp_path).
Git entra só por `harness._executar`, que aqui é sempre substituída (nada de git real).

ATENÇÃO: o próprio repositório é varrido pelo check-clean. Por isso nenhum CPF/CNPJ
válido, chave de API ou chave privada aparece inteiro neste arquivo: tudo é montado
por concatenação em tempo de execução e escrito só em arquivos de tmp_path.
"""

import re
import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import harness

# ---------------------------------------------------------------------------
# Valores sintéticos, montados em tempo de execução
# ---------------------------------------------------------------------------

CPF_VALIDO = "529982247" + "25"
CPF_VALIDO_PONTUADO = "529.982.247" + "-" + "25"
CNPJ_VALIDO = "11222333" + "0001" + "81"
CNPJ_VALIDO_PONTUADO = "11.222.333" + "/" + "0001" + "-" + "81"

CPF_DV_INVALIDO_PONTUADO = "111.222.333-00"  # DV inválido: pode ficar como literal
CPF_DV_INVALIDO = "11122233300"
CNPJ_DV_INVALIDO = "11222333" + "0001" + "00"
CNPJ_DV_INVALIDO_PONTUADO = "11.222.333" + "/" + "0001" + "-" + "00"

# Repetidos: para o CPF, 111... e 000... passam no cálculo do DV, por isso a regra
# "todos os dígitos iguais" precisa existir. Para o CNPJ, 000... idem.
CPF_REPETIDO = "1" * 11
CPF_REPETIDO_PONTUADO = "111.111.111" + "-" + "11"
CPF_ZEROS = "0" * 11
CNPJ_ZEROS = "0" * 14
CNPJ_ZEROS_PONTUADO = "00.000.000" + "/" + "0000" + "-" + "00"

CHAVE_SK = "sk" + "-" + "a" * 30
CHAVE_AWS = "AK" + "IA" + "A" * 16
TOKEN_GITHUB = "ghp" + "_" + "b" * 36
CHAVE_PRIVADA = "-----BEGIN " + "PRIVATE KEY-----"
VALOR_SEGREDO = "Zq4x" + "Lm8w" * 4  # 20 caracteres

NOME_PROIBIDO = "Fulano da Silva"

AVISO_SEM_NOMES = "AVISO: verificação de nomes pulada (variável não definida)"
TIPO_CPF = "CPF com dígito verificador válido"
TIPO_SEGREDO = "possível segredo (atribuição)"


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolar(monkeypatch):
    """Sem git real e sem a lista de nomes da máquina de quem roda o teste."""
    monkeypatch.delenv("LASTRO_NOMES_PROIBIDOS", raising=False)

    def sem_git(cmd, cwd):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(harness, "_executar", sem_git)


def escrever(raiz, relativo, conteudo):
    """Grava `conteudo` (str ou bytes) em <raiz>/<relativo>, sem conversão de quebra de linha."""
    caminho = Path(raiz) / relativo
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = conteudo if isinstance(conteudo, bytes) else conteudo.encode("utf-8")
    caminho.write_bytes(dados)
    return caminho


def atribuicao(chave, separador, valor):
    return f"{chave}{separador}{valor}\n"


def rodar(raiz, capsys):
    codigo = harness.main(["check-clean"], raiz=raiz)
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


def achados(out):
    """Linhas de achado do relatório: {(arquivo, linha)}. Formato: '  arquivo:linha  tipo'."""
    return {
        (m.group(1), int(m.group(2)))
        for m in re.finditer(r"^\s+(\S+):(\d+)\s+\S", out, re.MULTILINE)
    }


def arquivos_acusados(out):
    return {arquivo for arquivo, _ in achados(out)}


def pedacos(valor, tamanho=4):
    """Todos os trechos de `tamanho`+ caracteres contíguos do valor, sem espaço em branco."""
    return {
        valor[i : i + tamanho]
        for i in range(len(valor) - tamanho + 1)
        if not any(c.isspace() for c in valor[i : i + tamanho])
    }


def vazou(valor, texto):
    """True se o valor, ou um pedaço de 4+ caracteres dele, aparece no texto."""
    baixo = texto.lower()
    if valor in texto or valor.lower() in baixo:
        return True
    return any(p in texto or p.lower() in baixo for p in pedacos(valor))


# ---------------------------------------------------------------------------
# HX-04 c1: CPF e CNPJ só com DV válido
# ---------------------------------------------------------------------------


def test_cpf_valido_detectado(tmp_path, capsys):
    escrever(tmp_path, "pontuado.txt", f"CPF do cliente: {CPF_VALIDO_PONTUADO}\n")
    escrever(tmp_path, "solto.txt", f"documento {CPF_VALIDO} fim\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert arquivos_acusados(out) == {"pontuado.txt", "solto.txt"}


def test_cpf_dv_invalido_ignorado(tmp_path, capsys):
    escrever(tmp_path, "pontuado.txt", f"CPF de teste: {CPF_DV_INVALIDO_PONTUADO}\n")
    escrever(tmp_path, "solto.txt", f"documento {CPF_DV_INVALIDO} fim\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 0
    assert achados(out) == set()


def test_cpf_digitos_repetidos_ignorado(tmp_path, capsys):
    escrever(
        tmp_path,
        "repetidos.txt",
        f"{CPF_REPETIDO}\n{CPF_REPETIDO_PONTUADO}\n{CPF_ZEROS}\n",
    )

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 0
    assert achados(out) == set()


def test_cpf_dentro_de_numero_maior_ignorado(tmp_path, capsys):
    # "11 dígitos soltos com fronteira de palavra": 12 dígitos não é CPF
    escrever(tmp_path, "longo.txt", f"protocolo 7{CPF_VALIDO} e {CPF_VALIDO}9\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 0
    assert achados(out) == set()


def test_cnpj_valido_detectado(tmp_path, capsys):
    escrever(tmp_path, "pontuado.txt", f"CNPJ: {CNPJ_VALIDO_PONTUADO}\n")
    escrever(tmp_path, "solto.txt", f"empresa {CNPJ_VALIDO} fim\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert arquivos_acusados(out) == {"pontuado.txt", "solto.txt"}
    assert "CNPJ" in out


def test_cnpj_dv_invalido_ignorado(tmp_path, capsys):
    escrever(
        tmp_path,
        "invalidos.txt",
        # CNPJ_ZEROS: o DV "bate", mas todos os dígitos são iguais
        f"{CNPJ_DV_INVALIDO}\n{CNPJ_DV_INVALIDO_PONTUADO}\n{CNPJ_ZEROS}\n{CNPJ_ZEROS_PONTUADO}\n",
    )

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 0
    assert achados(out) == set()


# ---------------------------------------------------------------------------
# HX-04 c2: chaves, chave privada e atribuição de segredo
# ---------------------------------------------------------------------------


def test_chave_sk_detectada(tmp_path, capsys):
    escrever(tmp_path, "chaves.txt", f"uso a chave {CHAVE_SK} aqui\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert achados(out) == {("chaves.txt", 1)}


def test_chave_aws_detectada(tmp_path, capsys):
    escrever(tmp_path, "chaves.txt", f"uso a chave {CHAVE_AWS} aqui\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert achados(out) == {("chaves.txt", 1)}


def test_token_github_detectado(tmp_path, capsys):
    escrever(tmp_path, "chaves.txt", f"uso o token {TOKEN_GITHUB} aqui\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert achados(out) == {("chaves.txt", 1)}


def test_chave_privada_detectada(tmp_path, capsys):
    escrever(tmp_path, "cert.pem", f"{CHAVE_PRIVADA}\nconteudo ficticio\n")
    escrever(tmp_path, "rsa.pem", "-----BEGIN " + "RSA PRIVATE KEY-----\nx\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert achados(out) == {("cert.pem", 1), ("rsa.pem", 1)}


def test_atribuicao_de_segredo_detectada(tmp_path, capsys):
    escrever(tmp_path, "config.py", f'API_KEY = "{VALOR_SEGREDO}"\n')

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert achados(out) == {("config.py", 1)}


def test_atribuicao_variantes_detectadas(tmp_path, capsys):
    # cada palavra-chave da regra, com "=" e com ":", com e sem aspas
    escrever(tmp_path, "a.env", atribuicao("secret", " = ", VALOR_SEGREDO))
    escrever(tmp_path, "b.yml", atribuicao("password", ": ", f'"{VALOR_SEGREDO}"'))
    escrever(tmp_path, "c.ini", atribuicao("senha", "=", VALOR_SEGREDO))
    escrever(tmp_path, "d.ini", atribuicao("TOKEN", "=", VALOR_SEGREDO))

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert arquivos_acusados(out) == {"a.env", "b.yml", "c.ini", "d.ini"}


def test_atribuicao_placeholder_ignorada(tmp_path, capsys):
    linhas = [
        "API_KEY=changeme",
        "TOKEN=<seu-token>",
        # placeholders com 16+ caracteres: só passam se o placeholder for reconhecido
        "API_KEY=changeme-changeme-changeme",
        "TOKEN=<seu-token-aqui-completo>",
        "SECRET=${SECRET_DA_CI_AQUI_COMPLETO}",
        "PASSWORD=" + "x" * 20,
        "SENHA=exemplo-de-senha-bem-longa",
    ]
    escrever(tmp_path, "exemplo.env", "\n".join(linhas) + "\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 0
    assert achados(out) == set()


# ---------------------------------------------------------------------------
# HX-04 c3: nomes proibidos
# ---------------------------------------------------------------------------


def test_nome_proibido_detectado_sem_acento_e_caixa(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv(
        "LASTRO_NOMES_PROIBIDOS", f"{NOME_PROIBIDO};Beltrana Exemplo;Ciclano Açaí"
    )
    escrever(tmp_path, "caixa.txt", NOME_PROIBIDO.upper() + "\n")
    escrever(tmp_path, "acento.txt", "cliente " + NOME_PROIBIDO[:-1] + "á\n")
    escrever(tmp_path, "decomposto.txt", unicodedata.normalize("NFD", "Fulano da Silvá\n"))
    escrever(tmp_path, "segundo.txt", "x\nbeltrana exemplo\n")  # 2º nome da lista, linha 2
    escrever(tmp_path, "sem_acento.txt", "ciclano acai\n")  # acento só na lista
    escrever(tmp_path, "limpo.txt", "Fulano e Silva, pessoas diferentes\n")

    codigo, out, err = rodar(tmp_path, capsys)

    assert codigo == 1
    assert arquivos_acusados(out) == {
        "caixa.txt",
        "acento.txt",
        "decomposto.txt",
        "segundo.txt",
        "sem_acento.txt",
    }
    assert ("segundo.txt", 2) in achados(out)
    assert AVISO_SEM_NOMES not in err  # a variável existe: nada de aviso


def test_sem_env_de_nomes_avisa_e_continua(tmp_path, capsys):
    escrever(tmp_path, "docs/nota.md", f"cliente {NOME_PROIBIDO} comprou\n")

    codigo, out, err = rodar(tmp_path, capsys)

    assert codigo == 0  # não falha por falta da variável
    assert AVISO_SEM_NOMES in err
    assert AVISO_SEM_NOMES not in out
    assert achados(out) == set()


def test_sem_env_de_nomes_ainda_acusa_o_resto(tmp_path, capsys):
    escrever(tmp_path, "doc.txt", f"CPF {CPF_VALIDO}\n")

    codigo, out, err = rodar(tmp_path, capsys)

    assert codigo == 1
    assert AVISO_SEM_NOMES in err
    assert achados(out) == {("doc.txt", 1)}


# ---------------------------------------------------------------------------
# HX-05 c2: o relatório nunca mostra o valor
# ---------------------------------------------------------------------------


def test_saida_nunca_contem_o_valor(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("LASTRO_NOMES_PROIBIDOS", NOME_PROIBIDO)
    casos = {
        "cpf_pontuado.txt": CPF_VALIDO_PONTUADO,
        "cpf_solto.txt": CPF_VALIDO,
        "cnpj_pontuado.txt": CNPJ_VALIDO_PONTUADO,
        "cnpj_solto.txt": CNPJ_VALIDO,
        "chave_sk.txt": CHAVE_SK,
        "chave_aws.txt": CHAVE_AWS,
        "token_github.txt": TOKEN_GITHUB,
        "chave_pem.pem": CHAVE_PRIVADA,  # o nome não pode conter trechos do valor ("priv")
        "nome.txt": NOME_PROIBIDO,
    }
    for arquivo, valor in casos.items():
        escrever(tmp_path, arquivo, f"antes {valor} depois\n")
    escrever(tmp_path, "atribuicao.py", atribuicao("API_KEY", " = ", f'"{VALOR_SEGREDO}"'))
    casos["atribuicao.py"] = VALOR_SEGREDO

    codigo, out, err = rodar(tmp_path, capsys)

    assert codigo == 1
    # sem isto o teste passaria à toa: todo arquivo tem de ter sido acusado
    assert arquivos_acusados(out) == set(casos)
    for arquivo, valor in casos.items():
        assert not vazou(valor, out + err), f"o relatório vazou o valor de {arquivo}"


def test_saida_informa_arquivo_linha_tipo(tmp_path, capsys):
    escrever(tmp_path, "docs/exemplo.md", f"# Exemplo\n\nCPF: {CPF_VALIDO_PONTUADO}\n")
    escrever(
        tmp_path,
        "src/config.py",
        "import os\n" + atribuicao("API_KEY", " = ", f'"{VALOR_SEGREDO}"'),
    )

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    linhas = out.splitlines()
    assert "check-clean: 2 achado(s)" in linhas
    assert "RESULTADO: FALHOU" in linhas
    assert re.search(
        rf"^\s+docs/exemplo\.md:3\s+{re.escape(TIPO_CPF)}\s*$", out, re.MULTILINE
    )
    assert re.search(
        rf"^\s+src/config\.py:2\s+{re.escape(TIPO_SEGREDO)}\s*$", out, re.MULTILINE
    )


# ---------------------------------------------------------------------------
# HX-05 c1: só os arquivos certos são lidos
# ---------------------------------------------------------------------------


def test_binario_ignorado(tmp_path, capsys):
    binario = tmp_path / "binario"
    escrever(binario, "dados.bin", b"\x00\x01" + f" {CPF_VALIDO} ".encode())

    codigo, out, _ = rodar(binario, capsys)

    assert codigo == 0
    assert achados(out) == set()

    # controle: o \x00 só conta nos primeiros 8 KB; depois disso o arquivo é texto
    texto = tmp_path / "texto"
    escrever(texto, "dados.txt", f"{CPF_VALIDO}\n".encode() + b" " * 9000 + b"\x00")

    codigo, out, _ = rodar(texto, capsys)

    assert codigo == 1
    assert achados(out) == {("dados.txt", 1)}


def test_arquivo_nao_utf8_nao_quebra(tmp_path, capsys):
    escrever(tmp_path, "latin1.txt", b"caf\xe9 \xff\xfe " + f"{CPF_VALIDO}\n".encode())

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert achados(out) == {("latin1.txt", 1)}


def test_arquivo_grande_ignorado(tmp_path, capsys):
    enchimento = b"linha de enchimento sem nada\n" * 80_000  # ~2,3 MB
    assert len(enchimento) > 2 * 1024 * 1024
    escrever(tmp_path, "grande.txt", f"{CPF_VALIDO}\n".encode() + enchimento)

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 0
    assert achados(out) == set()


def test_pasta_ignorada(tmp_path, capsys):
    conteudo = f"CPF {CPF_VALIDO}\n"
    ignoradas = [
        ".git/config",
        "node_modules/pacote/index.js",
        "__pycache__/mod.txt",
        ".venv/Lib/x.txt",
        ".pytest_cache/v/cache.txt",
        "sub/node_modules/y.txt",  # também em subpastas
        "sub/__pycache__/z.txt",
    ]
    for relativo in ignoradas:
        escrever(tmp_path, relativo, conteudo)
    escrever(tmp_path, "src/valido.txt", conteudo)  # controle: este é lido

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert achados(out) == {("src/valido.txt", 1)}


def test_usa_git_ls_files_quando_disponivel(tmp_path, capsys, monkeypatch):
    escrever(tmp_path, "listado.txt", "nada aqui\n")
    escrever(tmp_path, "sub/outro.txt", f"x\nCPF {CPF_VALIDO}\n")
    escrever(tmp_path, "fora_da_lista.txt", f"CPF {CPF_VALIDO}\n")  # o git não lista
    chamadas = []

    def falso_git(cmd, cwd):
        chamadas.append((list(cmd), Path(cwd)))
        if "ls-files" in cmd:
            # "apagado.txt" está no índice mas não existe mais no disco
            return 0, "listado.txt\nsub/outro.txt\napagado.txt\n"
        return 0, "true\n"

    monkeypatch.setattr(harness, "_executar", falso_git)

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert achados(out) == {("sub/outro.txt", 2)}
    assert "fora_da_lista.txt" not in out
    listagem = [cmd for cmd, _ in chamadas if "ls-files" in cmd]
    assert len(listagem) == 1
    assert listagem[0][0] == "git"
    for opcao in ("--cached", "--others", "--exclude-standard"):
        assert opcao in listagem[0]
    assert all(cwd == tmp_path for _, cwd in chamadas)


def test_git_com_erro_cai_no_fallback(tmp_path, capsys, monkeypatch):
    # git existe, mas a raiz não é um repositório: sai com código != 0
    escrever(tmp_path, "src/a.txt", f"CPF {CPF_VALIDO}\n")
    monkeypatch.setattr(
        harness, "_executar", lambda cmd, cwd: (128, "fatal: not a git repository\n")
    )

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert achados(out) == {("src/a.txt", 1)}


def test_fallback_sem_git(tmp_path, capsys, monkeypatch):
    escrever(tmp_path, "a/b/fundo.txt", f"x\nx\nCPF {CPF_VALIDO}\n")
    escrever(tmp_path, "raiz.txt", "limpo\n")
    escrever(tmp_path, ".git/HEAD", f"CPF {CPF_VALIDO}\n")  # ignorado
    visto = []

    def sem_git(cmd, cwd):
        visto.append(cmd[0])
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(harness, "_executar", sem_git)

    codigo, out, _ = rodar(tmp_path, capsys)

    assert visto and visto[0] == "git"  # tentou o git antes de varrer a árvore
    assert codigo == 1
    assert achados(out) == {("a/b/fundo.txt", 3)}


# ---------------------------------------------------------------------------
# HX-05 c3: códigos de saída
# ---------------------------------------------------------------------------


def test_repo_limpo_exit_0(tmp_path, capsys):
    escrever(tmp_path, "README.md", "# Projeto\n\nTexto comum, sem dados.\n")
    escrever(tmp_path, "src/app.py", "print('ola')\n")
    escrever(tmp_path, "docs/teste.md", f"CPF de teste: {CPF_DV_INVALIDO_PONTUADO}\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 0
    assert achados(out) == set()
    assert "FALHOU" not in out


def test_repo_vazio_exit_0(tmp_path, capsys):
    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 0
    assert "FALHOU" not in out


def test_achado_exit_1(tmp_path, capsys):
    escrever(tmp_path, "README.md", "# Projeto\n")
    escrever(tmp_path, "src/app.py", f"DOC = '{CPF_VALIDO}'\n")

    codigo, out, _ = rodar(tmp_path, capsys)

    assert codigo == 1
    assert "RESULTADO: FALHOU" in out
