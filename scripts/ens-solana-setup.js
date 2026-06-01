/**
 * Sets the Solana address record on nobleport.eth via the ENS PublicResolver.
 *
 * ENS supports multi-chain address resolution using SLIP-44 coin types.
 * Solana is coin type 501. The resolver stores the raw 32-byte public key.
 *
 * Prerequisites:
 *   npm install ethers @ensdomains/ensjs
 *   export ETH_RPC_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"
 *   export ENS_OWNER_PRIVATE_KEY="..."   # owner of nobleport.eth
 *
 * Usage:
 *   node scripts/ens-solana-setup.js
 *
 * IMPORTANT: This sends an Ethereum mainnet transaction. The signer must
 * be the controller of nobleport.eth. Gas fees apply.
 */

const { ethers } = require("ethers");
const bs58 = require("bs58");

const ENS_NAME = "nobleport.eth";
const SOLANA_COIN_TYPE = 501;
const SOLANA_ADDRESS = "6fbr88Qmc1LSh5XATjcaGzvVnq1H7QmB57wAyxrKMXas";

const ENS_REGISTRY_ADDRESS = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e";

const REGISTRY_ABI = [
  "function resolver(bytes32 node) external view returns (address)",
];

const RESOLVER_ABI = [
  "function setAddr(bytes32 node, uint256 coinType, bytes calldata a) external",
  "function addr(bytes32 node, uint256 coinType) external view returns (bytes memory)",
];

async function main() {
  const rpcUrl = process.env.ETH_RPC_URL;
  const privateKey = process.env.ENS_OWNER_PRIVATE_KEY;

  if (!rpcUrl || !privateKey) {
    console.error("Required env vars: ETH_RPC_URL, ENS_OWNER_PRIVATE_KEY");
    process.exit(1);
  }

  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const wallet = new ethers.Wallet(privateKey, provider);

  console.log(`Signer: ${wallet.address}`);
  console.log(`ENS name: ${ENS_NAME}`);
  console.log(`Solana address: ${SOLANA_ADDRESS}`);

  const solanaBytes = bs58.decode(SOLANA_ADDRESS);
  if (solanaBytes.length !== 32) {
    console.error(`Solana address decodes to ${solanaBytes.length} bytes, expected 32`);
    process.exit(1);
  }

  const namehash = ethers.namehash(ENS_NAME);
  console.log(`Namehash: ${namehash}`);

  const registry = new ethers.Contract(ENS_REGISTRY_ADDRESS, REGISTRY_ABI, provider);
  const resolverAddress = await registry.resolver(namehash);

  if (resolverAddress === ethers.ZeroAddress) {
    console.error(`No resolver set for ${ENS_NAME}. Set one via app.ens.domains first.`);
    process.exit(1);
  }

  console.log(`Resolver: ${resolverAddress}`);

  const resolver = new ethers.Contract(resolverAddress, RESOLVER_ABI, wallet);

  const existing = await resolver.addr(namehash, SOLANA_COIN_TYPE);
  if (existing && existing !== "0x") {
    console.log(`Existing Solana record: 0x${Buffer.from(ethers.getBytes(existing)).toString("hex")}`);
    console.log("Will overwrite with new address.");
  }

  console.log("\nSending setAddr transaction...");
  const tx = await resolver.setAddr(namehash, SOLANA_COIN_TYPE, solanaBytes);
  console.log(`TX hash: ${tx.hash}`);
  console.log("Waiting for confirmation...");

  const receipt = await tx.wait();
  console.log(`Confirmed in block ${receipt.blockNumber}`);
  console.log(`Gas used: ${receipt.gasUsed.toString()}`);

  const verify = await resolver.addr(namehash, SOLANA_COIN_TYPE);
  const verifyHex = Buffer.from(ethers.getBytes(verify)).toString("hex");
  const expectedHex = Buffer.from(solanaBytes).toString("hex");

  if (verifyHex === expectedHex) {
    console.log("\nVerification PASSED — nobleport.eth now resolves to Solana address:");
    console.log(`  ${SOLANA_ADDRESS}`);
  } else {
    console.error("\nVerification FAILED — on-chain record does not match.");
    console.error(`  Expected: ${expectedHex}`);
    console.error(`  Got:      ${verifyHex}`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
