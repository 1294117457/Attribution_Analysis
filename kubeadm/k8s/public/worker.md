# Worker 节点加入步骤

> 把当前节点作为 **worker** 加入已有 kubeadm 集群。
> 前提：主节点已经跑过 `deploy.sh` 并正常 Ready。
> 本文档不需要 `k8s/` 目录的任何配置文件（kubelet 参数由 join 命令自动生成）。

---

## 0. 从主节点获取 join 命令

在**主节点**上跑：

```bash
kubeadm token create --print-join-command
```

输出类似：

```bash
kubeadm join 100.103.49.22:6443 --token abcdef.0123456789abcdef --discovery-token-ca-cert-hash sha256:xxxxx...
```

**复制这行**，后面第 5 步用。

---

## 1. Tailscale

**下载**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

**配置**

```bash
sudo tailscale up
```

**注意**：用**跟主节点同一个 Tailscale 账号**登录，否则 worker 进不来 100.x.x.x 内网。

**验证**

```bash
ping 100.103.49.22   # 换成主节点的 TAILSCALE_IP
```

ping 通再继续。

---

## 2. containerd

**下载**

```bash
sudo apt update
sudo apt install -y containerd.io
```

**配置**

```bash
# 生成默认配置
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml > /dev/null

# 开启 systemd cgroup driver（与 kubelet 对齐）
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# 重启 + 开机自启
sudo systemctl restart containerd
sudo systemctl enable containerd
```

**验证**

```bash
sudo ctr version
```

输出 `ctr version ...` 即可。

---

## 3. kubeadm / kubelet / kubectl

**下载**

```bash
sudo apt-get install -y apt-transport-https ca-certificates curl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

**配置**：无（apt 装完即可）。`kubelet` 启动参数由 join 命令自动生成。

**验证**

```bash
kubeadm version
```

---

## 4. 关闭 swap（kubeadm 强制要求）

**执行**

```bash
sudo swapoff -a
sudo sed -i '/\sswap\s/ s/^/#/' /etc/fstab
```

**验证**

```bash
free -h | grep Swap   # 第二行 Swap 应该为 0
```

---

## 5. 加入集群

**执行**

把第 0 步从主节点复制来的 join 命令**粘进来**（加 sudo）：

```bash
sudo kubeadm join 100.103.49.22:6443 --token abcdef.0123456789abcdef --discovery-token-ca-cert-hash sha256:xxxxx...
```

> ⚠️ **把上面 IP / token / hash 换成你自己的实际值**

看到类似输出就成功了：

```
This node has joined the cluster:
* Certificate signing request was approved
...
Run 'kubectl get nodes' on the control-plane to see this node join the cluster.
```

---

## 6. 回主节点验证

在**主节点**上跑：

```bash
kubectl get nodes -o wide
```

输出类似：

```
NAME    STATUS   ROLES           AGE   VERSION
node1   Ready    control-plane   1h    v1.33.13
node2   Ready    <none>          1m    v1.33.13   ← 新 worker Ready
```

**注意**：worker 节点的 `ROLES` 是 `<none>`，这是正常的（worker 默认无 role 标签）。

---

## 7. 验证 Pod 能正常调度

**应用一个测试 Pod**（主节点上）

```bash
# 用节点名强制调度到新 worker
kubectl run test --image=crpi-9nn64ebnbxd035lo.cn-shenzhen.personal.cr.aliyuncs.com/zhouch0149/pause:3.10.2 \
  --overrides='{"spec":{"nodeName":"<新worker的hostname>"}}'
```

**验证**

```bash
kubectl get pod test -o wide   # STATUS 应该是 Running
```

**清理**

```bash
kubectl delete pod test
```

---

## 常见问题

### Q1: join 时报 "kubelet not ready" / "cgroup driver mismatch"

**原因**：worker 节点的 containerd 没开 `SystemdCgroup = true`。
**解决**：回到步骤 2，重新执行 `sed` 和 `systemctl restart containerd`。

### Q2: join 时报 "connection refused" 到主节点

**原因 1**：Tailscale 没通。回到步骤 1 验证 `ping`。
**原因 2**：主节点防火墙没放行 6443 端口（Tailscale 环境下一般不会，因为 Tailscale 是 L3 VPN）。

### Q3: join 成功但 node 一直 NotReady

**原因**：CNI（flannel）没在 worker 上跑起来。
**解决**：等几分钟，flannel DaemonSet 会自动在 worker 上拉起 pod。检查：

```bash
kubectl -n kube-flannel get pods -o wide
# 应该有新 worker 上跑着 kube-flannel-ds-xxx
```

### Q4: 24 小时后想再加新 worker

```bash
# 主节点重新生成 token（旧的可能过期）
kubeadm token create --print-join-command
```

新 worker 再跑一次步骤 1-5 即可。

### Q5: worker 节点想"退役"（从集群移除）

**在 worker 节点上**：

```bash
sudo kubeadm reset -f
sudo systemctl stop kubelet
sudo systemctl stop containerd
```

**在主节点上**：

```bash
kubectl delete node <worker 的 hostname>
```
