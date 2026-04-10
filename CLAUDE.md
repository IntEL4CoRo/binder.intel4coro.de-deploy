# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repo maintains the Kubernetes configuration for [binder.intel4coro.de](https://binder.intel4coro.de/) — a BinderHub instance enabling GPU-accelerated reproducible computing environments (Isaac Sim, OpenGL/Vulkan apps) from Git repos. It also hosts the project's documentation site.

Two deployment targets are supported:
- **Self-hosted (MicroK8s)** — local Ubuntu machine with NVIDIA gpu-operator for time-slicing, Cloudflare Tunnel for public access. Config: `binder.yaml`.
- **Google Cloud (GKE)** — managed GKE cluster with GPU node pools, GKE-native time-slicing (set at node-pool creation), nginx ingress + cert-manager for HTTPS. Config: `binder-gke.yaml`.

## Key Files

| File | Purpose |
|------|---------|
| `binder.yaml` | BinderHub Helm values for **MicroK8s** |
| `binder-gke.yaml` | BinderHub Helm values for **GKE** (adds VirtualGL install, NVIDIA driver path setup, nginx ingress, HTTPS) |
| `resource-quota.yaml` | Namespace resource limits (max 60 pods) |
| `time-slicing-config-all.yaml` | NVIDIA GPU time-slicing config (2 replicas per GPU). **MicroK8s only** |
| `binderhub-issuer.yaml` | cert-manager `Issuer` for Let's Encrypt (**GKE only**) |
| `nginx-ingress.yaml` | nginx ingress controller Helm values (**GKE only**) |
| `secret.yaml` | **Not committed** — must be created manually with DockerHub credentials |
| `website/` | Docusaurus documentation site, auto-deployed to GitHub Pages |

`secret.yaml` required format:
```yaml
registry:
  username: <DockerHub user>
  password: <Token>
```

## Deploy / Update BinderHub

```bash
# Full install (first time) — MicroK8s
microk8s.helm upgrade --cleanup-on-fail \
  --install binder \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  --create-namespace \
  -f ./secret.yaml \
  -f ./binder.yaml

# Apply config changes only (no --install) — MicroK8s
microk8s.helm upgrade binder --cleanup-on-fail \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  -f ./secret.yaml \
  -f ./binder.yaml
```

For GKE, replace `microk8s.helm` with `helm` and `binder.yaml` with `binder-gke.yaml`.

To upgrade the BinderHub chart version: run `helm repo update`, check latest at https://hub.jupyter.org/helm-chart/#development-releases-binderhub, then replace the `--version` value.

## Documentation Website

The `website/` directory contains a Docusaurus site with deployment guides. Source docs live in `docs/`.

```bash
cd website
npm ci             # install dependencies
npm start          # dev server at localhost:3000
npm run build      # production build to website/build/
npm run typecheck   # TypeScript check
```

Deployed automatically to GitHub Pages on push to `main` via `.github/workflows/deploy.yml`.

## Common kubectl Operations

```bash
# Monitor pods
watch "microk8s.kubectl get pods -n binder"

# Pod logs / details
kubectl logs -n binder <pod-name> -f
kubectl describe pod -n binder <pod-name>

# Delete all user pods (prefix "jupyter-")
microk8s.kubectl get pods -n binder --no-headers=true | awk '/jupyter-/{print $1}' | xargs microk8s.kubectl delete pod -n binder

# Show / apply resource quota
kubectl get resourcequota -n binder
kubectl apply -f ./resource-quota.yaml -n binder

# Apply GPU time-slicing config (MicroK8s / gpu-operator only)
kubectl apply -f ./time-slicing-config-all.yaml -n gpu-operator-resources
kubectl patch clusterpolicies.nvidia.com/cluster-policy \
    -n gpu-operator-resources --type merge \
    -p '{"spec": {"devicePlugin": {"config": {"name": "time-slicing-config-all", "default": "any"}}}}'

# Restart GPU device plugin after time-slicing config update (MicroK8s only)
kubectl -n gpu-operator-resources rollout restart daemonset nvidia-device-plugin-daemonset

# Dashboard token (valid 2000h)
kubectl create token default --duration=2000h
```

