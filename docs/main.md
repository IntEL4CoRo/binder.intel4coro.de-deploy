---
sidebar_position: 0
slug: /
---

# VRB Binderhub Server Deployment Guide with GPU Resources

Complete guide for deploying the [Virtual Research Building (VRB)](https://vrb.ease-crc.org/) server — a cloud-based robotics platform built on the [BinderHub](https://github.com/jupyterhub/binderhub) project, with NVIDIA GPU support. BinderHub enables users to launch reproducible computing environments from Git repositories; this deployment extends it with GPU time-slicing and VirtualGL for GPU-accelerated rendering in user pods (Isaac Sim, OpenGL/Vulkan applications, etc.).

This guide covers **two deployment targets**, and each chapter walks through both in parallel:

| Target | Cluster | GPU sharing | Public access |
|--------|---------|-------------|---------------|
| **Google Cloud** | GKE managed cluster with GPU node pools | GKE-native time-slicing (set at node-pool creation via `gcloud` flags) | GKE Load Balancer + nginx ingress + cert-manager (Let's Encrypt) |
| **Self-hosted** | MicroK8s on your own Ubuntu machine | NVIDIA gpu-operator + `time-slicing-config-all.yaml` | Cloudflare Tunnel |

Pick whichever fits your situation — the chapters mark which steps apply to which target.

## Architecture Overview

```mermaid
flowchart TB
    User([User Browser])

    subgraph Public["Public Network"]
        DNS[DNS / HTTPS<br/>binder.example.org<br/>jupyter.example.org]
    end

    subgraph Ingress["Ingress Layer"]
        LB1[BinderHub<br/>LoadBalancer]
        LB2[JupyterHub proxy-public<br/>LoadBalancer]
    end

    subgraph K8s["Kubernetes Cluster (GKE or MicroK8s)"]
        subgraph BinderNS["namespace: binder"]
            BH[BinderHub Pod<br/>build & launch API]
            Hub[JupyterHub Pod<br/>user auth & spawning]
            Proxy[Proxy Pod<br/>traffic routing]
            Sched[User Scheduler]
            UserPods[User Pods<br/>JupyterLab + VirtualGL<br/>GPU via time-slicing]
        end

        subgraph GPU["GPU Layer"]
            GPUPlugin[NVIDIA Device Plugin<br/>time-slicing: 2 vGPUs / GPU]
            PhysGPU[(Physical GPU)]
        end
    end

    Registry[(Container Registry<br/>Docker Hub / GCR)]
    GitRepo[(Git Repository<br/>GitHub)]

    User --> DNS
    DNS --> LB1
    DNS --> LB2
    LB1 --> BH
    LB2 --> Proxy
    Proxy --> Hub
    Hub --> Sched
    Sched --> UserPods
    BH -->|pull source| GitRepo
    BH -->|build & push| Registry
    UserPods -->|pull image| Registry
    UserPods --> GPUPlugin
    GPUPlugin --> PhysGPU
```

## Table of Contents

| Chapter | Description |
|---------|-------------|
| [1. Kubernetes Cluster Setup](./01-kubernetes-setup.md) | Set up the Kubernetes cluster (self-hosted MicroK8s or Google Cloud GKE) |
| [2. Deploy BinderHub](./02-deploy-binderhub.md) | Prepare host filesystem, deploy BinderHub via Helm, expose to public network |
| [3. GPU Time-Slicing](./03-gpu-time-slicing.md) | Configure NVIDIA GPU time-slicing for multi-pod GPU sharing |
| [4. Troubleshooting](./04-troubleshooting.md) | troubleshooting, Day-to-day operations |
| [5. Shutdown and Uninstall](./05-shutdown-uninstall.md) | Tear down services and clean up resources |


## References:

- https://binderhub.readthedocs.io/en/latest/zero-to-binderhub/
- https://z2jh.jupyter.org/en/stable/index.html