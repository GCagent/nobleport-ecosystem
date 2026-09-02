#!/usr/bin/env bash
# ============================================================
# NOBLEPORT SOVEREIGN STACK — Full Deployment Script
# ============================================================
# Orchestrates: DNS → SSL → Docker → ENS → IPFS → Verify
#
# Usage:
#   ./deploy-sovereign-stack.sh              # Interactive full deploy
#   ./deploy-sovereign-stack.sh --preflight  # Preflight checks only
#   ./deploy-sovereign-stack.sh --docker     # Docker stack only
#   ./deploy-sovereign-stack.sh --dns        # DNS setup guide only
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$INFRA_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${CYAN}[DEPLOY]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }
header() { echo -e "\n${BOLD}═══ $1 ═══${NC}\n"; }

# ── Preflight ────────────────────────────────────────────────
preflight() {
    header "PREFLIGHT CHECKS"

    local passed=0
    local failed=0

    # Docker
    if command -v docker >/dev/null 2>&1; then
        ok "Docker installed: $(docker --version | head -1)"
        ((passed++))
    else
        err "Docker not installed"
        ((failed++))
    fi

    # Docker Compose
    if docker compose version >/dev/null 2>&1; then
        ok "Docker Compose installed: $(docker compose version | head -1)"
        ((passed++))
    else
        err "Docker Compose not installed"
        ((failed++))
    fi

    # Node.js
    if command -v node >/dev/null 2>&1; then
        ok "Node.js installed: $(node --version)"
        ((passed++))
    else
        err "Node.js not installed"
        ((failed++))
    fi

    # Nginx
    if command -v nginx >/dev/null 2>&1; then
        ok "Nginx installed: $(nginx -v 2>&1)"
        ((passed++))
    else
        warn "Nginx not installed (will use Docker container)"
    fi

    # Certbot
    if command -v certbot >/dev/null 2>&1; then
        ok "Certbot installed"
        ((passed++))
    else
        warn "Certbot not installed — SSL certs must be configured manually"
    fi

    # IPFS
    if command -v ipfs >/dev/null 2>&1; then
        ok "IPFS installed: $(ipfs version)"
        ((passed++))
    else
        warn "IPFS not installed — IPFS deployment will be skipped"
    fi

    # .env file
    if [ -f "$ROOT_DIR/.env" ]; then
        ok ".env file found"
        ((passed++))

        # Check required vars
        for var in ETHEREUM_RPC_URL REDIS_PASSWORD; do
            if grep -q "^${var}=" "$ROOT_DIR/.env"; then
                ok "  $var is set"
            else
                warn "  $var is NOT set"
            fi
        done
    else
        warn "No .env file — creating template..."
        create_env_template
    fi

    echo ""
    log "Passed: $passed | Failed: $failed"

    if [ "$failed" -gt 0 ]; then
        err "Fix $failed failed check(s) before deploying"
        return 1
    fi

    ok "All preflight checks passed"
}

# ── Environment Template ─────────────────────────────────────
create_env_template() {
    cat > "$ROOT_DIR/.env.template" << 'ENVEOF'
# ============================================================
# NOBLEPORT SOVEREIGN STACK — Environment Variables
# ============================================================
# Copy to .env and fill in values:
#   cp .env.template .env
# ============================================================

# ── Ethereum / ENS ──────────────────────────────────────────
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
DEPLOYER_PRIVATE_KEY=0x_YOUR_DEPLOYER_PRIVATE_KEY
RESOLVER_ADDRESS=0x_DEPLOYED_RESOLVER_CONTRACT
ENS_REGISTRY=0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e

# ── Infrastructure ──────────────────────────────────────────
VULTR_GATEWAY_IP=YOUR_VULTR_VPS_IP
HETZNER_STORAGE_IP=YOUR_HETZNER_IP
MEDIA_SERVER_IP=YOUR_MEDIA_SERVER_IP

# ── Redis ────────────────────────────────────────────────────
REDIS_PASSWORD=CHANGE_ME_STRONG_PASSWORD

# ── Monitoring ───────────────────────────────────────────────
GRAFANA_PASSWORD=CHANGE_ME_GRAFANA_PASSWORD

# ── Cloudflare ───────────────────────────────────────────────
CLOUDFLARE_API_TOKEN=YOUR_CF_API_TOKEN
CLOUDFLARE_ZONE_ID=YOUR_CF_ZONE_ID

# ── IPFS Pinning ─────────────────────────────────────────────
PINATA_API_KEY=YOUR_PINATA_KEY
PINATA_SECRET=YOUR_PINATA_SECRET
ENVEOF

    ok "Template created at .env.template"
}

