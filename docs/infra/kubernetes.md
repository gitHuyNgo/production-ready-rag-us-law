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

| File                    | Kind                             | Name                 | Ports       |
| ----------------------- | -------------------------------- | -------------------- | ----------- |
| `namespace.yaml`        | Namespace                        | `rag-us-law`         | —           |
| `api-gateway.yaml`      | Deployment + Service (ClusterIP) | `api-gateway`        | 8080 → 80   |
| `auth-api.yaml`         | Deployment + Service (ClusterIP) | `auth-api`           | 8001        |
| `user-api.yaml`         | Deployment + Service (ClusterIP) | `user-api`           | 8002        |
| `chat-api.yaml`         | Deployment + Service (ClusterIP) | `chat-api`           | 8000        |
| `ingestion-worker.yaml` | Deployment                       | `ingestion-worker`   | — (no HTTP) |
| `frontend.yaml`         | Deployment + Service (ClusterIP) | `frontend`           | 80          |
| `ingress.yaml`          | Ingress                          | `rag-us-law-ingress` | —           |

### Resource Allocations

| Service          | Replicas | CPU Request/Limit | Memory Request/Limit | Rationale                                          |
| ---------------- | -------- | ----------------- | -------------------- | -------------------------------------------------- |
| api-gateway      | 2        | 100m / 500m       | 128Mi / 512Mi        | Lightweight proxy, no business logic               |
| auth-api         | 2        | 100m / 500m       | 128Mi / 512Mi        | Small CRUD operations                              |
| user-api         | 2        | 100m / 500m       | 128Mi / 512Mi        | Simple MongoDB read/write                          |
| chat-api         | 2        | 200m / 1000m      | 256Mi / 1Gi          | RAG pipeline, rerankers, LLM streaming             |
| ingestion-worker | 1        | 200m / 1000m      | 256Mi / 2Gi          | PDF processing, batch embedding (memory-intensive) |
| frontend         | 2        | 50m / 200m        | 64Mi / 256Mi         | Static file server (NGINX)                         |

`chat-api` and `ingestion-worker` get higher limits because they run the RAG pipeline with large embedding vectors and LLM responses in memory.

---

## Health Checks

Every HTTP service defines readiness and liveness probes:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 5 # wait 5s before first check
  periodSeconds: 10 # check every 10s

livenessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 15 # wait 15s (app fully started)
  periodSeconds: 20 # check every 20s
```

**Readiness vs Liveness:**

| Probe         | What it checks                | Failure action                                            |
| ------------- | ----------------------------- | --------------------------------------------------------- |
| **Readiness** | "Can this pod serve traffic?" | Remove pod from Service endpoints (stop sending requests) |
| **Liveness**  | "Is this pod alive?"          | Kill and restart the pod                                  |

During a rolling update, the new pod must pass its readiness probe before the old pod is terminated. This guarantees zero-downtime deployments.

**Why different `initialDelaySeconds`?** Readiness check starts at 5s — we want to detect when the pod is ready to serve ASAP. Liveness check starts at 15s — we give the application more time to fully initialize (database connections, loading models) before declaring it dead.

---

## Secrets and ConfigMaps

### How secrets reach pods

Each Deployment loads its secrets via `envFrom.secretRef`, which injects every key in the named Kubernetes Secret as an environment variable:

```yaml
envFrom:
  - secretRef:
      name: auth-api-secret
```

There are two ways to create those Kubernetes Secrets — manual (local/dev) and External Secrets Operator (production).

---

### Option A — Manual (local dev / quick setup)

```bash
kubectl create secret generic api-gateway-secret \
  --from-literal=JWT_PUBLIC_KEY="$(cat ./app/auth-api/public.pem)" \
  -n rag-us-law

kubectl create secret generic auth-api-secret \
  --from-literal=AUTH_DB_URL="postgresql+psycopg2://auth_user:PASS@auth-db:5432/auth_db" \
  --from-literal=JWT_PRIVATE_KEY="$(cat ./app/auth-api/private.pem)" \
  --from-literal=JWT_PUBLIC_KEY="$(cat ./app/auth-api/public.pem)" \
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
  --from-literal=JWT_PUBLIC_KEY="$(cat ./app/auth-api/public.pem)" \
  -n rag-us-law
