"""IA-01: anonymization of bank statement descriptions before any call to an LLM.

Each test reproduces an example of `features/IA-01.json` (c1 to c8). Decisions used here are in
`planos/IA-01/plan.md`: markers `[CPF]`, `[CNPJ]`, `[AGENCIA]` and `[CONTA]` (D2), pseudonyms
stable within one call (D1, D5), the `NAME_PROTECTION_LEVEL` variable (D1, question 1) and the
reading of "piece of 3 letters or more" in c8 (D8).

No real data: CPF and CNPJ are generated at run time (valid and invalid check digits), and every
name is synthetic, with `TESTE` in the middle (SECURITY.md, section 3).
"""

import random
import re
import string
from pathlib import Path

import pytest
import yaml
from lastro.ai.contracts import InvalidNameProtectionLevelError, NameProtectionLevel
from lastro.ai.service import anonymize, load_name_protection_level

REPO_ROOT = Path(__file__).resolve().parents[2]
LISTS_FILE = REPO_ROOT / "src" / "lastro" / "ai" / "preservation_lists.yaml"
LEVEL_VARIABLE = "NAME_PROTECTION_LEVEL"

PERSON = r"PESSOA_\d{3}"
COMPANY = r"EMPRESA_\d{3}"
PSEUDONYM_OR_MARKER = re.compile(r"^(?:(?:PESSOA|EMPRESA)_\d{3,}|\[(?:CPF|CNPJ|AGENCIA|CONTA)\])$")
INVALID_LEVEL_MESSAGE = (
    "Nível de proteção de nomes inválido: medio. Use estrito, pessoas_protegidas ou desligado."
)

# ---------------------------------------------------------------------------
# Synthetic documents, generated at run time
# ---------------------------------------------------------------------------

_CNPJ_WEIGHTS_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNPJ_WEIGHTS_2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _mod11_digit(values, weights):
    remainder = sum(v * w for v, w in zip(values, weights, strict=True)) % 11
    return 0 if remainder < 2 else 11 - remainder


def _cpf(rng, *, valid_check_digits=True):
    """11 digits; with `valid_check_digits=False` the last digit is wrong on purpose."""
    base = [rng.randrange(10) for _ in range(9)]
    first = _mod11_digit(base, range(10, 1, -1))
    second = _mod11_digit([*base, first], range(11, 1, -1))
    if not valid_check_digits:
        second = (second + 1) % 10
    return "".join(map(str, [*base, first, second]))


def _cnpj(rng, *, alphanumeric=False, valid_check_digits=True):
    """14 characters: 12 base characters (letters allowed if alphanumeric) and 2 check digits.

    The check digit uses `ord(c) - 48` for each character, as in the alphanumeric CNPJ rule.
    An alphanumeric base always has at least two letters and two digits.
    """
    if alphanumeric:
        pool = string.ascii_uppercase + string.digits
        while True:
            base = [rng.choice(pool) for _ in range(12)]
            letters = sum(c.isalpha() for c in base)
            if letters >= 2 and 12 - letters >= 2:
                break
    else:
        base = [rng.choice(string.digits) for _ in range(12)]
    values = [ord(c) - 48 for c in base]
    first = _mod11_digit(values, _CNPJ_WEIGHTS_1)
    second = _mod11_digit([*values, first], _CNPJ_WEIGHTS_2)
    if not valid_check_digits:
        second = (second + 1) % 10
    return "".join(base) + f"{first}{second}"


def _mask_cpf(cpf):
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def _mask_cnpj(cnpj):
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def _assert_document_gone(output, document):
    """Neither the document as written nor its bare characters show up in the output."""
    bare = re.sub(r"[^0-9A-Za-z]", "", document)
    assert document not in output
    assert bare.upper() not in output.upper()


@pytest.fixture
def rng():
    return random.Random(20261123)


@pytest.fixture(autouse=True)
def default_configuration(monkeypatch):
    """Every test starts without the level variable, so the default level applies."""
    monkeypatch.delenv(LEVEL_VARIABLE, raising=False)


# ---------------------------------------------------------------------------
# c1: CPF and CNPJ
# ---------------------------------------------------------------------------


