from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time

router = APIRouter(prefix="/api/control-plane", tags=["control-plane"])


class NavUpdateRequest(BaseModel):
    value: float
    appraisal_hash: str


class WithdrawalRequest(BaseModel):
    to: str
    token: str
    amount: float
    reason: str


class WhitelistRequest(BaseModel):
    investor: str
    accredited_until: int
    country_code: str
    max_ownership_bps: int = 1000


class ComplianceAction(BaseModel):
    investor: str
    action: str
    reason: str = ""


_audit_log: list[dict] = []
_pending_withdrawals: list[dict] = []
_nav_history: list[dict] = []


def _append_audit(action: str, details: dict):
    entry = {
        "nonce": len(_audit_log),
        "action": action,
        "details": details,
        "timestamp": int(time.time()),
    }
    _audit_log.append(entry)
    return entry


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "contracts": {
            "registry": "NoblePortRegistry",
            "rwa_token": "NoblePortInstitutionalRWA",
            "treasury": "NoblePortTreasury",
            "subscription": "NoblePortSubscription",
            "redemption": "NoblePortRedemption",
        },
        "audit_entries": len(_audit_log),
        "pending_withdrawals": sum(1 for w in _pending_withdrawals if w["status"] == "pending"),
    }


@router.post("/nav/update")
async def update_nav(req: NavUpdateRequest):
    if req.value <= 0:
        raise HTTPException(400, "NAV must be positive")
    entry = {
        "value": req.value,
        "appraisal_hash": req.appraisal_hash,
        "timestamp": int(time.time()),
    }
    _nav_history.append(entry)
    _append_audit("NAV_UPDATE", entry)
    return {"success": True, "nav": entry}


@router.get("/nav/current")
async def get_nav():
    if not _nav_history:
        return {"nav": None}
    return {"nav": _nav_history[-1]}


@router.get("/nav/history")
async def nav_history():
    return {"history": _nav_history[-50:]}


@router.post("/treasury/request-withdrawal")
async def request_withdrawal(req: WithdrawalRequest):
    withdrawal = {
        "id": len(_pending_withdrawals),
        "to": req.to,
        "token": req.token,
        "amount": req.amount,
        "reason": req.reason,
        "status": "pending",
        "requested_at": int(time.time()),
        "approved_by": None,
        "executed_at": None,
    }
    _pending_withdrawals.append(withdrawal)
    _append_audit("WITHDRAWAL_REQUESTED", {"id": withdrawal["id"], "to": req.to, "amount": req.amount})
    return {"success": True, "withdrawal": withdrawal}


@router.post("/treasury/approve/{withdrawal_id}")
async def approve_withdrawal(withdrawal_id: int, approver: str = "admin"):
    if withdrawal_id >= len(_pending_withdrawals):
        raise HTTPException(404, "Withdrawal not found")
    w = _pending_withdrawals[withdrawal_id]
    if w["status"] != "pending":
        raise HTTPException(400, f"Withdrawal is {w['status']}")
    w["status"] = "approved"
    w["approved_by"] = approver
    _append_audit("WITHDRAWAL_APPROVED", {"id": withdrawal_id, "approver": approver})
    return {"success": True, "withdrawal": w}


@router.get("/treasury/pending")
async def pending_withdrawals():
    pending = [w for w in _pending_withdrawals if w["status"] == "pending"]
    return {"withdrawals": pending, "count": len(pending)}


@router.post("/compliance/whitelist")
async def whitelist_investor(req: WhitelistRequest):
    _append_audit("WHITELIST", {
        "investor": req.investor,
        "accredited_until": req.accredited_until,
        "country_code": req.country_code,
        "max_bps": req.max_ownership_bps,
    })
    return {"success": True, "investor": req.investor}


@router.post("/compliance/action")
async def compliance_action(req: ComplianceAction):
    if req.action not in ("sanction", "unsanction", "freeze", "unfreeze"):
        raise HTTPException(400, "Invalid action")
    _append_audit(f"COMPLIANCE_{req.action.upper()}", {"investor": req.investor, "reason": req.reason})
    return {"success": True, "action": req.action, "investor": req.investor}


@router.get("/audit/log")
async def audit_log(limit: int = 50):
    return {"entries": _audit_log[-limit:], "total": len(_audit_log)}


@router.get("/audit/hash")
async def audit_hash():
    if not _audit_log:
        return {"hash": None, "nonce": 0}
    latest = _audit_log[-1]
    return {"hash": f"0x{latest['nonce']:08x}", "nonce": latest["nonce"]}