```

**Limitation:** PEM files must exist on the machine running `kubectl`. Not suitable for CI/CD or team environments.

---

### Option B — External Secrets Operator (production)

In production, secrets live in **AWS Secrets Manager**. The External Secrets Operator (ESO) runs inside the cluster and automatically creates and keeps the Kubernetes Secrets up to date. No secret values ever touch GitHub, CI/CD pipelines, or developer machines.

#### Mental model

```
┌─────────────────────────────────────────────────────────────┐
│  One-time setup (run manually, once ever)                   │
│                                                             │
│  openssl genrsa → private.pem + public.pem                  │
│  aws secretsmanager put-secret-value → stored in AWS        │
│  terraform apply → EKS + IAM role + OIDC trust              │
│  helm install external-secrets → ESO runs in cluster        │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│  Every deploy (GitHub Actions)                              │
│                                                             │
│  docker build → push to ECR                                 │
│  kubectl apply -k k8s/base/ → deploys ExternalSecret YAMLs  │
│                                                             │
│  GitHub Actions never sees or touches secret values         │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│  Inside the cluster (ESO runs continuously, independently)  │
│                                                             │
│  ESO reads ExternalSecret resources                         │
│  ESO authenticates to AWS Secrets Manager via IRSA          │
│  ESO pulls secret values                                    │
│  ESO creates/updates Kubernetes Secrets                     │
│  Pods read those Kubernetes Secrets as env vars             │
└─────────────────────────────────────────────────────────────┘
```

#### How ESO is trusted by AWS (IRSA — no static keys)

ESO does not use a password or access key. It uses **IRSA (IAM Roles for Service Accounts)** — a keyless identity system built into EKS:

```
EKS automatically mounts a signed identity token into the ESO pod
  ↓
ESO presents that token to AWS STS
  ↓
AWS STS checks: is this cluster's OIDC provider registered with my IAM?  → yes (Terraform)
AWS STS checks: does the IAM role trust this ServiceAccount's token?     → yes (trust policy)
  ↓
AWS STS returns temporary credentials (valid 1h, auto-refreshed)
  ↓
ESO uses those credentials to read Secrets Manager
```

The trust is established entirely by Terraform wiring the EKS cluster's OIDC endpoint into AWS IAM. No key is stored or shared.

#### Step 1 — Terraform: OIDC + IAM role (`terraform/eso.tf`)

```hcl
# Register the EKS cluster's OIDC endpoint with AWS IAM.
# This is what makes AWS trust the signed tokens EKS issues to pods.
data "tls_certificate" "eks" {
  url = module.eks.cluster_oidc_issuer_url
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = module.eks.cluster_oidc_issuer_url
}

# IAM role that ESO will assume.
# Trust policy: only the ESO ServiceAccount inside the cluster can assume this role.
data "aws_iam_policy_document" "eso_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:external-secrets:external-secrets"]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eso" {
  name               = "eso-secrets-manager-role"
  assume_role_policy = data.aws_iam_policy_document.eso_trust.json
}

# Allow ESO to read any secret under rag-us-law/*
data "aws_iam_policy_document" "eso_permissions" {
  statement {
    effect  = "Allow"
    actions = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = [
      "arn:aws:secretsmanager:${var.aws_region}:*:secret:rag-us-law/*"
    ]
  }
}

resource "aws_iam_role_policy" "eso" {
  name   = "eso-read-secrets"
  role   = aws_iam_role.eso.id
  policy = data.aws_iam_policy_document.eso_permissions.json
}

# Named containers in AWS Secrets Manager.
# Values are uploaded separately via CLI — never stored in Terraform state.
resource "aws_secretsmanager_secret" "jwt_private_key" {
  name = "rag-us-law/jwt-private-key"
}

resource "aws_secretsmanager_secret" "jwt_public_key" {
  name = "rag-us-law/jwt-public-key"
}

