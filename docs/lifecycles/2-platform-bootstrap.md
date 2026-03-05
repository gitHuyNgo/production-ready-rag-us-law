# Lifecycle 2 — Platform Bootstrap

> **Frequency:** Run once per cluster, then when platform config changes (new database, upgraded middleware version, new secret).
> **Tools:** Helm, kubectl, Kustomize
> **Who runs it:** DevOps engineer (could be automated via GitOps with ArgoCD/Flux later).

---

## What This Lifecycle Does

After Terraform creates the cluster (Lifecycle 1), you have bare EC2 nodes running kubelet. No databases, no ingress controller, no monitoring, no secrets. Platform bootstrap installs everything the application needs to run.

Think of this as **installing all the software on a new server** — the database server, the web server, the monitoring agent — before deploying your application code.

---

## What Gets Installed (In Order)

The order matters because of dependencies. You cannot create a Secret in a namespace that doesn't exist. You cannot deploy auth-api if PostgreSQL isn't running.

```
Phase 1: Cluster-Wide Tools
  ├── ingress-nginx         (routes external traffic into the cluster)
  ├── cert-manager          (auto-provisions TLS certificates)
  └── kube-prometheus-stack  (Prometheus + Grafana + Alertmanager)

Phase 2: Namespace + Configuration
  ├── rag-us-law namespace
  ├── ConfigMaps             (non-sensitive config: hostnames, ports, log levels)
  └── Secrets                (credentials: DB passwords, JWT keys, API keys)

Phase 3: Databases + Middleware (StatefulSets)
  ├── PostgreSQL (auth-db)   → stores user accounts, auth tokens
  ├── MongoDB (user-db)      → stores user profiles, preferences
  ├── Redis                  → session cache, semantic cache, rate limiting
  ├── Weaviate               → vector database for RAG embeddings
  ├── Cassandra              → chat message history (high write throughput)
  ├── Zookeeper              → Kafka coordination
  └── Kafka                  → async event streaming (ingestion pipeline)

Phase 4: Database Migrations
  ├── alembic upgrade head   (PostgreSQL schema)
  ├── CQL scripts            (Cassandra keyspace + tables)
  └── Weaviate schema        (vector collections)
```

---

## Phase 1: Cluster-Wide Tools (Helm Charts)

### Ingress Controller (NGINX)

The ingress controller is the front door to your cluster. It watches for `Ingress` resources and configures NGINX to route traffic accordingly. On EKS, it automatically provisions an AWS Network Load Balancer (NLB) that has a public IP.

```
Internet
   │
   ▼
AWS NLB (public IP)                  ← created automatically by ingress-nginx
   │
   ▼
ingress-nginx pod (in cluster)       ← reads Ingress resources, configures routing
   │
   ├── Host: yourdomain.com /        → frontend:80
   └── Host: yourdomain.com /api     → api-gateway:80
```

**Installation:**

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  -n ingress-nginx --create-namespace \
  --set controller.service.type=LoadBalancer \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"=nlb \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-scheme"=internet-facing
```

**What happens behind the scenes:**

1. Helm creates a `Deployment` with NGINX pods in the `ingress-nginx` namespace
2. Helm creates a `Service` of type `LoadBalancer`
3. The AWS Cloud Controller Manager sees the `LoadBalancer` service
4. AWS creates a Network Load Balancer in the **public subnets** (tagged `kubernetes.io/role/elb = 1` by Terraform)
5. The NLB gets a public DNS name like `a1b2c3d4-abc123.elb.us-east-1.amazonaws.com`
6. You point your domain's DNS (Route53) at this NLB

### cert-manager

Automatically provisions and renews TLS certificates from Let's Encrypt.

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm upgrade --install cert-manager jetstack/cert-manager \
  -n cert-manager --create-namespace \
  --set crds.enabled=true
```

Then create a `ClusterIssuer`:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

**What happens when you uncomment the TLS block in `ingress.yaml`:**

1. cert-manager sees the `cert-manager.io/cluster-issuer: letsencrypt-prod` annotation
2. It creates an ACME challenge (temporary Ingress route at `/.well-known/acme-challenge/`)
3. Let's Encrypt verifies your domain
4. cert-manager receives the certificate and stores it as a Kubernetes Secret
5. ingress-nginx reads the Secret and serves HTTPS
6. cert-manager auto-renews 30 days before expiration

### kube-prometheus-stack

See [Monitoring docs](../infra/monitoring.md) for full details. The short version:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  --set grafana.adminPassword="$(openssl rand -base64 24)" \
  -f monitoring/kube-prometheus-stack-values.yaml

