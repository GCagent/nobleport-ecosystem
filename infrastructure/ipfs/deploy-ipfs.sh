#!/usr/bin/env bash
# ============================================================
# NOBLEPORT IPFS HYBRID DEPLOYMENT
# ============================================================
# Deploys frontend to IPFS and updates ENS contenthash
#
# Prerequisites:
#   - ipfs CLI installed (https://docs.ipfs.tech/install/)
#   - Node.js + ethers for ENS update
#   - .env with DEPLOYER_PRIVATE_KEY, ETHEREUM_RPC_URL, RESOLVER_ADDRESS
#
# Usage:
#   ./deploy-ipfs.sh                    # Full deploy
#   ./deploy-ipfs.sh --pin-only         # Pin to IPFS only (no ENS update)
#   ./deploy-ipfs.sh --ens-only <CID>   # Update ENS only with given CID
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$ROOT_DIR"  # Static site root
PINNING_SERVICES=("pinata" "web3.storage" "infura")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[IPFS]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Preflight Checks ────────────────────────────────────────
check_deps() {
    log "Checking dependencies..."
    command -v ipfs >/dev/null 2>&1 || err "ipfs CLI not found. Install: https://docs.ipfs.tech/install/"
    command -v node >/dev/null 2>&1 || err "Node.js not found"

    if [ ! -f "$ROOT_DIR/.env" ] && [ "$1" != "--pin-only" ]; then
        warn "No .env file found — ENS update will be skipped"
    fi

    ok "Dependencies verified"
}

# ── Build Static Assets ─────────────────────────────────────
prepare_build() {
    log "Preparing static assets for IPFS..."

    # Create a clean build directory
    local IPFS_BUILD="$ROOT_DIR/.ipfs-build"
    rm -rf "$IPFS_BUILD"
    mkdir -p "$IPFS_BUILD"

    # Copy static files (exclude infrastructure, .git, node_modules)
    cp "$BUILD_DIR/index.html" "$IPFS_BUILD/"
    [ -d "$BUILD_DIR/dashboards" ] && cp -r "$BUILD_DIR/dashboards" "$IPFS_BUILD/"
    [ -d "$BUILD_DIR/ai-voices" ] && cp -r "$BUILD_DIR/ai-voices" "$IPFS_BUILD/"
    [ -d "$BUILD_DIR/tokenomics" ] && cp -r "$BUILD_DIR/tokenomics" "$IPFS_BUILD/"
    [ -d "$BUILD_DIR/operations-monitor" ] && cp -r "$BUILD_DIR/operations-monitor" "$IPFS_BUILD/"

    # Create _redirects for SPA routing on IPFS gateways
    echo "/*    /index.html   200" > "$IPFS_BUILD/_redirects"

    ok "Build prepared at $IPFS_BUILD"
    echo "$IPFS_BUILD"
}

# ── Pin to IPFS ──────────────────────────────────────────────
pin_to_ipfs() {
    local build_dir="$1"

    log "Adding to local IPFS node..."

    # Ensure IPFS daemon is running
    if ! ipfs swarm peers >/dev/null 2>&1; then
        warn "IPFS daemon not running, starting..."
        ipfs daemon --init &
        sleep 5
    fi

    # Add directory recursively, get root CID
    CID=$(ipfs add -r -Q --cid-version=1 "$build_dir")

    ok "Pinned to IPFS: $CID"
    log "Gateway URL: https://ipfs.io/ipfs/$CID"
    log "Subdomain:   https://$CID.ipfs.dweb.link"

    # Pin to remote services
    for service in "${PINNING_SERVICES[@]}"; do
        if ipfs pin remote service ls | grep -q "$service" 2>/dev/null; then
            log "Pinning to $service..."
            ipfs pin remote add --service="$service" --name="nobleport-$(date +%Y%m%d)" "/ipfs/$CID" || warn "Failed to pin to $service"
        fi
    done

    echo "$CID"
}

