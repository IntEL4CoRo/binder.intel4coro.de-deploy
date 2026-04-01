# Chapter 4: Troubleshooting

Common commands for monitoring and troubleshooting the BinderHub deployment.

## Kubernetes Dashboard

The Kubernetes dashboard provides a web UI to inspect pods, logs, and cluster resources.

**1. Get the dashboard address:**

```bash
microk8s kubectl get svc -n kube-system kubernetes-dashboard
```

The dashboard runs as a `ClusterIP` service. To access it from your browser, use kubectl port-forward:

```bash
microk8s kubectl port-forward -n kube-system svc/kubernetes-dashboard 10443:443
```

Then open `https://localhost:10443` in your browser. If the dashboard is exposed via a reverse proxy or Cloudflare Tunnel, use that URL instead.

**2. Generate a login token** (valid for 2000 hours):

```bash
kubectl create token default --duration=2000h
```

Paste the token into the dashboard login page to authenticate.

## Command lines

**Watch pod status:**

```bash
# All namespaces
watch "microk8s.kubectl get pods -A"

# Binder namespace only
watch "microk8s.kubectl get pods -n binder"
```

**Pod logs and details:**

```bash
kubectl logs -n binder <pod-name> -f
kubectl describe pod -n binder <pod-name>
```

## Common Operations

**Manage resource quota** — by default there are no resource limits on the `binder` namespace. `resource-quota.yaml` can be applied to cap the total number of concurrent pods, CPU, or memory across all user sessions. If the current load exceeds the configured limit, new user pods will not be scheduled until resources are freed.

Edit `resource-quota.yaml` to set the limits you need, then apply:

```bash
kubectl apply -f ./resource-quota.yaml -n binder
```

To check current usage against the quota:

```bash
kubectl get resourcequota -n binder
```

To remove the quota entirely:

```bash
kubectl delete resourcequota binderhub -n binder
```

**Delete all user pods** (prefix `jupyter-`):

```bash
microk8s.kubectl get pods -n binder --no-headers=true | awk '/jupyter-/{print $1}' | xargs microk8s.kubectl delete pod -n binder
```

**Manage container images** (MicroK8s uses its own containerd, separate from Docker):

```bash
# List all images
microk8s ctr images ls

# List images matching a pattern
microk8s.ctr images ls | grep intel4coro

# Delete images matching a pattern
microk8s.ctr images rm $(microk8s.ctr images list | grep <pattern> | awk '{print $1}')
```

**Update BinderHub configuration** — after editing `binder.yaml`:

```bash
microk8s.helm upgrade binder --cleanup-on-fail \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  -f ./secret.yaml \
  -f ./binder.yaml
```

**Upgrade BinderHub version:**

1. Check the latest version at https://hub.jupyter.org/helm-chart/#development-releases-binderhub
2. Run `helm repo update`
3. Replace the `--version` value in the deploy command and re-run it

## Troubleshooting

### Firewall Issues After Reboot

Symptoms: pods cannot communicate, services unreachable.

```bash
sudo ufw disable
sudo ufw allow in on cni0
sudo ufw allow out on cni0
sudo ufw default allow routed
sudo ufw enable
```

### Pods Stuck in Pending State

```bash
kubectl describe pod -n binder <pod-name>
kubectl get resourcequota -n binder
```

Common causes:
- Insufficient CPU/memory/GPU resources
- Resource quota exceeded
- Build node selector mismatch

### GPU Not Available in Pods

```bash
# Verify GPU operator pods are running
kubectl get pods -n gpu-operator-resources

# Check node GPU resources
kubectl describe node <node-name> | grep nvidia

# Restart GPU device plugin if needed
kubectl -n gpu-operator-resources rollout restart daemonset nvidia-device-plugin-daemonset
```

### Binder Pods Fail to Restart After Reboot

Ensure MicroK8s is ready first:

```bash
microk8s status --wait-ready
```

If pods are stuck, a Helm upgrade can recover them:

```bash
microk8s.helm upgrade binder --cleanup-on-fail \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  -f ./secret.yaml \
  -f ./binder.yaml
```