output "eso_role_arn" {
  value = aws_iam_role.eso.arn
}
```

> **Why create the secret resource in Terraform but not the value?**
> `aws_secretsmanager_secret` creates the named container — safe to track in Terraform state. The actual PEM content would appear in state as plaintext if set here, so it is uploaded separately via CLI after `terraform apply`.

#### Step 2 — Upload secret values (once, after terraform apply)

```bash
aws secretsmanager put-secret-value \
  --secret-id rag-us-law/jwt-private-key \
  --secret-string "$(cat app/auth-api/private.pem)"

aws secretsmanager put-secret-value \
  --secret-id rag-us-law/jwt-public-key \
  --secret-string "$(cat app/auth-api/public.pem)"
```

#### Step 3 — Install ESO (once, after terraform apply)

```bash
helm repo add external-secrets https://charts.external-secrets.io

helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$(terraform output -raw eso_role_arn)
```

The `--set` flag annotates the ESO ServiceAccount with the IAM role ARN from Terraform. This tells EKS which IAM role to issue credentials for when it mounts the identity token into the ESO pod.

#### Step 4 — ClusterSecretStore (`k8s/base/cluster-secret-store.yaml`)

Tells ESO which AWS region to read from and which ServiceAccount identity to authenticate with:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
```

#### Step 5 — ExternalSecret per service

Each ExternalSecret tells ESO which AWS secret to fetch and which Kubernetes Secret to create. The Kubernetes Secret name must match what the Deployment's `secretRef` expects — so the Deployment YAMLs need no changes.

**`k8s/base/auth-api-external-secret.yaml`:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: auth-api-secret
  namespace: rag-us-law
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: auth-api-secret # creates this K8s Secret → auth-api Deployment reads it
    creationPolicy: Owner
  data:
    - secretKey: JWT_PRIVATE_KEY
      remoteRef:
        key: rag-us-law/jwt-private-key
    - secretKey: JWT_PUBLIC_KEY
      remoteRef:
        key: rag-us-law/jwt-public-key
```

**`k8s/base/api-gateway-external-secret.yaml`:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-gateway-secret
  namespace: rag-us-law
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: api-gateway-secret # creates this K8s Secret → api-gateway Deployment reads it
    creationPolicy: Owner
  data:
    - secretKey: JWT_PUBLIC_KEY
      remoteRef:
        key: rag-us-law/jwt-public-key
```

ESO syncs every hour. On key rotation: update the value in AWS Secrets Manager → ESO picks it up on the next refresh → Kubernetes Secret is updated → pods rolling-restart to load the new value.

#### What GitHub Actions does (and does not do)

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123:role/github-actions-deploy
          aws-region: us-east-1

      - name: Build and push to ECR
        run: |
          docker build -t $ECR/auth-api:$SHA app/auth-api
          docker push $ECR/auth-api:$SHA

      - name: Deploy
        run: |
          aws eks update-kubeconfig --name rag-us-law
          kubectl apply -k k8s/base/
          kubectl set image deployment/auth-api auth-api=$ECR/auth-api:$SHA -n rag-us-law
```

GitHub Actions builds images and applies manifests. It has no permission to read JWT secrets in Secrets Manager. Secret injection happens entirely inside the cluster via ESO — CI/CD is not involved.

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

| Missing manifest | What it deploys          | Storage        |
| ---------------- | ------------------------ | -------------- |
| `postgres.yaml`  | PostgreSQL (auth-db)     | 10Gi PVC (EBS) |
| `mongodb.yaml`   | MongoDB (user-db)        | 10Gi PVC (EBS) |
| `redis.yaml`     | Redis Stack              | 5Gi PVC (EBS)  |
| `weaviate.yaml`  | Weaviate vector DB       | 20Gi PVC (EBS) |
| `cassandra.yaml` | Cassandra                | 20Gi PVC (EBS) |
| `kafka.yaml`     | Kafka + Zookeeper        | 10Gi PVC (EBS) |
| `configmap.yaml` | Non-sensitive app config | —              |

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
