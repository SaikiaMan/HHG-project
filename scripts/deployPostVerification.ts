import { network } from "hardhat";

const { ethers } = await network.create();

const contract = await ethers.deployContract("PostVerification");

await contract.waitForDeployment();

console.log("PostVerification deployed to:");
console.log(await contract.getAddress());