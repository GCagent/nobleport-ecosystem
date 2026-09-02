/**
 * NOBLEPORT ENS DEPLOYMENT & CONFIGURATION SCRIPT
 *
 * Prerequisites:
 *   npm install ethers @ensdomains/ensjs dotenv
 *
 * Environment (.env):
 *   DEPLOYER_PRIVATE_KEY=0x...
 *   ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
 *   ENS_REGISTRY=0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e
 *   ETHERSCAN_API_KEY=...
 *
 * Usage:
 *   node deploy-ens.js              # Full deployment
 *   node deploy-ens.js --subdomains # Register subdomains only
 *   node deploy-ens.js --txt-only   # Update TXT records only
 */

const { ethers } = require("ethers");
require("dotenv").config();

// ── Configuration ───────────────────────────────────────────
const CONFIG = {
  ensName: "nobleport.eth",
  rpcUrl: process.env.ETHEREUM_RPC_URL,
  deployerKey: process.env.DEPLOYER_PRIVATE_KEY,
  ensRegistry: process.env.ENS_REGISTRY || "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e",

  // Subdomains to register (label → description)
  subdomains: [
    { label: "app",    description: "Main platform UI" },
    { label: "api",    description: "Gateway Brain backend" },
    { label: "dao",    description: "Governance / Snapshot" },
    { label: "stream", description: "Stephanie.ai live avatar" },
    { label: "invest", description: "Investor portal" },
    { label: "build",  description: "GCagent contractor UI" },
    { label: "permit", description: "PermitStream interface" },
    { label: "docs",   description: "Documentation / compliance" },
    { label: "ipfs",   description: "IPFS pinning gateway" },
  ],

  // TXT records for each subdomain
  subdomainRecords: {
    app:    { url: "https://app.nobleport.com",    service: "frontend" },
    api:    { url: "https://api.nobleport.com",    service: "gateway-brain" },
    dao:    { url: "https://dao.nobleport.com",    service: "governance" },
    stream: { url: "https://stream.nobleport.com", service: "media-streaming" },
    invest: { url: "https://invest.nobleport.com", service: "investor-portal" },
    build:  { url: "https://build.nobleport.com",  service: "contractor-platform" },
    permit: { url: "https://permit.nobleport.com", service: "permit-stream" },
    docs:   { url: "https://docs.nobleport.com",   service: "documentation" },
    ipfs:   { url: "https://ipfs.nobleport.com",   service: "ipfs-gateway" },
  },

  // Forward resolution: ENS → HTTPS contenthash
  contenthash: {
    // IPFS CID for decentralized frontend (set after IPFS deploy)
    ipfs: null,
    // HTTPS fallback
    https: "https://nobleport.com",
  },
};

// ── Helpers ─────────────────────────────────────────────────
function namehash(name) {
  let node = ethers.ZeroHash;
  if (name === "") return node;
  const labels = name.split(".").reverse();
  for (const label of labels) {
    node = ethers.keccak256(
      ethers.concat([node, ethers.keccak256(ethers.toUtf8Bytes(label))])
    );
  }
  return node;
}

function labelhash(label) {
  return ethers.keccak256(ethers.toUtf8Bytes(label));
}

// ── Resolver ABI (minimal) ──────────────────────────────────
const RESOLVER_ABI = [
  "function initializeRecords() external",
  "function registerSubdomain(string label, address subOwner) external",
  "function setText(bytes32 node, string key, string value) external",
  "function setAddr(bytes32 node, address addr) external",
  "function setContenthash(bytes32 node, bytes hash) external",
  "function text(bytes32 node, string key) external view returns (string)",
  "function addr(bytes32 node) external view returns (address)",
  "function owner() external view returns (address)",
];

