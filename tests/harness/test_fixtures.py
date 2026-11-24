"""HAR-03: fixtures e gabarito sintéticos gerados por semente fixa (`hx fixtures build`).

Os 14 testes com nome em `verificacao` da ficha vêm primeiro, na ordem de lá. Depois vêm
os testes das decisões aprovadas do plan (pergunta 2, D1 a D7), com nomes que não colidem.

Todo build roda em tmp_path via `harness.main([...], raiz=tmp_path)`. Nada grava em
fixtures/ da raiz do repositório.

O gerador (`tools/fixtures_sinteticas.py`, D1) é importado dentro de cada teste, e não no
topo: enquanto ele não existe, cada teste falha pelo próprio motivo, e não todos por um
ImportError na coleta.

ATENÇÃO: o próprio repositório é varrido pelo check-clean. Nenhum CPF ou CNPJ com DV válido
aparece inteiro neste arquivo: os DVs são calculados em tempo de execução com as funções
do harness, e o valor só é escrito em arquivos de tmp_path. Todos os dados são inventados.
"""

import importlib
import json
import random
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from pathlib import Path

RAIZ_REAL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REAL / "tools"))

import harness

PASTA = "fixtures"
SEMENTE_PADRAO = 1  # D5
NOME_DO_GERADOR = "fixtures_sinteticas"  # D1: tools/fixtures_sinteticas.py

ESCRITORIOS_ESPERADOS = {  # c1
    "ESC-1": {
        "usuarios": {("chefe_1", "chefe"), ("contador_a", "contador"), ("contador_b", "contador")},
        "clientes": {"EMP-1": "contador_a", "EMP-2": "contador_b"},
    },
    "ESC-2": {
        "usuarios": {("chefe_2", "chefe"), ("contador_x", "contador")},
        "clientes": {"EMP-9": "contador_x"},
    },
}

# Documentos de teste nas descrições (D5: com máscara, no formato que a IA-01 reconhece).
_CPF_COM_MASCARA = re.compile(r"(?<![0-9])[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}(?![0-9])")
_CNPJ_COM_MASCARA = re.compile(
    r"(?<![0-9A-Z])[0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-[0-9]{2}(?![0-9])",
    re.IGNORECASE,
)
_AGENCIA = re.compile(r"\bAG\b\.?\s*:?\s*\d{1,6}(?:-[\dX])?(?![\d-])", re.IGNORECASE)
_CONTA = re.compile(r"\bCC\b\.?\s*:?\s*\d[\d.]{0,14}-[\dX](?![\d-])", re.IGNORECASE)

_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BANCO = re.compile(r"^\d{3}$")


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def gerador():
    """O módulo do gerador (D1). Importado só na hora: ainda não existe na T1."""
    return importlib.import_module(NOME_DO_GERADOR)


def rodar(argv, raiz, capsys):
    """Roda o hx e devolve (código, stdout, stderr). Erro de uso do argparse vira código 2."""
    try:
        codigo = harness.main(argv, raiz=raiz)
    except SystemExit as e:  # argparse: subcomando ou opção inválida
        codigo = e.code if isinstance(e.code, int) else 2
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


def gerar(raiz, capsys, semente=None):
    """`hx fixtures build` em `raiz`, exigindo código 0. Devolve a pasta fixtures/ gerada."""
    raiz = Path(raiz)
    (raiz / PASTA).mkdir(parents=True, exist_ok=True)
    (raiz / PASTA / ".gitkeep").touch()
    argv = ["fixtures", "build"]
    if semente is not None:
        argv += ["--semente", str(semente)]
    codigo, out, err = rodar(argv, raiz, capsys)
    assert codigo == 0, f"build falhou com código {codigo}\nstdout:\n{out}\nstderr:\n{err}"
    return raiz / PASTA


def instantaneo(pasta):
    """Mapa caminho relativo (com /) → bytes de todos os arquivos, sem o .gitkeep."""
    pasta = Path(pasta)
    return {
        p.relative_to(pasta).as_posix(): p.read_bytes()
        for p in sorted(pasta.rglob("*"))
        if p.is_file() and p.name != ".gitkeep"
    }


def ler_cadastro(pasta):
    return json.loads((Path(pasta) / "cadastro.json").read_bytes().decode("utf-8"))


def clientes(cadastro):
    """(escritório, cliente) de todos os clientes do cadastro."""
    return [(esc, cli) for esc in cadastro["escritorios"] for cli in esc["clientes"]]


def contas(cadastro):
    """(cliente, conta bancária) de todas as contas do cadastro."""
    return [(cli, conta) for _, cli in clientes(cadastro) for conta in cli["contas_bancarias"]]


def ler_gabarito(pasta, conta):
    return json.loads((Path(pasta) / conta["gabarito"]).read_bytes().decode("utf-8"))