def test_cpf_e_cnpj_numericos_removidos(rng):
    for _ in range(20):
        cpf = _cpf(rng)
        cpf_wrong = _cpf(rng, valid_check_digits=False)
        cnpj = _cnpj(rng)
        cnpj_masked = _cnpj(rng)
        cases = [
            (f"PIX ENVIADO {_mask_cpf(cpf)}", "PIX ENVIADO [CPF]", _mask_cpf(cpf)),
            (f"TED RECEBIDA {cnpj}", "TED RECEBIDA [CNPJ]", cnpj),
            (f"BOLETO {_mask_cnpj(cnpj_masked)}", "BOLETO [CNPJ]", _mask_cnpj(cnpj_masked)),
            (f"PIX {cpf_wrong}", "PIX [CPF]", cpf_wrong),
            (f"PIX {_mask_cpf(cpf_wrong)}", "PIX [CPF]", _mask_cpf(cpf_wrong)),
        ]
        outputs = anonymize([description for description, _, _ in cases])
        for output, (_, expected, document) in zip(outputs, cases, strict=True):
            assert output == expected
            _assert_document_gone(output, document)


def test_cnpj_alfanumerico_removido(rng):
    for _ in range(20):
        cnpj = _cnpj(rng, alphanumeric=True)
        cnpj_wrong = _cnpj(rng, alphanumeric=True, valid_check_digits=False)
        cases = [
            (f"PAGAMENTO {_mask_cnpj(cnpj)}", "PAGAMENTO [CNPJ]", _mask_cnpj(cnpj)),
            (f"pagamento {cnpj.lower()}", "pagamento [CNPJ]", cnpj.lower()),
            (f"PAGAMENTO {_mask_cnpj(cnpj_wrong)}", "PAGAMENTO [CNPJ]", _mask_cnpj(cnpj_wrong)),
        ]
        outputs = anonymize([description for description, _, _ in cases])
        for output, (_, expected, document) in zip(outputs, cases, strict=True):
            assert output == expected
            _assert_document_gone(output, document)


# ---------------------------------------------------------------------------
# c2: branch (agência) and account (conta)
# ---------------------------------------------------------------------------


def test_agencia_e_conta_removidas():
    cases = {
        "TED AG 1234 C/C 56789-0": ("TED [AGENCIA] [CONTA]", ["1234", "56789"]),
        "TRANSF AGENCIA 0001 CONTA 9876543-2": ("TRANSF [AGENCIA] [CONTA]", ["0001", "9876543"]),
        "DOC AG:4321 CC:11223-4": ("DOC [AGENCIA] [CONTA]", ["4321", "11223"]),
    }
    outputs = anonymize(list(cases))
    for output, (expected, numbers) in zip(outputs, cases.values(), strict=True):
        assert output == expected
        for number in numbers:
            assert number not in output


# ---------------------------------------------------------------------------
# c3: every counterparty name becomes a stable pseudonym (D-03)
# ---------------------------------------------------------------------------

C3_DESCRIPTIONS = [
    "PIX SOCIO TESTE A",
    "PIX RECEBIDO MARIA TESTE SOUZA",
    "TED MARIA TESTE SOUZA",
    "BOLETO PADARIA TESTE LTDA",
]


def test_nomes_de_pessoas_viram_pseudonimos_estaveis():
    outputs = anonymize(C3_DESCRIPTIONS, partners=["SOCIO TESTE A"])

    partner = re.fullmatch(rf"PIX ({PERSON})", outputs[0])
    received = re.fullmatch(rf"PIX RECEBIDO ({PERSON})", outputs[1])
    sent = re.fullmatch(rf"TED ({PERSON})", outputs[2])
    assert partner and received and sent, outputs
    assert partner.group(1) != received.group(1)
    assert received.group(1) == sent.group(1)
    for output in outputs:
        assert "SOCIO TESTE A" not in output
        assert "MARIA TESTE SOUZA" not in output


