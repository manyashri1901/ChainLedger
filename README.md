# ChainLedger

**Detects drift between on-chain fund-share balances and the off-chain legal registry.**

![CI](https://github.com/manyashri1901/ChainLedger/actions/workflows/ci.yml/badge.svg)

ChainLedger is a prototype tokenised fund share registry. A permissioned ERC-20 token represents fund shares, a Python indexer rebuilds balances from on-chain events, and a four-rule reconciliation engine compares them with an off-chain investor registry. The chain is the settlement truth; the registry is the legal truth; ChainLedger reports where they disagree.

Built as a working prototype of a blockchain architecture for tokenised fund shares, with on-chain / off-chain reconciliation.

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

1. **Contract** (`contracts/contracts/FundShare.sol`): permissioned ERC-20 built on OpenZeppelin v5. Only whitelisted wallets can hold or receive shares; the issuer role whitelists investors, mints (`subscribe`), burns (`redeem`) and can freeze transfers. Every state change emits an event.
2. **Indexer** (`indexer/index_events.py`): reads `Transfer` and `WhitelistUpdated` events with web3.py and stores them in SQLite. It keeps a checkpoint, ignores duplicate events (keyed by transaction hash and log index) and rebuilds balances from the events. `--verify` compares the result with the contract's `balanceOf`, `totalSupply` and `whitelisted`; `--watch` keeps polling for new blocks.
3. **Registry** (`registry/`): mock off-chain registry loaded from CSV files (investors with KYC status, expected holdings, fund total).
4. **Reconciliation** (`reconcile/`): four rules compare indexed balances with the registry and print a report sorted Critical, Warning, OK.

| Rule | Checks | Severity |
|---|---|---|
| 1 | On-chain balance differs from registry expected balance | Warning |
| 2 | Wallet holds tokens but has no registry record | Critical |
| 3 | KYC revoked in registry but wallet still holds tokens | Critical |
| 4 | Total on-chain supply differs from registry total | Critical |

The reconciliation engine only reads. It never changes the chain or the registry, so a bug in a rule cannot corrupt ownership records.

## Project structure

```
contracts/    Solidity contract, Hardhat tests, seed script
common/       SQLite schema and connection helper
indexer/      Event indexer
registry/     Mock registry CSVs and loader
reconcile/    Rules, report formatting and CLI
tests/        Python tests (indexer and rules)
```

## Tech stack

Solidity, Hardhat 3, OpenZeppelin, viem and node:test (contract tests); Python 3, web3.py, SQLite and pytest (indexer and reconciliation); GitHub Actions (CI).

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

- 12 contract tests (Hardhat, viem, node:test): minting, burning, transfers, whitelist and freeze checks, access control, event emission.
- 12 Python tests (pytest): indexer idempotency, balance and whitelist verification against the contract, and a trigger and a no-trigger test for each reconciliation rule, plus the full worked example.

All tests run automatically on every push through GitHub Actions.

## Scope and limitations

- Runs on a local Hardhat network with sample data; the registry is a mock.
- The contract is not audited.
- Reorg handling would use confirmation depth on a public network; it is not needed on a local chain.
- A single `issuer` role controls whitelisting, minting, burning and freezing.

## Future work

- Integration with a real transfer agent or KYC provider
- Deployment to a public testnet
- A web dashboard and API for the drift report
- Static analysis and a formal security audit
- Multisig control of the issuer role

## Live on Sepolia testnet

The same contract is deployed on the Sepolia testnet, so the pipeline can be checked against a public chain.

- Contract: [`0x8b71c874cb876a8c780c326ccdacc461764777c5`](https://sepolia.etherscan.io/address/0x8b71c874cb876a8c780c326ccdacc461764777c5)
- Sample data: 4 whitelisted wallets holding 500 / 120 / 380 / 60 shares (supply 1060)

To run the indexer and report against Sepolia (after `scripts/deploy-sepolia.ts` has written `data/chain-config.sepolia.json`):

```powershell
$env:CHAIN_CONFIG="data\chain-config.sepolia.json"
$env:CHAINLEDGER_DB="data\sepolia.db"
$env:INDEX_BATCH="500"
python -m indexer.index_events --verify
python -m registry.load_registry
python -m reconcile.run
```

The deploy script needs a funded testnet wallet supplied through the `SEPOLIA_PRIVATE_KEY` and `SEPOLIA_RPC_URL` environment variables. Keys are never stored in the repo. Sepolia ETH has no real value.