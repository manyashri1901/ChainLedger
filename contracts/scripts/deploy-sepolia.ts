import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { network } from "hardhat";
import { getAddress } from "viem";

const { viem } = await network.create();
const publicClient = await viem.getPublicClient();
const [issuer] = await viem.getWalletClients();

const wait = (hash: `0x${string}`) =>
  publicClient.waitForTransactionReceipt({ hash });

// Sample investors (addresses only; no keys needed, the issuer mints to them).
const plan = [
  { name: "A", wallet: getAddress("0x70997970C51812dc3A010C7d01b50e0d17dc79C8"), shares: 500n },
  { name: "B", wallet: getAddress("0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"), shares: 120n },
  { name: "C", wallet: getAddress("0x90F79bf6EB2c4f870365E785982E1f101E93b906"), shares: 380n },
  { name: "D", wallet: getAddress("0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"), shares: 60n },
];

const blockBefore = await publicClient.getBlockNumber();
const fund = await viem.deployContract("FundShare");
console.log("FundShare deployed at", fund.address);

for (const p of plan) {
  await wait(await fund.write.addToWhitelist([p.wallet]));
  console.log("whitelisted", p.name, p.wallet);
}
for (const p of plan) {
  await wait(await fund.write.subscribe([p.wallet, p.shares]));
  console.log("minted", p.shares.toString(), "to", p.name);
}

const wallets: Record<string, string> = {};
for (const p of plan) wallets[p.name] = p.wallet;

const out = {
  network: "sepolia",
  rpcUrl: process.env.SEPOLIA_RPC_URL ?? "",
  contractAddress: fund.address,
  deployBlock: Number(blockBefore),
  issuer: getAddress(issuer.account.address),
  wallets,
};

const here = dirname(fileURLToPath(import.meta.url));
const dataDir = resolve(here, "..", "..", "data");
mkdirSync(dataDir, { recursive: true });
writeFileSync(
  resolve(dataDir, "chain-config.sepolia.json"),
  JSON.stringify(out, null, 2),
);

console.log("Total supply", await fund.read.totalSupply());
console.log("Etherscan: https://sepolia.etherscan.io/address/" + fund.address);