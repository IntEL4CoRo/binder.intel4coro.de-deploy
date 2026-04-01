# binder.intel4coro.de-deploy

Kubernetes configuration and deployment scripts for [binder.dev.intel4coro.de](https://binder.dev.intel4coro.de/) — a self-hosted [BinderHub](https://github.com/jupyterhub/binderhub) instance with NVIDIA GPU support, built on MicroK8s.

BinderHub enables users to launch reproducible computing environments directly from Git repositories. This deployment extends it with GPU time-slicing for GPU-accelerating in user pods.

## Key Files

| File | Description |
|------|-------------|
| `binder.yaml` | Main BinderHub Helm values |
| `secret.yaml` | DockerHub credentials(token not included) |
| `time-slicing-config-all.yaml` | NVIDIA GPU time-slicing config |
| `resource-quota.yaml` | Optional namespace resource limits |


## Documentation

For the full deployment guide, see **[https://intel4coro.github.io/binder.intel4coro.de-deploy/](https://intel4coro.github.io/binder.intel4coro.de-deploy/)**.