## Image Management

MicroK8s uses its own containerd instance, separate from Docker:

```bash
microk8s ctr images ls
microk8s.ctr images rm $(microk8s.ctr images list | grep <pattern> | awk '{print $1}')
```

## Architecture Notes

- **Two configs, one chart**: `binder.yaml` (MicroK8s) and `binder-gke.yaml` (GKE) both configure the same BinderHub Helm chart but differ significantly. GKE config includes a custom `singleuser.cmd` Python script that sets up NVIDIA driver paths, writes EGL vendor ICDs, and installs VirtualGL at pod startup. MicroK8s config relies on the gpu-operator handling driver paths and has VirtualGL env vars commented out.
- **Session limits differ**: MicroK8s culls after 4 hours (maxAge=14400s); GKE culls after 24 hours (maxAge=86400s). GKE also has longer spawn timeouts (600s vs 120s).
- **Network policy**: User pods block private IP egress (`privateIPs: false`) but allow all non-private IPs (`nonPrivateIPs: true`). Additional egress rules go under `jupyterhub.singleuser.networkPolicy.egress`. IP-based rules may become stale if DNS records change; re-deploy to refresh.
- **GitHub repo whitelist**: Controlled via `config.GitHubRepoProvider.whitelist` in `binder.yaml`. Enabled when `whitelist_enabled: true`. Not present in `binder-gke.yaml`.
- **User pods**: Run as root (uid/gid=0). GPU access uses NVIDIA time-slicing (2 virtual GPUs per physical GPU).
- **GPU time-slicing on GKE**: Configured at node-pool creation via gcloud flags (`gpu-sharing-strategy=time-sharing,max-shared-clients-per-gpu=2`). These flags **cannot** be added to an existing node pool — recreate it. `time-slicing-config-all.yaml` and `clusterpolicies.nvidia.com` patches are MicroK8s-only.
- **Custom UI (MicroK8s only)**: Loaded via `initContainers` git-cloning from `github.com/yxzhan/binderhub-custom-files` (branch `dev`) into `/etc/binderhub/custom/iai`.
- **Caches**: HuggingFace, pip, and Isaac Sim host-path mounts are defined but currently commented out in `binder.yaml` under `jupyterhub.singleuser.storage`.

## Troubleshooting

**Firewall issues after reboot** (pods can't communicate):
```bash
sudo ufw disable
sudo ufw allow in on cni0 && sudo ufw allow out on cni0
sudo ufw default allow routed && sudo ufw enable
```

**GPU not available in pods (MicroK8s)**:
```bash
kubectl get pods -n gpu-operator-resources
kubectl describe node <node-name> | grep nvidia
kubectl -n gpu-operator-resources rollout restart daemonset nvidia-device-plugin-daemonset
```

**GPU not available in pods (GKE)**:
```bash
kubectl get pods -n kube-system | grep nvidia-gpu-device-plugin
kubectl describe node <gpu-node> | grep nvidia.com/gpu
```
If `nvidia.com/gpu` is missing from `Allocatable`, the node pool was created without `gpu-driver-version=...`. If it shows `1` instead of the expected shared count, the pool was created without `gpu-sharing-strategy=time-sharing,max-shared-clients-per-gpu=N`. Both require recreating the node pool.

**Pods stuck in Pending** — check events, quota, and node resources:
```bash
kubectl describe pod -n binder <pod-name>
kubectl get resourcequota -n binder
kubectl describe node <node-name> | grep -A10 "Allocated resources"
```

**Binder pods fail to restart after reboot** — ensure MicroK8s is ready, then run a Helm upgrade to recover stuck pods:
```bash
microk8s status --wait-ready
```
