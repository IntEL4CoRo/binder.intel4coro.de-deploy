# BinderHub K8s Common Commands

## Deployment

```bash
# Add helm repo
microk8s.helm repo add jupyterhub https://hub.jupyter.org/helm-chart/
# Update helm repo
microk8s.helm repo update

# # Install & update BinderHub
# python3 binder_yaml.py && \
# microk8s.helm upgrade --cleanup-on-fail \
#   --install binder \
#   jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
#   --namespace=binder \
#   --create-namespace \
#   -f ./_binder.yaml

  # Install & update BinderHub
microk8s.helm upgrade --cleanup-on-fail \
  --install binder \
  jupyterhub/binderhub --version=1.0.0-0.dev.git.3506.hba24eb2a \
  --namespace=binder \
  --create-namespace \
  -f ./binder.yaml

# Delete Deploy
export TOBEDELETED='binder' && \
helm delete $TOBEDELETED --namespace $TOBEDELETED && \
kubectl delete namespace $TOBEDELETED

# Monitor pods status
watch microk8s.kubectl get pods -A

# Get cluster info
kubectl cluster-info

# Get all namespaces
kubectl get namespaces

# Get all pods or services
watch "microk8s.kubectl get namespaces && \
microk8s.kubectl get services -A && \
microk8s.kubectl get pods -A"

kubectl get all -A

# start a bash session in the Pod’s container
kubectl exec -it -n binder jupyter-intel4coro-2dease-5ffall-5fschool-5f2022-2dw4u1zf1e -- bash

# Delete a pod
microk8s.kubectl get pods -n binder --no-headers=true | awk '/jupyter-/{print $1}'| xargs microk8s.kubectl delete pod -n binder

# Create dashboard token
kubectl create token default --duration=10000h

# Output logs of a pod
kubectl logs jupyter-admin
kubectl logs -n binder hub-64979d6648-m9tjk -f
kubectl describe pod jupyter-admin

# Storage related
kubectl get sc
kubectl get pvc
```

## SSH reverse tunnel

```bash
# Forward the K8s service to localhost
kubectl port-forward service/binder -n binder 28359:80 --address='localhost'
kubectl port-forward service/proxy-public -n binder 28358:80 --address='localhost'

# SSH Reverse tunnel from PC ports to server localhost
ssh -NfR 28359:localhost:28359 -R 28358:localhost:28358 yanxiang@ivan.informatik.uni-bremen.de
autossh -M 0 -f -N -R 28358:localhost:28358 -R 28359:localhost:28359 yanxiang@ivan.informatik.uni-bremen.de

## --- On remote server ---##
# Add firewall rules allow nginx container access to localhost port 28359, 28358
sudo iptables -A INPUT -s 172.18.0.0/16 -p tcp --dport 28358 -j ACCEPT
sudo iptables -A INPUT -s 172.18.0.0/16 -p tcp --dport 28359 -j ACCEPT

# List iptables rules
sudo iptables -L INPUT --line-numbers -n
# List iptables CHAIN
sudo iptables -t nat -L -n -v

# Delete iptables rules
sudo iptables -D INPUT <line-number>

# Forward localhost to docker network
sudo socat TCP-LISTEN:28358,bind=172.18.0.1,fork TCP:127.0.0.1:28358
sudo socat TCP-LISTEN:28359,bind=172.18.0.1,fork TCP:127.0.0.1:28359

# Disconnect SSH Reverse tunnel
ps aux | grep "ssh -NfR"
# Or on server
sudo netstat -tlnp | grep 28359
```