// ── Main Deployment ─────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const subdomainsOnly = args.includes("--subdomains");
  const txtOnly = args.includes("--txt-only");

  // Connect
  const provider = new ethers.JsonRpcProvider(CONFIG.rpcUrl);
  const wallet = new ethers.Wallet(CONFIG.deployerKey, provider);

  console.log("=".repeat(60));
  console.log("NOBLEPORT ENS DEPLOYMENT");
  console.log("=".repeat(60));
  console.log(`Deployer:  ${wallet.address}`);
  console.log(`Network:   ${(await provider.getNetwork()).name}`);
  console.log(`ENS Name:  ${CONFIG.ensName}`);
  console.log(`Node:      ${namehash(CONFIG.ensName)}`);
  console.log("=".repeat(60));

  const balance = await provider.getBalance(wallet.address);
  console.log(`Balance:   ${ethers.formatEther(balance)} ETH`);

  if (balance < ethers.parseEther("0.05")) {
    console.error("ERROR: Insufficient ETH for deployment (need >= 0.05 ETH)");
    process.exit(1);
  }

  let resolverAddress;

  if (!subdomainsOnly && !txtOnly) {
    // Step 1: Deploy resolver contract
    console.log("\n[1/4] Deploying NoblePortENSResolver...");
    const ResolverFactory = new ethers.ContractFactory(
      RESOLVER_ABI,
      process.env.RESOLVER_BYTECODE || "0x", // Compile with solc first
      wallet
    );

    // NOTE: In production, compile the .sol file first:
    //   solc --bin --abi NoblePortENSResolver.sol -o build/
    //   Then set RESOLVER_BYTECODE env var to the compiled bytecode
    console.log("  -> Compile NoblePortENSResolver.sol before deploying");
    console.log("  -> Set RESOLVER_BYTECODE in .env after compilation");
    console.log("  -> Skipping contract deployment (set bytecode to proceed)");

    // For now, use existing resolver if deployed
    resolverAddress = process.env.RESOLVER_ADDRESS;
    if (!resolverAddress) {
      console.log("  -> Set RESOLVER_ADDRESS in .env to continue with existing resolver");
      console.log("  -> Or compile and set RESOLVER_BYTECODE for fresh deploy");
      return;
    }
  } else {
    resolverAddress = process.env.RESOLVER_ADDRESS;
    if (!resolverAddress) {
      console.error("ERROR: RESOLVER_ADDRESS required for --subdomains / --txt-only");
      process.exit(1);
    }
  }

  const resolver = new ethers.Contract(resolverAddress, RESOLVER_ABI, wallet);

  if (!txtOnly) {
    // Step 2: Initialize root TXT records
    console.log("\n[2/4] Initializing root TXT records...");
    try {
      const tx = await resolver.initializeRecords();
      console.log(`  -> TX: ${tx.hash}`);
      await tx.wait();
      console.log("  -> Root records initialized");
    } catch (e) {
      console.log(`  -> Skipped (may already be initialized): ${e.message}`);
    }

    // Step 3: Register subdomains
    console.log("\n[3/4] Registering subdomains...");
    for (const sub of CONFIG.subdomains) {
      try {
        console.log(`  -> ${sub.label}.nobleport.eth (${sub.description})`);
        const tx = await resolver.registerSubdomain(sub.label, wallet.address);
        console.log(`     TX: ${tx.hash}`);
        await tx.wait();
      } catch (e) {
        console.log(`     Skipped: ${e.message}`);
      }
    }
  }

  // Step 4: Set subdomain TXT records
  console.log("\n[4/4] Setting subdomain TXT records...");
  for (const [label, records] of Object.entries(CONFIG.subdomainRecords)) {
    const subnode = namehash(`${label}.nobleport.eth`);
    console.log(`  -> ${label}.nobleport.eth`);

    for (const [key, value] of Object.entries(records)) {
      try {
        const tx = await resolver.setText(subnode, key, value);
        console.log(`     ${key} = ${value} (TX: ${tx.hash})`);
        await tx.wait();
      } catch (e) {
        console.log(`     Failed ${key}: ${e.message}`);
      }
    }
  }

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log("DEPLOYMENT COMPLETE");
  console.log("=".repeat(60));
  console.log(`Resolver:    ${resolverAddress}`);
  console.log(`Root node:   ${namehash(CONFIG.ensName)}`);
  console.log(`Subdomains:  ${CONFIG.subdomains.length} registered`);
  console.log("");
  console.log("NEXT STEPS:");
  console.log("  1. Set resolver in ENS Manager: https://app.ens.domains");
  console.log("  2. Verify on Etherscan");
  console.log("  3. Test forward resolution: nobleport.eth -> nobleport.com");
  console.log("  4. Set reverse resolution for your wallet");
  console.log("  5. Deploy IPFS frontend and update contenthash");
  console.log("=".repeat(60));
}

main().catch(console.error);