def centavos(texto):
    """'-15.90' → -1590, sem float (regra 8). Aceita ponto ou vírgula decimal."""
    texto = texto.strip().replace(",", ".")
    sinal = -1 if texto.startswith("-") else 1
    inteiro, _, fracao = texto.lstrip("+-").partition(".")
    assert len(fracao) <= 2, f"valor com mais de 2 casas decimais: {texto!r}"
    return sinal * (int(inteiro or "0") * 100 + int((fracao + "00")[:2]))


def _campo(bloco, tag):
    """Valor de uma tag folha do OFX SGML (sem fechamento) ou None."""
    m = re.search(rf"<{tag}>([^<\r\n]*)", bloco)
    return m.group(1).strip() if m else None


def ler_ofx(caminho):
    """Leitura mínima do OFX 1.0.2: cabeçalho, transações e saldo final, em centavos."""
    texto = Path(caminho).read_bytes().decode("ascii")
    transacoes = []
    for bloco in re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, re.DOTALL):
        transacoes.append(
            {
                "fitid": _campo(bloco, "FITID"),
                "data": _campo(bloco, "DTPOSTED"),
                "valor": centavos(_campo(bloco, "TRNAMT")),
                "memo": _campo(bloco, "MEMO"),
                "name": _campo(bloco, "NAME"),
            }
        )
    saldo = re.search(r"<LEDGERBAL>.*?<BALAMT>([^<\r\n]*)", texto, re.DOTALL)
    return {
        "texto": texto,
        "transacoes": transacoes,
        "saldo_final": centavos(saldo.group(1)) if saldo else None,
    }


def ler_planilha(caminho):
    """Linhas (lista de textos) da 1ª aba de um .xlsx, só com zipfile + xml.etree."""
    ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        assert "xl/sharedStrings.xml" in nomes, f"{caminho} sem xl/sharedStrings.xml (D2)"
        compartilhadas = [
            "".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t"))
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns)
        ]
        livro = ET.fromstring(z.read("xl/workbook.xml"))
        id_da_aba = livro.find("m:sheets/m:sheet", ns).get(f"{{{ns['r']}}}id")
        relacoes = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        alvo = next(r.get("Target") for r in relacoes.findall("rel:Relationship", ns)
                    if r.get("Id") == id_da_aba)
        caminho_da_aba = alvo.lstrip("/") if alvo.startswith("/") else f"xl/{alvo}"
        aba = ET.fromstring(z.read(caminho_da_aba))
    linhas = []
    for linha in aba.iter(f"{{{ns['m']}}}row"):
        valores = []
        for celula in linha.findall("m:c", ns):
            tipo = celula.get("t")
            if tipo == "inlineStr":
                valores.append("".join(t.text or "" for t in celula.iter(f"{{{ns['m']}}}t")))
                continue
            v = celula.find("m:v", ns)
            texto = v.text if v is not None else ""
            valores.append(compartilhadas[int(texto)] if tipo == "s" else texto)
        linhas.append(valores)
    return linhas


def textos_gerados(pasta):
    """Texto de cada arquivo gerado; o .xlsx entra também membro a membro (já descompactado)."""
    textos = {}
    for relativo, dados in instantaneo(pasta).items():
        textos[relativo] = dados.decode("utf-8", errors="replace")
        if relativo.endswith(".xlsx"):
            with zipfile.ZipFile(Path(pasta) / relativo) as z:
                for membro in z.namelist():
                    textos[f"{relativo}!{membro}"] = z.read(membro).decode("utf-8", "replace")
    return textos


def assert_bloco_de_erro(codigo, out, err, citado):
    """D6: código 1, ERRO/MOTIVO/CORREÇÃO, cita o arquivo e manda rodar hx fixtures build."""
    assert codigo == 1, f"esperava código 1, veio {codigo}\nstdout:\n{out}\nstderr:\n{err}"
    for rotulo in ("ERRO:", "MOTIVO:", "CORREÇÃO:"):
        assert rotulo in err, f"faltou '{rotulo}' em stderr:\n{err}"
    assert citado in err, f"stderr não cita {citado!r}:\n{err}"
    correcao = err[err.index("CORREÇÃO:") :]
    assert "hx fixtures build" in correcao, f"a CORREÇÃO não manda rodar hx fixtures build:\n{err}"


def cpf_valido_inventado():
    """CPF com DV válido montado agora (base inventada); nunca escrito neste arquivo."""
    base = [4, 1, 8, 2, 7, 3, 6, 5, 0]
    dv1 = harness._digito_verificador(base, range(10, 1, -1))
    dv2 = harness._digito_verificador([*base, dv1], range(11, 1, -1))
    d = "".join(map(str, [*base, dv1, dv2]))
    valor = f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    assert harness.cpf_valido(valor)
    return valor