## wg-easy
```bash
## Deploy docker container
https://wg-easy.github.io/wg-easy/latest/examples/tutorials/basic-installation/

## On client
## Test port accessibility on client
nc -vz -u ivan.informatik.uni-bremen.de 51820
## Install wireguard
sudo apt install wireguard
## place config file
sudo mkdir -p /etc/wireguard
sudo cp ~/Downloads/client.conf /etc/wireguard/wg0.conf
## Change config file mode
sudo chmod 600 /etc/wireguard/wg0.conf
## Start VPN connection
sudo wg-quick up wg0
## Check VPN status
sudo wg show
## Disconnect VPN
sudo wg-quick down wg0

## Forward service to VPN interface in tmux terminal
# create a tmux session
tmux new -s portforward
nohup microk8s.kubectl port-forward service/binder -n binder 28359:80 --address='10.8.0.5' > /dev/null 2>&1 &
# Ctrl + B, and % , create a new bash
nohup microk8s.kubectl port-forward service/proxy-public -n binder 28358:80 --address='10.8.0.5' > /dev/null 2>&1 &
# exit tmux session
# Ctrl + B, and D
# Resume the terminal
tmux attach -t portforward


ps aux | grep "kubectl port-forward"
```

## Microk8s cluster across wireguard network

```bash
## Issue: KVM instance connected to VPN caused public network unaccessible.
## Reason: DNS nameserver not active
## Solution: manually config DNS server
resolvectl status
sudo resolvectl dns enp1s0 1.1.1.1
sudo resolvectl domain wg0 ""

# check status
curl -k https://10.152.183.1:443/version
kubectl get endpoints kubernetes -o wide

sudo vi /var/snap/microk8s/current/args/kube-apiserver
## Add line: --advertise-address=10.8.0.x

sudo vi /var/snap/microk8s/current/args/kubelet
## Add line: --node-ip=10.8.0.x

## Enable openebs
# Change jupyterhub db.pvc.storageClass to openebs-jiva-csi-default

# on main node
microk8s add-node

# on worker node
microk8s leave

# on main node
microk8s remove-node {node-name}
```

## Resources allocate

```bash
# Enable nvidia-runtime
microk8s enable nvidia

# Apply GPU time-slicing (https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)
kubectl apply -f ./time-slicing-config-all.yaml -n gpu-operator-resources
kubectl patch clusterpolicies.nvidia.com/cluster-policy \
    -n gpu-operator-resources --type merge \
    -p '{"spec": {"devicePlugin": {"config": {"name": "time-slicing-config-all", "default": "any"}}}}'

# Update time-slicing config need to manually restart deamonset pod
kubectl apply -f ./time-slicing-config-all.yaml -n gpu-operator-resources
kubectl -n gpu-operator-resources rollout restart daemonset nvidia-device-plugin-daemonset

# Check GPU resources on node
kubectl describe node ai-00039 | grep -A10 "Allocatable"
kubectl describe node gpu-worker | grep -A10 "Allocatable"


# Allow host xserver to user pod
# xhost +local:jovyan
xhost +local:docker
xhost +local:root
xhost +SI:localuser:root
xhost -SI:localuser:root

# limit resources of namespace
kubectl apply -f ./resource-quota.yaml -n binder
kubectl get resourcequota -n binder

kubectl get ippool -A

# Xorg -noreset +extension GLX +extension RANDR +extension RENDER -config ./xorg.conf :99
# sudo ps aux | grep "Xorg.*:99"


microk8s.kubectl port-forward service/binder -n binder 28359:80 --address='10.8.0.5'
```

## microk8s related
```bash
# Check status
microk8s status --wait-ready
microk8s inspect

# Enable loadbalancer
microk8s enable metallb:10.0.0.100-10.0.0.200
microk8s enable metallb:192.168.122.50-192.168.122.60
# Find images
microk8s.ctr images ls | grep intel4coro
# Delete images
microk8s.ctr images rm $(microk8s.ctr images list | grep multiverse | awk {'print $1'})

# Set default kubernetes namespace to binder
microk8s.kubectl config set-context $(microk8s.kubectl config current-context) --namespace kube-system
# Apply storage config
microk8s.kubectl apply -f ./storage.yaml
```