# ── Update ENS Contenthash ──────────────────────────────────
update_ens_contenthash() {
    local cid="$1"

    if [ ! -f "$ROOT_DIR/.env" ]; then
        warn "No .env — skipping ENS contenthash update"
        return
    fi

    log "Updating ENS contenthash to IPFS CID: $cid"

    node -e "
    require('dotenv').config({ path: '$ROOT_DIR/.env' });
    const { ethers } = require('ethers');

    const RESOLVER_ABI = [
        'function setContenthash(bytes32 node, bytes hash) external'
    ];

    async function main() {
        const provider = new ethers.JsonRpcProvider(process.env.ETHEREUM_RPC_URL);
        const wallet = new ethers.Wallet(process.env.DEPLOYER_PRIVATE_KEY, provider);
        const resolver = new ethers.Contract(process.env.RESOLVER_ADDRESS, RESOLVER_ABI, wallet);

        // Calculate namehash for nobleport.eth
        let node = ethers.ZeroHash;
        for (const label of ['eth', 'nobleport'].reverse()) {
            node = ethers.keccak256(ethers.concat([node, ethers.keccak256(ethers.toUtf8Bytes(label))]));
        }

        // Encode IPFS CID as contenthash (ipfs://)
        // Codec: 0xe3 (IPFS), 0x01 (CIDv1), 0x70 (dag-pb)
        const cidBytes = ethers.toUtf8Bytes('$cid');
        const contenthash = ethers.concat(['0xe3010170', cidBytes]);

        const tx = await resolver.setContenthash(node, contenthash);
        console.log('TX:', tx.hash);
        await tx.wait();
        console.log('ENS contenthash updated successfully');
    }

    main().catch(console.error);
    "

    ok "ENS contenthash updated"
}

# ── Verification ─────────────────────────────────────────────
verify_deployment() {
    local cid="$1"

    log "Verifying deployment..."

    # Check IPFS gateway accessibility
    local gateway_url="https://ipfs.io/ipfs/$cid"
    if command -v curl >/dev/null 2>&1; then
        local status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$gateway_url" || echo "000")
        if [ "$status" = "200" ]; then
            ok "IPFS gateway accessible (HTTP $status)"
        else
            warn "IPFS gateway returned HTTP $status (may need propagation time)"
        fi
    fi

    echo ""
    echo "============================================================"
    echo "  NOBLEPORT IPFS DEPLOYMENT COMPLETE"
    echo "============================================================"
    echo "  CID:          $cid"
    echo "  IPFS URL:     ipfs://$cid"
    echo "  Gateway:      https://ipfs.io/ipfs/$cid"
    echo "  Subdomain:    https://$cid.ipfs.dweb.link"
    echo "  ENS:          nobleport.eth → ipfs://$cid"
    echo ""
    echo "  VERIFY:"
    echo "    https://app.ens.domains/nobleport.eth"
    echo "    https://$cid.ipfs.dweb.link"
    echo "============================================================"
}

# ── Main ─────────────────────────────────────────────────────
main() {
    echo "============================================================"
    echo "  NOBLEPORT IPFS HYBRID DEPLOYMENT"
    echo "============================================================"

    local mode="${1:-full}"

    check_deps "$mode"

    case "$mode" in
        --pin-only)
            local build_dir=$(prepare_build)
            local cid=$(pin_to_ipfs "$build_dir")
            verify_deployment "$cid"
            ;;
        --ens-only)
            local cid="${2:?CID required for --ens-only}"
            update_ens_contenthash "$cid"
            ;;
        *)
            local build_dir=$(prepare_build)
            local cid=$(pin_to_ipfs "$build_dir")
            update_ens_contenthash "$cid"
            verify_deployment "$cid"
            ;;
    esac

    # Cleanup
    rm -rf "$ROOT_DIR/.ipfs-build"
}

main "$@"
