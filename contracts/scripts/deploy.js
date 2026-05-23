const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer:", deployer.address);

  // 1. Deploy zkSBT verifier
  const ZkSBTVerifier = await hre.ethers.getContractFactory("ZkSBTVerifier");
  const zkVerifier = await ZkSBTVerifier.deploy();
  await zkVerifier.waitForDeployment();
  console.log("ZkSBTVerifier:", await zkVerifier.getAddress());

  // 2. Deploy identity registry (linked to zkSBT)
  const IdentityRegistry = await hre.ethers.getContractFactory("IdentityRegistry");
  const identityRegistry = await IdentityRegistry.deploy(await zkVerifier.getAddress());
  await identityRegistry.waitForDeployment();
  console.log("IdentityRegistry:", await identityRegistry.getAddress());

  // 3. Deploy compliance module (linked to identity registry)
  const ModularCompliance = await hre.ethers.getContractFactory("ModularCompliance");
  const compliance = await ModularCompliance.deploy(await identityRegistry.getAddress());
  await compliance.waitForDeployment();
  console.log("ModularCompliance:", await compliance.getAddress());

  // 4. Deploy security token
  const NBPTSecurityToken = await hre.ethers.getContractFactory("NBPTSecurityToken");
  const token = await NBPTSecurityToken.deploy(
    "NoblePort Real Estate Token",
    "NBPT",
    await identityRegistry.getAddress(),
    await compliance.getAddress()
  );
  await token.waitForDeployment();
  console.log("NBPTSecurityToken:", await token.getAddress());

  // 5. Wire compliance to token
  await compliance.setTokenAddress(await token.getAddress());
  console.log("Compliance linked to token");

  // 6. Block OFAC-sanctioned jurisdictions (ISO 3166-1 numeric)
  // Cuba=192, Iran=364, North Korea=408, Syria=760, Crimea=804(UA sub)
  const ofacCountries = [192, 364, 408, 760];
  await compliance.batchBlockCountries(ofacCountries);
  console.log("OFAC countries blocked:", ofacCountries);

  // 7. Set Reg D parameters
  await compliance.setMaxHolders(2000);
  await compliance.setHoldingPeriod(365 * 24 * 60 * 60); // 12-month Rule 144
  console.log("Reg D: max 2000 holders, 12-month holding period");

  console.log("\n=== Deployment complete ===");
  console.log({
    zkVerifier: await zkVerifier.getAddress(),
    identityRegistry: await identityRegistry.getAddress(),
    compliance: await compliance.getAddress(),
    token: await token.getAddress(),
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
