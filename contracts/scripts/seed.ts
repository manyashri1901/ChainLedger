import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { network } from "hardhat";
import { getAddress } from "viem";

const { viem } = await network.create();
const publicClient = await viem.getPublicClient();
const [issuer, A, B, C, D] = await viem.getWalletClients();

const addr = (w: { account: { address: string } }) =>
  getAddress(w.account.address);

const blockBefore = await publicClient.getBlockNumber();
const fund = await viem.deployContract("FundShare");

for (const w of [A, B, C, D]) {
  await fund.write.addToWhitelist([addr(w)]);
}
await fund.write.subscribe([addr(A), 400n]);
await fund.write.subscribe([addr(B), 120n]);
await fund.write.subscribe([addr(C), 480n]);
await fund.write.subscribe([addr(D), 60n]);

const asC = await viem.getContractAt("FundShare", fund.address, {
  client: { wallet: C },
});
await asC.write.transfer([addr(A), 100n]);

const out = {
  rpcUrl: "http://127.0.0.1:8545",
  contractAddress: fund.address,
  deployBlock: Number(blockBefore) + 1,
  issuer: addr(issuer),
  wallets: { A: addr(A), B: addr(B), C: addr(C), D: addr(D) },
};

const here = dirname(fileURLToPath(import.meta.url));
const dataDir = resolve(here, "..", "..", "data");
mkdirSync(dataDir, { recursive: true });
writeFileSync(resolve(dataDir, "chain-config.json"), JSON.stringify(out, null, 2));

console.log("FundShare deployed at", fund.address);
for (const [name, w] of Object.entries({ A, B, C, D })) {
  const bal = await fund.read.balanceOf([addr(w)]);
  console.log(`${name} ${addr(w)} balance ${bal}`);
}
console.log("Total supply", await fund.read.totalSupply());