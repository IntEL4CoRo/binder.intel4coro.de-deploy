# Chapter 3: GPU Time-Slicing

Reference: [NVIDIA GPU Operator — GPU Sharing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)

## Why Time-Slicing?

By default, Kubernetes treats each physical GPU as an indivisible resource — only one pod can use it at a time. In a shared BinderHub environment where most sessions only need a fraction of a GPU, this severely limits concurrency.

NVIDIA GPU time-slicing exposes one physical GPU as multiple virtual replicas, allowing several pods to share it simultaneously. The trade-offs — no memory isolation, no performance guarantees — are acceptable for the interactive robotics sessions in VRB lab.

### Step 1: Check Current GPU Resources

Before enabling time-slicing, verify the GPU resources visible to Kubernetes across all nodes:

```bash
kubectl get nodes -o custom-columns="NODE:.metadata.name,GPU-CAPACITY:.status.capacity.nvidia\.com/gpu,GPU-ALLOCATABLE:.status.allocatable.nvidia\.com/gpu"
```

output:

```
NODE               GPU-CAPACITY   GPU-ALLOCATABLE
main-node          1              1
gpu-worker1        1              1
gpu-worker2        1              1
```

In this example output, the cluster has 3 physical GPUs in total — meaning at most 3 users can run GPU sessions simultaneously before time-slicing is applied.

### Step 2: Apply Time-Slicing Config

Open `time-slicing-config-all.yaml` and set the number of virtual replicas per physical GPU. For example, to virtualize each GPU into 4 replicas:

```yaml
sharing:
  timeSlicing:
    resources:
    - name: nvidia.com/gpu
      replicas: 4
```

With 3 physical GPUs and 4 replicas each, the cluster will expose 12 virtual GPUs — supporting up to 12 concurrent user sessions.

#### Then apply the config:

```bash
kubectl apply -f ./time-slicing-config-all.yaml -n gpu-operator-resources
```

#### Patch the cluster policy to use the time-slicing config:

```bash
kubectl patch clusterpolicies.nvidia.com/cluster-policy \
    -n gpu-operator-resources --type merge \
    -p '{"spec": {"devicePlugin": {"config": {"name": "time-slicing-config-all", "default": "any"}}}}'
```

#### Restart Device Plugin

After applying or updating the time-slicing config, restart the device plugin daemonset:

```bash
kubectl -n gpu-operator-resources rollout restart daemonset nvidia-device-plugin-daemonset
```

### Step 4: Verify GPU Resources

Check that GPU resources are advertised on the node:

```bash
kubectl get nodes -o custom-columns="NODE:.metadata.name,GPU-CAPACITY:.status.capacity.nvidia\.com/gpu,GPU-ALLOCATABLE:.status.allocatable.nvidia\.com/gpu"
```

You should see each node now has 4 GPUs:

```
NODE               GPU-CAPACITY   GPU-ALLOCATABLE
main-node          4              4
gpu-worker1        4              4
gpu-worker2        4              4
```

The full BinderHub deployment with GPU time-slicing is now complete. Users can access the platform at `https://binder.your-domain.org` and GPU resources are shared across concurrent sessions.

---

**Next**: [Chapter 4 — Troubleshooting](./04-troubleshooting.md) — common commands for troubleshooting and monitoring.