kubectl apply -f monitoring/service-monitors.yaml
```

This installs Prometheus (scrapes metrics), Grafana (dashboards), and Alertmanager (alerts to Slack/PagerDuty).

---

## Phase 2: Namespace, ConfigMaps, and Secrets

### Namespace

```bash
kubectl apply -f k8s/base/namespace.yaml
```

All application resources live in `rag-us-law`. This provides:
- **Resource isolation** — you can set ResourceQuotas per namespace
- **RBAC boundaries** — dev team gets access to `rag-us-law` but not `monitoring`
- **Network policies** — restrict which namespaces can talk to each other

### ConfigMap (Non-Sensitive Configuration)

ConfigMaps hold configuration that is **not secret** — hostnames, URLs, feature flags, log levels. Changing a ConfigMap does not require rotating encryption keys or secret management workflows.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: rag-us-law
data:
  # Service discovery — how services find each other inside the cluster
  AUTH_API_URL: "http://auth-api:8001"
  USER_API_URL: "http://user-api:8002"
  CHAT_API_URL: "http://chat-api:8000"
  WEAVIATE_URL: "http://weaviate:8080"
  REDIS_URL: "redis://redis:6379"
  AUTH_DB_HOST: "auth-db"
  USER_DB_HOST: "user-db"
  CASSANDRA_CONTACT_POINTS: "cassandra"
  KAFKA_BOOTSTRAP_SERVERS: "kafka:9092"

  # Application settings
  LOG_LEVEL: "INFO"
  APP_ENV: "production"
  JWT_ALGORITHM: "RS256"
```

**Why these hostnames work:** Kubernetes DNS resolves `auth-db` to `auth-db.rag-us-law.svc.cluster.local` — the headless Service IP for the PostgreSQL StatefulSet. Every service name in the ConfigMap corresponds to a Kubernetes `Service` resource.

### Secrets (Sensitive Configuration)

Secrets hold credentials, keys, and anything that should not appear in git or logs.

```bash
# Database credentials
kubectl create secret generic auth-db-secret \
  --from-literal=POSTGRES_USER=auth_user \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -base64 32)" \
  -n rag-us-law

kubectl create secret generic user-db-secret \
  --from-literal=MONGO_ROOT_USER=admin \
  --from-literal=MONGO_ROOT_PASSWORD="$(openssl rand -base64 32)" \
  -n rag-us-law

# Application secrets (per service)
kubectl create secret generic auth-api-secret \
  --from-literal=AUTH_DB_URL="postgresql+psycopg2://auth_user:PASSWORD@auth-db:5432/auth_db" \
  --from-file=JWT_PRIVATE_KEY=./app/auth-api/private.pem \
  --from-file=JWT_PUBLIC_KEY=./app/auth-api/public.pem \
  -n rag-us-law

kubectl create secret generic chat-api-secret \
  --from-literal=OPENAI_API_KEY="sk-..." \
  -n rag-us-law

kubectl create secret generic api-gateway-secret \
  --from-file=JWT_PUBLIC_KEY=./app/auth-api/public.pem \
  -n rag-us-law

kubectl create secret generic ingestion-worker-secret \
  --from-literal=OPENAI_API_KEY="sk-..." \
  -n rag-us-law
```

**How pods consume them:**

```yaml
# In a Deployment spec
envFrom:
  - configMapRef:
      name: app-config          # LOG_LEVEL, REDIS_URL, etc.
  - secretRef:
      name: auth-api-secret     # AUTH_DB_URL, JWT keys
```

**Production secret management:** In a real production setup, you would use AWS Secrets Manager or HashiCorp Vault instead of `kubectl create secret`. The **External Secrets Operator** can sync AWS Secrets Manager entries into Kubernetes Secrets automatically:

```
AWS Secrets Manager          External Secrets Operator          K8s Secret
  "auth-db-password"    →    watches + syncs every 60s    →    auth-db-secret
```

This way, secrets are never stored in git or typed on the command line.

---

## Phase 3: Databases and Middleware (StatefulSets)

### Why StatefulSet (Not Deployment)

Databases need three guarantees that `Deployment` does not provide:

| Guarantee | StatefulSet | Deployment |
| --- | --- | --- |
| **Stable network identity** | `auth-db-0`, `auth-db-1` — predictable forever | `auth-db-7d9f8b-xkq2p` — random, changes on restart |
| **Stable storage binding** | PVC `data-auth-db-0` is always bound to pod 0 | No guarantee which pod gets which PVC |
| **Ordered startup/shutdown** | Pod 0 starts first, then pod 1 | All pods start simultaneously |

