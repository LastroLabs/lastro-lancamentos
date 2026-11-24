"""Gerador de fixtures sintéticas do Lastro (HAR-03). Só biblioteca padrão; Python 3.11+.

`gerar_arquivos(semente)` é uma função pura: semente → {caminho relativo a fixtures/: bytes}.
O `hx fixtures build` (em `harness.py`) grava esse mapa; o `--check` só compara com o disco.

Regras (plan da HAR-03):
- D3: todo sorteio sai de `random.Random(semente).random()`, com conversões próprias. Métodos
  como `randrange` e `choice` não têm garantia de dar o mesmo resultado entre versões.
- D2: .xlsx escrito à mão com `zipfile`, entradas sem compressão e data 1980-01-01.
- D4: OFX 1.0.2 (SGML), ASCII, datas e período fixos (sem relógio).
- D5: CPF e CNPJ nas descrições têm DV inválido. Os CNPJs válidos dos clientes só existem em
  tempo de execução (`cnpjs_dos_clientes`) e nunca vão para arquivo.
- O cálculo de DV é o do harness (sem duplicar). O harness importa este módulo só no comando.

Todos os dados são inventados.
"""

from __future__ import annotations

import io
import json
import random
import zipfile
from xml.sax.saxutils import escape

import harness

SEMENTE_PADRAO = 1

# Período fixo do extrato (outubro de 2026) e data do servidor. Nada vem do relógio.
_ANO, _MES, _ULTIMO_DIA = 2026, 10, 31
_DTSERVER = "20261101"

_DATA_FIXA_DO_ZIP = (1980, 1, 1, 0, 0, 0)
_ALFANUMERICOS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

TRANSITORIA = "9.9.99"
PLANO_BASE = (
    ("1.1.01", "Caixa"),
    ("1.1.02", "Bancos conta movimento"),
    ("1.1.03", "Clientes a receber"),
    ("2.1.01", "Fornecedores a pagar"),
    ("2.1.02", "Impostos a recolher"),
    ("2.1.03", "Salários a pagar"),
    ("3.1.01", "Receita de vendas"),
    ("3.1.02", "Receita de serviços"),
    ("4.1.01", "Despesas bancárias"),
    ("4.1.02", "Aluguel"),
    ("4.1.03", "Energia e água"),
    ("4.1.04", "Pró-labore"),
    (TRANSITORIA, "Transitória"),
)

# Modelos de movimentação: (descrição, sinal, mínimo e máximo em centavos, conta correta).
# `{n}` vira um número de 2 dígitos. Contraparte sem nome vai para a transitória.
_MODELOS = (
    ("TARIFA PACOTE SERVICOS", -1, 1_500, 4_990, "4.1.01"),
    ("PIX RECEBIDO CLIENTE {n}", 1, 10_000, 500_000, "1.1.03"),
    ("VENDA CARTAO LOTE {n}", 1, 5_000, 300_000, "3.1.01"),
    ("BOLETO PAGO FORNECEDOR {n}", -1, 5_000, 300_000, "2.1.01"),
    ("PAGTO DARF IMPOSTOS", -1, 10_000, 200_000, "2.1.02"),
    ("FOLHA PAGAMENTO", -1, 100_000, 800_000, "2.1.03"),
    ("PAGTO ALUGUEL", -1, 150_000, 600_000, "4.1.02"),
    ("CONTA ENERGIA", -1, 8_000, 90_000, "4.1.03"),
    ("PRO LABORE SOCIO TESTE {n}", -1, 100_000, 500_000, "4.1.04"),
    ("PIX RECEBIDO CONTRAPARTE {n}", 1, 2_000, 150_000, TRANSITORIA),
)
_MODELO_TRANSITORIA = _MODELOS[-1]

# Cadastro fixo (c1). Cada conta bancária: (banco com 3 dígitos, apelido).
_ESCRITORIOS = (
    {
        "id": "ESC-1",
        "usuarios": (("chefe_1", "chefe"), ("contador_a", "contador"), ("contador_b", "contador")),
        "clientes": (
            ("EMP-1", "CLIENTE SINTETICO 1", "contador_a",
             (("001", "Conta movimento"), ("077", "Conta reserva"))),
            ("EMP-2", "CLIENTE SINTETICO 2", "contador_b", (("001", "Conta movimento"),)),
        ),
    },
    {
        "id": "ESC-2",
        "usuarios": (("chefe_2", "chefe"), ("contador_x", "contador")),
        "clientes": (
            ("EMP-9", "CLIENTE SINTETICO 9", "contador_x", (("077", "Conta movimento"),)),
        ),
    },
)


