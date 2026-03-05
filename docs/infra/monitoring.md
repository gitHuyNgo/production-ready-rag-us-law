# Monitoring — Prometheus, Grafana & Alertmanager

This document describes the observability stack for the US Law RAG system. All monitoring configuration lives in `monitoring/`.

---

## Overview

Monitoring is provided by the **kube-prometheus-stack** Helm chart, which bundles:

- **Prometheus** — metrics collection and storage (time-series database with 15-day retention by default).
- **Grafana** — dashboards and visualisation.
- **Alertmanager** — alert routing, grouping, and deduplication.
- **node-exporter** — per-node OS and hardware metrics (CPU, memory, disk, network).
- **kube-state-metrics** — Kubernetes object-level metrics (pod restarts, resource requests vs limits, replica counts, etc.).

```
┌─ Application Pods ───────────────────────────────────────┐
│                                                           │
│  api-gateway  ──── /metrics ──┐                           │
│  auth-api     ──── /metrics ──┤                           │
│  user-api     ──── /metrics ──┤  ServiceMonitors          │
│  chat-api     ──── /metrics ──┤  (scrape config)          │
│                               │                           │
└───────────────────────────────┤───────────────────────────┘
                                │
                                ▼
┌─ Monitoring Namespace ────────────────────────────────────┐
│                                                           │
│  Prometheus ◄───── ServiceMonitors                        │
│     │              (auto-discovered)                      │
│     │                                                     │
│     ├──── stores metrics (15 day retention)               │
│     │                                                     │
│     ├──► Alertmanager ──► Slack / PagerDuty / Email       │
│     │    (evaluates alert rules)                          │
│     │                                                     │
│     └──► Grafana ──► Dashboards                           │
│          (queries Prometheus)                             │
│                                                           │
│  node-exporter (DaemonSet on every node)                  │
│     └── CPU, memory, disk, network per node               │
│                                                           │
│  kube-state-metrics                                       │
│     └── pod status, replica counts, resource usage        │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Files

| File | Purpose |
| --- | --- |
| `kube-prometheus-stack-values.yaml` | Helm values — configures Prometheus, Grafana, Alertmanager, resource limits |
| `service-monitors.yaml` | `ServiceMonitor` CRDs that tell Prometheus which application pods to scrape |

---

## Components (Deep Dive)

### Prometheus

**What it does:** Pulls (scrapes) metrics from application pods every 30 seconds. Stores them as time-series data with labels.

**How scraping works:**

```
Every 30 seconds:
  Prometheus → HTTP GET http://api-gateway-pod:8080/metrics
  Response:
    # HELP http_requests_total Total HTTP requests
    # TYPE http_requests_total counter
    http_requests_total{method="GET",path="/health",status="200"} 15234
    http_requests_total{method="POST",path="/chat/",status="200"} 892
    http_requests_total{method="POST",path="/chat/",status="500"} 3

    # HELP http_request_duration_seconds Request latency
    # TYPE http_request_duration_seconds histogram
    http_request_duration_seconds_bucket{path="/chat/",le="0.1"} 50
    http_request_duration_seconds_bucket{path="/chat/",le="0.5"} 200
    http_request_duration_seconds_bucket{path="/chat/",le="1.0"} 500
    http_request_duration_seconds_bucket{path="/chat/",le="5.0"} 880
    http_request_duration_seconds_bucket{path="/chat/",le="+Inf"} 892
```

**Configuration:**
- `serviceMonitorSelectorNilUsesHelmValues: false` — scrape all ServiceMonitors in all namespaces, not just the monitoring namespace
- Retention: 15 days (adjust for longer history or add remote-write to Thanos/Cortex)
- Resources: 200m CPU / 512Mi request → 1000m / 2Gi limit

### Grafana

**What it does:** Provides a web UI for building dashboards and querying Prometheus.

**Access:**

```bash
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring
# Open http://localhost:3000
# Login: admin / changeme (override this in production!)
```

**Default admin password:** `changeme` — override before deploying:

```bash
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  --set grafana.adminPassword="$(openssl rand -base64 24)" \
  -f monitoring/kube-prometheus-stack-values.yaml
