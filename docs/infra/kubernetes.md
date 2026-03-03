# Kubernetes — Manifests and Deployment

This document describes the Kubernetes manifests for the US Law RAG system. All manifests live in `infra/k8s/base/` and are managed with Kustomize.

---

## Overview

All application workloads run in the `rag-us-law` namespace. External traffic enters through an NGINX Ingress controller which routes to the frontend and the API Gateway. The API Gateway is the single internal entry point for all API calls; backend services are not reachable from outside the cluster.

```
Internet
   │
   ▼
NGINX Ingress
   ├─ /       → frontend (port 80)
   └─ /api    → api-gateway (port 80)
                    ├─ auth-api    (8001)
                    ├─ user-api    (8002)
                    └─ chat-api    (8000)

ingestion-worker  (no HTTP — runs as a background worker)
```

---

## Files

| File | Contents |
|------|---------|
| `namespace.yaml` | `rag-us-law` namespace |
| `api-gateway.yaml` | Deployment + ClusterIP Service (port 8080 → 80) |
| `auth-api.yaml` | Deployment + ClusterIP Service (port 8001) |
| `user-api.yaml` | Deployment + ClusterIP Service (port 8002) |
| `chat-api.yaml` | Deployment + ClusterIP Service (port 8000) |
| `ingestion-worker.yaml` | Deployment only — no service exposed |
| `frontend.yaml` | Deployment + ClusterIP Service (port 80) |
| `ingress.yaml` | NGINX Ingress routing rules |
| `kustomization.yaml` | Kustomize entrypoint listing all resources |

---

## Services and Resources

| Service | Replicas | CPU Request/Limit | Memory Request/Limit |
|---------|----------|-------------------|----------------------|
| api-gateway | 2 | 100m / 500m | 128Mi / 512Mi |
| auth-api | 2 | 100m / 500m | 128Mi / 512Mi |
| user-api | 2 | 100m / 500m | 128Mi / 512Mi |
| chat-api | 2 | 200m / 1000m | 256Mi / 1Gi |
| ingestion-worker | 1 | 200m / 1000m | 256Mi / 2Gi |
| frontend | 2 | 50m / 200m | 64Mi / 256Mi |

`chat-api` and `ingestion-worker` receive higher limits because they run the RAG pipeline and LLM calls.

---

## Health Checks

Every HTTP service defines readiness and liveness probes against its `/health` endpoint. Adjust `initialDelaySeconds` if a service takes longer to start (e.g. when loading large model weights).

---

## Secrets

Each Deployment references a Kubernetes Secret via `envFrom.secretRef`. Create these secrets before deploying:

```bash
kubectl create secret generic api-gateway-secret \
  --from-env-file=app/api-gateway/.env \
  -n rag-us-law

kubectl create secret generic auth-api-secret \
  --from-env-file=app/auth-api/.env \
  -n rag-us-law

kubectl create secret generic user-api-secret \
  --from-env-file=app/user-api/.env \
  -n rag-us-law

kubectl create secret generic chat-api-secret \
  --from-env-file=app/chat-api/.env \
  -n rag-us-law

kubectl create secret generic ingestion-worker-secret \
  --from-env-file=app/ingestion-worker/.env \
  -n rag-us-law
```

---

## Ingress

The Ingress uses the `nginx` ingress class. TLS is supported via cert-manager; the relevant annotations and `tls` block are present but commented out in `ingress.yaml`. Replace `yourdomain.com` with the real hostname before deploying.

---

## Usage

```bash
# Apply the full base layer
kubectl apply -k infra/k8s/base

# Check rollout status
kubectl rollout status deployment -n rag-us-law

# Tail logs for a service
kubectl logs -f deployment/api-gateway -n rag-us-law
```
