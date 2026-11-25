"""Tests of IA-02: only anonymized text reaches the AI service (RF-SEG-03, D-03).

The AI service is a fake that records every request; no network, no SDK (SECURITY.md §5).
Data comes from `synthetic_fixtures_dir` (HAR-03) or is invented here. Valid CNPJs only exist
at run time, from `fixtures_sinteticas.cnpjs_dos_clientes()`.

Names fixed by planos/IA-02/plan.md (D1, D2, D3, D7, D8). The production names are imported
inside each test, so each one fails on its own while the gateway does not exist.
`test_conta_fora_do_plano_vira_nao_sei` is the c5 suggested in the plan (not yet in the card).
"""

import dataclasses
import importlib
import json
import logging
import re

import pytest

LEVEL_VARIABLE = "NAME_PROTECTION_LEVEL"
PERSON_PSEUDONYM = re.compile(r"PESSOA_\d{3}")
COMPANY_PSEUDONYM = re.compile(r"EMPRESA_\d{3}")
MASKED_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
MASKED_CNPJ = re.compile(r"[0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-\d{2}")
BRANCH = re.compile(r"\bAG (\d+)")
ACCOUNT = re.compile(r"\bCC (\d+)-\d")
CODE_NOT_IN_ANY_PLAN = "7.7.77"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _contracts():
    return importlib.import_module("lastro.ai.contracts")


def _suggest_accounts():
    return importlib.import_module("lastro.ai.service").suggest_accounts


class FakeLLMClient:
    """Records every request; answers with `responder(request)` or "não sei" for each entry."""

    def __init__(self, responder=None):
        self.requests = []
        self._responder = responder

    def suggest(self, request):
        self.requests.append(request)
        if self._responder is not None:
            return self._responder(request)
        return [None] * len(request.entries)


def _serialized(request):
    return json.dumps(dataclasses.asdict(request), ensure_ascii=False)


def _all_serialized(fake):
    return "\n".join(_serialized(request) for request in fake.requests)