def test_nomes_de_empresas_viram_pseudonimo_de_empresa():
    outputs = anonymize(C3_DESCRIPTIONS, partners=["SOCIO TESTE A"])

    assert re.fullmatch(rf"BOLETO {COMPANY}", outputs[3]), outputs[3]
    for output in outputs:
        assert "PADARIA TESTE LTDA" not in output


# ---------------------------------------------------------------------------
# c4: three levels chosen by configuration; unknown level stops the app
# ---------------------------------------------------------------------------


def test_pseudonimizacao_de_nomes_configuravel(monkeypatch, rng):
    cpf = _mask_cpf(_cpf(rng))
    description = f"PIX MARIA TESTE SOUZA {cpf} AG 1234 C/C 56789-0"
    protected = rf"PIX {PERSON} \[CPF\] \[AGENCIA\] \[CONTA\]"

    # (a) no configuration at all: the default level (estrito) applies
    assert load_name_protection_level() is NameProtectionLevel.STRICT
    (output,) = anonymize([description])
    assert re.fullmatch(protected, output), output

    # (b) pessoas_protegidas
    monkeypatch.setenv(LEVEL_VARIABLE, "pessoas_protegidas")
    (output,) = anonymize([description])
    assert re.fullmatch(protected, output), output

    # (c) desligado: the name stays, the identifiers still go
    monkeypatch.setenv(LEVEL_VARIABLE, "desligado")
    (output,) = anonymize([description])
    assert output == "PIX MARIA TESTE SOUZA [CPF] [AGENCIA] [CONTA]"
    _assert_document_gone(output, cpf)


def test_nivel_invalido_recusado_e_niveis_aceitos(monkeypatch):
    from lastro.api.app import create_app
    from lastro.core.config import Settings

    settings = Settings(database_url="postgresql+psycopg://teste:teste@localhost:5432/teste")

    monkeypatch.setenv(LEVEL_VARIABLE, "medio")
    with pytest.raises(InvalidNameProtectionLevelError) as refused:
        create_app(settings)
    assert str(refused.value) == INVALID_LEVEL_MESSAGE
    with pytest.raises(InvalidNameProtectionLevelError):
        load_name_protection_level()

    accepted = {
        "estrito": NameProtectionLevel.STRICT,
        "pessoas_protegidas": NameProtectionLevel.PEOPLE_PROTECTED,
        "desligado": NameProtectionLevel.OFF,
    }
    for value, level in accepted.items():
        monkeypatch.setenv(LEVEL_VARIABLE, value)
        assert load_name_protection_level() is level
        assert create_app(settings) is not None


# ---------------------------------------------------------------------------
# c5: text without personal data is unchanged
# ---------------------------------------------------------------------------


def test_texto_sem_dado_pessoal_inalterado():
    descriptions = ["TARIFA PACOTE SERVICOS", "IOF 15/10/2026", "COMPRA CARTAO R$ 1.234,56"]
    assert anonymize(descriptions) == descriptions


# ---------------------------------------------------------------------------
# c6: versioned preservation lists, with public sources and no conflict
# ---------------------------------------------------------------------------

WORD = re.compile(r"^[A-Z]+$")
CNAE_SOURCE = re.compile(r"^CNAE \d{4}-\d/\d{2}$")
URL_SOURCE = re.compile(r"^https://\S+ \(acesso em \d{2}/\d{2}/\d{4}\)$")
IBGE_NAMES_SOURCE = re.compile(
    r"^https://servicodados\.ibge\.gov\.br/api/v2/censos/nomes/[a-z]+ "
    r"\(acesso em \d{2}/\d{2}/\d{4}\)$"
)
REVIEWER = re.compile(r"^(pendente|[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)$")


