# Chapter 1: Kubernetes Cluster Setup

[Kubernetes](https://kubernetes.io/) (K8s) is a container orchestration platform that automates the deployment, scaling, and management of containerized applications. BinderHub runs on top of Kubernetes — it uses K8s to dynamically launch isolated user pods, each running a reproducible computing environment. **A working Kubernetes cluster is the foundation for everything that follows in this guide.**

## Key Concepts

| Term | Description |
|------|-------------|
| **Cluster** | The overall K8s deployment — a set of machines (nodes) managed together |
| **Node** | A physical or virtual machine in the cluster. Nodes are either the **control plane** (manages the cluster) or **workers** (run workloads) |
| **Pod** | The smallest deployable unit in K8s — wraps one or more containers that share the same network and storage |
| **Namespace** | A virtual partition within a cluster for isolating resources. This deployment uses the `binder` namespace for all BinderHub services |
| **Deployment** | A K8s resource that describes a desired state for a set of pods and keeps them running |
| **Service** | Exposes a set of pods as a stable network endpoint (IP + DNS name), even as pods are replaced |
| **ConfigMap** | Stores non-sensitive configuration data as key-value pairs, mountable into pods |
| **Helm** | A package manager for Kubernetes. BinderHub is installed as a Helm *chart* (a bundle of K8s manifests with configurable values) |

> **Recommendation**: **Option A (Google Cloud (GKE)) is strongly recommended**. Self-hosting a cluster (Option B) involves significant manual work — configuring networking, firewall rules, GPU drivers, and ongoing node maintenance. Managed services like GKE handle most of this for you.
>
> For deploying on AWS, Azure, or other managed Kubernetes services, see the Zero to JupyterHub guide: https://z2jh.jupyter.org/en/latest/kubernetes/setup-kubernetes.html

## Option A: Google Cloud (GKE)

For deploying on Google Kubernetes Engine, follow the official Zero to JupyterHub guide:

https://z2jh.jupyter.org/en/stable/kubernetes/google/step-zero-gcp.html

Key differences from the self-hosted setup:
- No need to install MicroK8s
- GPU nodes are added via GKE node pools with NVIDIA GPU accelerators
- Load balancing and TLS are handled by GKE Ingress / Google-managed certificates
- The NVIDIA GPU device plugin is pre-installed on GKE GPU node pools

After the GKE cluster is ready, continue from [Chapter 2](./02-deploy-binderhub.md) for BinderHub deployment, and [Chapter 3](./03-gpu-time-slicing.md) for GPU time-slicing configuration.

---

## Option B: Self-Hosted with MicroK8s

We use [MicroK8s](https://microk8s.io/docs/)(v1.32.13) as the Kubernetes distribution, as recommended by the [JupyterHub docs](https://z2jh.jupyter.org/en/2.0.0/kubernetes/other-infrastructure/step-zero-microk8s.html).

### Step 1: Hardware Preparation

A typical self-hosted cluster consists of a **control plane node** and one or more **worker nodes**:

| Role | GPU | Description |
|------|-----|-------------|
| **Main node** (control plane + worker) | NVIDIA RTX GPU | Workstation acting as both control plane and worker; runs the K8s control plane, build docker images |
| **Worker node 1** | NVIDIA RTX GPU | Additional workstation that runs user pods |
| **Worker node 2** | NVIDIA RTX GPU | Additional workstation that runs user pods |

The control plane schedules workloads and manages cluster state; worker nodes execute them. All user pods (Jupyter sessions) land on worker nodes.

**Minimum recommended specs per node:**

| | |
|---|---|
| **CPU** | 16+ cores |
| **RAM** | 32 GB+ |
| **Storage** | 500 GB+ |
| **GPU** | NVIDIA RTX 2070 or newer |
| **OS** | Ubuntu 22.04 or newer |

**Network**: All nodes must be on the same local network (e.g. `192.168.1.0/24`) and assigned static IPs so cluster addresses never change after a reboot:

| Node | Example IP |
|------|------------|
| Main node (control plane) | `192.168.1.10` |
| Worker node 1 | `192.168.1.11` |
| Worker node 2 | `192.168.1.12` |

If your nodes span different networks, see [Option C: Cross-Internet Cluster with WireGuard VPN](#option-c-cross-internet-cluster-with-wireguard-vpn).

---

### Step 2: Install GPU Drivers

Ensure the NVIDIA GPU driver is installed on every workstation before proceeding. Follow the official installation guide: https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/

After installation, reboot each machine and verify with `nvidia-smi` — it must show your GPU model and driver version. Do not continue until this is confirmed on all nodes.

---

### Step 3: Install MicroK8s on all nodes.

#### 3.1 Install

```bash
# Latest stable version
sudo snap install microk8s --classic

# Or pin to a specific version
sudo snap install microk8s --classic --channel=1.32/stable
```

To list available versions: `snap info microk8s`

#### 3.2 Verify

After installation, wait a few minutes for MicroK8s to fully start up, then run:

```bash
watch "microk8s.kubectl get pods -A"
```

MicroK8s is ready when all pods show `Running` status. Expected output:

```
NAMESPACE        NAME                                                     READY   STATUS    RESTARTS          AGE
kube-system      calico-kube-controllers-759cd8b574-4vmt2                 1/1     Running   14                510d
kube-system      calico-node-7szkr                                        1/1     Running   0                 103d
kube-system      coredns-7896dbf49-xzx6m                                  1/1     Running   14                510d
```

If pods are stuck in `Pending` or `CrashLoopBackOff`, use these commands to investigate:

```bash
microk8s.kubectl describe pod -n <namespace> <pod-name>
microk8s.kubectl logs --previous -n <namespace> <pod-name>
```

**Common cause: firewall blocking internal cluster traffic.** MicroK8s requires free communication between pods over the `cni0` network interface. If `ufw` is enabled, it may silently drop this traffic. Fix:

```bash
sudo ufw allow in on cni0
sudo ufw allow out on cni0
sudo ufw default allow routed
```

After applying the rules, restart MicroK8s:

```bash
sudo snap restart microk8s
```

---

### Step 4: Configure the Main Node

Run the following on the **main node (control plane) only**.

#### 4.1 Install Docker

BinderHub uses Docker to build images. Install it on the main node:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Log out and back in for the group change to take effect, then verify:

```bash
docker --version 
```

#### 4.2 Shell Aliases

Add to `.bashrc` to avoid the `microk8s.` prefix:

```bash
alias kubectl='microk8s kubectl'
alias helm='microk8s helm'
```

#### 4.3 Enable Addons

```bash
# Core addons
microk8s enable dns
microk8s enable helm3
microk8s enable hostpath-storage
microk8s enable community
microk8s enable dashboard

# NVIDIA GPU Operator (installs device plugin, container runtime, monitoring)
microk8s enable nvidia
```

> **Note**: MetalLB (load balancer) is installed in Step 6, after all worker nodes have joined the cluster.

Verify all addons and pods are healthy:

```bash
microk8s.kubectl get pods -A
```

---

### Step 5: Add Worker Nodes to the Cluster

Reference docs: https://microk8s.io/docs/clustering


#### 5.1 Join cluster

On the **main node**, generate a join token:

```bash
microk8s add-node
```

command will output:

```
From the node you wish to join to this cluster, run the following:
microk8s join 192.168.122.172:25000/fd2bcf0daba9515b10a232ed60594c76/4fee84ba7f3f

Use the '--worker' flag to join a node as a worker not running the control plane, eg:
microk8s join 192.168.122.172:25000/fd2bcf0daba9515b10a232ed60594c76/4fee84ba7f3f --worker

If the node you are adding is not reachable through the default interface you can use one of the following:
microk8s join 192.168.122.172:25000/fd2bcf0daba9515b10a232ed60594c76/4fee84ba7f3f
```

Run the output `microk8s join` command on a **worker node**:

```bash
microk8s join <master-ip>:25000/<token>
```

> Note: Each join token is single-use — run `microk8s add-node` on the **main node** once per worker to generate a fresh token.

#### 5.1 Verify nodes appear:

```bash
microk8s kubectl get no
```
should output:
```
NAME               STATUS   ROLES    AGE    VERSION
main-node          Ready    <none>   229d   v1.32.13
gpu-worker1        Ready    <none>   67d    v1.32.13
gpu-worker2        Ready    <none>   67d    v1.32.13
```

### Step 6: Install Load Balancer (MetalLB)

MetalLB provides `LoadBalancer`-type services for bare-metal clusters. It must be installed **after** all worker nodes have joined, as it assigns IPs from your local network range.

```bash
microk8s enable metallb:<IP-RANGE>
```

Choose an unused IP range within your local network subnet. For example, if your nodes are on `192.168.1.0/24`:

```bash
microk8s enable metallb:192.168.1.200-192.168.1.210
```

Verify MetalLB is running:

```bash
microk8s.kubectl get pods -n metallb-system
```

All pods should reach `Running` status. BinderHub services will be assigned IPs from this range when deployed.

The Kubernetes cluster is now ready. Continue to [Chapter 2](./02-deploy-binderhub.md) to deploy BinderHub.

---

## Option C: Cross-Internet Cluster with WireGuard VPN

If your nodes are geographically distributed (e.g. one node at a university, another at a data center), they cannot reach each other directly. WireGuard creates a private virtual network over the internet so that MicroK8s sees all nodes as if they were on the same LAN.

### Architecture

One node acts as the **VPN server** (it must have a public IP or a port-forwarded address). All other nodes connect to it as **VPN clients**. Once the VPN tunnel is up, MicroK8s is configured to use the VPN IPs for cluster communication.

```
[Main node]  ←──── internet ────→  [Worker node 1]
10.0.0.1 (VPN)                      10.0.0.2 (VPN)
203.0.113.10 (public IP)            behind NAT
```

### Todos: Complete guide

<!-- ### Step 1: Install WireGuard on All Nodes

```bash
sudo apt update
sudo apt install wireguard
```

### Step 2: Generate Key Pairs

Run on **each node**:

```bash
wg genkey | tee privatekey | wg pubkey > publickey
cat privatekey   # keep this secret
cat publickey    # share this with the other nodes
```

### Step 3: Configure the VPN Server (Main Node)

Create `/etc/wireguard/wg0.conf` on the **main node**:

```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <main-node-private-key>

# Worker node 1
[Peer]
PublicKey = <worker1-public-key>
AllowedIPs = 10.0.0.2/32

# Worker node 2
[Peer]
PublicKey = <worker2-public-key>
AllowedIPs = 10.0.0.3/32
```

Enable IP forwarding so traffic can be routed between peers:

```bash
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

Open the WireGuard port in the firewall:

```bash
sudo ufw allow 51820/udp
```

### Step 4: Configure VPN Clients (Worker Nodes)

Create `/etc/wireguard/wg0.conf` on each **worker node** (adjust `Address` per node):

```ini
[Interface]
Address = 10.0.0.2/24        # use 10.0.0.3/24 for worker node 2
PrivateKey = <this-node-private-key>

[Peer]
PublicKey = <main-node-public-key>
Endpoint = 203.0.113.10:51820   # main node's public IP and port
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
```

`PersistentKeepalive = 25` keeps the tunnel alive through NAT.

### Step 5: Start WireGuard on All Nodes

```bash
sudo wg-quick up wg0

# Enable auto-start on boot
sudo systemctl enable wg-quick@wg0
```

Verify the tunnel is up:

```bash
sudo wg show
ping 10.0.0.1    # from a worker, should reach the main node
```

### Step 6: Configure MicroK8s to Use VPN IPs

By default MicroK8s advertises the node's primary network interface IP. Override this so cluster traffic goes through the VPN:

On the **main node**, edit `/var/snap/microk8s/current/args/kube-apiserver` and ensure:

```
--advertise-address=10.0.0.1
--bind-address=10.0.0.1
```

On each **worker node**, edit `/var/snap/microk8s/current/args/kubelet`:

```
--node-ip=10.0.0.2    # use the node's own VPN IP
```

Restart MicroK8s after changes:

```bash
sudo snap restart microk8s
```

### Step 7: Join Worker Nodes

Once VPN connectivity is confirmed, follow [Step 4.5](#45-add-worker-nodes-optional) to add worker nodes to the cluster using their VPN IPs:

```bash
# On the main node — generates a join command
microk8s add-node

# On each worker node
microk8s join 10.0.0.1:25000/<token> --worker
```
 -->
