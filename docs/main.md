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
<!-- 
## Architecture Overview

```mermaid
block-beta
    columns 1
    block:user
        columns 1
        UserLabel["👤 User pods"]
        columns 4
        U1["🧑‍💻 IsaacSim"]
        U2["🧑‍💻 Newton Physics"]
        U3["🧑‍💻 Mujoco simulation"]
        U4["🧑‍💻 ..."]

    end

    block:binder
        columns 1
        BinderLabel["📦 BinderHub"]
        columns 2
        BH["BinderHub — build & launch"]
        JH["JupyterHub — spawn & manage pods"]
    end
    block:k8s
        columns 1
        K8sLabel["☸️ Kubernetes (GKE / MicroK8s)"]
        columns 3
        N1["Node 1\nNVIDIA GPU"]
        N2["Node 2\nNVIDIA GPU"]
        N3["Node ...\nNVIDIA GPU"]
    end

    style UserLabel fill:transparent,stroke:none,color:#333,font-weight:bold
    style BinderLabel fill:transparent,stroke:none,color:#333,font-weight:bold
    style K8sLabel fill:transparent,stroke:none,color:#333,font-weight:bold
``` -->

## Table of Contents

| Chapter | Description |
|---------|-------------|
| [1. Kubernetes Cluster Setup](./01-kubernetes-setup.md) | Set up the Kubernetes cluster (self-hosted MicroK8s or Google Cloud GKE) |
| [2. Deploy BinderHub](./02-deploy-binderhub.md) | Prepare host filesystem, deploy BinderHub via Helm, expose to public network |
| [3. GPU Time-Slicing](./03-gpu-time-slicing.md) | Configure NVIDIA GPU time-slicing for multi-pod GPU sharing |
| [4. Troubleshooting](./04-troubleshooting.md) | troubleshooting, Day-to-day operations |
| [5. Shutdown and Uninstall](./05-shutdown-uninstall.md) | Tear down services and clean up resources |


## Quick Deploy on GKE with AI Coding Agents

Instead of running each chapter manually, you can use an **AI coding agent** to read the docs and execute the entire deployment for you. The agent will follow the instructions in this guide, run the `gcloud`, `helm`, and `kubectl` commands, and handle the configuration — you just describe what you want and review its plan.

### Step 1: Open a Terminal on Google Cloud

Go to [console.cloud.google.com](https://console.cloud.google.com), click the **Cloud Shell** icon (terminal icon in the top-right corner) to open a terminal. Alternatively, click **Open Editor** to use the VS Code-based Cloud Shell Editor.

### Step 2: Set Your Project ID

```bash
gcloud config set project <YOUR_PROJECT_ID>
```

Replace `<YOUR_PROJECT_ID>` with your Google Cloud project ID. You can find it in the URL of [console.cloud.google.com](https://console.cloud.google.com/) when you select a project.

### Step 3: Clone Configuration Repository

```bash
git clone https://github.com/IntEL4CoRo/binder.intel4coro.de-deploy.git
cd binder.intel4coro.de-deploy
```

**Then fill in the DockerHub credentials in file `secret.yaml` — contact us to get the token of account `intel4coro`.**

### Step 4: Launch an AI Coding Agent

- Built-in Gemini:

    ```bash
    gemini
    ```

- Claude Code:

    ```bash
    # Install:
    curl -fsSL https://claude.ai/install.sh | bash
    # login
    claude
    ```

### Step 5: Describe Your Requirements

`Shift+Tab` to switch to plan mode

Tell the agent what you need. For example:

```
Follow the instructions under directory "docs" to deploy the full BinderHub system on GKE.

Requirements:
- Zone: europe-central2-b
- GPU node pool: 4 vCPUs, 15 GB memory, 1× T4 GPU shared by 4 user pods
- HTTPS: use sslip.io
- Don't use spot node.
```

> **Warning**: AI Agents may not produce a fully correct plan — carefully review each step before execution. Cross-check against the chapters in this guide to catch any missing or incorrect commands.

Once the plan looks good, `Shift+Tab` to switch to act mode and ask to execute it.

### Step 6: Execute the Plan

The agent will ask for your permission before running each command. Review the command it is about to execute, then confirm to proceed. If something looks wrong, reject it and provide corrections. The entire process takes roughly **20 minutes** if everything goes smoothly.

### Step 7: Verify the Deployment

Once deployment is complete, open the BinderHub URL(replace the IP address):

```
https://binder.34.6.205.29.sslip.io
```

Launch a test repo to verify everything works:

```
https://binder.34.6.205.29.sslip.io/v2/gh/IntEL4CoRo/binder-template.git/42f09b447e7bf6da65d2eafb0bea94019c264d0a
```

The first launch takes around **10 minutes** — Google Cloud needs to provision a GPU node (autoscaling from 0) and pull the container image. If the page times out, simply refresh the page and it will try again.

## Demo: GPU-Accelerated Simulations on GKE

The following recording tests GPU-accelerated simulatior running on GKE with an `n1-standard-8` instance with `NVIDIA Tesla T4` GPU.

<video controls autoPlay loop width="100%" src={require('./img/sim-test.mp4').default} />

## References:

- https://binderhub.readthedocs.io/en/latest/zero-to-binderhub/
- https://z2jh.jupyter.org/en/stable/index.html