import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "chainledger.db"
CONFIG_PATH = DATA_DIR / "chain-config.json"
ABI_PATH = (
    ROOT / "contracts" / "artifacts" / "contracts" / "FundShare.sol" / "FundShare.json"
)
MAX_INT64 = 2**63 - 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS chain_transfers (
    tx_hash      TEXT NOT NULL,
    log_index    INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    from_addr    TEXT NOT NULL,
    to_addr      TEXT NOT NULL,
    amount       INTEGER NOT NULL,
    PRIMARY KEY (tx_hash, log_index)
);
CREATE TABLE IF NOT EXISTS sync_state (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    last_block INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS chain_balances (
    wallet  TEXT PRIMARY KEY,
    balance INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS chain_whitelist (
    wallet       TEXT PRIMARY KEY,
    status       INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    log_index    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS registry_investors (
    wallet        TEXT PRIMARY KEY,
    investor_name TEXT NOT NULL,
    kyc_status    TEXT NOT NULL CHECK (kyc_status IN ('ACTIVE', 'REVOKED'))
);
CREATE TABLE IF NOT EXISTS registry_holdings (
    wallet           TEXT PRIMARY KEY REFERENCES registry_investors(wallet),
    expected_balance INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS registry_fund (
    fund_id      TEXT PRIMARY KEY,
    total_shares INTEGER NOT NULL
);
"""


def connect(path=DB_PATH):
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn