# CLAUDE.md — NoblePort Ecosystem

## Project Overview

NoblePort is a blockchain-powered real estate and construction ecosystem governed by an AI CEO (Stephanie.ai). It consists of static HTML/CSS/JS dashboards, a Python dev server, and tokenomics tooling for the NBPT token (ERC-1400, 100M fixed supply). The platform targets multi-chain DeFi integration across 9 networks (ETH, Arbitrum, Base, Polygon, Optimism, Avalanche, Solana, XRP, Cardano).

## Repository Structure

```
nobleport-ecosystem/
├── index.html                  # Main production dashboard (entry point)
├── server.py                   # Python dev server (port 8080, CORS enabled)
├── package.json                # Node config (v3.0.0, MIT license)
├── netlify.toml                # Netlify deployment config
├── vercel.json                 # Vercel deployment config
├── deployment_metrics.json     # Component status and metrics
├── dashboards/
│   ├── defi-dashboard.html     # DeFi analytics (pools, tokens, APY)
│   ├── lottery.html            # Viral lottery app ($5 entry, 5-person referral)
│   ├── essex-county.html       # Real estate portfolio viewer
│   └── essex-style.css         # Essex County styles
├── tokenomics/
│   ├── NBPT_Ultra_Scarce_Model.md   # Full tokenomics docs
│   ├── tokenomics_calculator.py     # Vesting/burn/price calculator (Python)
│   ├── NBPT_Executive_Summary.txt   # Summary metrics
│   ├── NBPT_Monthly_Releases.csv    # 36-month vesting schedule
│   ├── NBPT_Price_Projections.csv   # Price projections
│   └── NBPT_Burn_Schedule.csv       # Quarterly burn schedule
├── operations-monitor/
│   └── index.html              # Infrastructure monitoring dashboard
├── ai-voices/
│   └── stephanie_ai_boston_intro.wav  # Stephanie.ai voice intro (1.9MB WAV)
├── README.md
├── README_ULTIMATE.md
├── DEPLOYMENT_GUIDE.md
└── PROJECT_COMPLETION_SUMMARY.md
```

## Tech Stack

- **Frontend**: HTML5, CSS3 (Grid, Flexbox, animations, backdrop-filter), vanilla JavaScript (ES6+)
- **Backend**: Python 3 (`http.server` for local dev)
- **Deployment**: Netlify (static), Vercel (static + headers), IPFS/Arweave (decentralized)
- **Requirements**: Node.js >= 14.0.0, Python >= 3.8.0

## Development Commands

```bash
# Start local dev server (port 8000)
npm start
# or: python3 -m http.server 8000

# Dev mode (port 3000)
npm run dev

# Direct Python server (port 8080, with CORS)
python3 server.py
```

No build step is required — the site is fully static HTML/CSS/JS.

## Code Conventions

### File Naming
- HTML files: kebab-case (`defi-dashboard.html`, `essex-county.html`)
- AI agent names: CamelCase with `.ai` suffix (Stephanie.ai, GCagent.ai, PermitStream.ai, CyBorg.ai)
- Token references: uppercase `NBPT`

### Frontend Patterns
- All CSS is embedded in `<style>` tags within each HTML file (no external CSS framework)
- JavaScript is inline at the end of `<body>`
- Responsive design uses `repeat(auto-fit, minmax(300px, 1fr))` grid layouts
- Mobile breakpoint: 768px
- Color scheme:
  - Primary: purple gradient (`#667eea` to `#764ba2`)
  - Accent: gold (`#ffd700`)
  - Success: cyan/lime (`#00ff88`)
  - Background: dark (`#0a0a0a`, `#1a1a2e`)
- Visual effects: starfield backgrounds (150 stars), shooting star animations, shimmer/twinkle keyframes
- Hover interactions use `translateY` transforms with 0.3s transitions

### Python
- Standard library only — no external dependencies
- `server.py` uses `http.server.SimpleHTTPRequestHandler` with CORS headers

## Key Domain Concepts

- **NBPT Token**: 100M fixed supply, ERC-1400 (SEC-compliant security token), ICO price $1.00 USDC
- **Tokenomics**: 36-month vesting, quarterly fee burns (25% of tx fees), 8 allocation categories
- **AI Agents**: Stephanie.ai (CEO), GCagent.ai (construction), PermitStream.ai (permits), CyBorg.ai (security)
- **Viral Lottery**: $5 entry, mandatory 5-person referral chain, first 100 get $500, grand prize $2,500
- **Real Estate Portfolio**: $245.7M across 847 properties in Essex County

## Deployment

Both `netlify.toml` and `vercel.json` configure:
- Security headers (X-Frame-Options: DENY, X-Content-Type-Options: nosniff, XSS protection)
- SPA-style routing (all routes → `/index.html`)
- No build command needed (static site)
- Cache policy: no-store, no-cache, must-revalidate

## Guidelines for AI Assistants

- This is a static site — there is no build system, bundler, or framework. Edit HTML/CSS/JS files directly.
- Do not introduce external CSS or JS frameworks unless explicitly requested. The project uses vanilla web technologies by design.
- Maintain the existing visual style (dark backgrounds, purple gradients, gold accents, starfield animations) when adding new pages or components.
- Keep CSS and JS inline within HTML files — this is the established pattern.
- The `tokenomics_calculator.py` uses only Python standard library; keep it dependency-free.
- When adding new dashboard pages, follow the grid card layout pattern from `index.html` and link them from the main dashboard.
- Preserve security headers in deployment configs when modifying `netlify.toml` or `vercel.json`.
- The `.wav` file in `ai-voices/` is large (1.9MB) — avoid reading or modifying binary assets.
