import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("INDEX_BATCH", "500")

import pandas as pd
import streamlit as st
from web3 import Web3

from common.db import connect
from indexer.index_events import index_once
from reconcile.report import RANK, short
from reconcile.rules import run_rules
from registry.load_registry import load_registry

cfg = json.loads((ROOT / "deployments" / "sepolia.json").read_text())
abi = json.loads((ROOT / "deployments" / "FundShare.abi.json").read_text())

SEV_COLOR = {"CRITICAL": "#ffd6d6", "WARNING": "#fff1c2", "OK": "#d9f2dd"}

st.set_page_config(page_title="ChainLedger", layout="wide")


@st.cache_data(ttl=60, show_spinner="Reading the Sepolia chain...")
def compute():
    w3 = Web3(Web3.HTTPProvider(cfg["rpcUrl"]))
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(cfg["contractAddress"]), abi=abi
    )
    conn = connect(":memory:")
    index_once(conn, w3, contract, cfg["deployBlock"])
    load_registry(conn)
    findings = run_rules(conn)
    balances = [
        dict(r)
        for r in conn.execute("SELECT wallet, balance FROM chain_balances ORDER BY wallet")
    ]
    registry_total = conn.execute(
        "SELECT COALESCE(SUM(total_shares), 0) FROM registry_fund"
    ).fetchone()[0]
    return findings, balances, registry_total, w3.eth.block_number


st.title("ChainLedger")
st.caption(
    "Drift between on-chain fund-share balances and the off-chain legal registry. "
    "Live data from the Sepolia testnet."
)

findings, balances, registry_total, block = compute()

onchain_supply = sum(b["balance"] for b in balances)
critical = sum(1 for f in findings if f.severity == "CRITICAL")
warnings = sum(1 for f in findings if f.severity == "WARNING")

c1, c2, c3, c4 = st.columns(4)
c1.metric("On-chain supply", onchain_supply)
c2.metric("Registry total", registry_total)
c3.metric("Critical findings", critical)
c4.metric("Warnings", warnings)

st.subheader("Drift report")
ordered = sorted(findings, key=lambda f: (RANK[f.severity], f.rule, f.subject))
df = pd.DataFrame(
    [
        {
            "Severity": f.severity,
            "Rule": f.rule or "-",
            "Subject": short(f.subject),
            "Finding": f.message,
        }
        for f in ordered
    ]
)
styled = df.style.apply(
    lambda row: [f"background-color: {SEV_COLOR[row['Severity']]}; color: #111"] * len(row),
    axis=1,
)
st.dataframe(styled, hide_index=True)

st.subheader("On-chain balances (indexed from events)")
st.dataframe(pd.DataFrame(balances), hide_index=True)

st.markdown(
    f"Contract: [{cfg['contractAddress']}]"
    f"(https://sepolia.etherscan.io/address/{cfg['contractAddress']}) · "
    f"latest block {block}"
)
st.caption(
    "The chain is the settlement truth; the registry (sample CSV data) is the legal truth. "
    "Rules: 1 balance mismatch, 2 unverified holder, 3 KYC revoked but holding, 4 supply mismatch."
)