```

**Useful PromQL queries for this project:**

| What | Query |
| --- | --- |
| Request rate (per service) | `rate(http_requests_total{namespace="rag-us-law"}[5m])` |
| Error rate | `rate(http_requests_total{status=~"5.."}[5m])` |
| P95 latency | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` |
| Chat API latency (RAG pipeline) | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{app="chat-api",path="/chat/"}[5m]))` |
| Pod restarts | `kube_pod_container_status_restarts_total{namespace="rag-us-law"}` |
| Memory usage vs limit | `container_memory_working_set_bytes / kube_pod_container_resource_limits{resource="memory"}` |
| CPU throttling | `rate(container_cpu_cfs_throttled_seconds_total[5m])` |

### Alertmanager

**What it does:** Receives alerts from Prometheus, deduplicates them, groups them, and routes them to receivers (Slack, PagerDuty, email).

**Deployed and ready;** configure receivers in a separate Secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-config
  namespace: monitoring
stringData:
  alertmanager.yaml: |
    receivers:
      - name: slack
        slack_configs:
          - api_url: https://hooks.slack.com/services/T00/B00/XXXX
            channel: '#alerts'
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ .CommonAnnotations.description }}'
    route:
      receiver: slack
      group_by: ['alertname', 'namespace']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
```

**Recommended alert rules for this project:**

| Alert | Condition | Severity |
| --- | --- | --- |
| HighErrorRate | `rate(http_requests_total{status=~"5.."}[5m]) > 0.05` | critical |
| PodCrashLooping | `kube_pod_container_status_restarts_total > 5` (in 1h) | warning |
| HighLatency | P95 latency > 5s for chat-api | warning |
| PVCAlmostFull | PVC usage > 80% | warning |
| NodeNotReady | `kube_node_status_condition{condition="Ready",status="true"} == 0` | critical |
| CertExpiringSoon | cert-manager certificate expires in < 14 days | warning |

---

## ServiceMonitors

`service-monitors.yaml` registers ServiceMonitors in the `monitoring` namespace:

| ServiceMonitor | Target | Scrape path | Interval | Port |
| --- | --- | --- | --- | --- |
| `api-gateway` | `app: api-gateway` in `rag-us-law` | `/metrics` | 30s | 8080 |
| `auth-api` | `app: auth-api` in `rag-us-law` | `/metrics` | 30s | 8001 |
| `user-api` | `app: user-api` in `rag-us-law` | `/metrics` | 30s | 8002 |
| `chat-api` | `app: chat-api` in `rag-us-law` | `/metrics` | 30s | 8000 |

**How ServiceMonitors work:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: api-gateway
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: ["rag-us-law"]
  selector:
    matchLabels:
      app: api-gateway            # matches the Service's labels
  endpoints:
    - port: http                  # named port on the Service
      path: /metrics
      interval: 30s
```

Prometheus watches for ServiceMonitor resources. When it finds one, it discovers all pods matching the selector and adds them to its scrape list. When pods scale up or down, Prometheus automatically adjusts.

### Application Instrumentation

Each FastAPI service must include `prometheus-fastapi-instrumentator`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

This automatically exposes:
- `http_requests_total` — counter with labels: method, path, status
- `http_request_duration_seconds` — histogram with labels: method, path
- `http_requests_in_progress` — gauge of concurrent requests

---

## Usage

### Install

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f monitoring/kube-prometheus-stack-values.yaml

kubectl apply -f monitoring/service-monitors.yaml
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
# Go to Status → Targets to see all scrape targets
```

### Verify Scraping

```bash
# Check that all targets are UP
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 -n monitoring
# Open http://localhost:9090/targets
# All ServiceMonitors should show state "UP"

# Quick test query
curl -s 'http://localhost:9090/api/v1/query?query=up{namespace="rag-us-law"}' | jq '.data.result[] | {instance: .metric.instance, up: .value[1]}'
```

### Uninstall

```bash
helm uninstall monitoring -n monitoring
kubectl delete -f monitoring/service-monitors.yaml
```

---

## Storage and Retention

Prometheus stores metrics on disk. With 4 services scraped every 30s and ~100 metrics per service:

```
4 services × 100 metrics × 2 samples/min = 800 samples/minute
800 × 60 × 24 = 1,152,000 samples/day
At ~1.5 bytes/sample compressed = ~1.7 MB/day
15 days retention = ~25 MB
```

This is very small. Even with 10x more metrics, Prometheus storage is typically < 1 GB for a 15-day window.

For longer retention (months/years), configure remote-write to a long-term storage backend:
- **Thanos** — adds a sidecar to Prometheus that uploads blocks to S3
- **Cortex** — horizontally scalable Prometheus-compatible storage
- **Amazon Managed Prometheus** — fully managed, no infrastructure to manage