### How Kubernetes Volumes Work (Deep Dive)

This is the #1 source of confusion when coming from Docker Compose.

**Docker Compose volumes** are directories on your laptop:

```
docker volume create auth_db_data
→ Creates /var/lib/docker/volumes/auth_db_data/_data on your Mac
→ If your laptop dies, the data is gone
```

**Kubernetes volumes** are cloud-managed block storage:

```
Pod creates a PersistentVolumeClaim (PVC)
  → "I need 10Gi of ReadWriteOnce storage"

StorageClass (gp3 by default on EKS) handles the request
  → Calls AWS EBS CSI driver

EBS CSI driver provisions real AWS infrastructure
  → Creates an EBS volume (vol-0abc123) in the same AZ as the node
  → Formats it as ext4
  → Attaches it to the EC2 instance
  → Mounts it at the pod's mountPath

If the pod moves to a different node:
  → EBS detaches from old node
  → EBS attaches to new node (must be in the same AZ)
  → Data is preserved
```

```
 ┌─── Your Pod ────────────────────────┐
 │  Container: postgres                 │
 │    mountPath: /var/lib/postgresql     │
 │         │                            │
 └─────────│────────────────────────────┘
           │
 ┌─────────▼────────────────────────────┐
 │  PersistentVolumeClaim (PVC)         │
 │    name: auth-db-data-auth-db-0      │
 │    storage: 10Gi                     │
 │    accessMode: ReadWriteOnce         │
 └──────────│───────────────────────────┘
            │ bound to
 ┌──────────▼───────────────────────────┐
 │  PersistentVolume (PV)               │
 │    (auto-created by StorageClass)    │
 │    volumeHandle: vol-0abc123def456   │
 └──────────│───────────────────────────┘
            │ backed by
 ┌──────────▼───────────────────────────┐
 │  AWS EBS Volume (real disk)          │
 │    vol-0abc123def456                 │
 │    10 GiB, gp3, us-east-1a          │
 │    Exists independently of any EC2   │
 │    Survives node crashes             │
 │    Billed at $0.08/GB/month          │
 └──────────────────────────────────────┘
```

**`ReadWriteOnce` (RWO):** Only one node can mount the volume at a time. This is correct for databases (Postgres, Mongo, etc.) because they expect exclusive access to their data directory.

**`ReadWriteMany` (RWX):** Multiple nodes can mount simultaneously. Requires EFS (NFS-based), not EBS. Useful for shared file storage but not for databases.

### PostgreSQL (auth-db)

Stores user accounts, password hashes, refresh tokens, and OAuth grants for the auth-api.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: auth-db
  namespace: rag-us-law
spec:
  serviceName: auth-db           # headless service name
  replicas: 1
  selector:
    matchLabels:
      app: auth-db
  template:
    metadata:
      labels:
        app: auth-db
    spec:
      containers:
        - name: postgres
          image: postgres:16
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: auth_db
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: auth-db-secret
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: auth-db-secret
                  key: POSTGRES_PASSWORD
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          volumeMounts:
            - name: auth-db-data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
  volumeClaimTemplates:
    - metadata:
        name: auth-db-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 10Gi
```

**Headless Service** (required for StatefulSet DNS):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: auth-db
  namespace: rag-us-law
spec:
  clusterIP: None              # headless — no virtual IP
  selector:
    app: auth-db
  ports:
    - port: 5432
      targetPort: 5432
```

**Why `clusterIP: None`?** A normal Service has a virtual IP (ClusterIP) and load-balances traffic across pods. A headless Service skips the virtual IP and returns the pod IPs directly via DNS. This is essential for databases because:
- Clients connect to a *specific* instance, not a random one
- DNS resolves `auth-db-0.auth-db.rag-us-law.svc.cluster.local` directly to that pod's IP
- The short name `auth-db` also resolves (to all pod IPs), which works for single-replica

### MongoDB (user-db)

Stores user profiles, preferences, and document metadata as flexible JSON documents.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: user-db
  namespace: rag-us-law
spec:
  serviceName: user-db
  replicas: 1
  selector:
    matchLabels:
      app: user-db
  template:
    metadata:
      labels:
        app: user-db
    spec:
      containers:
        - name: mongodb
          image: mongo:7
          ports:
            - containerPort: 27017
          env:
            - name: MONGO_INITDB_ROOT_USERNAME
              valueFrom:
                secretKeyRef:
                  name: user-db-secret
                  key: MONGO_ROOT_USER
            - name: MONGO_INITDB_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: user-db-secret
                  key: MONGO_ROOT_PASSWORD
          volumeMounts:
            - name: user-db-data
              mountPath: /data/db
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
  volumeClaimTemplates:
    - metadata:
        name: user-db-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 10Gi
