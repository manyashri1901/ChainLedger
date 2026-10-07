import csv
import json
import os
import urllib.request
from pathlib import Path

from web3 import Web3

from common.db import connect

REGISTRY_DIR = Path(__file__).resolve().parent


def _rows(name):
    with open(REGISTRY_DIR / name, newline="") as f:
        return list(csv.DictReader(f))


def _fetch(path):
    base = os.environ["REGISTRY_API_URL"].rstrip("/")
    req = urllib.request.Request(
        base + path,
        headers={"X-API-Key": os.environ.get("REGISTRY_API_KEY", "dev-key")},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def _source(csv_name, api_path):
    """Registry rows from the API when REGISTRY_API_URL is set, else from CSV."""
    if os.environ.get("REGISTRY_API_URL"):
        return _fetch(api_path)
    return _rows(csv_name)


def load_registry(conn):
    investors = _source("investors.csv", "/investors")
    holdings = _source("holdings.csv", "/holdings")
    fund = _source("fund.csv", "/fund")

    conn.execute("DELETE FROM registry_holdings")
    conn.execute("DELETE FROM registry_investors")
    conn.execute("DELETE FROM registry_fund")

    for r in investors:
        status = r["kyc_status"].strip().upper()
        if status not in ("ACTIVE", "REVOKED"):
            raise ValueError(f"bad kyc_status: {r['kyc_status']}")
        conn.execute(
            "INSERT INTO registry_investors (wallet, investor_name, kyc_status) "
            "VALUES (?, ?, ?)",
            (Web3.to_checksum_address(r["wallet"].strip()), r["investor_name"].strip(), status),
        )
    for r in holdings:
        expected = int(r["expected_balance"])
        if expected < 0:
            raise ValueError("expected_balance cannot be negative")
        conn.execute(
            "INSERT INTO registry_holdings (wallet, expected_balance) VALUES (?, ?)",
            (Web3.to_checksum_address(r["wallet"].strip()), expected),
        )
    for r in fund:
        conn.execute(
            "INSERT INTO registry_fund (fund_id, total_shares) VALUES (?, ?)",
            (r["fund_id"].strip(), int(r["total_shares"])),
        )
    conn.commit()


def main():
    conn = connect()
    load_registry(conn)
    print("registry_investors")
    for r in conn.execute("SELECT * FROM registry_investors"):
        print("  ", r["wallet"], r["investor_name"], r["kyc_status"])
    print("registry_holdings")
    for r in conn.execute("SELECT * FROM registry_holdings"):
        print("  ", r["wallet"], r["expected_balance"])
    print("registry_fund")
    for r in conn.execute("SELECT * FROM registry_fund"):
        print("  ", r["fund_id"], r["total_shares"])


if __name__ == "__main__":
    main()
