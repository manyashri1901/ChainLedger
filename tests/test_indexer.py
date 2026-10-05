import pytest

from common.db import connect
from indexer.index_events import index_once, load_context, verify_balances


@pytest.fixture(scope="module")
def ctx():
    try:
        w3, contract, cfg = load_context()
    except FileNotFoundError:
        pytest.skip("run `npm run seed` first")
    if not w3.is_connected():
        pytest.skip("start the local chain with `npm run node`")
    return w3, contract, cfg


def test_running_twice_creates_no_duplicates(ctx):
    w3, contract, cfg = ctx
    conn = connect(":memory:")
    first = index_once(conn, w3, contract, cfg["deployBlock"])
    count = conn.execute("SELECT COUNT(*) FROM chain_transfers").fetchone()[0]
    second = index_once(conn, w3, contract, cfg["deployBlock"])
    assert first == count
    assert second == 0
    assert conn.execute("SELECT COUNT(*) FROM chain_transfers").fetchone()[0] == count


def test_balances_equal_balanceof_and_total_supply(ctx, capsys):
    w3, contract, cfg = ctx
    conn = connect(":memory:")
    index_once(conn, w3, contract, cfg["deployBlock"])
    assert verify_balances(conn, contract) is True