```

### Redis

Redis stores everything in RAM during operation but writes to disk for durability:
- **RDB snapshots** — periodic full dump to `dump.rdb`
- **AOF (Append Only File)** — logs every write to `appendonly.aof`

Without a volume, every Redis restart (pod crash, node drain, deploy) wipes all sessions, caches, and rate-limit counters. Users get logged out, caches go cold, and rate limiters reset.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: rag-us-law
spec:
  serviceName: redis
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis/redis-stack:latest
          ports:
            - containerPort: 6379
          volumeMounts:
            - name: redis-data
              mountPath: /data
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "1Gi"
  volumeClaimTemplates:
    - metadata:
        name: redis-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 5Gi
```

### Weaviate (Vector Database)

Stores document embeddings for the RAG retrieval pipeline. Losing this data means re-running the entire ingestion pipeline (re-embedding all law documents with the LLM), which costs real money in API calls.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: weaviate
  namespace: rag-us-law
spec:
  serviceName: weaviate
  replicas: 1
  selector:
    matchLabels:
      app: weaviate
  template:
    metadata:
      labels:
        app: weaviate
    spec:
      containers:
        - name: weaviate
          image: cr.weaviate.io/semitechnologies/weaviate:1.30.0
          args: ["--host", "0.0.0.0", "--port", "8080", "--scheme", "http"]
          ports:
            - containerPort: 8080
            - containerPort: 50051
          env:
            - name: QUERY_DEFAULTS_LIMIT
              value: "25"
            - name: AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED
              value: "true"
            - name: PERSISTENCE_DATA_PATH
              value: /var/lib/weaviate
            - name: DEFAULT_VECTORIZER_MODULE
              value: none
            - name: CLUSTER_HOSTNAME
              value: node1
          volumeMounts:
            - name: weaviate-data
              mountPath: /var/lib/weaviate
          readinessProbe:
            httpGet:
              path: /v1/.well-known/ready
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2"
              memory: "4Gi"
  volumeClaimTemplates:
    - metadata:
        name: weaviate-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 20Gi
```

### Cassandra

Stores chat message history. Cassandra is designed for high write throughput — ideal for storing every message in every conversation.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: cassandra
  namespace: rag-us-law
spec:
  serviceName: cassandra
  replicas: 1
  selector:
    matchLabels:
      app: cassandra
  template:
    metadata:
      labels:
        app: cassandra
    spec:
      containers:
        - name: cassandra
          image: cassandra:5
          ports:
            - containerPort: 9042
          env:
            - name: CASSANDRA_CLUSTER_NAME
              value: chat-memory
            - name: MAX_HEAP_SIZE
              value: "512M"
            - name: HEAP_NEWSIZE
              value: "128M"
          volumeMounts:
            - name: cassandra-data
              mountPath: /var/lib/cassandra
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2"
              memory: "2Gi"
  volumeClaimTemplates:
    - metadata:
        name: cassandra-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 20Gi
```

### Kafka + Zookeeper

Kafka handles async event streaming for the ingestion pipeline. When a user uploads a document, the API publishes an event to Kafka. The `ingestion-worker` consumes it, processes the document, generates embeddings, and stores them in Weaviate.

```yaml
# Zookeeper (Kafka coordination)
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: zookeeper
  namespace: rag-us-law
spec:
  serviceName: zookeeper
  replicas: 1
  selector:
    matchLabels:
      app: zookeeper
  template:
    metadata:
      labels:
        app: zookeeper
    spec:
      containers:
        - name: zookeeper
          image: confluentinc/cp-zookeeper:7.5.0
          ports:
            - containerPort: 2181
          env:
            - name: ZOOKEEPER_CLIENT_PORT
              value: "2181"
            - name: ZOOKEEPER_TICK_TIME
              value: "2000"
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
---
# Kafka
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kafka
  namespace: rag-us-law
spec:
  serviceName: kafka
  replicas: 1
  selector:
    matchLabels:
      app: kafka
  template:
    metadata:
      labels:
        app: kafka
    spec:
      containers:
        - name: kafka
          image: confluentinc/cp-kafka:7.5.0
          ports:
            - containerPort: 9092
          env:
            - name: KAFKA_BROKER_ID
              value: "1"
            - name: KAFKA_ZOOKEEPER_CONNECT
              value: "zookeeper:2181"
            - name: KAFKA_ADVERTISED_LISTENERS
              value: "PLAINTEXT://kafka:9092"
            - name: KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
              value: "1"
          volumeMounts:
            - name: kafka-data
              mountPath: /var/lib/kafka/data
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
  volumeClaimTemplates:
    - metadata:
        name: kafka-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 10Gi
```

