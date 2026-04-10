---
sidebar_position: 5
---

# Chapter 5: Shutdown and Uninstall

## 5.1 Delete BinderHub Only

Remove the BinderHub Helm release and its namespace, while keeping the Kubernetes cluster intact:

```bash
helm delete binder --namespace binder
kubectl delete namespace binder
```

## 5.2 Tear Down the Cluster


### Option A: Google Cloud (GKE)

Reference: [Deleting a cluster — Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine/docs/how-to/deleting-a-cluster)


**Delete a node pool:**

```bash
gcloud container node-pools delete <node-pool-name> \
    --zone <zone> \
    --cluster <cluster-name>
#Example:
gcloud container node-pools delete user-pool \
    --cluster vrb-gpu \
    --zone europe-central2-b
```

**Delete the GKE cluster:**

```bash
gcloud container clusters delete <cluster-name> --zone <zone>
# example:
gcloud container clusters delete vrb-gpu --zone europe-central2-b --quiet
```

**Check for and remove any remaining billable resources:**

```bash
# Orphaned persistent disks
gcloud compute disks list

## Delete persistent disks
gcloud compute disks delete <pvc-name> --region <zone>

# Orphaned load balancers / forwarding rules
gcloud compute forwarding-rules list --global

# Reserved static IP addresses
gcloud compute addresses list

## Delete Reserved static IP
gcloud compute addresses delete <ip-name> --region <zone>
```

> **Warning**: GKE cluster deletion is irreversible. Verify all important data is backed up before proceeding.

---

### Option B: Self-Hosted (MicroK8s)

**Reset MicroK8s** — deletes all namespaces, pods, and add-on configurations, restoring MicroK8s to a clean state:

```bash
sudo microk8s reset
```

> **Warning**: This is irreversible. All deployed workloads, persistent volumes, and configurations will be lost.

**Uninstall MicroK8s completely:**

```bash
sudo snap remove microk8s --purge
```

Remove any shell aliases from `.bashrc` if you added them.
