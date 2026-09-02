# CLAUDE.md — NoblePort Ecosystem

## Project Overview

NoblePort is a static web-based dashboard ecosystem for **Stephanie.ai**, an AI-governed real estate and construction platform with the NBPT utility token. The repository is a **static site** (no build step) consisting of HTML dashboards, CSS, JavaScript, Python utilities, and tokenomics documentation.

**Version:** 3.0.0
**License:** MIT

## Repository Structure

```
nobleport-ecosystem/
├── index.html                     # Main landing page / central dashboard hub
├── server.py                      # Python HTTP server with CORS headers (port 8080)
├── package.json                   # Project metadata and npm start scripts
├── netlify.toml                   # Netlify deployment config (static, SPA redirects)
├── vercel.json                    # Vercel deployment config (static)
├── deployment_metrics.json        # System metrics and deployment status snapshot
├── server.log                     # Server runtime log (checked in, not gitignored)
├── dashboards/
│   ├── defi-dashboard.html        # DeFi pool vs token analytics dashboard
│   ├── essex-county.html          # Essex County real estate portfolio viewer
│   ├── essex-style.css            # Styles for Essex County dashboard
│   └── lottery.html               # Viral lottery app ($5 entry, referral-based)
├── operations-monitor/
│   └── index.html                 # Multi-chain infrastructure monitoring dashboard
├── tokenomics/
│   ├── NBPT_Ultra_Scarce_Model.md # Full tokenomics whitepaper (100M supply)
│   ├── tokenomics_calculator.py   # Python tokenomics model (pandas/numpy/matplotlib)
│   ├── NBPT_Executive_Summary.txt # Generated executive summary
│   ├── NBPT_Monthly_Releases.csv  # Monthly token release schedule
│   ├── NBPT_Price_Projections.csv # Price projection data
│   └── NBPT_Burn_Schedule.csv     # Quarterly burn schedule
├── ai-voices/
│   └── stephanie_ai_boston_intro.wav # Stephanie.ai voice intro audio
├── README.md                      # Primary README
├── README_ULTIMATE.md             # Extended feature overview
├── DEPLOYMENT_GUIDE.md            # Full deployment & legal compliance guide
└── PROJECT_COMPLETION_SUMMARY.md  # Feature inventory and completion status
```

## Tech Stack

- **Frontend:** Vanilla HTML, CSS, JavaScript (no frameworks, no bundler)
- **Backend/Dev Server:** Python 3.8+ (`http.server` / `server.py`)
- **Tokenomics Tooling:** Python 3 with `pandas`, `numpy`, `matplotlib`
- **Deployment Targets:** Netlify, Vercel, GitHub Pages, Replit, IPFS (all static)
- **Blockchain Standards:** ERC-1400 security tokens, multi-chain (ETH, ARB, BASE, MATIC, OP, AVAX, SOL, XRP, ADA)

## Development Workflow

### Running Locally

```bash
# Option 1: npm script (port 8000)
npm start

# Option 2: npm dev (port 3000)
npm run dev

# Option 3: Python server with CORS (port 8080)
python3 server.py
```

Then open `http://localhost:<port>` in a browser.

### There Is No Build Step

This is a static site. All HTML/CSS/JS is served as-is. There is no transpilation, bundling, or compilation. The `netlify.toml` build command is literally `echo 'Static site - no build required'`.

### There Are No Tests

No test framework or test files exist in this repository. Manual testing is done via the checklist in `DEPLOYMENT_GUIDE.md`.

## Key Conventions

### Code Style
- HTML files are self-contained: styles are inlined in `<style>` tags, scripts in `<script>` tags
- CSS uses modern features: `grid`, `flexbox`, `backdrop-filter`, CSS animations
- JavaScript is vanilla ES6+ (no jQuery, no frameworks)
- Python follows standard PEP 8 conventions

### Dashboard Architecture
- Each dashboard is a standalone HTML file with embedded CSS/JS
- The main `index.html` links to all sub-dashboards via card-based navigation
- Dashboards use simulated/static data (no live backend APIs currently connected)
- Common visual theme: dark backgrounds, gradient accents (`#667eea` to `#764ba2`), glassmorphism cards

### Security Headers
Both `netlify.toml` and `vercel.json` configure security headers:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- Referrer-Policy and Permissions-Policy (Netlify only)

### File Naming
- HTML dashboards: lowercase with hyphens (e.g., `defi-dashboard.html`)
- Python files: lowercase with underscores (e.g., `tokenomics_calculator.py`)
- Documentation: UPPER_CASE with underscores (e.g., `DEPLOYMENT_GUIDE.md`)
- CSV data: `NBPT_` prefix with descriptive name

## Important Domain Context

- **NBPT Token:** 100M fixed supply, ERC-1400 standard, $1.00 ICO price
- **Stephanie.ai:** AI CEO persona governing the NoblePort ecosystem
- **AI Agents:** GCagent.ai (construction), PermitStream.ai (permits), CyBorg.ai (security)
- **Wallet Address:** `0xc59e66BB2b6E19699F82A72a1569821cb1711504`
- **Token Contract:** `0x3778E67655Ec26D6bC8294C6F7a1e754AFD2C91C`

## Working with the Tokenomics Calculator

```bash
cd tokenomics
pip install pandas numpy matplotlib
python3 tokenomics_calculator.py
```

This generates/regenerates the CSV files and executive summary in the `tokenomics/` directory.

## Deployment

### Netlify
Push to the repository; Netlify serves the root directory as a static site with SPA fallback redirects to `index.html`.

### Vercel
Uses `@vercel/static` builder. Routes pass through directly to files.

### Local / Replit
Use `python3 -m http.server 8000` or `python3 server.py` (adds CORS and cache-busting headers).

## Known Issues

- `server.log` contains a stale `OSError: Address already in use` traceback — this file is checked in but represents a one-time runtime error, not a persistent issue
- The lottery app uses `localStorage` for referral tracking (a production backend would be needed for real use)
- Dashboard data is simulated/static; no live API integrations are wired up yet