def test_listas_versionadas_com_fonte_e_sem_conflito():
    lists = yaml.safe_load(LISTS_FILE.read_text(encoding="utf-8"))

    operation, activity, conflict = lists["operacao"], lists["atividade"], lists["conflito"]
    assert len(operation) >= 40
    assert len(activity) >= 100
    assert conflict

    for entry in [*operation, *activity]:
        assert {"palavra", "fonte", "revisado"} <= set(entry), entry
        # One word, uppercase ASCII letters only: no person or company name fits here.
        assert WORD.fullmatch(entry["palavra"]), entry
        assert CNAE_SOURCE.fullmatch(entry["fonte"]) or URL_SOURCE.fullmatch(entry["fonte"]), entry
        assert REVIEWER.fullmatch(str(entry["revisado"])), entry

    for entry in conflict:
        assert WORD.fullmatch(entry["palavra"]), entry
        assert IBGE_NAMES_SOURCE.fullmatch(entry["fonte"]), entry
        # A conflict word is an activity word: it keeps the CNAE where it was found.
        assert CNAE_SOURCE.fullmatch(entry["cnae"]), entry

    words = [entry["palavra"] for entry in [*operation, *activity, *conflict]]
    assert len(words) == len(set(words)), "a word repeats inside or across lists"
    conflict_words = {entry["palavra"] for entry in conflict}
    assert not conflict_words & {entry["palavra"] for entry in [*operation, *activity]}
    assert "ROSA" in conflict_words


# ---------------------------------------------------------------------------
# c7: level pessoas_protegidas keeps operation and activity words
# ---------------------------------------------------------------------------


def test_nivel_intermediario_preserva_operacao_e_atividade(monkeypatch, rng):
    monkeypatch.setenv(LEVEL_VARIABLE, "pessoas_protegidas")
    outputs = anonymize(
        [
            "PIX ENVIADO POSTO TESTE SAO JORGE LTDA",
            "COMPRA FARMACIA TESTE CENTRO",
            "BOLETO FARMACIA TESTE CENTRO",
            "TARIFA PACOTE SERVICOS",
        ]
    )
    assert re.fullmatch(rf"PIX ENVIADO POSTO {COMPANY}", outputs[0]), outputs[0]
    bought = re.fullmatch(rf"COMPRA FARMACIA ({COMPANY})", outputs[1])
    paid = re.fullmatch(rf"BOLETO FARMACIA ({COMPANY})", outputs[2])
    assert bought and paid, outputs
    assert bought.group(1) == paid.group(1)
    assert outputs[3] == "TARIFA PACOTE SERVICOS"
    for output in outputs:
        for hidden in ("TESTE", "SAO JORGE", "CENTRO"):
            assert hidden not in output

    # Identifiers keep being replaced in this level too.
    cnpj = _mask_cnpj(_cnpj(rng))
    cpf = _cpf(rng)
    (output,) = anonymize([f"PIX ENVIADO {cnpj} {cpf} AG 1234 C/C 56789-0"])
    assert output == "PIX ENVIADO [CNPJ] [CPF] [AGENCIA] [CONTA]"

    # The default level does not change: activity words are hidden too.
    monkeypatch.delenv(LEVEL_VARIABLE)
    bakery, gas_station = anonymize(
        ["BOLETO PADARIA TESTE LTDA", "PIX ENVIADO POSTO TESTE SAO JORGE LTDA"]
    )
    assert re.fullmatch(rf"BOLETO {COMPANY}", bakery), bakery
    assert re.fullmatch(rf"PIX ENVIADO {COMPANY}", gas_station), gas_station
    assert bakery.split()[-1] != gas_station.split()[-1]
    for output in (bakery, gas_station):
        assert "PADARIA" not in output
        assert "POSTO" not in output


# ---------------------------------------------------------------------------
# c8: no person name in clear, in any level with pseudonyms on
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "MARIA", "JOSE", "ANA", "JOAO", "ANTONIO", "FRANCISCA", "CARLOS", "PAULO", "ADRIANA",
    "LUCAS", "JULIANA", "MARCOS", "ROSA", "MARINA", "PEDRO", "FERNANDA", "LUIZ", "PATRICIA",
    "RAFAEL", "ALINE",
]  # fmt: skip
SURNAMES = [
    "SILVA", "SANTOS", "OLIVEIRA", "SOUZA", "RODRIGUES", "FERREIRA", "ALVES", "PEREIRA",
    "LIMA", "GOMES",
]  # fmt: skip
CORPUS_OPERATIONS = [
    "PIX", "PIX RECEBIDO", "TED", "PIX ENVIADO", "TRANSF", "DOC", "BOLETO", "PAGAMENTO",
]  # fmt: skip


