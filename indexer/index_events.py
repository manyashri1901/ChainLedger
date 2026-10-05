import argparse
import json
import time

from web3 import Web3

from common.db import ABI_PATH, CONFIG_PATH, MAX_INT64, connect

ZERO = "0x0000000000000000000000000000000000000000"
BATCH = 2000


def load_context():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    with open(ABI_PATH) as f:
        abi = json.load(f)["abi"]
    w3 = Web3(Web3.HTTPProvider(cfg["rpcUrl"]))
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(cfg["contractAddress"]), abi=abi
    )
    return w3, contract, cfg


def _adjust(conn, wallet, delta):
    if abs(delta) > MAX_INT64:
        raise ValueError("amount exceeds SQLite 64-bit integer range")
    conn.execute(
        "INSERT INTO chain_balances (wallet, balance) VALUES (?, ?) "
        "ON CONFLICT(wallet) DO UPDATE SET balance = balance + excluded.balance",
        (wallet, delta),
    )


def index_once(conn, w3, contract, deploy_block):
    row = conn.execute("SELECT last_block FROM sync_state WHERE id = 1").fetchone()
    last = row["last_block"] if row else deploy_block - 1
    latest = w3.eth.block_number
    new_events = 0

    start = last + 1
    while start <= latest:
        end = min(start + BATCH - 1, latest)
        logs = contract.events.Transfer.get_logs(from_block=start, to_block=end)
        for log in logs:
            tx_hash = "0x" + bytes(log["transactionHash"]).hex()
            sender = log["args"]["from"]
            receiver = log["args"]["to"]
            amount = int(log["args"]["value"])
            if amount > MAX_INT64:
                raise ValueError("amount exceeds SQLite 64-bit integer range")
            cur = conn.execute(
                "INSERT OR IGNORE INTO chain_transfers "
                "(tx_hash, log_index, block_number, from_addr, to_addr, amount) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (tx_hash, log["logIndex"], log["blockNumber"], sender, receiver, amount),
            )
            if cur.rowcount == 1:  # only new events change balances
                if sender != ZERO:
                    _adjust(conn, sender, -amount)
                if receiver != ZERO:
                    _adjust(conn, receiver, amount)
                new_events += 1
        conn.execute(
            "INSERT INTO sync_state (id, last_block) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET last_block = excluded.last_block",
            (end,),
        )
        conn.commit()
        start = end + 1
    return new_events


def verify_balances(conn, contract):
    ok = True
    total = 0
    for row in conn.execute("SELECT wallet, balance FROM chain_balances ORDER BY wallet"):
        onchain = contract.functions.balanceOf(row["wallet"]).call()
        status = "MATCH" if onchain == row["balance"] else "MISMATCH"
        ok = ok and status == "MATCH"
        total += row["balance"]
        print(f"{status:<8} {row['wallet']}  indexed={row['balance']}  on-chain={onchain}")
    supply = contract.functions.totalSupply().call()
    status = "MATCH" if supply == total else "MISMATCH"
    ok = ok and status == "MATCH"
    print(f"{status:<8} total supply  indexed={total}  on-chain={supply}")
    return ok


def main():
    parser = argparse.ArgumentParser(description="ChainLedger event indexer")
    parser.add_argument("--watch", action="store_true", help="keep indexing new blocks")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between polls")
    parser.add_argument("--verify", action="store_true", help="compare with balanceOf")
    args = parser.parse_args()

    w3, contract, cfg = load_context()
    conn = connect()
    while True:
        n = index_once(conn, w3, contract, cfg["deployBlock"])
        print(f"indexed {n} new transfer event(s)")
        if args.verify:
            verify_balances(conn, contract)
        if not args.watch:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()