# Solana Key Verification

## Address

```
6fbr88Qmc1LSh5XATjcaGzvVnq1H7QmB57wAyxrKMXas
```

## Label

`NobleKuzo Primary Solana Rail` (`noblekuzo.solana.treasury`)

## Verification Results

| Check                       | Result                                                             |
|-----------------------------|--------------------------------------------------------------------|
| Encoding                    | Base58                                                             |
| Character length            | 44                                                                 |
| Decoded byte length         | 32                                                                 |
| Ed25519 on-curve            | TRUE (valid wallet keypair, not a Program Derived Address)         |
| Public key (hex)            | `542de82d8484f0821839e928fca1fed3ce1296b894e4d2954b82fcb255d2cc84` |
| Verified on                 | 2026-05-21                                                         |
| Status                      | LIVE_PENDING_OWNERSHIP_CONFIRMATION                                |

The address is structurally valid for Solana mainnet. It decodes to a
well-formed 32-byte ed25519 public key that lies on the curve, which means
it corresponds to a real keypair (signing-capable wallet) rather than a PDA.

## Verification Method

```python
import base58
from nacl.signing import VerifyKey

key = "6fbr88Qmc1LSh5XATjcaGzvVnq1H7QmB57wAyxrKMXas"
decoded = base58.b58decode(key)
assert len(decoded) == 32
VerifyKey(decoded)  # raises if not on-curve
```

## Policy Tags

```json
{
  "chain": "solana",
  "network_role": "usdc_payment_rail",
  "treasury_authority": false,
  "governance_authority": false,
  "nbpt_enabled": false,
  "bridge_enabled": false,
  "status": "LIVE_PENDING_VERIFICATION"
}
```

These tags align with the existing NoblePort architectural constraints:

- Solana is used as a payment rail only
- No NBPT issuance on Solana
- No autonomous treasury authority
- Settlement remains human-gated

## Required Follow-Up (Not Done In This Commit)

1. **Confirm ownership** by running `solana address` on the originating
   wallet machine and matching the output exactly to the address above.
2. **Read-only monitoring**: track incoming USDC, failed transfers,
   settlement timing, and webhook events. Do not grant write authority.
3. **Audit registry**: once a wallet registry layer exists, add this
   address to the treasury allowlist, attribution reconciliation,
   webhook verification, and settlement logs.
4. **Storage discipline**: when consumed by services, store via env vars
   or server-side config — never hardcode in frontend bundles.

## Marketing / Language Constraints

When referencing flows that touch this address publicly, use payment-rail
language only: "payment rail", "treasury settlement", "USDC operations",
"project payments". Do not market yield, investment returns, token
appreciation, or staking against this address unless counsel approves.
