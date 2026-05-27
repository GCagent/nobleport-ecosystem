# NoblePort Systems - Complete Deployment Guide

**Version:** 2.0 - Viral Lottery + Legal Documentation
**Date:** November 29, 2025
**Status:** Construction OS launch — token offering pending counsel review

## Overview

This deployment package contains the complete NoblePort Systems ecosystem with the newly integrated Viral Lottery App and the legal documentation for the 236 High Rd, Newbury, MA property tokenization.

## What's Included

### 1. NoblePort Ultimate Production Ecosystem

The main production-ready NoblePort dashboard with all core features:

- **Main Dashboard** (`index.html`): Central hub with links to all subsystems
- **DeFi Analytics Dashboard** (`dashboards/defi-dashboard.html`): Real-time pool vs token metrics
- **Essex County Properties** (`dashboards/essex-county.html`): Real estate portfolio viewer
- **Viral Lottery App** (`dashboards/lottery.html`): **NEW** - $5 entry, 5-person referral requirement
- **Operations Monitor** (`operations-monitor/index.html`): Live system metrics
- **Tokenomics Documentation** (`tokenomics/`): Ultra-scarce NBPT model with 100M fixed supply
- **Stephanie.ai Voice** (`ai-voices/stephanie_ai_boston_intro.wav`): Orchestration assistant introduction

### 2. Viral Lottery App Features

**Exact Mechanics as Specified:**
- **$5 Entry Fee**: Single, simple entry price
- **Mandatory 5-Person Referral**: Users must share their unique link with 5 people to unlock lottery entry
- **First 100 Participants**: Eligible for $500 reward (subject to terms)
- **$2,500 Grand Prize Pool**: All winners enter drawing to help build the platform
- **Unique Referral Tracking**: Each participant gets a personalized invite link
- **Live Stats Dashboard**: Real-time participant count, spots remaining, qualified winners, total referrals

**Technical Implementation:**
- Referral code generation using localStorage (production version would use backend database)
- Modal-based entry flow with wallet address and email collection
- Simulated live updates every 15 seconds
- Responsive design for mobile and desktop
- Integration with NoblePort.eth wallet: `0xc59e66BB2b6E19699F82A72a1569821cb1711504`

### 3. 236 High Rd Legal Documentation Kit

Complete legal package for property tokenization:

- **Operating Agreement** (`236_High_Rd_Operating_Agreement.md`): MA LLC agreement for NBPT 236 HIGH ROAD LLC
- **SEC Form D** (`form_d.pdf`): Official SEC form for Regulation D offering (must file within 15 days of first sale)
- **IPFS Anchoring Script** (`ipfs_anchor.sh`): Decentralized storage on IPFS
- **Arweave Anchoring Script** (`arweave_anchor.sh`): Permanent storage on Arweave
- **README** (`README.md`): Step-by-step guide for legal compliance

## Deployment Instructions

### Option 1: Static Hosting (Recommended for Quick Launch)

1. **Extract the Package:**
   ```bash
   unzip nobleport-complete-with-lottery-and-legal.zip
   cd nobleport-ultimate
   ```

2. **Deploy to Static Host:**
   - **Netlify**: Drag and drop the `nobleport-ultimate` folder to Netlify
   - **Vercel**: Run `vercel --prod` in the `nobleport-ultimate` directory
   - **GitHub Pages**: Push to a GitHub repo and enable Pages
   - **IPFS**: Use `ipfs add -r nobleport-ultimate` for decentralized hosting

