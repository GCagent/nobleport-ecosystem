"""Stephanie FastAPI endpoint — the API surface for NoblePort operations.

Provides:
- POST /api/v1/stephanie/execute  (Bearer auth, rate limited)
- POST /api/v1/webhooks/openclaw  (HMAC-validated webhook receiver)
- GET  /health
"""

import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .rate_limit import rate_limiter
from .schemas import (
    ExecuteRequest,
    ExecuteResponse,
    HealthResponse,
    WebhookEvent,
    WebhookResponse,
)
from .security import ApiKeyDep, verify_webhook_signature
from .services import dispatch_action, process_webhook_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("stephanie")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Stephanie endpoint starting up")
    yield
    logger.info("Stephanie endpoint shutting down")


app = FastAPI(
    title="Stephanie Endpoint",
    description="NoblePort Stephanie AI operational API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Audit logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    logger.info(
        "audit: method=%s path=%s client=%s",
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown",
    )
    response: Response = await call_next(request)
    logger.info(
        "audit: method=%s path=%s status=%s",
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Service health check."""
    return HealthResponse()


@app.post(
    "/api/v1/stephanie/execute",
    response_model=ExecuteResponse,
    tags=["stephanie"],
)
async def execute_action(
    body: ExecuteRequest,
    request: Request,
    _api_key: ApiKeyDep,
):
    """Execute a Stephanie action (create job, check permit, sync CRM, etc.)."""
    rate_limiter.check(request)
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    result = await dispatch_action(
        action=body.action,
        data=body.data,
        dry_run=body.dry_run,
    )

    return ExecuteResponse(
        request_id=request_id,
        status="dry_run" if body.dry_run else "ok",
        action=body.action.value,
        result=result,
    )


@app.post(
    "/api/v1/webhooks/openclaw",
    response_model=WebhookResponse,
    tags=["webhooks"],
)
async def webhook_openclaw(
    request: Request,
    raw_body: bytes = Depends(verify_webhook_signature),
):
    """Receive and validate webhook events from OpenC Law."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    event = WebhookEvent(**json.loads(raw_body))
    await process_webhook_event(event.event_type, event.payload)

    return WebhookResponse(
        event_type=event.event_type,
        request_id=request_id,
    )
