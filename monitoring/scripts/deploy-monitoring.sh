#!/usr/bin/env bash
# Deploy the NoblePort monitoring stack to Kubernetes.
# Idempotent: re-running updates the ConfigMaps and reloads Prometheus.
#
#   ./deploy-monitoring.sh [namespace]   (default: nobleport-monitoring)
set -euo pipefail

NS="${1:-nobleport-monitoring}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ">> Validating stack before deploy"
python3 "${HERE}/scripts/validate-monitoring-stack.py"

if command -v promtool >/dev/null 2>&1; then
  echo ">> promtool check rules"
  promtool check rules "${HERE}"/prometheus/rules/*.yml
else
  echo ">> promtool not found — skipping rule lint (install for stricter checks)"
fi

echo ">> Ensuring namespace ${NS}"
kubectl create namespace "${NS}" --dry-run=client -o yaml | kubectl apply -f -

echo ">> Applying Prometheus config + rules"
kubectl -n "${NS}" create configmap prometheus-config \
  --from-file="${HERE}/prometheus/prometheus.yml" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "${NS}" create configmap prometheus-rules \
  --from-file="${HERE}/prometheus/rules" \
  --dry-run=client -o yaml | kubectl apply -f -

echo ">> Applying Alertmanager config"
kubectl -n "${NS}" create configmap alertmanager-config \
  --from-file="${HERE}/alertmanager/alertmanager.yml" \
  --dry-run=client -o yaml | kubectl apply -f -

echo ">> Applying Grafana dashboards + provisioning"
kubectl -n "${NS}" create configmap grafana-dashboards \
  --from-file="${HERE}/grafana/dashboards" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "${NS}" create configmap grafana-provisioning \
  --from-file="${HERE}/grafana/provisioning" \
  --dry-run=client -o yaml | kubectl apply -f -

# Hot-reload Prometheus if it is already running (lifecycle API or HUP).
if kubectl -n "${NS}" get deploy/prometheus >/dev/null 2>&1; then
  echo ">> Reloading Prometheus"
  kubectl -n "${NS}" exec deploy/prometheus -- kill -HUP 1 2>/dev/null \
    || echo "   (could not signal Prometheus; restart the pod to pick up changes)"
fi

echo ">> Done. ConfigMaps applied to ${NS}."
echo "   Mount prometheus-config -> /etc/prometheus, prometheus-rules -> /etc/prometheus/rules,"
echo "   grafana-* into the Grafana pod, then access Grafana dashboard uid 'nobleport-ops'."