3. **Update ENS Records:**
   - Point `nobleport.eth` to your deployment URL
   - Add IPFS CID to ENS content hash for decentralized access
   - Set Solana address record (see [ENS-Solana Setup](#ens-solana-setup) below)

### Option 2: Full-Stack Deployment (For Production Backend)

1. **Backend Setup:**
   ```bash
   # Install dependencies
   npm install express cors sqlite3
   
   # Create backend for referral tracking
   node backend/server.js
   ```

2. **Database Configuration:**
   - Set up PostgreSQL or MongoDB for referral tracking
   - Store: user wallets, referral codes, referral counts, reward eligibility

3. **Smart Contract Integration:**
   - Deploy NBPT token contract (ERC-1400 compliant)
   - Deploy lottery reward distribution contract
   - Connect frontend to Web3 provider (MetaMask, WalletConnect)

4. **Payment Integration:**
   - Integrate Stripe for $5 credit card payments
   - Integrate multi-chain USDC support (ETH, ARB, BASE, MATIC, OP, AVAX)
   - Set up payment webhooks for automatic lottery entry

### Option 3: Replit Deployment (Easiest for Testing)

1. **Import to Replit:**
   - Create new Repl
   - Upload `nobleport-complete-with-lottery-and-legal.zip`
   - Extract files

2. **Configure Replit:**
   - Set up `.replit` file to serve `nobleport-ultimate/index.html`
   - Enable "Always On" for 24/7 availability
   - Use Replit Database for referral tracking

3. **Publish:**
   - Click "Publish" in Replit
   - Get public URL
   - Update ENS records

## Legal Compliance Steps

### For 236 High Rd Property Tokenization:

1. **Execute Operating Agreement:**
   - NoblePort Systems LLC signs as sole member
   - Store executed copy with corporate records

2. **Anchor Documents to Blockchain:**
   ```bash
   cd 236_high_rd_legal_kit
   chmod +x ipfs_anchor.sh arweave_anchor.sh
   ./ipfs_anchor.sh
   ./arweave_anchor.sh
   ```

3. **Update ENS TXT Records:**
   ```
   nobleport.eth TXT "operating-agreement-ipfs=<CID>"
   nobleport.eth TXT "operating-agreement-arweave=<TX_ID>"
   ```

4. **File Form D with SEC:**
   - Complete all fields in `form_d.pdf`
   - File electronically via EDGAR within 15 days of first sale
   - Requires SEC EDGAR access codes (CIK, CCC)

5. **Implement zkSBT Verification:**
   - Deploy zkSBT smart contract for accredited investor verification
   - Integrate with lottery app to gate $500+ rewards
   - Maintain privacy while ensuring compliance

## Testing Checklist

- [ ] Main dashboard loads correctly
- [ ] All navigation links work
- [ ] Lottery app displays properly
- [ ] Referral link generation works
- [ ] Referral tracking updates correctly
- [ ] Payment modal displays
- [ ] Stats update in real-time
- [ ] Mobile responsive design works
- [ ] Stephanie.ai voice plays
- [ ] DeFi dashboard loads data
- [ ] Operations monitor shows metrics

## Launch Sequence (Per Legal Review)

### Phase 1 — Construction OS (LAUNCH FIRST)
- Lead → Estimate → Deposit → Permit → Build → Invoice → Closeout
- Terms of service, privacy policy, WISP
- HIC-compliant contract templates
- Human review gates and audit logs
- Payment processor integration

### Phase 2 — Web3 Infrastructure (COUNSEL REQUIRED)
- DocumentRegistry and AuditBeacon
- Wallet read-only intelligence
- OFAC screening
- USDC treasury reporting
- Non-custodial receipts

### Phase 3 — Securities Package (COUNSEL MUST SIGN OFF)
- PPM, subscription agreement, investor questionnaire
- Form D, Blue Sky review
- Transfer restrictions, KYC vendor
- Cap table / transfer agent logic

### Phase 4 — Regulated Expansion (SERIOUS CAPITAL + COUNSEL)
- NY BitLicense or partner path review
- Broker-dealer / ATS analysis
- Custody structure
- Security token transfer infrastructure

## Key Metrics to Track

- **Lottery Participants**: Target 100+ in first wave
- **Referral Conversion**: Track 5-person referral completion rate
- **Early Adopter Rewards**: $500 × 100 (subject to terms)
- **Grand Prize Pool**: $2,500 for platform development
- **Token Status**: Monitor mainnet deployment and compliance

## ENS-Solana Setup

Link `nobleport.eth` to the verified Solana payment rail address so
that ENS-aware wallets and dApps can resolve the Solana destination.

### Option A: Manual (ENS Manager App)

1. Go to [app.ens.domains](https://app.ens.domains)
2. Connect the wallet that controls `nobleport.eth`
3. Navigate to **nobleport.eth → Records → Addresses**
4. Add coin type **SOL (501)**
5. Paste: `6fbr88Qmc1LSh5XATjcaGzvVnq1H7QmB57wAyxrKMXas`
6. Save and confirm the transaction

### Option B: Script

```bash
npm install ethers bs58
export ETH_RPC_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"
export ENS_OWNER_PRIVATE_KEY="..."  # controller of nobleport.eth
node scripts/ens-solana-setup.js
```

### Verify

```bash
export ETH_RPC_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"
node scripts/verify-ens-solana.js
```

Expected output:
```
ENS name:  nobleport.eth
ETH addr:  0xc59e66BB2b6E19699F82A72a1569821cb1711504
SOL addr:  6fbr88Qmc1LSh5XATjcaGzvVnq1H7QmB57wAyxrKMXas
STATUS:    MATCH — record is correct
```

### Cross-Chain Registry

All chain addresses and ENS record targets are tracked in
`scripts/chain-registry.json`. Update this file whenever addresses
change so that the verification script and downstream services stay
in sync.

## Support & Resources

- **NoblePort.eth**: Main gateway
- **Ethereum Wallet**: `0xc59e66BB2b6E19699F82A72a1569821cb1711504`
- **Solana Rail**: `6fbr88Qmc1LSh5XATjcaGzvVnq1H7QmB57wAyxrKMXas`
- **NBPT Token Contract**: `0x3778E67655Ec26D6bC8294C6F7a1e754AFD2C91C`
- **Discord**: [Create invite link]
- **Telegram**: [Create channel]
- **Twitter**: @NoblePortSystems

## Security Considerations

1. **Smart Contract Security:**
   - Audit all contracts before deployment
   - Use OpenZeppelin libraries
   - Implement emergency pause functionality

2. **Data Privacy:**
   - Use zkSBTs for accredited investor verification
   - Encrypt sensitive user data
   - Comply with GDPR and CCPA

3. **Financial Security:**
   - Use Gnosis Safe for treasury management
   - Implement multi-sig for large transactions
   - Regular security audits

## Next Steps

1. **Deploy the lottery app** to start viral growth
2. **Execute legal documents** for 236 High Rd property
3. **Anchor to IPFS/Arweave** for permanent record
4. **File Form D** after first token sale
5. **Prepare token infrastructure** — pending securities counsel review

---

**Built with AI Speed Vibe Coding™**
**Powered by Stephanie.ai • NoblePort Systems • Ultra-Scarce NBPT**