def _texts(value):
    """Every string inside a request (descriptions and account names), not the amounts."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _texts(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _texts(item)


def _request_texts(fake):
    return [
        text
        for request in fake.requests
        for text in _texts(dataclasses.asdict(request))
    ]


def _entry_descriptions(fake):
    return [entry.description for request in fake.requests for entry in request.entries]


def _digits_and_letters(document):
    return re.sub(r"[^0-9A-Za-z]", "", document)


def _mask_cnpj(cnpj):
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def _cadastro(folder):
    return json.loads((folder / "cadastro.json").read_text(encoding="utf-8"))


def _client(folder, client_id):
    """(firm id, client record) of a client of the synthetic register."""
    for firm in _cadastro(folder)["escritorios"]:
        for client in firm["clientes"]:
            if client["id"] == client_id:
                return firm["id"], client
    raise AssertionError(f"cliente {client_id} não está no cadastro sintético")


def _movements(folder, client):
    movements = []
    for bank_account in client["contas_bancarias"]:
        answer_key = json.loads(
            (folder / bank_account["gabarito"]).read_text(encoding="utf-8")
        )
        movements.extend(answer_key["movimentacoes"])
    return movements


def _accounts(client):
    candidate_account = _contracts().CandidateAccount
    return tuple(
        candidate_account(code=row["codigo"], name=row["nome"])
        for row in client["plano"]
    )


def _partners(client):
    return tuple(partner["nome"] for partner in client["socios"])


def _item(firm_id, client_id, description, amount_cents):
    return _contracts().ClientDescription(
        firm_id=firm_id,
        client_id=client_id,
        description=description,
        amount_cents=amount_cents,
    )


def _distinct_amount_movements(movements, how_many, taken=()):
    """Movements with amounts different from each other and from `taken`."""
    chosen, seen = [], set(taken)
    for movement in movements:
        if movement["valor_centavos"] not in seen:
            chosen.append(movement)
            seen.add(movement["valor_centavos"])
        if len(chosen) == how_many:
            return chosen
    raise AssertionError("o gabarito sintético não tem movimentações suficientes")


@pytest.fixture(autouse=True)
def default_configuration(monkeypatch):
    """Every test starts without the level variable, so the default level (D-03) applies."""
    monkeypatch.delenv(LEVEL_VARIABLE, raising=False)


# ---------------------------------------------------------------------------
# c1: no CPF, CNPJ, branch or account in any request
# ---------------------------------------------------------------------------


def test_requisicao_sem_cpf_cnpj_agencia_conta(synthetic_fixtures_dir):
    # tools/fixtures_sinteticas.py, on sys.path once `synthetic_fixtures_dir` runs (conftest).
    generator = importlib.import_module("fixtures_sinteticas")
    firm_id, client = _client(synthetic_fixtures_dir, "EMP-1")
    cnpjs = generator.cnpjs_dos_clientes()
    alphanumeric = next(cnpj for cnpj in cnpjs.values() if not cnpj.isdigit())
    numeric = next(cnpj for cnpj in cnpjs.values() if cnpj.isdigit())

    descriptions = [
        movement["descricao"] for movement in _movements(synthetic_fixtures_dir, client)
    ]
    descriptions += [f"TED RECEBIDA {numeric}", f"PAGAMENTO {_mask_cnpj(alphanumeric)}"]
    items = [
        _item(firm_id, "EMP-1", description, -1000 - position)
        for position, description in enumerate(descriptions)
    ]

    documents = [alphanumeric, numeric]
    branches, accounts = [], []
    for description in descriptions:
        documents += MASKED_CPF.findall(description) + MASKED_CNPJ.findall(description)
        branches += BRANCH.findall(description)
        accounts += ACCOUNT.findall(description)
    # The answer key promises CPF, CNPJ, branch and account in EMP-1 (HAR-03 c2).
    assert len(documents) >= 4 and branches and accounts

    fake = FakeLLMClient()
    _suggest_accounts()(
        items,
        llm_client=fake,
        accounts_by_client={(firm_id, "EMP-1"): _accounts(client)},
        partners_by_client={(firm_id, "EMP-1"): _partners(client)},
    )

    assert len(fake.requests) >= 1
    payload = _all_serialized(fake)
    for document in documents:
        assert document not in payload
        assert _digits_and_letters(document) not in payload
        assert _digits_and_letters(document).lower() not in payload
    texts = "\n".join(_request_texts(fake))
    for number in branches + accounts:
        assert not re.search(rf"(?<!\d){number}(?!\d)", texts), number


# ---------------------------------------------------------------------------
# c2: partners and other counterparties only as pseudonyms (D-03)
# ---------------------------------------------------------------------------


def test_nome_de_socio_vai_como_pseudonimo(synthetic_fixtures_dir):
    firm_id, client = _client(synthetic_fixtures_dir, "EMP-1")
    partner = client["socios"][0]["nome"]
    descriptions = [
        f"PIX {partner}",
        "PIX RECEBIDO MARIA TESTE SOUZA",
        "BOLETO PADARIA TESTE LTDA",
    ]
    items = [
        _item(firm_id, "EMP-1", text, -500 * (n + 1))
        for n, text in enumerate(descriptions)
    ]

    fake = FakeLLMClient()
    _suggest_accounts()(
        items,
        llm_client=fake,
        accounts_by_client={(firm_id, "EMP-1"): _accounts(client)},
        partners_by_client={(firm_id, "EMP-1"): _partners(client)},
    )

    payload = _all_serialized(fake)
    for name in (partner, "MARIA TESTE SOUZA", "PADARIA TESTE LTDA"):
        assert name not in payload
    # The synthetic partner ends in a number (`SOCIO TESTE 01`), read as a number by IA-01;
    # the name part must still be gone (plan §4).
    assert "SOCIO TESTE" not in payload
    sent = "\n".join(_entry_descriptions(fake))
    assert len(set(PERSON_PSEUDONYM.findall(sent))) == 2
    assert len(set(COMPANY_PSEUDONYM.findall(sent))) == 1


# ---------------------------------------------------------------------------
# c3: one client per request
# ---------------------------------------------------------------------------


def test_cada_requisicao_leva_um_unico_cliente(synthetic_fixtures_dir):
    firm_1, client_1 = _client(synthetic_fixtures_dir, "EMP-1")
    firm_9, client_9 = _client(synthetic_fixtures_dir, "EMP-9")
    from_1 = _distinct_amount_movements(_movements(synthetic_fixtures_dir, client_1), 3)
    amounts_1 = {movement["valor_centavos"] for movement in from_1}
    from_9 = _distinct_amount_movements(
        _movements(synthetic_fixtures_dir, client_9), 2, amounts_1
    )
    amounts_9 = {movement["valor_centavos"] for movement in from_9}

    def item(firm_id, client_id, movement):
        return _item(
            firm_id, client_id, movement["descricao"], movement["valor_centavos"]
        )

    # Interleaved on purpose: one single call, each item tagged with its client.
    items = [
        item(firm_1, "EMP-1", from_1[0]),
        item(firm_9, "EMP-9", from_9[0]),
        item(firm_1, "EMP-1", from_1[1]),
        item(firm_9, "EMP-9", from_9[1]),
        item(firm_1, "EMP-1", from_1[2]),
    ]

    fake = FakeLLMClient()
    _suggest_accounts()(
        items,
        llm_client=fake,
        accounts_by_client={
            (firm_1, "EMP-1"): _accounts(client_1),
            (firm_9, "EMP-9"): _accounts(client_9),
        },
        partners_by_client={
            (firm_1, "EMP-1"): _partners(client_1),
            (firm_9, "EMP-9"): _partners(client_9),
        },
    )

    assert len(fake.requests) == 2
    sent_amounts = [
        {entry.amount_cents for entry in request.entries} for request in fake.requests
    ]
    for amounts in sent_amounts:
        assert amounts in (amounts_1, amounts_9)  # never a mix of the two clients
    sizes = {
        frozenset(amounts): len(request.entries)
        for amounts, request in zip(sent_amounts, fake.requests, strict=True)
    }
    assert sizes[frozenset(amounts_1)] == 3
    assert sizes[frozenset(amounts_9)] == 2


def test_mesmo_cliente_em_dois_escritorios_nao_se_mistura():
    accounts = (
        _contracts().CandidateAccount(code="4.1.01", name="Despesas bancarias"),
    )
    items = [
        _item("ESC-1", "EMP-1", "TARIFA PACOTE SERVICOS", -4417),
        _item("ESC-2", "EMP-1", "TARIFA PACOTE SERVICOS", -4321),
    ]

    fake = FakeLLMClient()
    _suggest_accounts()(
        items,
        llm_client=fake,
        accounts_by_client={("ESC-1", "EMP-1"): accounts, ("ESC-2", "EMP-1"): accounts},
    )

    assert len(fake.requests) == 2
    assert sorted(len(request.entries) for request in fake.requests) == [1, 1]


# ---------------------------------------------------------------------------
# c4: nothing to classify, no call
# ---------------------------------------------------------------------------


def test_lista_vazia_nao_chama_servico():
    fake = FakeLLMClient()

    result = _suggest_accounts()([], llm_client=fake, accounts_by_client={})

    assert result == []
    assert fake.requests == []


# ---------------------------------------------------------------------------
# c5 (suggested in the plan): the answer must be an account of the client's plan
# ---------------------------------------------------------------------------


def test_conta_fora_do_plano_vira_nao_sei(synthetic_fixtures_dir):
    firm_1, client_1 = _client(synthetic_fixtures_dir, "EMP-1")
    firm_9, client_9 = _client(synthetic_fixtures_dir, "EMP-9")
    plan_1 = _accounts(client_1)
    plan_9 = tuple(
        account for account in _accounts(client_9) if account.code != "4.1.02"
    )
    codes_1 = {account.code for account in plan_1}
    assert CODE_NOT_IN_ANY_PLAN not in codes_1 and "4.1.02" in codes_1

    answers = {-101: CODE_NOT_IN_ANY_PLAN, -102: "4.1.02", -103: "4.1.02"}
    fake = FakeLLMClient(
        lambda request: [answers[e.amount_cents] for e in request.entries]
    )
    items = [
        _item(firm_1, "EMP-1", "PAGTO ALUGUEL", -101),
        _item(firm_1, "EMP-1", "PAGTO ALUGUEL", -102),
        _item(firm_9, "EMP-9", "PAGTO ALUGUEL", -103),
    ]

    result = _suggest_accounts()(
        items,
        llm_client=fake,
        accounts_by_client={(firm_1, "EMP-1"): plan_1, (firm_9, "EMP-9"): plan_9},
    )

    # Not in EMP-1's plan → "não sei"; in it → kept; in EMP-1's plan but not EMP-9's → "não sei".
    assert result == [None, "4.1.02", None]


# ---------------------------------------------------------------------------
# Extras from the plan (D4, D6, D7, D8)
# ---------------------------------------------------------------------------


def test_valor_segue_a_descricao_certa():
    accounts = (
        _contracts().CandidateAccount(code="4.1.01", name="Despesas bancarias"),
    )
    items = [
        _item("ESC-1", "EMP-1", "TARIFA PACOTE SERVICOS", -4590),
        _item("ESC-1", "EMP-1", "PIX RECEBIDO MARIA TESTE SOUZA", 800000),
    ]

    fake = FakeLLMClient()
    _suggest_accounts()(
        items, llm_client=fake, accounts_by_client={("ESC-1", "EMP-1"): accounts}
    )

    (request,) = fake.requests
    first, second = request.entries
    assert first.description == "TARIFA PACOTE SERVICOS"
    assert first.amount_cents == -4590
    assert second.amount_cents == 800000
    assert "MARIA TESTE SOUZA" not in second.description
    for entry in request.entries:
        assert type(entry.amount_cents) is int  # cents, never float or bool (rule 8)


@pytest.mark.parametrize("amount", [45.9, -45.0, True])
def test_valor_float_e_recusado(amount):
    with pytest.raises((TypeError, ValueError)):
        _item("ESC-1", "EMP-1", "TARIFA PACOTE SERVICOS", amount)


def test_nome_de_conta_sai_sem_documento_e_socio(synthetic_fixtures_dir):
    """D7 (option B): account names lose documents and partner names, and stay readable."""
    firm_id, client = _client(synthetic_fixtures_dir, "EMP-1")
    partner = client["socios"][0]["nome"]
    cpf = "111.222.333-00"  # invalid check digits: synthetic (SECURITY.md §3)
    candidate_account = _contracts().CandidateAccount
    accounts = (
        candidate_account(code="4.1.04", name=f"ADIANTAMENTO {partner}"),
        candidate_account(code="4.1.01", name="Despesas bancarias"),
        candidate_account(code="4.1.02", name="Aluguel"),
        candidate_account(code="4.1.05", name=f"Reembolso {cpf}"),
    )

    fake = FakeLLMClient()
    _suggest_accounts()(
        [_item(firm_id, "EMP-1", f"PIX {partner}", -250000)],
        llm_client=fake,
        accounts_by_client={(firm_id, "EMP-1"): accounts},
        partners_by_client={(firm_id, "EMP-1"): _partners(client)},
    )

    (request,) = fake.requests
    sent = {account.code: account.name for account in request.accounts}
    assert list(sent) == [
        "4.1.04",
        "4.1.01",
        "4.1.02",
        "4.1.05",
    ]  # codes untouched, same order
    # Readable names are not turned into pseudonyms (this is what the full anonymizer broke).
    assert sent["4.1.01"] == "Despesas bancarias"
    assert sent["4.1.02"] == "Aluguel"
    # Partner name gone; same pseudonym as in the description of the same batch.
    assert "SOCIO TESTE" not in sent["4.1.04"]
    account_pseudonyms = PERSON_PSEUDONYM.findall(sent["4.1.04"])
    assert len(account_pseudonyms) == 1
    assert account_pseudonyms == PERSON_PSEUDONYM.findall(
        request.entries[0].description
    )
    # Document gone.
    assert cpf not in sent["4.1.05"]
    assert "11122233300" not in sent["4.1.05"]


def test_cliente_sem_contas_nao_chama_servico():
    fake = FakeLLMClient()
    items = [
        _item("ESC-1", "EMP-1", "TARIFA PACOTE SERVICOS", -4417),
        _item("ESC-1", "EMP-1", "CONTA ENERGIA", -48626),
    ]

    result = _suggest_accounts()(
        items, llm_client=fake, accounts_by_client={("ESC-1", "EMP-1"): ()}
    )

    assert result == [None, None]
    assert fake.requests == []


def test_resultado_volta_na_ordem_do_pedido():
    candidate_account = _contracts().CandidateAccount
    accounts = (
        candidate_account(code="4.1.01", name="Despesas bancarias"),
        candidate_account(code="4.1.02", name="Aluguel"),
        candidate_account(code="4.1.03", name="Energia e agua"),
    )
    answers = {-11: "4.1.01", -22: "4.1.02", -33: "4.1.03"}
    fake = FakeLLMClient(
        lambda request: [answers[e.amount_cents] for e in request.entries]
    )
    items = [
        _item("ESC-1", "EMP-1", "TARIFA PACOTE SERVICOS", -11),
        _item("ESC-2", "EMP-9", "PAGTO ALUGUEL", -22),
        _item("ESC-1", "EMP-1", "CONTA ENERGIA", -33),
    ]

    result = _suggest_accounts()(
        items,
        llm_client=fake,
        accounts_by_client={("ESC-1", "EMP-1"): accounts, ("ESC-2", "EMP-9"): accounts},
    )

    assert result == ["4.1.01", "4.1.02", "4.1.03"]
    assert len(fake.requests) == 2


def test_resposta_com_tamanho_errado_e_recusada():
    invalid_response = _contracts().InvalidLLMResponseError
    accounts = (
        _contracts().CandidateAccount(code="4.1.01", name="Despesas bancarias"),
    )
    fake = FakeLLMClient(lambda request: ["4.1.01"])  # one answer for two entries
    items = [
        _item("ESC-1", "EMP-1", "TARIFA PACOTE SERVICOS", -4417),
        _item("ESC-1", "EMP-1", "TARIFA PACOTE SERVICOS", -4778),
    ]

    with pytest.raises(invalid_response):
        _suggest_accounts()(
            items, llm_client=fake, accounts_by_client={("ESC-1", "EMP-1"): accounts}
        )


def test_resposta_errada_de_um_cliente_cancela_a_chamada_inteira():
    """All or nothing (docs/modulos/ai.md): a bad answer for the 2nd client fails the call."""
    invalid_response = _contracts().InvalidLLMResponseError
    accounts = (
        _contracts().CandidateAccount(code="4.1.01", name="Despesas bancarias"),
    )

    # one answer per request: right for the 1st client (1 entry), short for the 2nd (2 entries)
    fake = FakeLLMClient(lambda request: ["4.1.01"])
    items = [
        _item("ESC-1", "EMP-1", "TARIFA PACOTE SERVICOS", -4417),
        _item("ESC-1", "EMP-2", "TARIFA PACOTE SERVICOS", -4778),
        _item("ESC-1", "EMP-2", "TARIFA PACOTE SERVICOS", -4900),
    ]

    with pytest.raises(invalid_response):
        _suggest_accounts()(
            items,
            llm_client=fake,
            accounts_by_client={
                ("ESC-1", "EMP-1"): accounts,
                ("ESC-1", "EMP-2"): accounts,
            },
        )

    assert len(fake.requests) == 2  # the 1st client was asked (and answered) before


def test_descricao_original_nao_aparece_no_repr():
    description = "PIX RECEBIDO SOCIO TESTE"
    item = _item("ESC-1", "EMP-1", description, -4417)

    assert description not in repr(item)
    assert description not in f"{[item]}"


def test_nivel_invalido_falha_antes_de_chamar_servico(monkeypatch):
    invalid_level = _contracts().InvalidNameProtectionLevelError
    monkeypatch.setenv(LEVEL_VARIABLE, "medio")
    accounts = (
        _contracts().CandidateAccount(code="4.1.01", name="Despesas bancarias"),
    )
    fake = FakeLLMClient()

    with pytest.raises(invalid_level):
        _suggest_accounts()(
            [_item("ESC-1", "EMP-1", "PIX RECEBIDO MARIA TESTE SOUZA", 800000)],
            llm_client=fake,
            accounts_by_client={("ESC-1", "EMP-1"): accounts},
        )

    assert fake.requests == []


def test_gateway_nao_registra_texto_original_em_log(caplog):
    cpf = "111.222.333-00"  # invalid check digits: synthetic (SECURITY.md §3)
    accounts = (
        _contracts().CandidateAccount(code="4.1.01", name="Despesas bancarias"),
    )
    fake = FakeLLMClient()

    with caplog.at_level(logging.DEBUG):
        _suggest_accounts()(
            [_item("ESC-1", "EMP-1", f"PIX RECEBIDO MARIA TESTE SOUZA {cpf}", 873451)],
            llm_client=fake,
            accounts_by_client={("ESC-1", "EMP-1"): accounts},
        )

    assert len(fake.requests) == 1
    for secret in (cpf, "11122233300", "MARIA TESTE SOUZA", "873451"):
        assert secret not in caplog.text
