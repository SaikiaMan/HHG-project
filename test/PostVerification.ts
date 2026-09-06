import { expect } from "chai";
import { network } from "hardhat";

describe("PostVerification", function () {

  it("Should store and verify a hash", async function () {

    const { ethers } = await network.create();

    const contract =
      await ethers.deployContract("PostVerification");

    const hash =
      "0x1234000000000000000000000000000000000000000000000000000000000000";

    await contract.storeHash(hash);

    const result =
      await contract.verifyHash(hash);

    expect(result).to.equal(true);
  });

  it("Should reject a modified hash", async function () {

    const { ethers } = await network.create();

    const contract =
      await ethers.deployContract("PostVerification");

    const originalHash =
      "0x1234000000000000000000000000000000000000000000000000000000000000";

    const modifiedHash =
      "0x1235000000000000000000000000000000000000000000000000000000000000";

    await contract.storeHash(originalHash);

    const result =
      await contract.verifyHash(modifiedHash);

    expect(result).to.equal(false);
  });

});