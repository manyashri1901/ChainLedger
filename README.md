# ChainLedger

A tokenized fund share registry that keeps blockchain state and
off-chain investor records in agreement — and surfaces it loudly
when they drift.

When a fund tokenizes its shares, ownership exists in two systems at
once: token balances on-chain, and the transfer agent's registry of
verified investor identities, subscriptions, and NAV off-chain.
Neither is authoritative alone. The chain is settlement truth; the
registry is legal truth. Reconciling them is the core operational
problem in real-world asset tokenization, and it's what this project
implements.

**Stack:** Solidity · Hardhat · web3.py · FastAPI · PostgreSQL ·
SQLAlchemy · Next.js · TypeScript

[architecture diagram]
[screenshot: reconciliation view with a detected break]