def git_falso_que_ignora_fixtures(listados):
    """`git ls-files` simulado: responde com sucesso, sem fixtures/ (que está no .gitignore)."""

    def executar(cmd, cwd):
        assert cmd[0] == "git", f"comando inesperado: {cmd}"
        return 0, "".join(f"{c}\n" for c in listados)

    return executar


def lista_de_cnpjs(devolvido):
    """`cnpjs_dos_clientes` pode devolver mapa (cliente → CNPJ) ou sequência."""
    # CONTRATO A CONFIRMAR: o tipo do retorno de cnpjs_dos_clientes (dict ou lista) não
    # está fixado no plan nem na ficha; o teste aceita os dois.
    if hasattr(devolvido, "values"):
        return list(devolvido.values())
    return list(devolvido)


# ---------------------------------------------------------------------------
# c1: cadastro dos dois escritórios e planilha do plano por cliente
# ---------------------------------------------------------------------------


def test_build_gera_cadastro_dos_dois_escritorios(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)  # sem opções: semente padrão
    cadastro = ler_cadastro(pasta)

    assert cadastro["semente"] == SEMENTE_PADRAO, "semente padrão deve ser 1 (D5)"
    por_id = {esc["id"]: esc for esc in cadastro["escritorios"]}
    assert set(por_id) == set(ESCRITORIOS_ESPERADOS)

    for id_esc, esperado in ESCRITORIOS_ESPERADOS.items():
        esc = por_id[id_esc]
        usuarios = {(u["handle"], u["papel"]) for u in esc["usuarios"]}
        assert usuarios == esperado["usuarios"], f"{id_esc}: usuários {usuarios}"
        responsaveis = {c["id"]: c["responsavel"] for c in esc["clientes"]}
        assert responsaveis == esperado["clientes"], f"{id_esc}: clientes {responsaveis}"

        for cli in esc["clientes"]:
            assert cli["contas_bancarias"], f"{cli['id']} sem conta bancária"
            for conta in cli["contas_bancarias"]:
                assert conta["banco"] and conta["apelido"], f"{cli['id']}: {conta}"
            assert cli["socios"] and all(s["nome"] for s in cli["socios"]), cli["id"]
            assert cli["plano"], f"{cli['id']} sem plano de contas"
            assert all(c["codigo"] and c["nome"] for c in cli["plano"]), cli["id"]
            transitorias = [c for c in cli["plano"] if c["transitoria"] is True]
            assert len(transitorias) == 1, f"{cli['id']}: {len(transitorias)} transitórias"


