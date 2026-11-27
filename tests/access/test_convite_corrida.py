"""ACE-02, review finding: two "new invitation" requests for the same accountant at once.

Extra test, outside `verificacao` and apart from `test_cadastro_contador.py` (whose tests
stay as they were). With a pending invitation K1, two simultaneous requests used to end with
one 201 and one unhandled unique-index violation (HTTP 500): the second request did not see the
invitation the first one had just stored. The expected result is serial: both answer 201 and
only the last code written stays valid. No real data.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

from test_cadastro_contador import (  # noqa: F401 (world is a fixture, resolved by name)
    NAME_C,
    _add_accountant,
    _client,
    _hash_of,
    _invites_of,
    _new_invitation,
    _pending_count,
    _sign_in,
    head_database,
    world,
)


def test_dois_convites_simultaneos_para_o_mesmo_contador_valem_em_serie(world):  # noqa: F811
    contador_c, code_1 = _add_accountant(world, "contador_c", NAME_C)
    chefe_1 = world.people["chefe_1"]
    barrier = threading.Barrier(2)

    def request_invitation():
        # Own app, own engine, own session cookie, own database connection.
        with _client(world.database) as client:
            signed_in = _sign_in(client, "chefe_1", chefe_1.password)
            assert signed_in.status_code == 200, signed_in.text
            barrier.wait(timeout=30)
            return _new_invitation(client, contador_c)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(request_invitation) for _ in range(2)]
        responses = [future.result(timeout=60) for future in futures]

    assert [response.status_code for response in responses] == [201, 201], [
        response.text for response in responses
    ]
    codes = {response.json()["invitation_code"] for response in responses}
    assert len(codes) == 2 and code_1 not in codes

    rows = {row[0]: row for row in _invites_of(world, contador_c)}
    assert _pending_count(world, contador_c) == 1
    assert rows[_hash_of(code_1)][2] is not None, "K1 was not revoked"
    still_valid = [code for code in codes if rows[_hash_of(code)][1:] == (None, None)]
    assert len(still_valid) == 1, "exactly one of the two new codes must stay valid"
