from common.db import connect
from reconcile.report import build_report
from reconcile.rules import (
    rule1_balance_mismatch,
    rule2_unverified_holder,
    rule3_kyc_revoked,
    rule4_supply_mismatch,
    run_rules,
)

A = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
B = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
C = "0x90F79bf6EB2c4f870365E785982E1f101E93b906"
D = "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"


def make_db(balances=None, investors=None, holdings=None, fund_total=0):
    conn = connect(":memory:")
    for wallet, bal in (balances or {}).items():
        conn.execute("INSERT INTO chain_balances (wallet, balance) VALUES (?, ?)", (wallet, bal))
    for wallet, name, kyc in investors or []:
        conn.execute(
            "INSERT INTO registry_investors (wallet, investor_name, kyc_status) VALUES (?, ?, ?)",
            (wallet, name, kyc),
        )
    for wallet, expected in (holdings or {}).items():
        conn.execute(
            "INSERT INTO registry_holdings (wallet, expected_balance) VALUES (?, ?)",
            (wallet, expected),
        )
    conn.execute("INSERT INTO registry_fund (fund_id, total_shares) VALUES ('MTF', ?)", (fund_total,))
    conn.commit()
    return conn


def test_rule1_flags_balance_drift():
    conn = make_db({A: 500}, [(A, "Investor A", "ACTIVE")], {A: 300})
    found = rule1_balance_mismatch(conn)
    assert len(found) == 1
    assert found[0].severity == "WARNING"
    assert "drift 200" in found[0].message


def test_rule1_ignores_matching_balance():
    conn = make_db({A: 300}, [(A, "Investor A", "ACTIVE")], {A: 300})
    assert rule1_balance_mismatch(conn) == []


def test_rule2_flags_holder_without_registry_record():
    conn = make_db({D: 60})
    found = rule2_unverified_holder(conn)
    assert len(found) == 1
    assert found[0].severity == "CRITICAL"
    assert "no registry record" in found[0].message


def test_rule2_ignores_registered_holder_and_zero_balance():
    conn = make_db({A: 100, D: 0}, [(A, "Investor A", "ACTIVE")])
    assert rule2_unverified_holder(conn) == []


def test_rule3_flags_revoked_investor_still_holding():
    conn = make_db({B: 120}, [(B, "Investor B", "REVOKED")])
    found = rule3_kyc_revoked(conn)
    assert len(found) == 1
    assert found[0].severity == "CRITICAL"
    assert "120" in found[0].message


def test_rule3_ignores_revoked_investor_with_zero_balance():
    conn = make_db({B: 0}, [(B, "Investor B", "REVOKED")])
    assert rule3_kyc_revoked(conn) == []


def test_rule4_flags_supply_mismatch():
    conn = make_db({A: 500, B: 120, C: 380, D: 60}, fund_total=800)
    found = rule4_supply_mismatch(conn)
    assert len(found) == 1
    assert found[0].severity == "CRITICAL"
    assert "drift 260" in found[0].message


def test_rule4_ignores_matching_supply():
    conn = make_db({A: 500, B: 120, C: 380, D: 60}, fund_total=1060)
    assert rule4_supply_mismatch(conn) == []


def test_full_worked_example_report():
    conn = make_db(
        {A: 500, B: 120, C: 380, D: 60},
        [(A, "Investor A", "ACTIVE"), (B, "Investor B", "REVOKED"), (C, "Investor C", "ACTIVE")],
        {A: 300, B: 120, C: 380},
        fund_total=800,
    )
    lines = build_report(run_rules(conn)).splitlines()
    assert len(lines) == 5
    assert lines[0].startswith("[CRITICAL]") and "Rule 2" in lines[0]
    assert lines[1].startswith("[CRITICAL]") and "Rule 3" in lines[1]
    assert lines[2].startswith("[CRITICAL]") and "Rule 4" in lines[2]
    assert lines[3].startswith("[WARNING ]") and "Rule 1" in lines[3]
    assert lines[4].startswith("[OK      ]")