# ---------------------------------------------------------------------------
# T2: sorteio e modelo em memória
# ---------------------------------------------------------------------------


class _Sorteio:
    """Sorteios derivados só de `Random(semente).random()` (D3)."""

    def __init__(self, semente: int) -> None:
        self._gerador = random.Random(semente)

    def inteiro(self, minimo: int, maximo: int) -> int:
        """Inteiro em [minimo, maximo]."""
        return minimo + int(self._gerador.random() * (maximo - minimo + 1))

    def escolha(self, opcoes: tuple | list):
        return opcoes[self.inteiro(0, len(opcoes) - 1)]

    def digitos(self, quantidade: int) -> list[int]:
        return [self.inteiro(0, 9) for _ in range(quantidade)]


def _dv_errado(certo: int) -> int:
    return (certo + 1) % 10


def _cpf_invalido(sorteio: _Sorteio) -> str:
    """CPF com máscara e 1º DV errado de propósito."""
    base = sorteio.digitos(9)
    dv1 = harness._digito_verificador(base, range(10, 1, -1))
    dv2 = harness._digito_verificador([*base, dv1], range(11, 1, -1))
    d = "".join(map(str, [*base, _dv_errado(dv1), dv2]))
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def _cnpj_com_dv(caracteres: str, dv_certo: bool) -> str:
    """CNPJ (14 caracteres, sem máscara) a partir dos 12 primeiros, com DV certo ou errado."""
    valores = [ord(c) - 48 for c in caracteres]
    dv1 = harness._digito_verificador(valores, harness._PESOS_CNPJ_1)
    dv2 = harness._digito_verificador([*valores, dv1], harness._PESOS_CNPJ_2)
    if not dv_certo:
        dv1 = _dv_errado(dv1)
    return f"{caracteres}{dv1}{dv2}"