---

## Phase 4: Database Migrations

After the databases are running and healthy, apply schema migrations before deploying application code. Kubernetes `Job` resources are ideal — they run once to completion.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: auth-db-migrate
  namespace: rag-us-law
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: auth-api:latest
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - secretRef:
                name: auth-api-secret
      restartPolicy: Never
  backoffLimit: 3
```

```bash
kubectl apply -f k8s/base/db-migration-job.yaml
kubectl wait --for=condition=complete job/auth-db-migrate -n rag-us-law --timeout=120s
kubectl logs job/auth-db-migrate -n rag-us-law
```

---

## Full Bootstrap Script

Putting it all together as a single runbook:

```bash
#!/bin/bash
set -euo pipefail

echo "=== Phase 1: Cluster-wide tools ==="
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  -n ingress-nginx --create-namespace \
  --set controller.service.type=LoadBalancer

helm upgrade --install cert-manager jetstack/cert-manager \
  -n cert-manager --create-namespace \
  --set crds.enabled=true

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f monitoring/kube-prometheus-stack-values.yaml

echo "=== Phase 2: Namespace + config ==="
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/configmap.yaml

# Create secrets (in production, use External Secrets Operator instead)
kubectl create secret generic auth-db-secret \
  --from-literal=POSTGRES_USER=auth_user \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -base64 32)" \
  -n rag-us-law --dry-run=client -o yaml | kubectl apply -f -
# ... repeat for each secret ...

echo "=== Phase 3: Databases + middleware ==="
kubectl apply -f k8s/base/postgres.yaml
kubectl apply -f k8s/base/mongodb.yaml
kubectl apply -f k8s/base/redis.yaml
kubectl apply -f k8s/base/weaviate.yaml
kubectl apply -f k8s/base/cassandra.yaml
kubectl apply -f k8s/base/zookeeper.yaml
kubectl apply -f k8s/base/kafka.yaml

echo "Waiting for databases to be ready..."
kubectl rollout status statefulset/auth-db -n rag-us-law --timeout=300s
kubectl rollout status statefulset/user-db -n rag-us-law --timeout=300s
kubectl rollout status statefulset/redis -n rag-us-law --timeout=300s
kubectl rollout status statefulset/weaviate -n rag-us-law --timeout=300s
kubectl rollout status statefulset/cassandra -n rag-us-law --timeout=600s
kubectl rollout status statefulset/kafka -n rag-us-law --timeout=300s

echo "=== Phase 4: Migrations ==="
kubectl apply -f k8s/base/db-migration-job.yaml
kubectl wait --for=condition=complete job/auth-db-migrate -n rag-us-law --timeout=120s

echo "=== Platform ready ==="
```

---

## Verification Checklist

After bootstrap, verify everything is healthy:

```bash
# All pods running
kubectl get pods -n rag-us-law
# Expected: auth-db-0, user-db-0, redis-0, weaviate-0, cassandra-0,
#           zookeeper-0, kafka-0 — all 1/1 Running

# PVCs bound to EBS volumes
kubectl get pvc -n rag-us-law
# Expected: auth-db-data-auth-db-0 Bound 10Gi
#           user-db-data-user-db-0 Bound 10Gi
#           redis-data-redis-0     Bound 5Gi
#           ...

# Services resolvable
kubectl run dns-test --rm -it --image=busybox -- nslookup auth-db.rag-us-law.svc.cluster.local
# Expected: returns pod IP

# Ingress controller has external IP
kubectl get svc -n ingress-nginx
# Expected: EXTERNAL-IP shows the NLB address

# Prometheus scraping
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 -n monitoring
# Open localhost:9090 → Status → Targets → all green
```

---

## Relationship to Lifecycle 3

After platform bootstrap completes, you have:

| What exists | What doesn't exist yet |
| --- | --- |
| All databases running with persistent storage | Application Deployments (api-gateway, auth-api, etc.) |
| Secrets and ConfigMaps created | Docker images in ECR |
| Ingress controller with public IP | Ingress rules applied (no routes configured) |
| Monitoring collecting cluster metrics | Application metrics (no app pods to scrape) |

The platform is like a **restaurant kitchen fully stocked with equipment and ingredients** — ovens are hot, fridges are cold, pantry is full — but no chef has started cooking yet. Lifecycle 3 deploys the chefs (your application code).