def test_build_gera_planilha_do_plano_por_cliente(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    cadastro = ler_cadastro(pasta)

    for _, cli in clientes(cadastro):
        planilha = pasta / cli["plano_planilha"]
        assert planilha.suffix == ".xlsx" and planilha.is_file(), f"{cli['id']}: {planilha}"
        linhas = ler_planilha(planilha)
        assert linhas[0][:2] == ["código", "nome"], f"{cli['id']}: cabeçalho {linhas[0]}"
        corpo = [tuple(linha[:2]) for linha in linhas[1:] if any(linha)]
        esperado = [(str(c["codigo"]), c["nome"]) for c in cli["plano"]]
        assert corpo == esperado, f"{cli['id']}: planilha difere do plano do cadastro"


# ---------------------------------------------------------------------------
# c2: OFX e gabarito por conta bancária; saldo fecha em centavos
# ---------------------------------------------------------------------------


def test_ofx_e_gabarito_tem_mesmas_movimentacoes(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    cadastro = ler_cadastro(pasta)
    todas = contas(cadastro)

    emp1 = next(cli for _, cli in clientes(cadastro) if cli["id"] == "EMP-1")
    assert len(emp1["contas_bancarias"]) >= 2, "EMP-1 deve ter 2 contas bancárias (D5)"

    # 1 OFX e 1 gabarito por conta, sem repetir arquivo
    ofxs = [conta["ofx"] for _, conta in todas]
    gabaritos = [conta["gabarito"] for _, conta in todas]
    assert len(set(ofxs)) == len(todas) and len(set(gabaritos)) == len(todas)
    gerados_ofx = {r for r in instantaneo(pasta) if r.lower().endswith(".ofx")}
    assert gerados_ofx == set(ofxs), f"OFX gerados {gerados_ofx} ≠ citados {set(ofxs)}"

    for cli, conta in todas:
        ofx = ler_ofx(pasta / conta["ofx"])
        gab = ler_gabarito(pasta, conta)
        assert gab["cliente"] == cli["id"]
        assert gab["banco"] == conta["banco"] and gab["apelido"] == conta["apelido"]
        movs = gab["movimentacoes"]
        assert movs, f"{conta['gabarito']} sem movimentações"
        assert len(movs) == len(ofx["transacoes"]), conta["ofx"]

        por_fitid = {t["fitid"]: t for t in ofx["transacoes"]}
        assert len(por_fitid) == len(ofx["transacoes"]), f"FITID repetido em {conta['ofx']}"
        for mov in movs:
            t = por_fitid.get(mov["id_transacao"])
            assert t is not None, f"{mov['id_transacao']} não está em {conta['ofx']}"
            assert t["data"][:8] == mov["data"].replace("-", ""), mov["id_transacao"]
            assert t["valor"] == mov["valor_centavos"], mov["id_transacao"]
            assert mov["descricao"] in (t["memo"], t["name"]), mov["id_transacao"]


def test_saldo_do_ofx_fecha_em_centavos(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)

    for _, conta in contas(ler_cadastro(pasta)):
        ofx = ler_ofx(pasta / conta["ofx"])
        gab = ler_gabarito(pasta, conta)
        inicial, final = gab["saldo_inicial_centavos"], gab["saldo_final_centavos"]
        valores = [m["valor_centavos"] for m in gab["movimentacoes"]]
        for v in (inicial, final, *valores):
            assert type(v) is int, f"{conta['gabarito']}: {v!r} não é inteiro (regra 8)"

        assert ofx["saldo_final"] is not None, f"{conta['ofx']} sem LEDGERBAL/BALAMT"
        assert ofx["saldo_final"] == final, conta["ofx"]
        soma_ofx = sum(t["valor"] for t in ofx["transacoes"])
        assert inicial + soma_ofx == ofx["saldo_final"], f"{conta['ofx']} não fecha"
        assert inicial + sum(valores) == final, f"{conta['gabarito']} não fecha"


def test_conta_correta_existe_no_plano_do_cliente(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)

    for cli, conta in contas(ler_cadastro(pasta)):
        codigos = {c["codigo"] for c in cli["plano"]}
        for mov in ler_gabarito(pasta, conta)["movimentacoes"]:
            assert mov["conta_correta"] in codigos, (
                f"{cli['id']}/{mov['id_transacao']}: {mov['conta_correta']!r} fora do plano"
            )


def test_descricoes_trazem_documentos_de_teste(tmp_path, capsys):
    # O check-clean não detecta agência, conta nem documento com DV inválido: só este teste
    # prova que a IA-02 terá o que anonimizar.
    pasta = gerar(tmp_path, capsys)
    cadastro = ler_cadastro(pasta)

    for _, cli in clientes(cadastro):
        completas = []
        for conta in cli["contas_bancarias"]:
            for mov in ler_gabarito(pasta, conta)["movimentacoes"]:
                d = mov["descricao"]
                cpfs = _CPF_COM_MASCARA.findall(d)
                cnpjs = _CNPJ_COM_MASCARA.findall(d)
                for doc in cpfs:
                    assert not harness.cpf_valido(doc), f"{cli['id']}: CPF com DV válido"
                for doc in cnpjs:
                    assert not harness.cnpj_valido(doc), f"{cli['id']}: CNPJ com DV válido"
                if cpfs and cnpjs and _AGENCIA.search(d) and _CONTA.search(d):
                    completas.append(mov["id_transacao"])
        assert completas, (
            f"{cli['id']}: nenhuma movimentação com CPF e CNPJ de teste (com máscara), "
            "agência (AG nnnn) e conta (CC nnnnn-n) na mesma descrição"
        )


# ---------------------------------------------------------------------------
# c3: mesma semente, mesmos bytes; outra semente, outros dados
# ---------------------------------------------------------------------------


def test_mesma_semente_gera_saida_identica(tmp_path, capsys):
    primeira = instantaneo(gerar(tmp_path / "a", capsys))
    segunda = instantaneo(gerar(tmp_path / "b", capsys, semente=SEMENTE_PADRAO))
    assert primeira, "o build não gerou nenhum arquivo"
    assert sorted(primeira) == sorted(segunda), "listas de arquivos diferentes"
    diferentes = [r for r in primeira if primeira[r] != segunda[r]]
    assert not diferentes, f"conteúdo diferente com a mesma semente: {diferentes}"

    # Rodar de novo na mesma pasta também não muda nada
    assert instantaneo(gerar(tmp_path / "a", capsys)) == primeira

    # As planilhas abrem só com zipfile + xml.etree e têm sharedStrings (D2)
    planilhas = [r for r in primeira if r.endswith(".xlsx")]
    assert planilhas, "nenhuma planilha .xlsx gerada"
    for relativo in planilhas:
        assert ler_planilha(tmp_path / "a" / PASTA / relativo)


def test_outra_semente_gera_saida_diferente(tmp_path, capsys):
    padrao = instantaneo(gerar(tmp_path / "s1", capsys))
    outra_pasta = gerar(tmp_path / "s2", capsys, semente=2)
    outra = instantaneo(outra_pasta)

    assert ler_cadastro(outra_pasta)["semente"] == 2
    ofx_padrao = {r: b for r, b in padrao.items() if r.lower().endswith(".ofx")}
    ofx_outra = {r: b for r, b in outra.items() if r.lower().endswith(".ofx")}
    assert ofx_padrao and ofx_outra, "nenhum OFX gerado"
    assert sorted(ofx_padrao.values()) != sorted(ofx_outra.values()), (
        "a semente 2 gerou os mesmos OFX da semente 1"
    )


# ---------------------------------------------------------------------------
# c4: --check confere sem regravar
# ---------------------------------------------------------------------------


def test_check_sem_divergencia_passa(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    antes = instantaneo(pasta)

    codigo, out, err = rodar(["fixtures", "build", "--check"], tmp_path, capsys)
    assert codigo == 0, f"esperava código 0, veio {codigo}\nstdout:\n{out}\nstderr:\n{err}"
    assert "em dia" in (out + err).lower(), f"faltou a mensagem 'fixtures em dia':\n{out}{err}"
    assert instantaneo(pasta) == antes, "o --check alterou arquivos"


def test_check_com_arquivo_alterado_falha_sem_regravar(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    _, conta = contas(ler_cadastro(pasta))[0]
    ofx = pasta / conta["ofx"]
    dados = bytearray(ofx.read_bytes())
    posicao = len(dados) // 2
    dados[posicao] = ord("#") if dados[posicao] != ord("#") else ord("@")
    ofx.write_bytes(bytes(dados))

    codigo, out, err = rodar(["fixtures", "build", "--check"], tmp_path, capsys)
    assert_bloco_de_erro(codigo, out, err, Path(conta["ofx"]).name)
    assert ofx.read_bytes() == bytes(dados), "o --check regravou o OFX alterado"


def test_check_com_arquivo_ausente_falha_sem_regravar(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    _, conta = contas(ler_cadastro(pasta))[-1]
    gabarito = pasta / conta["gabarito"]
    gabarito.unlink()

    codigo, out, err = rodar(["fixtures", "build", "--check"], tmp_path, capsys)
    assert_bloco_de_erro(codigo, out, err, Path(conta["gabarito"]).name)
    assert not gabarito.exists(), "o --check recriou o gabarito ausente"


def test_fixtures_passam_no_check_clean(tmp_path, capsys, monkeypatch):
    # Pergunta 1 do plan: fixtures/ está no .gitignore, então o check-clean precisa varrê-la
    # mesmo quando o git não a lista. O git é simulado (responde sem fixtures/).
    monkeypatch.delenv(harness.VARIAVEL_NOMES, raising=False)
    monkeypatch.setattr(harness, "_executar", git_falso_que_ignora_fixtures([".gitignore"]))

    limpa = tmp_path / "limpa"
    pasta = gerar(limpa, capsys)
    (limpa / ".gitignore").write_text("/fixtures/\n", encoding="utf-8")

    # (a) uma cópia com um CPF válido plantado em fixtures/ é achada (prova que a pasta é varrida)
    suja = tmp_path / "suja"
    shutil.copytree(limpa, suja)
    (suja / PASTA / "plantado.txt").write_text(f"doc {cpf_valido_inventado()}\n", "utf-8")
    achados = harness.varrer(suja, [])
    assert achados == [("fixtures/plantado.txt", 1, harness.TIPO_CPF)], achados

    # (b) a pasta gerada não tem achado, nem pela função nem pelo comando
    assert harness.varrer(limpa, []) == [], "a pasta gerada tem achado no check-clean"
    codigo, out, err = rodar(["check-clean"], limpa, capsys)
    assert codigo == 0, f"check-clean achou algo nas fixtures:\n{out}\n{err}"
    assert pasta.is_dir()


def test_cnpj_em_tempo_de_execucao_valido_e_estavel(tmp_path, capsys):
    gen = gerador()
    primeira = lista_de_cnpjs(gen.cnpjs_dos_clientes(SEMENTE_PADRAO))
    segunda = lista_de_cnpjs(gen.cnpjs_dos_clientes(SEMENTE_PADRAO))

    assert primeira == segunda, "duas consultas com a mesma semente devolveram valores diferentes"
    total_de_clientes = sum(len(e["clientes"]) for e in ESCRITORIOS_ESPERADOS.values())
    assert len(primeira) == total_de_clientes, f"esperava 1 CNPJ por cliente ({total_de_clientes})"
    assert all(harness.cnpj_valido(c) for c in primeira), "CNPJ com DV inválido"
    assert len(set(primeira)) == len(primeira), "CNPJs repetidos"
    assert any(re.search(r"[A-Za-z]", c) for c in primeira), "nenhum CNPJ alfanumérico"

    # Nenhum deles aparece em arquivo gerado (com ou sem máscara, em qualquer caixa)
    textos = textos_gerados(gerar(tmp_path, capsys))
    for cnpj in primeira:
        so_alnum = "".join(ch for ch in cnpj.upper() if ch.isalnum())
        mascarado = f"{so_alnum[:2]}.{so_alnum[2:5]}.{so_alnum[5:8]}/{so_alnum[8:12]}-{so_alnum[12:]}"
        for relativo, texto in textos.items():
            alto = texto.upper()
            assert so_alnum not in alto and mascarado not in alto, (
                f"CNPJ de execução apareceu em {relativo}"
            )


# ---------------------------------------------------------------------------
# c6: formato fixo do cadastro e do gabarito (contrato v0 de CAD-05 e IA-02)
# ---------------------------------------------------------------------------


def _chaves_recursivas(valor):
    if isinstance(valor, dict):
        for k, v in valor.items():
            yield k
            yield from _chaves_recursivas(v)
    elif isinstance(valor, list):
        for v in valor:
            yield from _chaves_recursivas(v)


def _caminho_relativo_existente(pasta, caminho, onde):
    assert isinstance(caminho, str) and caminho, f"{onde}: caminho vazio"
    # CONTRATO A CONFIRMAR: plano_planilha é relativo a fixtures/, como ofx e gabarito
    # (o c6 diz "caminho relativo do .xlsx" sem dizer a quê).
    assert not Path(caminho).is_absolute() and ".." not in Path(caminho).parts, (
        f"{onde}: {caminho!r} não é relativo a fixtures/"
    )
    assert (Path(pasta) / caminho).is_file(), f"{onde}: {caminho!r} não existe"


def test_formato_do_cadastro_e_do_gabarito(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    cadastro = json.loads((pasta / "cadastro.json").read_bytes().decode("utf-8"))

    assert type(cadastro["semente"]) is int
    assert isinstance(cadastro["escritorios"], list) and cadastro["escritorios"]
    cnpj_em_chave = [k for k in _chaves_recursivas(cadastro) if "cnpj" in k.lower()]
    assert not cnpj_em_chave, f"cadastro com campo de CNPJ: {cnpj_em_chave}"

    for esc in cadastro["escritorios"]:
        assert re.fullmatch(r"ESC-\d+", esc["id"]), esc["id"]
        handles = set()
        for u in esc["usuarios"]:
            assert isinstance(u["handle"], str) and u["handle"]
            assert u["papel"] in ("chefe", "contador"), u
            handles.add(u["handle"])

        for cli in esc["clientes"]:
            onde = f"{esc['id']}/{cli.get('id')}"
            assert re.fullmatch(r"EMP-\d+", cli["id"]), onde
            assert isinstance(cli["nome"], str) and cli["nome"], onde
            assert cli["responsavel"] in handles, f"{onde}: responsável de outro escritório"
            # IA-02 lê socios[].nome
            assert isinstance(cli["socios"], list) and cli["socios"], onde
            assert all(isinstance(s["nome"], str) and s["nome"] for s in cli["socios"]), onde
            # plano: {codigo, nome, transitoria}, exatamente 1 transitória
            for c in cli["plano"]:
                assert isinstance(c["codigo"], str) and c["codigo"], onde
                assert isinstance(c["nome"], str) and c["nome"], onde
                assert type(c["transitoria"]) is bool, onde
            assert sum(c["transitoria"] for c in cli["plano"]) == 1, onde
            codigos = {c["codigo"] for c in cli["plano"]}
            # CAD-05 lê plano_planilha
            _caminho_relativo_existente(pasta, cli["plano_planilha"], f"{onde} plano_planilha")

            assert isinstance(cli["contas_bancarias"], list) and cli["contas_bancarias"], onde
            for conta in cli["contas_bancarias"]:
                assert isinstance(conta["banco"], str) and _BANCO.match(conta["banco"]), onde
                assert isinstance(conta["apelido"], str) and conta["apelido"], onde
                _caminho_relativo_existente(pasta, conta["ofx"], f"{onde} ofx")
                _caminho_relativo_existente(pasta, conta["gabarito"], f"{onde} gabarito")

                gab = json.loads((pasta / conta["gabarito"]).read_bytes().decode("utf-8"))
                assert gab["cliente"] == cli["id"], onde
                assert gab["banco"] == conta["banco"] and gab["apelido"] == conta["apelido"]
                assert type(gab["saldo_inicial_centavos"]) is int, onde
                assert type(gab["saldo_final_centavos"]) is int, onde
                fitids = {t["fitid"] for t in ler_ofx(pasta / conta["ofx"])["transacoes"]}
                assert isinstance(gab["movimentacoes"], list) and gab["movimentacoes"], onde
                for mov in gab["movimentacoes"]:
                    assert _DATA_ISO.match(mov["data"]), mov
                    date.fromisoformat(mov["data"])  # data de calendário válida
                    assert type(mov["valor_centavos"]) is int, mov
                    assert isinstance(mov["descricao"], str) and mov["descricao"], mov
                    assert mov["id_transacao"] in fitids, f"{onde}: id_transacao ≠ FITID"
                    assert mov["conta_correta"] in codigos, mov


# ---------------------------------------------------------------------------
# Pergunta 2 do plan: arquivo a mais (nome sugerido no PR da ficha)
# ---------------------------------------------------------------------------


def test_check_com_arquivo_a_mais_falha_sem_apagar(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    _, conta = contas(ler_cadastro(pasta))[0]
    sobra = pasta / "sobra.txt"
    sobra.write_text("arquivo de versão antiga do gerador\n", encoding="utf-8")
    sobra_na_subpasta = (pasta / conta["ofx"]).parent / "velho.ofx"
    sobra_na_subpasta.write_text("OFXHEADER:100\n", encoding="utf-8")

    codigo, out, err = rodar(["fixtures", "build", "--check"], tmp_path, capsys)
    assert_bloco_de_erro(codigo, out, err, "sobra.txt")
    assert "velho.ofx" in err, f"stderr não cita velho.ofx:\n{err}"
    assert sobra.exists() and sobra_na_subpasta.exists(), "o --check apagou arquivo a mais"

    # Um novo build apaga o que não gera e preserva o .gitkeep
    gerar(tmp_path, capsys)
    assert not sobra.exists() and not sobra_na_subpasta.exists(), "o build não apagou a sobra"
    assert (pasta / ".gitkeep").exists(), "o build apagou o .gitkeep"
    codigo, out, err = rodar(["fixtures", "build", "--check"], tmp_path, capsys)
    assert codigo == 0, f"depois do build, o --check devia passar:\n{out}\n{err}"


# ---------------------------------------------------------------------------
# D6: --check sem fixtures geradas; opção inválida
# ---------------------------------------------------------------------------


def test_check_em_pasta_vazia_falha_sem_gravar(tmp_path, capsys):
    (tmp_path / PASTA).mkdir()
    (tmp_path / PASTA / ".gitkeep").touch()

    codigo, out, err = rodar(["fixtures", "build", "--check"], tmp_path, capsys)
    assert_bloco_de_erro(codigo, out, err, "cadastro.json")
    restantes = [p.name for p in (tmp_path / PASTA).rglob("*")]
    assert restantes == [".gitkeep"], f"o --check gravou arquivos: {restantes}"


def test_semente_invalida_sai_com_codigo_2(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    antes = instantaneo(pasta)

    codigo, out, err = rodar(["fixtures", "build", "--semente", "abc"], tmp_path, capsys)
    assert codigo == 2, f"esperava código 2 (argparse), veio {codigo}\n{out}\n{err}"
    assert "--semente" in err, f"o erro não cita a opção --semente:\n{err}"
    assert instantaneo(pasta) == antes, "opção inválida alterou as fixtures"


# ---------------------------------------------------------------------------
# D1: harness importa o gerador só dentro do comando
# ---------------------------------------------------------------------------


def test_harness_importa_gerador_so_no_comando(tmp_path):
    # Subprocesso: neste processo, outros testes já podem ter importado o gerador.
    (tmp_path / PASTA).mkdir()
    (tmp_path / PASTA / ".gitkeep").touch()
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(RAIZ_REAL / 'tools')!r})\n"
        "import harness\n"
        f"antes = {NOME_DO_GERADOR!r} in sys.modules\n"
        "try:\n"
        f"    codigo = harness.main(['fixtures', 'build'], raiz={str(tmp_path)!r})\n"
        "except SystemExit as e:\n"
        "    codigo = e.code\n"
        f"depois = {NOME_DO_GERADOR!r} in sys.modules\n"
        "print(f'RESULTADO {antes} {codigo} {depois}')\n"
    )
    r = subprocess.run(
        [sys.executable, "-I", "-c", script], capture_output=True, text=True, check=False
    )
    m = re.search(r"RESULTADO (\w+) (\d+) (\w+)", r.stdout)
    assert m, f"o subprocesso não chegou ao fim:\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    assert m.groups() == ("False", "0", "True"), (
        f"esperava gerador fora do import do harness e carregado pelo comando: {m.groups()}"
    )


# ---------------------------------------------------------------------------
# D2: planilha sem compressão e com data fixa
# ---------------------------------------------------------------------------


def test_planilha_sem_compressao_e_data_fixa(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    for _, cli in clientes(ler_cadastro(pasta)):
        with zipfile.ZipFile(pasta / cli["plano_planilha"]) as z:
            for info in z.infolist():
                assert info.compress_type == zipfile.ZIP_STORED, f"{info.filename} comprimido"
                assert info.date_time == (1980, 1, 1, 0, 0, 0), f"{info.filename}: data {info.date_time}"


# ---------------------------------------------------------------------------
# D3: sorteio só com Random(semente).random()
# ---------------------------------------------------------------------------

_METODOS_SEM_GARANTIA = (
    "randrange", "randint", "choice", "choices", "sample", "shuffle", "uniform",
    "getrandbits", "randbytes", "triangular", "gauss", "normalvariate", "expovariate",
)


def test_sorteio_usa_so_random(tmp_path, capsys, monkeypatch):
    # Os métodos sem garantia de reprodutibilidade entre versões falham se chamados
    # diretamente pelo gerador. Outros módulos (ex.: tempfile) continuam livres.
    def proibir(nome, original):
        def substituto(self, *args, **kwargs):
            chamador = sys._getframe(1).f_globals.get("__name__", "")
            assert chamador != NOME_DO_GERADOR, f"o gerador chamou Random.{nome} (D3)"
            return original(self, *args, **kwargs)

        return substituto

    for nome in _METODOS_SEM_GARANTIA:
        original = getattr(random.Random, nome, None)
        if original is not None:
            monkeypatch.setattr(random.Random, nome, proibir(nome, original))

    gerar(tmp_path, capsys)


# ---------------------------------------------------------------------------
# D4: OFX 1.0.2 SGML, ASCII
# ---------------------------------------------------------------------------


def test_ofx_versao_102_sgml_ascii(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    for _, conta in contas(ler_cadastro(pasta)):
        dados = (pasta / conta["ofx"]).read_bytes()
        texto = dados.decode("ascii")  # falha se não for ASCII
        cabecalho = texto.split("<OFX>", 1)[0]
        for linha in ("OFXHEADER:100", "DATA:OFXSGML", "VERSION:102"):
            assert linha in cabecalho, f"{conta['ofx']}: faltou {linha} no cabeçalho"
        assert "<?xml" not in texto, f"{conta['ofx']} parece OFX 2.x (XML)"
        assert re.search(r"<DTSERVER>\d{8}", texto), f"{conta['ofx']} sem DTSERVER"


# ---------------------------------------------------------------------------
# D5: conteúdo sintético mínimo
# ---------------------------------------------------------------------------


def test_conteudo_minimo_do_modelo(tmp_path, capsys):
    pasta = gerar(tmp_path, capsys)
    cadastro = ler_cadastro(pasta)

    for _, cli in clientes(cadastro):
        assert all(re.fullmatch(r"SOCIO TESTE \d{2}", s["nome"]) for s in cli["socios"]), (
            f"{cli['id']}: sócios fora do padrão 'SOCIO TESTE nn'"
        )
        transitoria = next(c for c in cli["plano"] if c["transitoria"])
        assert transitoria["codigo"] == "9.9.99", f"{cli['id']}: transitória {transitoria}"
        movs = [
            m
            for conta in cli["contas_bancarias"]
            for m in ler_gabarito(pasta, conta)["movimentacoes"]
        ]
        assert len(movs) >= 3, f"{cli['id']}: só {len(movs)} movimentações (IA-02 pede ≥ 3)"
        assert any(m["conta_correta"] == transitoria["codigo"] for m in movs), (
            f"{cli['id']}: nenhuma movimentação vai para a transitória"
        )


# ---------------------------------------------------------------------------
# D7: trava de segurança antes de gravar
# ---------------------------------------------------------------------------


def test_build_aborta_se_linha_tiver_documento_valido(tmp_path, capsys, monkeypatch):
    # Simula um CPF com DV válido surgido por acaso: o detector do harness acusa toda linha
    # com dígito. O build deve abortar com ERRO/MOTIVO/CORREÇÃO e não gravar nada.
    gen = gerador()
    real = harness.tipos_da_linha

    def detector_que_acusa(linha, nomes):
        tipos = list(real(linha, nomes))
        if re.search(r"\d", linha) and harness.TIPO_CPF not in tipos:
            tipos.append(harness.TIPO_CPF)
        return tipos

    # CONTRATO A CONFIRMAR: o plan (D7) diz que o gerador usa `harness.tipos_da_linha`; o
    # teste troca a função no harness e, se o gerador a importou pelo nome, também nele.
    monkeypatch.setattr(harness, "tipos_da_linha", detector_que_acusa)
    monkeypatch.setattr(gen, "tipos_da_linha", detector_que_acusa, raising=False)

    (tmp_path / PASTA).mkdir()
    (tmp_path / PASTA / ".gitkeep").touch()
    codigo, out, err = rodar(["fixtures", "build"], tmp_path, capsys)

    assert codigo != 0, f"o build devia abortar, veio código {codigo}\n{out}\n{err}"
    for rotulo in ("ERRO:", "MOTIVO:", "CORREÇÃO:"):
        assert rotulo in err, f"faltou '{rotulo}' em stderr:\n{err}"
    restantes = sorted(p.name for p in (tmp_path / PASTA).rglob("*"))
    assert restantes == [".gitkeep"], f"o build gravou arquivos antes de abortar: {restantes}"