def _mascarar_cnpj(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def _descricao_com_documentos(sorteio: _Sorteio) -> str:
    """Descrição com CPF e CNPJ de teste (DV inválido), agência e conta (D5, para a IA-02)."""
    cpf = _cpf_invalido(sorteio)
    base_cnpj = "".join(map(str, sorteio.digitos(12)))
    cnpj = _mascarar_cnpj(_cnpj_com_dv(base_cnpj, dv_certo=False))
    agencia = sorteio.inteiro(1000, 9999)
    conta = f"{sorteio.inteiro(10000, 99999)}-{sorteio.inteiro(0, 9)}"
    return f"TED ENVIADA CPF {cpf} CNPJ {cnpj} AG {agencia} CC {conta}"


def cnpjs_dos_clientes(semente: int = SEMENTE_PADRAO) -> dict[str, str]:
    """CNPJ válido de cada cliente (id → CNPJ sem máscara), só em tempo de execução.

    O primeiro é alfanumérico (padrão de julho/2026). Nunca é gravado em arquivo.
    """
    sorteio = _Sorteio(semente)
    ids = [cli[0] for esc in _ESCRITORIOS for cli in esc["clientes"]]
    cnpjs: dict[str, str] = {}
    for posicao, id_cliente in enumerate(ids):
        while True:
            if posicao == 0:
                letra = sorteio.escolha(_ALFANUMERICOS[10:])
                resto = "".join(sorteio.escolha(_ALFANUMERICOS) for _ in range(11))
                base = letra + resto
            else:
                base = "".join(map(str, sorteio.digitos(12)))
            cnpj = _cnpj_com_dv(base, dv_certo=True)
            if harness.cnpj_valido(cnpj) and cnpj not in cnpjs.values():
                break
        cnpjs[id_cliente] = cnpj
    return cnpjs


def _valor(sorteio: _Sorteio, modelo: tuple) -> tuple[str, int, str]:
    descricao, sinal, minimo, maximo, conta = modelo
    texto = descricao.format(n=f"{sorteio.inteiro(1, 99):02d}")
    return texto, sinal * sorteio.inteiro(minimo, maximo), conta


def _movimentacoes(sorteio: _Sorteio, numero_da_conta: str, com_documentos: bool) -> list[dict]:
    """Movimentações de uma conta bancária, em ordem de data, já com a conta correta."""
    linhas = [_valor(sorteio, sorteio.escolha(_MODELOS)) for _ in range(sorteio.inteiro(15, 30))]
    linhas.append(_valor(sorteio, _MODELO_TRANSITORIA))  # ao menos 1 na transitória (D5)
    if com_documentos:
        valor = -sorteio.inteiro(10_000, 200_000)
        linhas.append((_descricao_com_documentos(sorteio), valor, TRANSITORIA))
    dias = sorted(sorteio.inteiro(1, _ULTIMO_DIA) for _ in linhas)
    movimentacoes = []
    for seq, (dia, (descricao, valor, conta)) in enumerate(zip(dias, linhas), start=1):
        movimentacoes.append(
            {
                "data": f"{_ANO:04d}-{_MES:02d}-{dia:02d}",
                "valor_centavos": valor,
                "descricao": descricao,
                "id_transacao": f"F{numero_da_conta}{seq:04d}",
                "conta_correta": conta,
            }
        )
    return movimentacoes


def gerar_modelo(semente: int = SEMENTE_PADRAO) -> dict:
    """Modelo completo em memória (escritórios, clientes, contas e movimentações). Puro."""
    sorteio = _Sorteio(semente)
    escritorios = []
    for esc in _ESCRITORIOS:
        clientes = []
        for id_cliente, nome, responsavel, bancos in esc["clientes"]:
            contas = []
            for ordem, (banco, apelido) in enumerate(bancos, start=1):
                sufixo = f"{id_cliente}-{ordem:02d}"
                numero = f"{sorteio.inteiro(10000, 99999)}"
                movs = _movimentacoes(sorteio, numero, com_documentos=ordem == 1)
                inicial = sorteio.inteiro(100_000, 5_000_000)
                contas.append(
                    {
                        "banco": banco,
                        "apelido": apelido,
                        "ofx": f"ofx/{sufixo}.ofx",
                        "gabarito": f"gabaritos/{sufixo}.json",
                        "agencia": f"{sorteio.inteiro(1000, 9999)}",
                        "conta": f"{numero}-{sorteio.inteiro(0, 9)}",
                        "saldo_inicial_centavos": inicial,
                        "saldo_final_centavos": inicial + sum(m["valor_centavos"] for m in movs),
                        "movimentacoes": movs,
                    }
                )
            clientes.append(
                {
                    "id": id_cliente,
                    "nome": nome,
                    "responsavel": responsavel,
                    "socios": [{"nome": f"SOCIO TESTE {n:02d}"} for n in (1, 2)],
                    "plano": [
                        {"codigo": codigo, "nome": nome_conta, "transitoria": codigo == TRANSITORIA}
                        for codigo, nome_conta in PLANO_BASE
                    ],
                    "plano_planilha": f"planos/{id_cliente}.xlsx",
                    "contas_bancarias": contas,
                }
            )
        escritorios.append(
            {
                "id": esc["id"],
                "usuarios": [{"handle": h, "papel": p} for h, p in esc["usuarios"]],
                "clientes": clientes,
            }
        )
    return {"semente": semente, "escritorios": escritorios}


# ---------------------------------------------------------------------------
# T3: cadastro.json e planilha .xlsx
# ---------------------------------------------------------------------------


def _json(valor: object) -> bytes:
    return (json.dumps(valor, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _cadastro(modelo: dict) -> dict:
    """Contrato v0 do c6: só o que CAD-05 e IA-02 leem. Sem CNPJ, sem movimentações."""
    campos_da_conta = ("banco", "apelido", "ofx", "gabarito")
    return {
        "semente": modelo["semente"],
        "escritorios": [
            {
                "id": esc["id"],
                "usuarios": esc["usuarios"],
                "clientes": [
                    {
                        **{k: cli[k] for k in ("id", "nome", "responsavel", "socios", "plano")},
                        "plano_planilha": cli["plano_planilha"],
                        "contas_bancarias": [
                            {k: conta[k] for k in campos_da_conta}
                            for conta in cli["contas_bancarias"]
                        ],
                    }
                    for cli in esc["clientes"]
                ],
            }
            for esc in modelo["escritorios"]
        ],
    }


_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
_TIPO_OOXML = "application/vnd.openxmlformats-officedocument.spreadsheetml"


def _membros_da_planilha(linhas: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Membros (nome, XML) de um .xlsx mínimo de 1 aba, com sharedStrings (D2)."""
    textos: list[str] = []
    indice: dict[str, int] = {}
    xml_linhas = []
    for numero, valores in enumerate(linhas, start=1):
        celulas = []
        for coluna, valor in zip("AB", valores):
            if valor not in indice:
                indice[valor] = len(textos)
                textos.append(valor)
            celulas.append(f'<c r="{coluna}{numero}" t="s"><v>{indice[valor]}</v></c>')
        xml_linhas.append(f'<row r="{numero}">{"".join(celulas)}</row>')
    compartilhadas = "".join(f"<si><t>{escape(t)}</t></si>" for t in textos)
    return [
        ("[Content_Types].xml", (
            f'{_XML}<Types xmlns="{_NS_CT}">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/xl/workbook.xml" ContentType="{_TIPO_OOXML}.sheet.main+xml"/>'
            f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{_TIPO_OOXML}.worksheet+xml"/>'
            f'<Override PartName="/xl/styles.xml" ContentType="{_TIPO_OOXML}.styles+xml"/>'
            f'<Override PartName="/xl/sharedStrings.xml" ContentType="{_TIPO_OOXML}.sharedStrings+xml"/>'
            "</Types>"
        )),
        ("_rels/.rels", (
            f'{_XML}<Relationships xmlns="{_NS_PKG}">'
            f'<Relationship Id="rId1" Type="{_NS_REL}/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        )),
        ("xl/workbook.xml", (
            f'{_XML}<workbook xmlns="{_NS_MAIN}" xmlns:r="{_NS_REL}">'
            '<sheets><sheet name="Plano" sheetId="1" r:id="rId1"/></sheets></workbook>'
        )),
        ("xl/_rels/workbook.xml.rels", (
            f'{_XML}<Relationships xmlns="{_NS_PKG}">'
            f'<Relationship Id="rId1" Type="{_NS_REL}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{_NS_REL}/styles" Target="styles.xml"/>'
            f'<Relationship Id="rId3" Type="{_NS_REL}/sharedStrings" Target="sharedStrings.xml"/>'
            "</Relationships>"
        )),
        ("xl/worksheets/sheet1.xml", (
            f'{_XML}<worksheet xmlns="{_NS_MAIN}"><sheetData>{"".join(xml_linhas)}</sheetData>'
            "</worksheet>"
        )),
        ("xl/styles.xml", (
            f'{_XML}<styleSheet xmlns="{_NS_MAIN}">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            "</styleSheet>"
        )),
        ("xl/sharedStrings.xml", (
            f'{_XML}<sst xmlns="{_NS_MAIN}" count="{len(textos)}" uniqueCount="{len(textos)}">'
            f"{compartilhadas}</sst>"
        )),
    ]


def membros_xlsx(dados: bytes) -> dict[str, str]:
    """Texto de cada membro de um .xlsx (para a trava de documentos do harness, D7)."""
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        return {nome: z.read(nome).decode("utf-8", errors="replace") for nome in z.namelist()}


def _planilha(plano: list[dict]) -> bytes:
    """Plano de contas em .xlsx, igual byte a byte para a mesma entrada (D2)."""
    linhas = [("código", "nome"), *((c["codigo"], c["nome"]) for c in plano)]
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", compression=zipfile.ZIP_STORED) as z:
        for nome, xml in _membros_da_planilha(linhas):
            info = zipfile.ZipInfo(nome, date_time=_DATA_FIXA_DO_ZIP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 0  # o padrão muda entre Windows e Unix
            info.external_attr = 0
            z.writestr(info, xml.encode("utf-8"))
    return saida.getvalue()


# ---------------------------------------------------------------------------
# T4: OFX 1.0.2 e gabarito por conta bancária
# ---------------------------------------------------------------------------


def _decimal(centavos: int) -> str:
    """-1590 → '-15.90' (sem float, regra 8)."""
    sinal = "-" if centavos < 0 else ""
    return f"{sinal}{abs(centavos) // 100}.{abs(centavos) % 100:02d}"


def _data_ofx(data_iso: str) -> str:
    return data_iso.replace("-", "")


def _ofx(conta: dict) -> bytes:
    """Extrato OFX 1.0.2 SGML, ASCII, com período e DTSERVER fixos (D4)."""
    inicio, fim = f"{_ANO:04d}{_MES:02d}01", f"{_ANO:04d}{_MES:02d}{_ULTIMO_DIA:02d}"
    linhas = [
        "OFXHEADER:100", "DATA:OFXSGML", "VERSION:102", "SECURITY:NONE", "ENCODING:USASCII",
        "CHARSET:1252", "COMPRESSION:NONE", "OLDFILEUID:NONE", "NEWFILEUID:NONE", "",
        "<OFX>", "<SIGNONMSGSRSV1>", "<SONRS>", "<STATUS>", "<CODE>0", "<SEVERITY>INFO",
        "</STATUS>", f"<DTSERVER>{_DTSERVER}", "<LANGUAGE>POR", "</SONRS>", "</SIGNONMSGSRSV1>",
        "<BANKMSGSRSV1>", "<STMTTRNRS>", "<TRNUID>1", "<STATUS>", "<CODE>0", "<SEVERITY>INFO",
        "</STATUS>", "<STMTRS>", "<CURDEF>BRL", "<BANKACCTFROM>", f"<BANKID>{conta['banco']}",
        f"<BRANCHID>{conta['agencia']}", f"<ACCTID>{conta['conta']}", "<ACCTTYPE>CHECKING",
        "</BANKACCTFROM>", "<BANKTRANLIST>", f"<DTSTART>{inicio}", f"<DTEND>{fim}",
    ]
    for mov in conta["movimentacoes"]:
        linhas += [
            "<STMTTRN>",
            f"<TRNTYPE>{'CREDIT' if mov['valor_centavos'] > 0 else 'DEBIT'}",
            f"<DTPOSTED>{_data_ofx(mov['data'])}",
            f"<TRNAMT>{_decimal(mov['valor_centavos'])}",
            f"<FITID>{mov['id_transacao']}",
            f"<MEMO>{mov['descricao']}",
            "</STMTTRN>",
        ]
    linhas += [
        "</BANKTRANLIST>", "<LEDGERBAL>", f"<BALAMT>{_decimal(conta['saldo_final_centavos'])}",
        f"<DTASOF>{fim}", "</LEDGERBAL>", "</STMTRS>", "</STMTTRNRS>", "</BANKMSGSRSV1>", "</OFX>",
    ]
    return ("\r\n".join(linhas) + "\r\n").encode("ascii")


def _gabarito(cliente: dict, conta: dict) -> dict:
    """Contrato v0 do c6: o que está no OFX e a conta correta de cada linha."""
    return {
        "cliente": cliente["id"],
        "banco": conta["banco"],
        "apelido": conta["apelido"],
        "saldo_inicial_centavos": conta["saldo_inicial_centavos"],
        "saldo_final_centavos": conta["saldo_final_centavos"],
        "movimentacoes": conta["movimentacoes"],
    }


# ---------------------------------------------------------------------------
# Função pura usada pelo `hx fixtures build`
# ---------------------------------------------------------------------------


def gerar_arquivos(semente: int = SEMENTE_PADRAO) -> dict[str, bytes]:
    """Semente → {caminho relativo a fixtures/ (com /): bytes}, em ordem fixa. Puro."""
    modelo = gerar_modelo(semente)
    arquivos: dict[str, bytes] = {"cadastro.json": _json(_cadastro(modelo))}
    for esc in modelo["escritorios"]:
        for cli in esc["clientes"]:
            arquivos[cli["plano_planilha"]] = _planilha(cli["plano"])
            for conta in cli["contas_bancarias"]:
                arquivos[conta["ofx"]] = _ofx(conta)
                arquivos[conta["gabarito"]] = _json(_gabarito(cli, conta))
    return arquivos
