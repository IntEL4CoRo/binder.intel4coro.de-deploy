```bash
# Update helm repo
microk8s.helm repo update

# limit resources of namespace
kubectl apply -f ./resource-quota.yaml -n binder
kubectl get resourcequota -n binder

# mount VM config directory to host machine
sshfs binderhub@192.168.122.247:/home/binderhub/binder.intel4coro.de /raid/intel4coro/vm-binderhub

# Install BinderHub
python3 binder_yaml.py && \
microk8s.helm upgrade --cleanup-on-fail \
  --install binder \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  --create-namespace \
  -f ./secret.yaml \
  -f ./_binder.yaml

# Upgrade BinderHub
# New release version: https://hub.jupyter.org/helm-chart/#development-releases-binderhub
python3 binder_yaml.py && \
microk8s.helm upgrade binder --cleanup-on-fail \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a  \
  --namespace=binder \
  -f ./secret.yaml \
  -f ./_binder.yaml

# Delete BinderHub
export TOBEDELETED='binder' && \
microk8s.helm delete $TOBEDELETED --namespace $TOBEDELETED && \
microk8s.kubectl delete namespace $TOBEDELETED

# Monitor pods status
watch microk8s.kubectl get pods -A
watch microk8s.kubectl get pods -n binder

# Get cluster info
microk8s.kubectl cluster-info

# Get all namespaces
microk8s.kubectl get namespaces

# Get all info
microk8s.kubectl get all -A

# Start a bash session in a Pod
microk8s.kubectl exec -ti -n binder jupyter-intel4coro-2dease-5ffall-5fschool-5f2022-2dw4u1zf1e -- bash

# Delete a pod
microk8s.kubectl delete pod jupyter-intel4coro-2dease-5ffall-5fschool-5f2022-2dw4u1zf1e

# Delete multiple pods with keywords "jupyter-"
microk8s.kubectl get pods -n binder --no-headers=true | awk '/jupyter-/{print $1}'| xargs microk8s.kubectl delete pod -n binder

# Generate dashboard token
microk8s.kubectl create token default --duration=10000h

# Forward dashboard service to localhost
microk8s.kubectl port-forward service/kubernetes-dashboard -n kube-system 10024:443 --address='0.0.0.0'

# Check logs of a pod
microk8s.kubectl logs -n binder jupyter-intel4coro-2dease-5ffall-5fschool-5f2022-2dw4u1zf1e

# Check pods details
microk8s.kubectl describe pod -n binder jupyter-intel4coro-2dease-5ffall-5fschool-5f2022-2dw4u1zf1e

# Storage related
microk8s enable openebs
microk8s.kubectl get storageClass
microk8s.kubectl get pods -n openebs
microk8s.kubectl get sc
microk8s.kubectl get pvc

# Check microk8s status and addson
microk8s status --wait-ready

# Inspect microk8s errors
microk8s inspect

# List containerd images
microk8s.ctr images ls
microk8s ctr images ls | grep intel4coro

# Delete images with keywords
microk8s ctr images rm $(microk8s ctr images ls name~='teaching' | awk {'print $1'})
microk8s ctr images rm $(microk8s.ctr images list | grep multiverse | awk {'print $1'})

# Enable Metal Loadbalancer
microk8s enable metallb:10.0.0.100-10.0.0.200

# Set default kubernetes namespace to binder
microk8s.kubectl config set-context $(microk8s.kubectl config current-context) --namespace binder
```