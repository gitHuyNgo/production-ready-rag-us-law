# Terraform — AWS EKS Provisioning

This document describes the Terraform configuration used to provision the AWS EKS cluster and the supporting VPC network for the US Law RAG system.

All Terraform files live in `infra/terraform/`.

---

## Overview

The configuration uses two official Terraform modules:

- **`terraform-aws-modules/vpc/aws`** — creates the VPC, public/private subnets across three AZs, an Internet Gateway, and a single NAT Gateway.
- **`terraform-aws-modules/eks/aws`** — creates the EKS control plane, OIDC provider (IRSA), managed add-ons, and a managed node group.

The EKS API endpoint is publicly accessible by default; restrict `cluster_endpoint_public_access_cidrs` in the provider before deploying to production.

---

## Files

| File | Purpose |
|------|---------|
| `main.tf` | Provider, VPC module, EKS module |
| `variables.tf` | All tuneable inputs (region, cluster name, node sizing, tags) |
| `outputs.tf` | Cluster endpoint, OIDC URL, subnet IDs, kubeconfig command |

---

## Key Design Decisions

- **Private subnets for nodes** — worker nodes live in private subnets; only the NAT Gateway has a public IP.
- **IRSA enabled** — `enable_irsa = true` creates the OIDC provider so pods can assume IAM roles without node-level credentials.
- **Managed add-ons** — CoreDNS, kube-proxy, VPC-CNI, and the EBS CSI driver are installed and kept up to date by EKS.
- **Single NAT Gateway** — cheaper for non-production; set `single_nat_gateway = false` for high-availability.
- **Remote state** — the `backend "s3"` block is present but commented out; uncomment and configure an S3 bucket + DynamoDB lock table before collaborating or deploying to production.

---

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region |
| `cluster_name` | `rag-us-law` | EKS cluster name |
| `cluster_version` | `1.32` | Kubernetes version |
| `vpc_cidr` | `10.0.0.0/16` | VPC CIDR block |
| `node_instance_types` | `["t3.medium"]` | EC2 instance types for the node group |
| `node_min_size` | `1` | Minimum nodes |
| `node_max_size` | `5` | Maximum nodes |
| `node_desired_size` | `2` | Desired nodes |
| `tags` | see file | Common resource tags |

---

## Outputs

| Output | Description |
|--------|-------------|
| `cluster_name` | EKS cluster name |
| `cluster_endpoint` | Kubernetes API server endpoint |
| `cluster_certificate_authority_data` | Base64 CA data (sensitive) |
| `cluster_oidc_issuer_url` | OIDC provider URL for IRSA |
| `vpc_id` | VPC ID |
| `private_subnets` | Private subnet IDs |
| `public_subnets` | Public subnet IDs |
| `kubeconfig_command` | Ready-to-run `aws eks update-kubeconfig` command |

---

## Usage

```bash
cd infra/terraform

# 1. Initialise providers and modules
terraform init

# 2. Preview changes
terraform plan

# 3. Apply
terraform apply

# 4. Configure kubectl
$(terraform output -raw kubeconfig_command)
```

To destroy all resources:

```bash
terraform destroy
```
