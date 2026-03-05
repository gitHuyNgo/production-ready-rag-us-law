# Kubernetes — Manifests and Deployment

This document describes the Kubernetes manifests for the US Law RAG system. All manifests live in `k8s/base/` and are managed with Kustomize.

---

## Overview

All application workloads run in the `rag-us-law` namespace. External traffic enters through an NGINX Ingress controller which routes to the frontend and the API Gateway. The API Gateway is the single internal entry point for all API calls; backend services are not reachable from outside the cluster.

```mermaid
graph TD
    INET["Internet"]
    NLB["AWS NLB (public IP)"]
    NGINX["NGINX Ingress Controller (ingress-nginx namespace)"]
    FE["frontend :80<br/>static React/Vite app served by NGINX"]
    GW["api-gateway :80<br/>proxies to auth/user/chat services"]
    AUTH["auth-api :8001<br/>identity, JWT, OIDC"]
    USER["user-api :8002<br/>profile CRUD"]
    CHAT["chat-api :8000<br/>RAG pipeline, WebSocket"]
    ING["ingestion-worker<br/>no HTTP — background worker"]

    INET --> NLB --> NGINX
    NGINX -- "/" --> FE
    NGINX -- "/api" --> GW
    GW -- "/auth/*" --> AUTH
    GW -- "/profiles/*" --> USER
    GW -- "/chat/*" --> CHAT
```

---

## Directory Structure

```
k8s/
├── base/                          ← base manifests (environment-agnostic)
│   ├── kustomization.yaml         ← Kustomize entrypoint
│   ├── namespace.yaml
│   ├── api-gateway.yaml           ← Deployment + Service
│   ├── auth-api.yaml              ← Deployment + Service
│   ├── user-api.yaml              ← Deployment + Service
│   ├── chat-api.yaml              ← Deployment + Service
│   ├── ingestion-worker.yaml      ← Deployment only (no Service)
│   ├── frontend.yaml              ← Deployment + Service
│   └── ingress.yaml               ← NGINX Ingress routing rules
└── overlays/                      ← environment-specific patches (see below)
    ├── dev/
    │   ├── kustomization.yaml
    │   └── patches/
    └── prod/
        ├── kustomization.yaml
        └── patches/
```

---

## Application Manifests

### Files and Resources

| File | Kind | Name | Ports |
| --- | --- | --- | --- |
| `namespace.yaml` | Namespace | `rag-us-law` | — |
| `api-gateway.yaml` | Deployment + Service (ClusterIP) | `api-gateway` | 8080 → 80 |
| `auth-api.yaml` | Deployment + Service (ClusterIP) | `auth-api` | 8001 |
| `user-api.yaml` | Deployment + Service (ClusterIP) | `user-api` | 8002 |
| `chat-api.yaml` | Deployment + Service (ClusterIP) | `chat-api` | 8000 |
| `ingestion-worker.yaml` | Deployment | `ingestion-worker` | — (no HTTP) |
| `frontend.yaml` | Deployment + Service (ClusterIP) | `frontend` | 80 |
| `ingress.yaml` | Ingress | `rag-us-law-ingress` | — |

### Resource Allocations

| Service | Replicas | CPU Request/Limit | Memory Request/Limit | Rationale |
| --- | --- | --- | --- | --- |
| api-gateway | 2 | 100m / 500m | 128Mi / 512Mi | Lightweight proxy, no business logic |
| auth-api | 2 | 100m / 500m | 128Mi / 512Mi | Small CRUD operations |
| user-api | 2 | 100m / 500m | 128Mi / 512Mi | Simple MongoDB read/write |
| chat-api | 2 | 200m / 1000m | 256Mi / 1Gi | RAG pipeline, rerankers, LLM streaming |
| ingestion-worker | 1 | 200m / 1000m | 256Mi / 2Gi | PDF processing, batch embedding (memory-intensive) |
| frontend | 2 | 50m / 200m | 64Mi / 256Mi | Static file server (NGINX) |

`chat-api` and `ingestion-worker` get higher limits because they run the RAG pipeline with large embedding vectors and LLM responses in memory.

---

## Health Checks

Every HTTP service defines readiness and liveness probes:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 5      # wait 5s before first check
  periodSeconds: 10            # check every 10s

livenessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 15     # wait 15s (app fully started)
  periodSeconds: 20            # check every 20s
```

**Readiness vs Liveness:**

| Probe | What it checks | Failure action |
| --- | --- | --- |
| **Readiness** | "Can this pod serve traffic?" | Remove pod from Service endpoints (stop sending requests) |
| **Liveness** | "Is this pod alive?" | Kill and restart the pod |

During a rolling update, the new pod must pass its readiness probe before the old pod is terminated. This guarantees zero-downtime deployments.

**Why different `initialDelaySeconds`?** Readiness check starts at 5s — we want to detect when the pod is ready to serve ASAP. Liveness check starts at 15s — we give the application more time to fully initialize (database connections, loading models) before declaring it dead.

---

## Secrets and ConfigMaps

### Secrets (created manually or via External Secrets Operator)

Each Deployment references a Kubernetes Secret via `envFrom.secretRef`:

```yaml
envFrom:
  - secretRef:
      name: auth-api-secret
