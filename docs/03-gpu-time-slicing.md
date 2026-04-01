---
sidebar_position: 3
---

# Chapter 3: GPU Time-Slicing

Reference: [NVIDIA GPU Operator — GPU Sharing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)

## Why Time-Slicing?

By default, Kubernetes treats each physical GPU as an indivisible resource — only one pod can use it at a time. In a shared BinderHub environment where most sessions only need a fraction of a GPU, this severely limits concurrency.

NVIDIA GPU time-slicing exposes one physical GPU as multiple virtual replicas, allowing several pods to share it simultaneously. The trade-offs — no memory isolation, no performance guarantees — are acceptable for the interactive robotics sessions in VRB lab.

### Check Current GPU Resources

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

### Apply Time-Slicing Config

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

### Verify GPU Resources

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

## GPU-Accelerated 3D Rendering

By default, GPU compute workloads (e.g. CUDA, neural networks) work out of the box once a pod has a `nvidia.com/gpu` resource. However, **3D rendering** (OpenGL, Vulkan) requires additional setup — these APIs expect a display server or GPU device descriptor that is not automatically available inside a headless container.

### Part 1: Vulkan

Vulkan requires an ICD (Installable Client Driver) configuration file that points to the GPU driver's Vulkan implementation. Each GPU model has a different ICD file, so the simplest approach is to mount the host node's ICD directory directly into the pod.

Uncomment the following volume and volumeMount in `binder.yaml` under `jupyterhub.singleuser.storage`:

```yaml
jupyterhub:
  singleuser:
    storage:
      extraVolumeMounts:
        - name: vulkan-icd
          mountPath: /etc/vulkan/icd.d
      extraVolumes:
        - name: vulkan-icd
          hostPath:
            path: /usr/share/vulkan/icd.d
            type: Directory
```

This mounts the host's `/usr/share/vulkan/icd.d` into the container's `/etc/vulkan/icd.d`, giving the pod access to the correct GPU-specific Vulkan driver config without any changes to the container image.

### Part 2: OpenGL (VirtualGL)

OpenGL is more complex in a headless environment. Without a physical display, applications fall back to CPU-based software rendering (Mesa). [VirtualGL](https://virtualgl.org/) solves this by intercepting OpenGL calls and redirecting them to the GPU via EGL.

Since VirtualGL is not typically pre-installed in user images, `binder.yaml` includes a commented-out startup command that **automatically installs VirtualGL when the pod starts**, before launching JupyterLab. Uncomment the `cmd` block under `jupyterhub.singleuser` (from line 85 to 128 of `binder.yaml`):

```yaml
jupyterhub:
  singleuser:
    cmd:
      - python3
      - "-c"
      - |
        # ... installs VirtualGL from a pre-downloaded .deb on the host,
        # then launches jupyter-lab
```

> **Note**: This startup script installs VirtualGL from a `.deb` package pre-placed at `/mnt/dev-tools/installers/virtualgl_3.1.2_amd64.deb` on the host node (mounted into the pod). Ensure this file exists on the node before enabling this feature.

Then uncomment the VirtualGL environment variables in `binder.yaml` under `jupyterhub.singleuser.extraEnv` (around line 139):

```yaml
jupyterhub:
  singleuser:
    extraEnv:
      VGL_DISPLAY: "egl"
      VGL_ISACTIVE: "1"
      LD_PRELOAD: "libdlfaker.so:libvglfaker.so"
```

| Variable | Purpose |
|----------|---------|
| `VGL_DISPLAY: "egl"` | Directs VirtualGL to render via EGL (headless GPU) |
| `VGL_ISACTIVE: "1"` | Activates VirtualGL interception globally |
| `LD_PRELOAD` | Loads VirtualGL faker libraries so all OpenGL calls are transparently redirected to the GPU |

Without these variables, OpenGL applications will silently fall back to CPU rendering even if VirtualGL is installed.

After editing `binder.yaml`, apply the changes with a Helm upgrade (see Chapter 2, Step 4).

---

**Next**: [Chapter 4 — Troubleshooting](./04-troubleshooting.md) — common commands for troubleshooting and monitoring.