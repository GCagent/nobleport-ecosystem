import React, { useState } from 'react';

const PQCReadinessV2 = () => {
  const [expanded, setExpanded] = useState(null);
  const [showMethodology, setShowMethodology] = useState(false);

  // Deterministic rule-based control-readiness model. Not a Monte Carlo /
  // probabilistic simulation — a threat is either gateway-scoped (baseline
  // "at risk", target "simulated ready" once the Phase 1 gateway control set
  // is implemented AND independently validated) or external control plane.
  // Seed governs case-ID ordering for audit-trail reproducibility only.
  const seed = 20260826;
  const totalTests = 1000;

  const results = [
    { id: 1, name: 'RSA / ECC / DH / DSA breakage', scope: 'gateway', severity: null,
      control: 'ML-KEM (FIPS 203) + ML-DSA-65 (FIPS 204)',
      gap: 'Deployed at transport/API layer only; no independent validation (pen-test, protocol analyzer) yet run' },
    { id: 2, name: 'Harvest-now, decrypt-later', scope: 'gateway', severity: null,
      control: 'Hybrid classical+PQC on gateway-terminated traffic',
      gap: 'Hybrid confirmed at transport/API only, not verified across every data-in-transit path' },
    { id: 3, name: 'Digital-signature forgery', scope: 'gateway', severity: null,
      control: 'ML-DSA-65 (Dilithium) + Falcon-512',
      gap: 'SPHINCS+ (FIPS 205) only partially integrated; no forgery-attempt testing performed' },
    { id: 4, name: 'TLS / HTTPS interception', scope: 'gateway', severity: null,
      control: 'PQC ciphersuites at transport layer',
      gap: 'No protocol-analyzer confirmation that vulnerable cipher suites are actually excluded' },
    { id: 5, name: 'VPN / IPsec compromise', scope: 'external', severity: 'UNSCOPED',
      control: null,
      gap: 'No PQC IKEv2/VPN workstream exists in current architecture — not deprioritized, simply absent' },
    { id: 6, name: 'Blockchain / cryptocurrency theft', scope: 'external', severity: 'KNOWN VULNERABLE',
      control: null,
      gap: 'CyborgClawbotRegistry + NBPT (ERC-1400) run standard ECDSA on testnet; documented signer-key-reuse risk across Arbitrum/Base Gnosis Safe instances. This is evidenced exposure, not an unscoped gap.' },
    { id: 7, name: 'Grover weakening of symmetric cryptography', scope: 'gateway', severity: null,
      control: 'AES-256 assumed in use',
      gap: 'Not independently confirmed across every service; no side-channel testing performed' },
    { id: 8, name: 'IoT / critical-infrastructure exposure', scope: 'external', severity: 'UNSCOPED',
      control: null,
      gap: 'Limited applicability to current architecture; no managed field/IoT devices currently in scope to test' },
    { id: 9, name: 'Supply-chain / firmware attacks', scope: 'gateway', severity: null,
      control: 'Cloud signing service (FastAPI) operational',
      gap: 'HSM hardening — the control that would actually protect the signing keys — is not yet complete' },
    { id: 10, name: 'Long-term data confidentiality loss', scope: 'gateway', severity: null,
      control: 'N/A — no control currently deployed',
      gap: 'No PQC-at-rest layer on PostgreSQL/Redis managed services' },
  ];

  const gatewayCases = results.filter(r => r.scope === 'gateway').length * 100;
  const externalCases = results.filter(r => r.scope === 'external').length * 100;
  const verified = 0;
  const knownVulnCases = results.filter(r => r.severity === 'KNOWN VULNERABLE').length * 100;
  const unscopedCases = results.filter(r => r.severity === 'UNSCOPED').length * 100;

  const limitations = [
    { t: 'No cryptographic verification', d: 'Does not run actual PQC algorithms, TLS handshakes, or quantum attacks. This is a control-scoping exercise, not a technical test.' },
    { t: '"Simulated ready" ≠ "ready"', d: 'The 700 gateway-scoped cases are still at risk in reality until PQC libraries are integrated, keys generated, certs issued, and interoperability tested.' },
    { t: 'External threats are deferred, not solved', d: 'VPN/IPsec, blockchain, and IoT remain real attack surfaces. Being out of gateway scope does not mean they are being addressed elsewhere.' },
    { t: 'No performance or side-channel analysis', d: 'PQC algorithms have different performance profiles and may be vulnerable to side-channel attacks. Not tested here.' },
    { t: 'Assumes perfect implementation', d: 'The model presumes that if a gateway control is implemented, it fully mitigates the threat. It does not account for misconfiguration, software bugs, or human error.' },
  ];

  const roadmap = [
    { phase: 'A. Implement gateway controls', items: ['Deploy hybrid PQC on all gateway-terminated traffic (TLS, HTTPS, email)', 'ML-KEM for key exchange, ML-DSA/SLH-DSA for signatures', 'Update crypto libraries (OpenSSL/BoringSSL) to PQC-supporting versions'] },
    { phase: 'B. Independently validate (Threats 1–4, 7, 9, 10)', items: ['Live pen tests with quantum-simulation tools', 'Protocol analyzers confirming no vulnerable cipher suites negotiated', 'Signature verification against test certs from a PQC-enabled PKI'] },
    { phase: 'C. Address external control planes', items: ['VPN/IPsec: PQC-capable IKEv2 groups, hybrid or pure PQC', 'Blockchain: resolve signer-key-reuse first; PQC contract signing or sidechain/oracle wrapping is a longer-term follow-on', 'IoT: lightweight PQC (SPHINCS+) where applicable, or isolate/replace unmanaged devices'] },
    { phase: 'D. Continuous monitoring & crypto-agility', items: ['PQC readiness checks in CI/CD to prevent regression to classical algorithms', 'Live cryptographic inventory, auto-flagging quantum-vulnerable components'] },
  ];

  const scopeStyle = {
    gateway: { text: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/30' },
    external: { text: 'text-slate-400', bg: 'bg-slate-500/10', border: 'border-slate-500/30' },
  };
  const severityStyle = {
    'KNOWN VULNERABLE': { text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' },
    'UNSCOPED': { text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  };

  return (
    <div style={{ fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace" }} className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h1 className="text-xl font-bold tracking-tight">CYBORG.AI / NOBLEPORT SECURITY</h1>
            <span className="text-xs px-2 py-0.5 rounded border bg-red-500/15 text-red-300 border-red-500/30">v2 — CORRECTED MODEL</span>
          </div>
          <p className="text-slate-500 text-xs">PQC Readiness Simulator · {totalTests.toLocaleString()} tests · 10 threat classes × 100 cases · Seed {seed}</p>
        </div>

        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 mb-6 flex items-start gap-3">
          <span className="text-red-400 text-lg leading-none">⚠</span>
          <div className="text-xs text-red-200 leading-relaxed">
            <span className="font-bold">Simulation completed; cryptographic verification did not.</span> This is an offline control-readiness model, not live PQC, TLS, VPN, blockchain, IoT, penetration-test, or production-certification evidence. Outcomes are rule-based (a threat is either gateway-controllable or it isn't), not probabilistic — the seed governs case ordering for audit-trail reproducibility, not confidence intervals. Zero cases are verified protected until independent validation exists.
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <div className="text-xs text-slate-500 mb-1">Suite Execution</div>
            <div className="text-3xl font-bold text-slate-300">{totalTests}/{totalTests}</div>
            <div className="text-xs text-slate-600 mt-1">Completed</div>
          </div>
          <div className="bg-slate-900/60 border border-emerald-500/20 rounded-xl p-4">
            <div className="text-xs text-slate-500 mb-1">Verified Protected</div>
            <div className="text-3xl font-bold text-emerald-500">{verified}</div>
            <div className="text-xs text-slate-600 mt-1">No live cryptographic proof</div>
          </div>
          <div className="bg-slate-900/60 border border-cyan-500/20 rounded-xl p-4">
            <div className="text-xs text-slate-500 mb-1">Gateway At Risk</div>
            <div className="text-3xl font-bold text-cyan-400">{gatewayCases}</div>
            <div className="text-xs text-slate-600 mt-1">Evidenced control gaps</div>
          </div>
          <div className="bg-slate-900/60 border border-slate-700 rounded-xl p-4">
            <div className="text-xs text-slate-500 mb-1">External / Unverified</div>
            <div className="text-3xl font-bold text-slate-400">{externalCases}</div>
            <div className="text-xs text-slate-600 mt-1">VPN, blockchain, IoT</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
          <div className="bg-red-500/5 border border-red-500/25 rounded-xl p-4">
            <div className="text-xs text-red-400 font-semibold mb-1">KNOWN VULNERABLE — {knownVulnCases} cases</div>
            <div className="text-xs text-slate-400 leading-relaxed">Blockchain/crypto theft. Not "unscoped" — actively evidenced: testnet-only ECDSA on CyborgClawbotRegistry/NBPT plus documented signer-key-reuse across Arbitrum/Base Safes. Distinct severity from the two threats below.</div>
          </div>
          <div className="bg-amber-500/5 border border-amber-500/25 rounded-xl p-4">
            <div className="text-xs text-amber-400 font-semibold mb-1">UNSCOPED — {unscopedCases} cases</div>
            <div className="text-xs text-slate-400 leading-relaxed">VPN/IPsec and IoT. No workstream exists, but also no specific evidenced exploit path documented — genuinely unaddressed rather than known-bad.</div>
          </div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 mb-6">
          <h3 className="font-semibold mb-4 text-sm">Per-Threat Result</h3>
          <div className="space-y-2">
            {results.map(r => {
              const ss = scopeStyle[r.scope];
              const sev = r.severity ? severityStyle[r.severity] : null;
              const isOpen = expanded === r.id;
              return (
                <div key={r.id} className={`border rounded-lg overflow-hidden ${sev ? sev.border : ss.border} ${sev ? sev.bg : ss.bg}`}>
                  <div className="p-3 cursor-pointer" onClick={() => setExpanded(isOpen ? null : r.id)}>
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs text-slate-500 shrink-0">T{r.id}</span>
                        <span className="text-sm font-medium truncate">{r.name}</span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                        {r.severity && (
                          <span className={`text-xs px-2 py-0.5 rounded border ${sev.border} ${sev.text}`}>{r.severity}</span>
                        )}
                        <span className={`text-xs px-2 py-0.5 rounded border ${ss.border} ${ss.text}`}>
                          {r.scope === 'gateway' ? '100 at risk → 100 simulated ready' : `100 unverified → external control plane`}
                        </span>
                      </div>
                    </div>
                    {isOpen && (
                      <div className="mt-3 pt-3 border-t border-slate-700/50 text-xs text-slate-400 leading-relaxed space-y-1">
                        {r.control && <div><span className="text-slate-500">Proposed/current control:</span> {r.control}</div>}
                        <div><span className="text-slate-500">Gap:</span> {r.gap}</div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 mb-6">
          <h3 className="font-semibold mb-3 text-sm text-red-300">Critical Limitations</h3>
          <div className="space-y-3">
            {limitations.map((l, i) => (
              <div key={i} className="text-xs">
                <span className="text-slate-300 font-semibold">{i + 1}. {l.t}</span>
                <span className="text-slate-500"> — {l.d}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 mb-6">
          <h3 className="font-semibold mb-4 text-sm">Path From Simulated Ready → Verified Protected</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {roadmap.map((r, i) => (
              <div key={i} className="bg-slate-800/40 rounded-lg p-3">
                <div className="text-xs font-semibold text-cyan-400 mb-2">{r.phase}</div>
                <ul className="space-y-1">
                  {r.items.map((item, j) => (
                    <li key={j} className="text-xs text-slate-400 leading-relaxed flex gap-1.5">
                      <span className="text-slate-600 shrink-0">·</span>{item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-amber-500/5 border border-amber-500/25 rounded-xl p-4 mb-6">
          <h3 className="text-sm font-semibold text-amber-300 mb-2">Open Item — Training Dashboard Reconciliation</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            The existing <span className="text-slate-300 font-mono">cyborg-training-dashboard.jsx</span> shows PQC Ready Score 89%, CRYSTALS-Kyber 100%, CRYSTALS-Dilithium 100%, with no unverified/simulated disclaimer. This model shows 0 verified. Both should not circulate to different audiences as if they're the same claim — the training dashboard needs the same "deployed ≠ verified" language retrofitted, or it should be retired in favor of this framework.
          </p>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5">
          <button onClick={() => setShowMethodology(!showMethodology)} className="text-sm font-semibold flex items-center gap-2 w-full text-left">
            <svg className={`w-4 h-4 transition-transform ${showMethodology ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Reproducibility & Methodology
          </button>
          {showMethodology && (
            <div className="mt-3 text-xs text-slate-400 leading-relaxed space-y-2">
              <p>10 threat classes × 100 modeled cases = 1,000 total. For each threat, classification into gateway-scope vs. external-control-plane is a fixed rule based on current NoblePort/CYBORG.AI architecture, not a random draw — there is no probabilistic claim being made about whether a control "works," only a binary claim about whether it is (a) gateway-controllable in principle and (b) independently validated (currently: never, for all 1,000 cases).</p>
              <p>Seed {seed} governs deterministic case-ID shuffling within each threat class, for audit-trail purposes (so a re-run produces the identical case ordering) — it does not affect the pass/fail outcome, since outcomes are rule-based rather than sampled.</p>
              <p>Executed via Python (random.Random(seed).shuffle per threat class). Script available on request for independent re-run.</p>
            </div>
          )}
        </div>

        <div className="mt-6 text-center text-xs text-slate-700">
          PQC Readiness Simulator v2 · Deterministic rule-based control-readiness model · Not a certified security assessment
        </div>
      </div>
    </div>
  );
};

export default PQCReadinessV2;