```

Create secrets before deploying:

```bash
kubectl create secret generic api-gateway-secret \
  --from-file=JWT_PUBLIC_KEY=./app/auth-api/public.pem \
  -n rag-us-law

kubectl create secret generic auth-api-secret \
  --from-literal=AUTH_DB_URL="postgresql+psycopg2://auth_user:PASS@auth-db:5432/auth_db" \
  --from-file=JWT_PRIVATE_KEY=./app/auth-api/private.pem \
  --from-file=JWT_PUBLIC_KEY=./app/auth-api/public.pem \
  --from-literal=SESSION_SECRET_KEY="$(openssl rand -hex 32)" \
  -n rag-us-law

kubectl create secret generic chat-api-secret \
  --from-literal=OPENAI_API_KEY="sk-..." \
  --from-literal=COHERE_API_KEY="..." \
  -n rag-us-law

kubectl create secret generic ingestion-worker-secret \
  --from-literal=OPENAI_API_KEY="sk-..." \
  -n rag-us-law

kubectl create secret generic user-api-secret \
  --from-literal=USER_DB_URL="mongodb://user-db:27017/user_db" \
  --from-file=JWT_PUBLIC_KEY=./app/auth-api/public.pem \
  -n rag-us-law
```

### ConfigMap (recommended — not yet in base)

Non-sensitive config should be in a ConfigMap, not a Secret:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: rag-us-law
data:
  AUTH_API_URL: "http://auth-api:8001"
  USER_API_URL: "http://user-api:8002"
  CHAT_API_URL: "http://chat-api:8000"
  WEAVIATE_URL: "http://weaviate:8080"
  REDIS_URL: "redis://redis:6379"
  LOG_LEVEL: "INFO"
```

---

## Ingress

The Ingress uses the `nginx` ingress class:

```yaml
spec:
  rules:
    - host: yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-gateway
                port:
                  number: 80
```

**TLS:** cert-manager annotations and the `tls` block are present but commented out. To enable HTTPS:

1. Install cert-manager and create a `ClusterIssuer`
2. Uncomment the annotations in `ingress.yaml`
3. Uncomment the `tls` block
4. Replace `yourdomain.com` with the real hostname
5. Apply — cert-manager will automatically provision a Let's Encrypt certificate

---

## Kustomize Overlays

The base manifests are environment-agnostic — they use `image: api-gateway:latest` without a registry prefix. Overlays customize for each environment.

### Dev Overlay

```yaml
# k8s/overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: rag-us-law-dev
resources:
  - ../../base
commonLabels:
  env: dev
images:
  - name: api-gateway
    newName: 123456789.dkr.ecr.us-east-1.amazonaws.com/api-gateway
    newTag: dev-latest
```

**Apply:** `kubectl apply -k k8s/overlays/dev`

### Prod Overlay

```yaml
# k8s/overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: rag-us-law
resources:
  - ../../base
commonLabels:
  env: prod
images:
  - name: api-gateway
    newName: 123456789.dkr.ecr.us-east-1.amazonaws.com/api-gateway
    newTag: "1.0.0"
```

**Or use `kubectl set image` from CI** — the overlay provides defaults, CI overrides with the exact SHA tag at deploy time.

---

## Missing Infrastructure Manifests

The current base only includes application services. Production also needs StatefulSets for databases and middleware:

| Missing manifest | What it deploys | Storage |
| --- | --- | --- |
| `postgres.yaml` | PostgreSQL (auth-db) | 10Gi PVC (EBS) |
| `mongodb.yaml` | MongoDB (user-db) | 10Gi PVC (EBS) |
| `redis.yaml` | Redis Stack | 5Gi PVC (EBS) |
| `weaviate.yaml` | Weaviate vector DB | 20Gi PVC (EBS) |
| `cassandra.yaml` | Cassandra | 20Gi PVC (EBS) |
| `kafka.yaml` | Kafka + Zookeeper | 10Gi PVC (EBS) |
| `configmap.yaml` | Non-sensitive app config | — |

See [Platform Bootstrap](../lifecycles/2-platform-bootstrap.md) for the full StatefulSet manifests.

---

## Usage

```bash
# Apply the full base layer
kubectl apply -k k8s/base

# Apply a specific overlay
kubectl apply -k k8s/overlays/dev
kubectl apply -k k8s/overlays/prod

# Check rollout status
kubectl rollout status deployment -n rag-us-law

# Watch pods
kubectl get pods -n rag-us-law -w

# Tail logs for a service
kubectl logs -f deployment/api-gateway -n rag-us-law

# Describe a pod for debugging
kubectl describe pod api-gateway-xxxxx -n rag-us-law

# Port-forward to access a service locally
kubectl port-forward svc/api-gateway 8080:80 -n rag-us-law
```
