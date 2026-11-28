"""CAD-04, review finding: two PATCH of the same account at the same time.

Extra test, outside `verificacao`, apart from `test_contas_bancarias.py` (which stays as it
was). One PATCH changes only the nickname and the other only the last month. Both must end up
applied: a field that a request does not send must not change (plan CAD-04, answer P4), even
when the other request commits first. The service used to read the account before it took the
lock on the client, so the second PATCH wrote back the old value it had read.

To make the order certain, the test holds the lock on the client row from its own connection,
starts both PATCH, waits until both are blocked on that lock, and only then releases it. No
real data.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from test_contas_bancarias import (  # noqa: F401 (world is a fixture, resolved by name)
    _accounts_path,
    _connect,
    _inform,
    _insert_client,
    _list,
    _row_count,
    _signed_in,
    world,
)

BLOCKED_WAIT_SECONDS = 20


def _blocked_on_lock(conn) -> int:
    """How many other backends of the test database are waiting for a lock."""
    return conn.execute(
        "SELECT count(*) FROM pg_stat_activity"
        " WHERE datname = current_database() AND wait_event_type = 'Lock'"
        " AND pid <> pg_backend_pid()"
    ).fetchone()[0]


def test_dois_patch_simultaneos_na_mesma_conta_nao_desfazem_um_ao_outro(world):  # noqa: F811
    emp_1 = _insert_client(world, "EMP-1", "contador_a")
    with _signed_in(world, "ESC-1", "contador_a") as setup:
        created = _inform(
            setup,
            emp_1,
            bank="341",
            nickname="Conta antiga",
            first_month="2026-01",
        )
        assert created.status_code == 201, created.text
    path = f"{_accounts_path(emp_1)}/{created.json()['id']}"
    rows_before = _row_count(world)
    barrier = threading.Barrier(2)

    def patch(body):
        with _signed_in(world, "ESC-1", "contador_a") as client:
            barrier.wait(timeout=30)
            return client.patch(path, json=body)

    with _connect(world.database) as holder:
        holder.autocommit = False
        holder.execute("SELECT id FROM cliente WHERE id = %s FOR UPDATE", (emp_1,))
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(patch, {"nickname": "Conta principal"}),
                pool.submit(patch, {"last_month": "2026-11"}),
            ]
            deadline = time.monotonic() + BLOCKED_WAIT_SECONDS
            with _connect(world.database) as observer:
                while _blocked_on_lock(observer) < 2:
                    assert time.monotonic() < deadline, "the two PATCH never blocked"
                    time.sleep(0.1)
            holder.commit()
            responses = [future.result(timeout=60) for future in futures]

    assert [response.status_code for response in responses] == [200, 200], [
        response.text for response in responses
    ]
    with _signed_in(world, "ESC-1", "contador_a") as client:
        [account] = _list(client, emp_1)
    assert account["nickname"] == "Conta principal", "the nickname change was undone"
    assert account["last_month"] == "2026-11", "the last month change was undone"
    assert account["first_month"] == "2026-01"
    assert account["bank"] == "341"
    assert _row_count(world) == rows_before