# ── DNS Setup Guide ──────────────────────────────────────────
dns_setup() {
    header "DNS CONFIGURATION GUIDE"

    echo "1. Transfer domain to Cloudflare Registrar"
    echo "   https://dash.cloudflare.com → Add Site → nobleport.com"
    echo ""
    echo "2. Import DNS zone file:"
    echo "   Dashboard → DNS → Import DNS Records"
    echo "   File: infrastructure/dns/cloudflare-zone.conf"
    echo ""
    echo "3. Replace placeholder IPs in zone file:"
    echo "   - VULTR_GATEWAY_IP  → Your Vultr VPS IP"
    echo "   - HETZNER_STORAGE_IP → Your Hetzner IP"
    echo "   - MEDIA_SERVER_IP    → Your streaming server IP"
    echo ""
    echo "4. Apply Cloudflare security settings:"
    echo "   Reference: infrastructure/cloudflare/settings.json"
    echo "   - SSL → Full (Strict)"
    echo "   - Always HTTPS → ON"
    echo "   - WAF → ON"
    echo "   - Bot Management → ON"
    echo "   - Min TLS Version → 1.2"
    echo ""
    echo "5. Create firewall rules (see settings.json → firewall_rules)"
    echo ""
    echo "6. Configure page rules (see settings.json → page_rules)"
}

# ── Docker Deployment ────────────────────────────────────────
deploy_docker() {
    header "DEPLOYING DOCKER STACK"

    cd "$INFRA_DIR/docker"

    log "Pulling latest images..."
    docker compose pull

    log "Starting sovereign stack..."
    docker compose up -d

    log "Waiting for health checks..."
    sleep 10

    # Check service health
    local services=("nobleport-gateway" "nobleport-redis" "nobleport-ipfs" "nobleport-nginx")
    for svc in "${services[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "$svc"; then
            ok "$svc is running"
        else
            warn "$svc is not running"
        fi
    done

    docker compose ps
}

# ── Full Deployment ──────────────────────────────────────────
full_deploy() {
    header "NOBLEPORT SOVEREIGN STACK DEPLOYMENT"

    echo "This will deploy the complete NoblePort infrastructure:"
    echo "  1. Preflight checks"
    echo "  2. DNS configuration guide"
    echo "  3. Docker stack deployment"
    echo "  4. IPFS pinning (if available)"
    echo "  5. Verification"
    echo ""

    # Step 1
    preflight || return 1

    # Step 2
    dns_setup

    # Step 3
    deploy_docker

    # Step 4: IPFS
    if command -v ipfs >/dev/null 2>&1; then
        header "IPFS DEPLOYMENT"
        bash "$INFRA_DIR/ipfs/deploy-ipfs.sh" --pin-only
    else
        warn "Skipping IPFS deployment (ipfs not installed)"
    fi

    # Step 5: Summary
    header "DEPLOYMENT SUMMARY"
    echo "============================================================"
    echo "  NOBLEPORT SOVEREIGN STACK — DEPLOYED"
    echo "============================================================"
    echo ""
    echo "  SERVICES:"
    echo "    Gateway Brain:    http://localhost:8080"
    echo "    Stephanie Stream: http://localhost:8081"
    echo "    WebSocket:        http://localhost:8082"
    echo "    IPFS Gateway:     http://localhost:8083"
    echo "    Redis:            localhost:6379"
    echo "    Prometheus:       http://localhost:9090"
    echo "    Grafana:          http://localhost:3000"
    echo ""
    echo "  SUBDOMAINS (configure in Cloudflare):"
    echo "    app.nobleport.com    → Frontend (Vercel)"
    echo "    api.nobleport.com    → Gateway Brain"
    echo "    dao.nobleport.com    → Governance"
    echo "    stream.nobleport.com → Stephanie.ai"
    echo "    invest.nobleport.com → Investor Portal"
    echo "    build.nobleport.com  → GCagent UI"
    echo "    permit.nobleport.com → PermitStream"
    echo "    docs.nobleport.com   → Documentation"
    echo ""
    echo "  ENS: nobleport.eth"
    echo "    Deploy resolver: node infrastructure/ens/deploy-ens.js"
    echo ""
    echo "  NEXT STEPS:"
    echo "    1. Fill in .env (from .env.template)"
    echo "    2. Import DNS zone to Cloudflare"
    echo "    3. Apply Cloudflare security settings"
    echo "    4. Deploy ENS resolver contract"
    echo "    5. Register ENS subdomains"
    echo "    6. Deploy IPFS frontend"
    echo "============================================================"
}

# ── Main ─────────────────────────────────────────────────────
case "${1:-}" in
    --preflight) preflight ;;
    --dns)       dns_setup ;;
    --docker)    deploy_docker ;;
    *)           full_deploy ;;
esac
