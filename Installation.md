# Setup BinderHub on a Ubuntu server

> Note: On the iris server(134.102.137.239), the binderhub is not directly installed on the host machine, but on a KVM virtual machine. Therefore, there are some extra steps to access to the VM (Via SSH or GUI `Virtual machine Manager`), and extra config to expose the services to the public Network.

## Prerequisite

- Ubuntu machine (newer than 20.04).
- A user account with `sudo` permission.
- Two domain names (e.g., `binder.intel4coro.de`, `jupyter.intel4coro.de`)

## 1. Install Microk8s

We will use [Microk8s](https://microk8s.io/docs/) to setup our self-host kubernetes cluster. As the [Jupyterhub 2.0.0 docs](https://z2jh.jupyter.org/en/2.0.0/kubernetes/other-infrastructure/step-zero-microk8s.html) recommended. If you are prefer k3s, you can try out this tutorial [zero-to-jupyterhub-k8s/CONTRIBUTING.md](https://github.com/jupyterhub/zero-to-jupyterhub-k8s/blob/main/CONTRIBUTING.md).

### 1.1 Install Microk8s

Install the latest stable version:

    sudo snap install microk8s --classic

or install a specific version:

    sudo snap install microk8s --classic --channel=1.30/stable

to check the available versions:

    snap info microk8s

### 1.2 Join the group `microk8s` (optional)

This step is to add you linux user to the user ground `microk8s`, so that you don't need `sudo` permission for running `microk8s` commands.

    sudo usermod -a -G microk8s $USER
    sudo chown -f -R $USER ~/.kube

Re-enter the session for the group update to take place:

    su - $USER

or simply login out and login again.

### 1.3 Check Microk8s status

    microk8s status --wait-ready

For more details check out the [get started tutorial](https://microk8s.io/docs/getting-started).

### 1.4 Check kubernetes status

To ensure the kubernetes cluster is running properly, run:

    microk8s.kubectl get pods -A

Or monitor continuously:

    watch "microk8s.kubectl get pods -A"

If some pods got errors, check the logs or describe the pods, for example:

    microk8s.kubectl describe pod -n kube-system calico-kube-controllers-{SomeRandomString}
    microk8s.kubectl logs --previous -n kube-system calico-kube-controllers-{SomeRandomString}

### 1.5 Troubleshoot: Firewall Issue

The firewall rules of your host machine could possibly block pods communication.
Solution can be found here: <https://cylab.be/blog/246/install-kubernetes-on-ubuntu-2204-with-microk8s>.

    sudo ufw allow in on cni0
    sudo ufw allow out on cni0
    sudo ufw default allow routed
    sudo ufw enable

Restart the Microk8s after the firewall update.

*Note*: If your reboot your machine, the firewall issue would possibly appear again. It could be the conflicts between `ufw` and `iptables` rules, details and solutions can be found here: https://bugs.launchpad.net/ufw/+bug/1987227. Simple solution: before reboot, disable the the `ufw` by `sudo ufw disable`, config the firewall again after reboot and then enable ufw again `sudo ufw enable`.

## 2. Enable Microk8s add-ons

### 2.1 Enable the necessary Add ons

    microk8s enable dns
    microk8s enable helm3

### 2.2 Configure load balancer network:

    microk8s enable metallb:192.168.123.0-192.168.123.20

If installing on the host machine, the IP address range should be within your host network DHCP range. If installing on a virtural machine, the range should be within the virtual network DHCP range (e.g., 192.168.122.2-192.168.122.254). You can check out the network interface with command `ifconfig`.

### 2.3 Configure Storage:

    microk8s enable hostpath-storage

### 2.4 Install kubernetes dashboard

This is a very useful GUI tool for monitoring and managing the kubernetes system, which free you from typing complex shell commands.

    microk8s enable dashboard


At this point, if all the pods are running and ready, the kubernetes setup is done.

## 3. Install BinderHub via Helm chart

### 3.1 Config helm chart

The mircok8s shipped with a `Helm`, add repo:

    microk8s.helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
    microk8s.helm repo update

### 3.2 Copy BinderHub config

Copy file [binder.yaml](./binder.yaml) and [binder_yaml.py](./binder_yaml.py) to the server or VM if you have clone this repo. More information about the configuration can be found in the [README.md](./README.md) or the config file comments.

On the iris server, I clone the repository on the host and then mount it on the VM for ease of editing. Tutorial of sharing directories to VM: https://github.com/libfuse/sshfs

### 3.3 Setup Python enviroment

Install miniconda: https://docs.anaconda.com/miniconda/#quick-command-line-install

Install python dependencies:

    pip install -r requirement.txt

### 3.4 Deply BinderHub

Deploy the the BinderHub with `Helm`:

    python3 binder_yaml.py && \
    microk8s.helm upgrade --cleanup-on-fail \
    --install binder \
    jupyterhub/binderhub --version=1.0.0-0.dev.git.3424.h2ef5e98 \
    --namespace=binder \
    --create-namespace \
    -f ./_binder.yaml

> Note: The [binder_yaml.py](./binder_yaml.py) script is to convert [binder.yaml](./binder.yaml) to a validate helm config file [_binder.yaml](./_binder.yaml). The reason why we did it in this way to simpified the config of the network policy which contains a long list of IP addresses. The network policy is to prevent user pods from accessing to arbitrary external services. This is due to cybersecurity concerns and avoidance of legal risks.

## 4. Verify the setup

Ensure all the pods under namespace `binder` are ready:

     microk8s.kubectl get pods -n binder

The normal status should looks like this:

    NAME                              READY   STATUS    RESTARTS   AGE
    binder-84865654fd-dmprl           1/1     Running   0          3m23s
    hub-97bb86b88-rsx6w               1/1     Running   0          3m23s
    proxy-55d986689c-ng8cz            1/1     Running   0          3m23s
    user-scheduler-7b5bf99979-g26ff   1/1     Running   0          3m23s
    user-scheduler-7b5bf99979-rw9ph   1/1     Running   0          3m23s


Check out the services under namespace `binder`:

    microk8s.kubectl get svc -n binder

The normal output looks like this:

    NAME           TYPE           CLUSTER-IP       EXTERNAL-IP       PORT(S)        AGE
    binder         LoadBalancer   10.152.183.224   192.168.122.200   80:30856/TCP   4m57s
    hub            ClusterIP      10.152.183.127   <none>            8081/TCP       4m57s
    proxy-api      ClusterIP      10.152.183.151   <none>            8001/TCP       4m57s
    proxy-public   LoadBalancer   10.152.183.81    192.168.122.201   80:32656/TCP   4m57s

At this point you should be able to access to the binderhub page via the IP address of services `binder` (192.168.122.200).

## 5. Exposing Binderhub to the public network

### [Nginx Proxy Manager](https://github.com/NginxProxyManager/nginx-proxy-manager)

## 6. Update Config.yaml

To apply the updates of config file `config.yaml`, you should run the helm update to make changes alive:

    python3 binder_yaml.py && \
    microk8s.helm upgrade binder --cleanup-on-fail \
        jupyterhub/binderhub --version=1.0.0-0.dev.git.3424.h2ef5e98  \
        --namespace=binder \
        -f ./_binder.yaml

## 7. Uninstall and remove resources manually

To delete a kubernetes pod:

    microk8s.kubectl delete pod jupyter-user1 

To delete a pvc (user storage):

    microk8s.kubectl delete pvc claim-user1

To delete a kubernetes namespace:

    microk8s.kubectl delete namespace binder

To delete a helm release:

    microk8s.helm delete binder --namespace binder

To reset the Microk8s (this will delete all namespaces and pods):

    sudo microk8s reset

To uninstall the Microk8s (and remove the alias in `.bashrc`):

    sudo snap remove microk8s

## 8. Future works

- Setup the HTTPS
- Config the proxy


## Others

If you don't what to type commands with prefix microk8s, add the following lines to your `.bashrc` (or other shell rc files)

    alias kubectl='microk8s kubectl'
    alias helm='microk8s helm'
