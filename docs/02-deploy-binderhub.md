---
sidebar_position: 2
---

# Chapter 2: Deploy BinderHub

All commands in this chapter are run on the machine that has `kubectl` and `helm` access to the cluster:

| Setup | Where to run |
|-------|-------------|
| **Google Cloud (GKE)** | Google Cloud Shell |
| **Self-hosted (MicroK8s)** | The main node (control plane) via SSH or directly |

### Step 1: Add Helm Repository

```bash
helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
helm repo update
```

### Step 2: Clone Configuration Repository

Clone the deployment configuration:

```bash
git clone https://github.com/IntEL4CoRo/binder.intel4coro.de-deploy.git
cd binder.intel4coro.de-deploy
```

The repository already includes a `secret.yaml`. Open it and fill in your Docker Hub credentials:

```yaml
registry:
  username: <your-dockerhub-username>
  password: <your-dockerhub-token>
```

> **Tip**: Alternatively, you can share the `intel4coro` Docker Hub account — all previously built VRB lab images are already available under that account and can be pulled directly without rebuilding. Contact us to obtain the login token.

> **Other registries**: To use a registry other than Docker Hub (e.g., GitHub Container Registry, Google Artifact Registry), refer to the official guide:
> [Set up the container registry](https://binderhub.readthedocs.io/en/latest/zero-to-binderhub/setup-registry.html#set-up-the-container-registry)

### Step 3: Review `binder.yaml` Configuration

Before deploying, review `binder.yaml` and update these values for your environment:

| Field | Description |
|-------|-------------|
| `config.BinderHub.hub_url` | Public URL of the JupyterHub (e.g., `https://jupyter.intel4coro.de`) |
| `config.BinderHub.build_node_selector` | Hostname of the node that should run builds |
| `jupyterhub.singleuser.memory` | Memory guarantee/limit for user pods |
| `jupyterhub.singleuser.cpu` | CPU guarantee/limit for user pods |
| `jupyterhub.singleuser.extraResource` | GPU resource requests |
| `config.BinderHub.image_prefix` | Docker Hub image prefix (e.g., `intel4coro/`) |

#### Shared Storage (Self-Hosted Only)

The `binder.yaml` includes commented-out volume mounts under `jupyterhub.singleuser.storage`. These mount host directories into every user pod for shared large files and caches (HuggingFace models, pip packages, Isaac Sim cache, etc.):

```yaml
# jupyterhub.singleuser.storage.extraVolumeMounts / extraVolumes
# - huggingface-cache  →  /home/jovyan/.cache/huggingface
# - pip-cache          →  /home/jovyan/.cache/pip
# - isaacsim-cache     →  /mnt/isaacsim-cache
```

These use `hostPath` volumes pointing to directories on the node (e.g. `/srv/binder.intel4coro.de/cache/`), which only works in a self-hosted environment where you control the node filesystem. To enable them, uncomment the relevant blocks in `binder.yaml` and ensure the directories exist on the node with the correct permissions.

> **Google Cloud**: `hostPath` volumes are not suitable for GKE. To achieve equivalent shared storage, replace them with [Google Filestore](https://cloud.google.com/filestore) (NFS-backed `PersistentVolume`) or [GCS FUSE](https://cloud.google.com/storage/docs/gcsfuse-mount) mounts, and update the volume definitions accordingly.

### Step 4: Deploy BinderHub

The version pinned below (`1.0.0-0.dev.git.3506.hba24eb2a`) has been tested and confirmed stable for this setup. Newer versions are available but have not been verified.

```bash
helm upgrade --cleanup-on-fail \
  --install binder \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  --create-namespace \
  -f ./secret.yaml \
  -f ./binder.yaml
```

To try a newer version, check https://hub.jupyter.org/helm-chart/#development-releases-binderhub and replace the `--version` value, then run `helm repo update` first.

### Step 5: Verify Deployment

Check that all pods are running:

```bash
kubectl get pods -n binder
```

Expected output:

```
NAME                              READY   STATUS    RESTARTS   AGE
binder-84865654fd-dmprl           1/1     Running   0          3m
hub-97bb86b88-rsx6w               1/1     Running   0          3m
proxy-55d986689c-ng8cz            1/1     Running   0          3m
user-scheduler-7b5bf99979-g26ff   1/1     Running   0          3m
user-scheduler-7b5bf99979-rw9ph   1/1     Running   0          3m
```

Check services:

```bash
kubectl get svc -n binder
```

Expected output:

```
NAME           TYPE           CLUSTER-IP       EXTERNAL-IP       PORT(S)        AGE
binder         LoadBalancer   10.152.183.224   192.168.1.200     80:30856/TCP   5m
hub            ClusterIP      10.152.183.127   <none>            8081/TCP       5m
proxy-api      ClusterIP      10.152.183.151   <none>            8001/TCP       5m
proxy-public   LoadBalancer   10.152.183.81    192.168.1.201     80:32656/TCP   5m
```

The two `LoadBalancer` services — `binder` and `proxy-public` — are the entry points for BinderHub and JupyterHub respectively.

- **Google Cloud (GKE)**: GKE automatically provisions cloud load balancers with **public IPs**. The `EXTERNAL-IP` values shown above will be publicly routable — you can access BinderHub directly at `http://<binder-external-ip>` right away, without any additional networking setup.
- **Self-hosted (MicroK8s)**: MetalLB assigns **local network IPs** (e.g., `192.168.1.x`). These are only reachable within the local network — a reverse proxy or tunnel is needed to expose them to the internet (see Step 6).

To make the full system work, update `config.BinderHub.hub_url` in `binder.yaml` to point to the `proxy-public` external IP:

```yaml
config:
  BinderHub:
    hub_url: http://<proxy-public-external-ip>
```

Then re-run the deploy command to apply the change:

```bash
helm upgrade binder --cleanup-on-fail \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  -f ./secret.yaml \
  -f ./binder.yaml
```

After this, the service is fully functional — open `http://<binder-external-ip>` to use BinderHub, which will redirect users to JupyterHub at the `proxy-public` IP for their sessions.

### Step 6: Configure Domain Names and HTTPS

> **Two domain names required**: BinderHub consists of two publicly accessible services — the **BinderHub frontend** (handles repo building and launching) and the **JupyterHub proxy** (hosts the actual user sessions). Each needs its own domain name, e.g.:
> - `binder.your-domain.org` → BinderHub (`binder` service)
> - `jupyter.your-domain.org` → JupyterHub (`proxy-public` service)


#### Option A: Google Cloud (GKE)

GKE automatically provisions a cloud load balancer when a `LoadBalancer` service is created. The `binder` and `proxy-public` services will receive public IPs directly — no additional setup is needed.

Point your DNS records to the external IPs shown in `kubectl get svc -n binder`, then configure HTTPS using [Google-managed certificates](https://cloud.google.com/kubernetes-engine/docs/how-to/managed-certs) or [cert-manager with Let's Encrypt](https://binderhub.readthedocs.io/en/latest/https.html#adjust-binderhub-config-to-serve-via-https).

Update `config.BinderHub.hub_url` in `binder.yaml` with your JupyterHub domain, then apply the changes:

```bash
helm upgrade binder --cleanup-on-fail \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  -f ./secret.yaml \
  -f ./binder.yaml
```

#### Option B: Self-Hosted (MicroK8s)

The MetalLB load balancer assigns local network IPs to the `binder` and `proxy-public` services. These IPs are only reachable within the local network. Use [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) to expose them publicly without opening firewall ports or requiring a public IP.

**Prerequisites**: A domain managed by Cloudflare (free plan is sufficient).

Follow the official guide to install `cloudflared`, authenticate, and create a tunnel:
[Create a locally-managed tunnel (CLI)](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-local-tunnel/)

Cloudflare handles HTTPS automatically — no certificate management required. Both domains will be accessible publicly once the tunnel is running.

Next, update `binder.yaml` with your domain names as described in the official BinderHub guide:
[Exposing JupyterHub and BinderHub](https://binderhub.readthedocs.io/en/latest/zero-to-binderhub/setup-binderhub.html#exposing-jupyterhub-and-binderhub)

Then apply the changes:

```bash
helm upgrade binder --cleanup-on-fail \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  -f ./secret.yaml \
  -f ./binder.yaml
```

### Step 7: Verify the Deployment

The BinderHub system is now fully deployed. Open your BinderHub domain in a browser:

```
https://binder.your-domain.org
```

To verify the full system is working end-to-end, launch the VRB lab test environment:

```
https://binder.your-domain.org/v2/gh/IntEL4CoRo/binder-template.git/main
```

This will trigger a full build-and-launch cycle — building the Docker image, pushing it to Docker Hub, and spawning a user session. If the JupyterLab interface loads successfully, the deployment is complete.

---

**Next**: [Chapter 3 — GPU Time-Slicing](./03-gpu-time-slicing.md) — enable multiple users to share a single physical GPU.
