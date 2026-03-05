# Monitoring — Prometheus, Grafana & Alertmanager

This document describes the observability stack for the US Law RAG system. All monitoring configuration lives in `monitoring/`.

---

## Overview

Monitoring is provided by the **kube-prometheus-stack** Helm chart, which bundles:

- **Prometheus** — metrics collection and storage (15-day retention by default).
- **Grafana** — dashboards and visualisation.
- **Alertmanager** — alert routing and deduplication.
- **node-exporter** — per-node OS and hardware metrics.
- **kube-state-metrics** — Kubernetes object-level metrics (pod restarts, resource requests vs limits, etc.).

Application services expose a `/metrics` endpoint (using `prometheus-fastapi-instrumentator`) and are scraped via **ServiceMonitor** custom resources.

---

## Files

| File                                | Purpose                                         |
| ----------------------------------- | ----------------------------------------------- |
| `kube-prometheus-stack-values.yaml` | Helm values — enables/configures all components |
| `service-monitors.yaml`             | `ServiceMonitor` CRDs for each FastAPI service  |

---

## Components

### Prometheus

- Scrapes all `ServiceMonitor` resources across namespaces (`serviceMonitorSelectorNilUsesHelmValues: false`).
- 15-day retention; adjust `retention` in the values file for longer storage or add a remote-write target (e.g. Thanos, Cortex).
- Resources: 200m CPU / 512Mi → 1000m / 2Gi.

### Grafana

- Accessible via `kubectl port-forward` by default (no Ingress configured).
- Default admin password is `changeme` — override before deploying:
  ```bash
  helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
    -n monitoring --create-namespace \
    --set grafana.adminPassword="$(openssl rand -base64 24)" \
    -f infra/monitoring/kube-prometheus-stack-values.yaml
  ```
- Dashboard provider is pre-configured to load dashboards from `/var/lib/grafana/dashboards/default`; add ConfigMap-backed dashboards there.

### Alertmanager

- Deployed and ready; configure receivers (Slack, PagerDuty, email) in a separate `alertmanager-config` Secret.

### ServiceMonitors

`service-monitors.yaml` registers ServiceMonitors in the `monitoring` namespace for:

| ServiceMonitor | Target                             | Scrape path | Interval |
| -------------- | ---------------------------------- | ----------- | -------- |
| `api-gateway`  | `app: api-gateway` in `rag-us-law` | `/metrics`  | 30s      |
| `auth-api`     | `app: auth-api` in `rag-us-law`    | `/metrics`  | 30s      |
| `user-api`     | `app: user-api` in `rag-us-law`    | `/metrics`  | 30s      |
| `chat-api`     | `app: chat-api` in `rag-us-law`    | `/metrics`  | 30s      |

> Each FastAPI service must include `prometheus-fastapi-instrumentator` and call `Instrumentator().instrument(app).expose(app)` during startup for the `/metrics` endpoint to exist.

---

## Usage

### Install

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f infra/monitoring/kube-prometheus-stack-values.yaml

kubectl apply -f infra/monitoring/service-monitors.yaml
```

### Access Grafana

```bash
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring
# Open http://localhost:3000 — admin / changeme
```

### Access Prometheus

```bash
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 -n monitoring
# Open http://localhost:9090
```

### Uninstall

```bash
helm uninstall monitoring -n monitoring
kubectl delete -f infra/monitoring/service-monitors.yaml
```
