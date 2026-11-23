"""NUC-02: access rule by firm, role and portfolio (P-09).

Each test reproduces one example of features/NUC-02.json. The state is built
in memory; no database, network or HTTP. Only invented ids (ESC-1, EMP-1, ...).

The rule modules are imported inside `_core()` so that, while they do not
exist, each test fails on its own with ModuleNotFoundError.
"""

import importlib

CLIENTE_INEXISTENTE = "EMP-404"


def _core():
    contracts = importlib.import_module("lastro.core.contracts")
    service = importlib.import_module("lastro.core.service")
    return contracts, service


def _estado():
    """Reference state of the ficha (c1 + c3 + c4 + c6 + c7)."""
    c, _ = _core()
    m, r = c.Membership, c.Role
    membros = {
        "chefe_1": m(member_id="chefe_1", firm_id="ESC-1", role=r.MANAGER, is_active=True),
        "contador_a": m(member_id="contador_a", firm_id="ESC-1", role=r.ACCOUNTANT, is_active=True),
        "contador_b": m(member_id="contador_b", firm_id="ESC-1", role=r.ACCOUNTANT, is_active=True),
        "chefe_2": m(member_id="chefe_2", firm_id="ESC-2", role=r.MANAGER, is_active=True),
        "contador_x": m(member_id="contador_x", firm_id="ESC-2", role=r.ACCOUNTANT, is_active=True),
        "usuario_sem_escritorio": m(
            member_id="usuario_sem_escritorio", firm_id=None, role=None, is_active=True
        ),
        "usuario_sem_papel": m(
            member_id="usuario_sem_papel", firm_id="ESC-1", role=None, is_active=True
        ),
    }
    s = c.ClientScope
    clientes = {
        "EMP-1": s(client_id="EMP-1", firm_id="ESC-1", responsible_member_id="contador_a"),
        "EMP-2": s(client_id="EMP-2", firm_id="ESC-1", responsible_member_id="contador_b"),
        "EMP-3": s(client_id="EMP-3", firm_id="ESC-1", responsible_member_id=None),
        "EMP-4": s(client_id="EMP-4", firm_id="ESC-1", responsible_member_id="chefe_1"),
        "EMP-9": s(client_id="EMP-9", firm_id="ESC-2", responsible_member_id="contador_x"),
    }
    return membros, clientes


def _decidir(quem, acao, cliente_id):
    """Decide one action; an unknown client id reaches the rule as None (plan D4)."""
    _, service = _core()
    membros, clientes = _estado()
    return service.decide_access(membros[quem], acao, clientes.get(cliente_id))


def _tabela(pares, acao):
    return {(quem, cid): _decidir(quem, acao, cid) for quem, cid in pares}


def test_chefe_ve_todos_na_lista():
    c, _ = _core()
    pares = [("chefe_1", "EMP-1"), ("chefe_1", "EMP-2"), ("chefe_1", "EMP-3")]
    assert _tabela(pares, c.Action.LIST) == dict.fromkeys(pares, c.AccessDecision.ALLOWED)


def test_contador_acessa_so_atribuidos():
    c, _ = _core()
    d = c.AccessDecision
    esperado = {
        ("contador_a", "EMP-1"): d.ALLOWED,
        ("contador_a", "EMP-2"): d.NOT_FOUND,
        ("contador_a", "EMP-3"): d.NOT_FOUND,
    }
    for acao in (c.Action.LIST, c.Action.ACCESS):
        assert _tabela(esperado, acao) == esperado, acao


def test_outro_escritorio_sempre_negado():
    c, _ = _core()
    pares = [("chefe_2", "EMP-1"), ("contador_x", "EMP-1"), ("chefe_1", "EMP-9")]
    esperado = dict.fromkeys(pares, c.AccessDecision.NOT_FOUND)
    for acao in (c.Action.LIST, c.Action.ACCESS):
        assert _tabela(pares, acao) == esperado, acao


def test_usuario_sem_escritorio_ou_papel_negado():
    c, _ = _core()
    pares = [
        (quem, cid)
        for quem in ("usuario_sem_escritorio", "usuario_sem_papel")
        for cid in ("EMP-1", "EMP-3")
    ]
    esperado = dict.fromkeys(pares, c.AccessDecision.NOT_FOUND)
    for acao in (c.Action.LIST, c.Action.ACCESS):
        assert _tabela(pares, acao) == esperado, acao


def test_filtro_de_lista_devolve_so_visiveis():
    _, service = _core()
    membros, clientes = _estado()
    lista = [clientes[cid] for cid in ("EMP-1", "EMP-2", "EMP-3", "EMP-9")]
    esperado = {
        "contador_a": ["EMP-1"],
        "chefe_1": ["EMP-1", "EMP-2", "EMP-3"],
        "chefe_2": ["EMP-9"],
    }
    obtido = {
        quem: [cl.client_id for cl in service.filter_visible_clients(membros[quem], lista)]
        for quem in esperado
    }
    assert obtido == esperado


def test_chefe_acessa_so_atribuidos_a_ele():
    c, _ = _core()
    d = c.AccessDecision
    esperado = {
        ("chefe_1", "EMP-1"): d.NOT_ASSIGNED,
        ("chefe_1", "EMP-3"): d.NOT_ASSIGNED,
        ("chefe_1", "EMP-4"): d.ALLOWED,
    }
    assert _tabela(esperado, c.Action.ACCESS) == esperado


def test_recusa_por_falta_de_atribuicao_so_para_chefe():
    c, _ = _core()
    d = c.AccessDecision
    acesso = c.Action.ACCESS
    a = _decidir("chefe_1", acesso, "EMP-2")
    b = _decidir("contador_a", acesso, "EMP-2")
    c_ = _decidir("chefe_2", acesso, "EMP-1")
    d_ = _decidir("chefe_1", acesso, CLIENTE_INEXISTENTE)
    assert a == d.NOT_ASSIGNED
    assert b == d.NOT_FOUND
    assert b == c_ == d_


def test_gerir_atribuicao_exige_chefe_do_escritorio():
    c, _ = _core()
    d = c.AccessDecision
    esperado = {
        ("chefe_1", "EMP-1"): d.ALLOWED,
        ("chefe_1", "EMP-3"): d.ALLOWED,
        ("chefe_1", "EMP-4"): d.ALLOWED,
        ("contador_a", "EMP-1"): d.FORBIDDEN_ROLE,
        ("chefe_2", "EMP-1"): d.NOT_FOUND,
    }
    assert _tabela(esperado, c.Action.MANAGE_ASSIGNMENT) == esperado
