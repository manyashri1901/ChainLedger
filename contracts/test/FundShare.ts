import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { network } from "hardhat";
import { getAddress } from "viem";

describe("FundShare", async function () {
  const { viem } = await network.create();

  async function deployFundShare() {
    const [issuer, alice, bob] = await viem.getWalletClients();
    const fundShare = await viem.deployContract("FundShare");
    return { fundShare, issuer, alice, bob };
  }

  it("mints on subscribe and increases totalSupply and balance", async function () {
    const { fundShare, alice } = await deployFundShare();
    const aliceAddress = getAddress(alice.account.address);

    await fundShare.write.addToWhitelist([aliceAddress]);
    await fundShare.write.subscribe([aliceAddress, 1000n]);

    assert.equal(await fundShare.read.totalSupply(), 1000n);
    assert.equal(await fundShare.read.balanceOf([aliceAddress]), 1000n);
  });

  it("burns on redeem and decreases totalSupply and balance", async function () {
    const { fundShare, alice } = await deployFundShare();
    const aliceAddress = getAddress(alice.account.address);

    await fundShare.write.addToWhitelist([aliceAddress]);
    await fundShare.write.subscribe([aliceAddress, 1000n]);
    await fundShare.write.redeem([aliceAddress, 400n]);

    assert.equal(await fundShare.read.totalSupply(), 600n);
    assert.equal(await fundShare.read.balanceOf([aliceAddress]), 600n);
  });

  it("allows transfer between two whitelisted addresses", async function () {
    const { fundShare, alice, bob } = await deployFundShare();
    const aliceAddress = getAddress(alice.account.address);
    const bobAddress = getAddress(bob.account.address);

    await fundShare.write.addToWhitelist([aliceAddress]);
    await fundShare.write.addToWhitelist([bobAddress]);
    await fundShare.write.subscribe([aliceAddress, 1000n]);

    const aliceFundShare = await viem.getContractAt("FundShare", fundShare.address, {
      client: { wallet: alice },
    });
    await aliceFundShare.write.transfer([bobAddress, 300n]);

    assert.equal(await fundShare.read.balanceOf([aliceAddress]), 700n);
    assert.equal(await fundShare.read.balanceOf([bobAddress]), 300n);
  });

  it("reverts transfer to a non-whitelisted address", async function () {
    const { fundShare, alice, bob } = await deployFundShare();
    const aliceAddress = getAddress(alice.account.address);
    const bobAddress = getAddress(bob.account.address);

    await fundShare.write.addToWhitelist([aliceAddress]);
    await fundShare.write.subscribe([aliceAddress, 1000n]);

    const aliceFundShare = await viem.getContractAt("FundShare", fundShare.address, {
      client: { wallet: alice },
    });

    await viem.assertions.revertWithCustomError(
      aliceFundShare.write.transfer([bobAddress, 300n]),
      fundShare,
      "NotWhitelisted",
    );
  });

  it("reverts transfer from a non-whitelisted address", async function () {
    const { fundShare, issuer, alice, bob } = await deployFundShare();
    const aliceAddress = getAddress(alice.account.address);
    const bobAddress = getAddress(bob.account.address);

    // Whitelist alice long enough to receive shares, then remove her before
    // she tries to send them on.
    await fundShare.write.addToWhitelist([aliceAddress]);
    await fundShare.write.addToWhitelist([bobAddress]);
    await fundShare.write.subscribe([aliceAddress, 1000n]);
    await fundShare.write.removeFromWhitelist([aliceAddress]);

    const aliceFundShare = await viem.getContractAt("FundShare", fundShare.address, {
      client: { wallet: alice },
    });

    await viem.assertions.revertWithCustomError(
      aliceFundShare.write.transfer([bobAddress, 300n]),
      fundShare,
      "NotWhitelisted",
    );
  });

  it("reverts any transfer while frozen", async function () {
    const { fundShare, alice, bob } = await deployFundShare();
    const aliceAddress = getAddress(alice.account.address);
    const bobAddress = getAddress(bob.account.address);

    await fundShare.write.addToWhitelist([aliceAddress]);
    await fundShare.write.addToWhitelist([bobAddress]);
    await fundShare.write.subscribe([aliceAddress, 1000n]);
    await fundShare.write.freeze();

    const aliceFundShare = await viem.getContractAt("FundShare", fundShare.address, {
      client: { wallet: alice },
    });

    await viem.assertions.revertWithCustomError(
      aliceFundShare.write.transfer([bobAddress, 300n]),
      fundShare,
      "TransfersFrozen",
    );
  });

  it("reverts mint (subscribe) to a non-whitelisted address", async function () {
    const { fundShare, bob } = await deployFundShare();
    const bobAddress = getAddress(bob.account.address);

    await viem.assertions.revertWithCustomError(
      fundShare.write.subscribe([bobAddress, 1000n]),
      fundShare,
      "NotWhitelisted",
    );
  });

  it("prevents a non-issuer from minting", async function () {
    const { fundShare, alice, bob } = await deployFundShare();
    const aliceAddress = getAddress(alice.account.address);
    const bobAddress = getAddress(bob.account.address);

    await fundShare.write.addToWhitelist([bobAddress]);

    const aliceFundShare = await viem.getContractAt("FundShare", fundShare.address, {
      client: { wallet: alice },
    });

    await viem.assertions.revertWithCustomError(
      aliceFundShare.write.subscribe([bobAddress, 1000n]),
      fundShare,
      "NotIssuer",
    );
  });

  it("prevents a non-issuer from burning", async function () {
    const { fundShare, alice, bob } = await deployFundShare();
    const bobAddress = getAddress(bob.account.address);

    await fundShare.write.addToWhitelist([bobAddress]);
    await fundShare.write.subscribe([bobAddress, 1000n]);

    const aliceFundShare = await viem.getContractAt("FundShare", fundShare.address, {
      client: { wallet: alice },
    });

    await viem.assertions.revertWithCustomError(
      aliceFundShare.write.redeem([bobAddress, 500n]),
      fundShare,
      "NotIssuer",
    );
  });

  it("prevents a non-issuer from modifying the whitelist", async function () {
    const { fundShare, alice, bob } = await deployFundShare();
    const aliceAddress = getAddress(alice.account.address);
    const bobAddress = getAddress(bob.account.address);

    const aliceFundShare = await viem.getContractAt("FundShare", fundShare.address, {
      client: { wallet: alice },
    });

    await viem.assertions.revertWithCustomError(
      aliceFundShare.write.addToWhitelist([bobAddress]),
      fundShare,
      "NotIssuer",
    );
    await viem.assertions.revertWithCustomError(
      aliceFundShare.write.removeFromWhitelist([bobAddress]),
      fundShare,
      "NotIssuer",
    );
  });
});
