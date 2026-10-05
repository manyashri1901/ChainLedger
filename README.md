# ChainLedger

**Detects drift between on-chain fund-share balances and the off-chain legal registry.**

ChainLedger is a prototype tokenised fund share registry. A permissioned ERC-20 token represents fund shares, a Python indexer rebuilds balances from on-chain events, and a four-rule reconciliation engine compares them with an off-chain investor registry. The chain is the settlement truth; the registry is the legal truth; ChainLedger reports where they disagree.

Built as the working prototype for VIT Case Study II (Blockchain Architecture Design).

## Example drift report

```
ChainLedger drift report
------------------------
[CRITICAL] Rule 2  0x15d3...6A65  Holds 60 tokens but has no registry record
[CRITICAL] Rule 3  0x3C44...93BC  KYC revoked in registry, wallet still holds 120 tokens
[CRITICAL] Rule 4  Fund           On-chain supply 1060, registry total 800 (drift 260)
[WARNING ] Rule 1  0x7099...79C8  On-chain balance 500, registry expects 300 (drift 200)
[OK      ]         0x90F7...b906  Balance 380 matches registry
```

## Architecture

1. **Contract** (`contracts/contracts/FundShare.sol`): permissioned ERC-20 built on OpenZeppelin v5. Only whitelisted wallets can hold or receive shares; the issuer role mints (`subscribe`), burns (`redeem`) and can freeze transfers.
2. **Indexer** (`indexer/index_events.py`): reads `Transfer` events with web3.py and stores them in SQLite. It keeps a checkpoint, ignores duplicate events (keyed by transaction hash and log index) and rebuilds balances from the events.
3. **Registry** (`registry/`): mock off-chain registry loaded from CSV files (investors with KYC status, expected holdings, fund total).
4. **Reconciliation** (`reconcile/`): four rules compare indexed balances with the registry and print a report sorted Critical, Warning, OK.

| Rule | Checks | Severity |
|---|---|---|
| 1 | On-chain balance differs from registry expected balance | Warning |
| 2 | Wallet holds tokens but has no registry record | Critical |
| 3 | KYC revoked in registry but wallet still holds tokens | Critical |
| 4 | Total on-chain supply differs from registry total | Critical |

## Tech stack

Solidity, Hardhat 3, OpenZeppelin, viem and node:test (contract tests); Python 3, web3.py, SQLite and pytest (indexer and reconciliation).

## Run it locally

Requires Node 22+, Python 3.11+ and Git.

```powershell
# Terminal 1: local blockchain
cd contracts
npm install
npm test
npm run node

# Terminal 2: deploy and seed sample data
cd contracts
npm run seed

# Terminal 3: indexer, registry and report (from the repo root)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m indexer.index_events --verify
python -m registry.load_registry
python -m reconcile.run
python -m pytest -v
```

If you restart the local node, delete `data\chainledger.db` and run `npm run seed` again.

## Tests

- 12 contract tests (Hardhat, viem, node:test)
- 11 Python tests (pytest): indexer idempotency, balance verification and each reconciliation rule

## Scope and limitations

- Runs on a local Hardhat network with sample data; the registry is a mock.
- The contract is not audited.
- Reorg handling would use confirmation depth on a public network; it is not needed locally.
- The contract calls its operator `issuer` and uses `subscribe` / `redeem` / `freeze`; the Case Study II report describes the same roles as Agent, mint, burn and Admin.
- Out of scope: real transfer-agent or KYC integration, testnet deployment, a web dashboard, formal security audit.