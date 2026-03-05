# Infrastructure Documentation

This folder documents the infrastructure layer for the US Law RAG system.

| Document                    | Description                                                              |
| --------------------------- | ------------------------------------------------------------------------ |
| [terraform](terraform.md)   | AWS EKS cluster provisioning with Terraform — VPC, node groups, add-ons  |
| [kubernetes](kubernetes.md) | Kubernetes manifests — namespaces, deployments, services, ingress        |
| [monitoring](monitoring.md) | Observability stack — Prometheus, Grafana, Alertmanager, ServiceMonitors |

All infrastructure lives under `infra/` at the repository root:

```
├── terraform/          # EKS cluster provisioning
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── k8s/
│   └── base/           # Kubernetes base manifests (Kustomize)
│       ├── namespace.yaml
│       ├── api-gateway.yaml
│       ├── auth-api.yaml
│       ├── user-api.yaml
│       ├── chat-api.yaml
│       ├── ingestion-worker.yaml
│       ├── frontend.yaml
│       ├── ingress.yaml
│       └── kustomization.yaml
└── monitoring/
    ├── kube-prometheus-stack-values.yaml
    └── service-monitors.yaml
```

For application service architecture, see [Services](../services/README.md). For API contracts, see [API](../api/README.md).
