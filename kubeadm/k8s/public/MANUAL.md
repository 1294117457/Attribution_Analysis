# 手动部署步骤

> 在 `/home/project/k8s/` 目录下，**不跑 `deploy.sh`**，手动一行行执行。
> 适合：debug、定制组件、自动化脚本要拆解步骤。

## 0. 准备

```bash
cd /home/project/k8s/public
cp public.env.example public.env
vim public.env               # 改 TAILSCALE_IP / NODE_NAME / ACR_PREFIX
source public.env
```

---

## 1. Tailscale

**下载**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

**配置**

```bash
sudo tailscale up
# 浏览器打开提示的链接登录账号
```

记下 `tailscale0` 的 IP（`ip addr show tailscale0`），写进 `public.env` 的 `TAILSCALE_IP`。

---

## 2. containerd

**下载**

```bash
sudo apt update
sudo apt install -y containerd.io
```

**配置**

```bash
# 用本仓库的 config.toml 替换默认
sudo mkdir -p /etc/containerd
envsubst < ../etc/containerd/config.toml | sudo tee /etc/containerd/config.toml > /dev/null
sudo systemctl restart containerd
sudo systemctl enable containerd
```

---

## 3. kubeadm / kubelet / kubectl

**下载**

```bash
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

**配置**：无（apt 装完即可）。`kubelet` 启动参数由 `kubeadm init` 自动生成。

---

## 4. 预拉镜像（可选，省 init 时间）

```bash
envsubst < ../etc/kubernetes/kubeadm-config.yaml | sudo tee /etc/kubernetes/kubeadm-config.yaml > /dev/null
sudo kubeadm config images pull --config /etc/kubernetes/kubeadm-config.yaml
sudo crictl pull ${ACR_PREFIX}/pause:${PAUSE_VERSION}
```

---

## 5. kubeadm init

**执行**

```bash
envsubst < ../etc/kubernetes/kubeadm-config.yaml | sudo tee /etc/kubernetes/kubeadm-config.yaml > /dev/null
sudo kubeadm init --config=/etc/kubernetes/kubeadm-config.yaml --skip-phases=preflight
```

**保存屏幕上的 join 命令**（其他节点加入用），或稍后跑：
```bash
kubeadm token create --print-join-command
```

---

## 6. kubectl 配置

```bash
mkdir -p $HOME/.kube
sudo cp -f /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

---

## 7. （单节点）去掉 control-plane taint

```bash
kubectl taint nodes ${NODE_NAME} node-role.kubernetes.io/control-plane-
```

---

## 8. flannel

**应用**

```bash
envsubst < ../cni/flannel-tailscale.yaml | kubectl apply -f -
```

**验证**

```bash
kubectl -n kube-flannel get pods -o wide    # 全部 Running
```

---

## 9. dashboard

**应用**

```bash
envsubst < ../addons/dashboard.yaml | kubectl apply -f -
```

**验证**

```bash
kubectl -n kubernetes-dashboard get pods    # 全部 Running
```

---

## 10. 访问 dashboard

```bash
# 入口
echo "https://${TAILSCALE_IP}:${DASHBOARD_NODEPORT}"

# token
kubectl -n kubernetes-dashboard create token admin-user
```

---

## 11. 出错：reset

```bash
cd /home/project/k8s/public
./reset.sh
```

或手动：
```bash
sudo kubeadm reset -f
sudo rm -rf /etc/kubernetes/manifests /etc/kubernetes/pki /var/lib/etcd
sudo rm -rf /var/lib/cni/ /var/run/flannel /run/flannel
sudo iptables -F && sudo iptables -t nat -F && sudo iptables -t mangle -F && sudo iptables -X
```