@pytest.fixture
def synthetic_person_corpus():
    """200 synthetic descriptions `<operation> <FIRST> TESTE <SURNAME>` (plan, D9)."""
    corpus = []
    for i, (first, surname) in enumerate(
        (first, surname) for first in FIRST_NAMES for surname in SURNAMES
    ):
        operation = CORPUS_OPERATIONS[i % len(CORPUS_OPERATIONS)]
        name = f"{first} TESTE {surname}"
        corpus.append((operation, name, f"{operation} {name}"))
    assert len(corpus) == 200
    return corpus


def _leaked_words(output, person_words):
    """Output words equal to a name word of 3+ letters or to a 3+ letter prefix of one (D8)."""
    leaked = []
    for token in output.split():
        if PSEUDONYM_OR_MARKER.fullmatch(token):
            continue
        word = re.sub(r"[^A-Z]", "", token.upper())
        if len(word) < 3:
            continue
        if any(name_word.startswith(word) for name_word in person_words):
            leaked.append(word)
    return leaked


def test_nenhum_nome_de_pessoa_sai_em_claro(monkeypatch, rng, synthetic_person_corpus):
    cpf = _cpf(rng)
    explicit = [
        "PIX MARIA TESTE SOUZA",
        "BOLETO MARIA TESTE SOUZA ME",
        f"PIX JOAO TESTE LIMA {cpf}",
        "PIX SOCIO TESTE",
        "BOLETO ADVOCACIA MARIA TESTE SOUZA",
        "COMPRA POSTOTESTE CENTRO",
        "PIX ROSA TESTE CAMPOS",
    ]
    person_names = ["MARIA TESTE SOUZA", "JOAO TESTE LIMA", "SOCIO TESTE A", "ROSA TESTE CAMPOS"]
    person_names += [name for _, name, _ in synthetic_person_corpus]
    person_words = {word for name in person_names for word in name.split() if len(word) >= 3}
    descriptions = explicit + [description for _, _, description in synthetic_person_corpus]

    for level in ("pessoas_protegidas", "estrito"):
        monkeypatch.setenv(LEVEL_VARIABLE, level)
        outputs = anonymize(descriptions, partners=["SOCIO TESTE A"])

        for output in outputs:
            assert not _leaked_words(output, person_words), (level, output)

        maria = re.fullmatch(rf"PIX ({PERSON})", outputs[0])
        assert maria, (level, outputs[0])
        assert re.fullmatch(rf"BOLETO {maria.group(1)}", outputs[1]), (level, outputs[1])
        assert re.fullmatch(rf"PIX {PERSON} \[CPF\]", outputs[2]), (level, outputs[2])
        assert re.fullmatch(rf"PIX {PERSON}", outputs[3]), (level, outputs[3])
        lawyer = rf"BOLETO ADVOCACIA {maria.group(1)}"
        if level == "estrito":
            lawyer = rf"BOLETO {maria.group(1)}"
        assert re.fullmatch(lawyer, outputs[4]), (level, outputs[4])
        assert re.fullmatch(r"COMPRA (?:PESSOA|EMPRESA)_\d{3}", outputs[5]), (level, outputs[5])
        assert re.fullmatch(rf"PIX {PERSON}", outputs[6]), (level, outputs[6])

        pseudonyms = {}
        for (operation, name, _), output in zip(
            synthetic_person_corpus, outputs[len(explicit) :], strict=True
        ):
            match = re.fullmatch(rf"{re.escape(operation)} ({PERSON})", output)
            assert match, (level, output)
            assert pseudonyms.setdefault(name, match.group(1)) == match.group(1)
        assert len(set(pseudonyms.values())) == len(pseudonyms) == 200

        # The truncated partner name gets the partner's own pseudonym.
        full, truncated = anonymize(
            ["PIX SOCIO TESTE A", "PIX SOCIO TESTE"], partners=["SOCIO TESTE A"]
        )
        assert re.fullmatch(rf"PIX {PERSON}", full), (level, full)
        assert truncated == full
