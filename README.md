# binder.intel4coro.de-deploy

Kubernetes deployment configuration and documentation for the cloud infrastructure behind the [EASE Virtual Research Building (VRB)](https://vrb.ease-crc.org/).

Two deployment targets are supported:

- **Google Cloud (GKE)** — runs on a managed GKE cluster with GPU node pools, using GKE-native time-slicing (configured at node-pool creation), nginx ingress + cert-manager for HTTPS, and Google Cloud Load Balancers as entry points.

- **Self-hosted (MicroK8s)** — runs on your own Ubuntu machine with a local NVIDIA GPU, using MicroK8s + the NVIDIA gpu-operator for time-slicing, and Cloudflare Tunnel to expose services publicly.

BinderHub enables users to launch reproducible computing environments directly from Git repositories. This deployment extends it with GPU time-slicing and VirtualGL for GPU-accelerated rendering in user pods (Isaac Sim, OpenGL/Vulkan apps, etc.).

## Key Files

| File | Description |
|------|-------------|
| `binder.yaml` | BinderHub Helm values for **self-hosted / MicroK8s** |
| `binder-gke.yaml` | BinderHub Helm values for **Google Cloud / GKE** (adds Vulkan/OpenGL init, nginx ingress, HTTPS) |
| `secret.yaml` | DockerHub credentials (token not included) |
| `time-slicing-config-all.yaml` | NVIDIA GPU time-slicing config (MicroK8s / gpu-operator only) |
| `binderhub-issuer.yaml` | cert-manager `Issuer` for Let's Encrypt (GKE HTTPS) |
| `nginx-ingress.yaml` | nginx ingress controller Helm values (GKE HTTPS) |
| `resource-quota.yaml` | Optional namespace resource limits |


## Documentation

For the full deployment guide, see **[https://intel4coro.github.io/binder.intel4coro.de-deploy/](https://intel4coro.github.io/binder.intel4coro.de-deploy/)**.
