/**
 * Read-only verification that nobleport.eth resolves to the expected
 * Solana address. No wallet/signer required — just an RPC endpoint.
 *
 * Usage:
 *   export ETH_RPC_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"
 *   node scripts/verify-ens-solana.js
 */

const { ethers } = require("ethers");
const bs58 = require("bs58");

const ENS_NAME = "nobleport.eth";
const SOLANA_COIN_TYPE = 501;
const EXPECTED_SOLANA = "6fbr88Qmc1LSh5XATjcaGzvVnq1H7QmB57wAyxrKMXas";

const ENS_REGISTRY_ADDRESS = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e";

const REGISTRY_ABI = [
  "function resolver(bytes32 node) external view returns (address)",
];

const RESOLVER_ABI = [
  "function addr(bytes32 node, uint256 coinType) external view returns (bytes memory)",
  "function addr(bytes32 node) external view returns (address)",
];

async function main() {
  const rpcUrl = process.env.ETH_RPC_URL;
  if (!rpcUrl) {
    console.error("Required: ETH_RPC_URL");
    process.exit(1);
  }

  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const namehash = ethers.namehash(ENS_NAME);

  const registry = new ethers.Contract(ENS_REGISTRY_ADDRESS, REGISTRY_ABI, provider);
  const resolverAddress = await registry.resolver(namehash);

  if (resolverAddress === ethers.ZeroAddress) {
    console.log(`${ENS_NAME}: no resolver set`);
    process.exit(1);
  }

  const resolver = new ethers.Contract(resolverAddress, RESOLVER_ABI, provider);

  console.log(`ENS name:  ${ENS_NAME}`);
  console.log(`Resolver:  ${resolverAddress}`);

  const ethAddr = await resolver["addr(bytes32)"](namehash);
  console.log(`ETH addr:  ${ethAddr}`);

  try {
    const solBytes = await resolver["addr(bytes32,uint256)"](namehash, SOLANA_COIN_TYPE);
    if (!solBytes || solBytes === "0x" || ethers.dataLength(solBytes) === 0) {
      console.log("SOL addr:  (not set)");
      process.exit(0);
    }

    const raw = ethers.getBytes(solBytes);
    const solAddr = bs58.encode(Buffer.from(raw));
    console.log(`SOL addr:  ${solAddr}`);

    if (solAddr === EXPECTED_SOLANA) {
      console.log("STATUS:    MATCH — record is correct");
    } else {
      console.log(`STATUS:    MISMATCH — expected ${EXPECTED_SOLANA}`);
    }
  } catch {
    console.log("SOL addr:  resolver does not support multicoin (EIP-2304)");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
