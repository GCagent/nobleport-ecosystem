//! NoblePort Systems edge gateway.
//!
//! Public entrypoint for nobleportsystem.io / *.kuzo.io. Responsibilities:
//!   - `/health`, `/gateway/status` served locally
//!   - `/api/*` reverse-proxied to the Python orchestrator
//!   - `/ws/avatar` WebSocket passthrough to the orchestrator's avatar session
//!   - per-client token-bucket rate limiting on all proxied traffic
//!
//! TLS terminates at the front proxy (Caddy/Nginx on the Hostinger VPS); the
//! gateway listens on plain HTTP inside the compose network.

use std::{
    collections::HashMap,
    net::{IpAddr, SocketAddr},
    sync::{Arc, Mutex},
    time::Instant,
};

use axum::{
    body::Body,
    extract::{
        ws::{Message as AxumMessage, WebSocket},
        ConnectInfo, State, WebSocketUpgrade,
    },
    http::{HeaderMap, Method, StatusCode, Uri},
    response::{IntoResponse, Response},
    routing::{any, get},
    Json, Router,
};
use futures_util::{SinkExt, StreamExt};
use tokio_tungstenite::tungstenite::Message as TungsteniteMessage;

const RATE_CAPACITY: f64 = 60.0; // burst
const RATE_REFILL_PER_SEC: f64 = 1.0; // sustained rps per client

struct Bucket {
    tokens: f64,
    last: Instant,
}

#[derive(Clone)]
struct AppState {
    orchestrator_http: String,
    orchestrator_ws: String,
    client: reqwest::Client,
    buckets: Arc<Mutex<HashMap<IpAddr, Bucket>>>,
}

impl AppState {
    fn allow(&self, ip: IpAddr) -> bool {
        let mut buckets = self.buckets.lock().expect("bucket lock");
        let now = Instant::now();
        let bucket = buckets.entry(ip).or_insert(Bucket {
            tokens: RATE_CAPACITY,
            last: now,
        });
        let elapsed = now.duration_since(bucket.last).as_secs_f64();
        bucket.tokens = (bucket.tokens + elapsed * RATE_REFILL_PER_SEC).min(RATE_CAPACITY);
        bucket.last = now;
        if bucket.tokens >= 1.0 {
            bucket.tokens -= 1.0;
            true
        } else {
            false
        }
    }
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    let orchestrator =
        std::env::var("ORCHESTRATOR_URL").unwrap_or_else(|_| "http://orchestrator:8000".into());
    let orchestrator_ws = orchestrator
        .replacen("http://", "ws://", 1)
        .replacen("https://", "wss://", 1);

    let state = AppState {
        orchestrator_http: orchestrator.clone(),
        orchestrator_ws,
        client: reqwest::Client::new(),
        buckets: Arc::new(Mutex::new(HashMap::new())),
    };

    let app = Router::new()
        .route("/health", get(health))
        .route("/gateway/status", get(status))
        .route("/ws/avatar", get(avatar_ws))
        .route("/api/{*path}", any(proxy))
        .with_state(state);

    let addr: SocketAddr = std::env::var("GATEWAY_ADDR")
        .unwrap_or_else(|_| "0.0.0.0:8080".into())
        .parse()
        .expect("invalid GATEWAY_ADDR");
    tracing::info!(%addr, upstream = %orchestrator, "nobleport-gateway listening");

    let listener = tokio::net::TcpListener::bind(addr).await.expect("bind");
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .with_graceful_shutdown(async {
        let _ = tokio::signal::ctrl_c().await;
    })
    .await
    .expect("server error");
}

async fn health() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "ok", "service": "nobleport-gateway" }))
}

async fn status(State(state): State<AppState>) -> impl IntoResponse {
    let upstream_healthy = state
        .client
        .get(format!("{}/health", state.orchestrator_http))
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false);
    Json(serde_json::json!({
        "service": "nobleport-gateway",
        "upstream": state.orchestrator_http,
        "upstream_healthy": upstream_healthy,
    }))
}

