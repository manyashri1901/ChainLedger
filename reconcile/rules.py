from dataclasses import dataclass

CRITICAL = "CRITICAL"
WARNING = "WARNING"
OK = "OK"


@dataclass
class Finding:
    severity: str
    rule: str
    subject: str
    message: str


def rule1_balance_mismatch(conn):
    """Rule 1: on-chain balance differs from the registry's expected balance."""
    rows = conn.execute(
        "SELECT h.wallet AS wallet, h.expected_balance AS expected, "
        "COALESCE(c.balance, 0) AS onchain "
        "FROM registry_holdings h LEFT JOIN chain_balances c ON c.wallet = h.wallet "
        "WHERE COALESCE(c.balance, 0) != h.expected_balance"
    ).fetchall()
    return [
        Finding(
            WARNING,
            "Rule 1",
            r["wallet"],
            f"On-chain balance {r['onchain']}, registry expects {r['expected']} "
            f"(drift {abs(r['onchain'] - r['expected'])})",
        )
        for r in rows
    ]


def rule2_unverified_holder(conn):
    """Rule 2: a wallet holds tokens but has no registry record."""
    rows = conn.execute(
        "SELECT c.wallet AS wallet, c.balance AS balance FROM chain_balances c "
        "WHERE c.balance > 0 AND c.wallet NOT IN (SELECT wallet FROM registry_investors)"
    ).fetchall()
    return [
        Finding(
            CRITICAL,
            "Rule 2",
            r["wallet"],
            f"Holds {r['balance']} tokens but has no registry record",
        )
        for r in rows
    ]


def rule3_kyc_revoked(conn):
    """Rule 3: KYC is revoked in the registry but the wallet still holds tokens."""
    rows = conn.execute(
        "SELECT i.wallet AS wallet, c.balance AS balance FROM registry_investors i "
        "JOIN chain_balances c ON c.wallet = i.wallet "
        "WHERE i.kyc_status = 'REVOKED' AND c.balance > 0"
    ).fetchall()
    return [
        Finding(
            CRITICAL,
            "Rule 3",
            r["wallet"],
            f"KYC revoked in registry, wallet still holds {r['balance']} tokens",
        )
        for r in rows
    ]


def rule4_supply_mismatch(conn):
    """Rule 4: total on-chain supply differs from the registry's total shares."""
    supply = conn.execute("SELECT COALESCE(SUM(balance), 0) FROM chain_balances").fetchone()[0]
    total = conn.execute("SELECT COALESCE(SUM(total_shares), 0) FROM registry_fund").fetchone()[0]
    if supply == total:
        return []
    return [
        Finding(
            CRITICAL,
            "Rule 4",
            "Fund",
            f"On-chain supply {supply}, registry total {total} (drift {abs(supply - total)})",
        )
    ]


def ok_wallets(conn, findings):
    """Registry wallets that no rule flagged are reported as OK."""
    flagged = {f.subject for f in findings}
    rows = conn.execute(
        "SELECT h.wallet AS wallet, COALESCE(c.balance, 0) AS onchain "
        "FROM registry_holdings h LEFT JOIN chain_balances c ON c.wallet = h.wallet "
        "ORDER BY h.wallet"
    ).fetchall()
    return [
        Finding(OK, "", r["wallet"], f"Balance {r['onchain']} matches registry")
        for r in rows
        if r["wallet"] not in flagged
    ]


def run_rules(conn):
    findings = []
    findings += rule1_balance_mismatch(conn)
    findings += rule2_unverified_holder(conn)
    findings += rule3_kyc_revoked(conn)
    findings += rule4_supply_mismatch(conn)
    findings += ok_wallets(conn, findings)
    return findings