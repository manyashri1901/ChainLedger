from common.db import connect
from reconcile.report import build_report
from reconcile.rules import run_rules


def main():
    conn = connect()
    chain_rows = conn.execute("SELECT COUNT(*) FROM chain_balances").fetchone()[0]
    registry_rows = conn.execute("SELECT COUNT(*) FROM registry_investors").fetchone()[0]
    if chain_rows == 0:
        print("No indexed balances. Run: python -m indexer.index_events")
        return
    if registry_rows == 0:
        print("Registry is empty. Run: python -m registry.load_registry")
        return

    findings = run_rules(conn)
    print("ChainLedger drift report")
    print("-" * 24)
    print(build_report(findings))


if __name__ == "__main__":
    main()