/// Reverse-proxy `/api/{path}` to the orchestrator, stripping the `/api`
/// prefix (gateway: `/api/modules` -> orchestrator: `/modules`).
async fn proxy(
    State(state): State<AppState>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    method: Method,
    uri: Uri,
    headers: HeaderMap,
    body: Body,
) -> Response {
    if !state.allow(peer.ip()) {
        return (StatusCode::TOO_MANY_REQUESTS, "rate_limited").into_response();
    }

    let path = uri.path().trim_start_matches("/api");
    let mut upstream = format!("{}{}", state.orchestrator_http, path);
    if let Some(q) = uri.query() {
        upstream.push('?');
        upstream.push_str(q);
    }

    let body_bytes = match axum::body::to_bytes(body, 2 * 1024 * 1024).await {
        Ok(b) => b,
        Err(_) => return (StatusCode::PAYLOAD_TOO_LARGE, "body_too_large").into_response(),
    };

    let mut req = state.client.request(method, upstream);
    for (name, value) in headers.iter() {
        // hop-by-hop headers stay local
        if matches!(name.as_str(), "host" | "connection" | "content-length") {
            continue;
        }
        req = req.header(name, value);
    }
    req = req.header("x-forwarded-for", peer.ip().to_string());

    match req.body(body_bytes).send().await {
        Ok(resp) => {
            let status = StatusCode::from_u16(resp.status().as_u16())
                .unwrap_or(StatusCode::BAD_GATEWAY);
            let mut builder = Response::builder().status(status);
            for (name, value) in resp.headers().iter() {
                if name.as_str() != "transfer-encoding" {
                    builder = builder.header(name, value);
                }
            }
            let bytes = resp.bytes().await.unwrap_or_default();
            builder
                .body(Body::from(bytes))
                .unwrap_or_else(|_| StatusCode::BAD_GATEWAY.into_response())
        }
        Err(err) => {
            tracing::warn!(error = %err, "upstream request failed");
            (StatusCode::BAD_GATEWAY, "upstream_unavailable").into_response()
        }
    }
}

/// Bidirectional WebSocket passthrough for the Stephanie.ai avatar channel.
async fn avatar_ws(
    State(state): State<AppState>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    upgrade: WebSocketUpgrade,
) -> Response {
    if !state.allow(peer.ip()) {
        return (StatusCode::TOO_MANY_REQUESTS, "rate_limited").into_response();
    }
    let upstream_url = format!("{}/ws/avatar", state.orchestrator_ws);
    upgrade.on_upgrade(move |client| bridge_avatar(client, upstream_url))
}

async fn bridge_avatar(client: WebSocket, upstream_url: String) {
    let upstream = match tokio_tungstenite::connect_async(&upstream_url).await {
        Ok((ws, _)) => ws,
        Err(err) => {
            tracing::warn!(error = %err, "avatar upstream connect failed");
            return;
        }
    };

    let (mut client_tx, mut client_rx) = client.split();
    let (mut upstream_tx, mut upstream_rx) = upstream.split();

    let to_upstream = async {
        while let Some(Ok(msg)) = client_rx.next().await {
            let forward = match msg {
                AxumMessage::Text(t) => TungsteniteMessage::text(t.as_str()),
                AxumMessage::Binary(b) => TungsteniteMessage::binary(b),
                AxumMessage::Close(_) => break,
                _ => continue,
            };
            if upstream_tx.send(forward).await.is_err() {
                break;
            }
        }
    };

    let to_client = async {
        while let Some(Ok(msg)) = upstream_rx.next().await {
            let forward = match msg {
                TungsteniteMessage::Text(t) => AxumMessage::Text(t.as_str().into()),
                TungsteniteMessage::Binary(b) => AxumMessage::Binary(b),
                TungsteniteMessage::Close(_) => break,
                _ => continue,
            };
            if client_tx.send(forward).await.is_err() {
                break;
            }
        }
    };

    tokio::select! {
        _ = to_upstream => {},
        _ = to_client => {},
    }
}
