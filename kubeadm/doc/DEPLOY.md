# K8s 集群部署指南（混合 yaml + script）

## 文件结构

```
kubeadm/docs/
├── etc/
│   ├── kubernetes/
│   │   └── kubeadm-config.yaml      # kubeadm init 配置（控制平面）
│   └── containerd/
│       └── config.toml               # containerd 运行时配置（SystemdCgroup=true + 镜像仓库 mirror）
├── cni/
│   └── flannel-tailscale.yaml        # Flannel CNI（走 Tailscale 接口 tailscale0）
├── scripts/
│   ├── init-control-plane.sh         # 控制平面一键 init + flannel + taint
│   ├── add-worker.sh                 # worker 一键加入
│   └── reset-cluster.sh              # 完全清理集群
└── DEPLOY.md                         # 本文件
```

## 整体流程

```
0. 准备机器
   ├─ 装好 containerd + kubeadm + kubelet + kubectl
   ├─ 装好 tailscale，三台机器组成内网
   └─ 写好 /etc/hosts（小写 hostname）

2. 控制平面（node1）一键 init
   ├─ kubeadm init
   ├─ kubectl 自动配
   ├─ 装 flannel（走 tailscale0）
   ├─ 去 control-plane taint
   └─ 输出 join 命令（保存！）

3. Worker（node2/3）加入集群
   ├─ 在 node1 跑: kubeadm token create --print-join-command
   └─ 在 node2/3 跑: sudo ./add-worker.sh '<join cmd>'

4. 验证
   ├─ node 全部 Ready
   ├─ pod 全 Ready
   └─ 跨节点 pod 通信

6. 部署应用
   ├─ 装 ingress（未来）
   ├─ 装 metrics-server
   └─ 部署业务
```

## 快速上手

### A. 在控制平面（node1）init

```bash
# 1. 把仓库目录 scp 到服务器
scp -r kubeadm/docs/ ubuntu@100.103.49.22:~/

# 2. SSH 上去
ssh ubuntu@100.103.49.22

# 3. 一键 init
cd ~/docs/scripts
sudo chmod +x *.sh
sudo ./init-control-plane.sh
```

### B. 在 worker（node2/3）加入

```bash
# 1. 在 node1 拿 join 命令
ssh ubuntu@100.103.49.22
sudo kubeadm token create --print-join-command
# 复制输出

# 2. 在 node2 上跑
scp -r kubeadm/docs/ ubuntu@<node2 Tailscale IP>:~/
ssh ubuntu@<node2 Tailscale IP>
cd ~/docs/scripts
sudo chmod +x *.sh
sudo ./add-worker.sh '<完整的 join 命令>'
```

### C. 完全清理（init 失败重做）

```bash
sudo ./scripts/reset-cluster.sh
sudo ./scripts/init-control-plane.sh
```

## 关键决策

### 1. 为什么 kubeadm-config.yaml 没有 node-labels 字段

kubeadm 的 `nodeRegistration` 配置下**没有** `node-labels` 字段（你在 kubeadm v1.33 试过会报错）。

正确做法：init 完之后用 `kubectl label` 单独加标签。

### 2. 为什么 flannel 走 tailscale0 而不是 eth0

Tailscale 内网模式下，pod 跨节点通信如果走 eth0（公网 IP），flannel VXLAN 流量会从公网绕一圈。

让 flannel 走 tailscale0（Tailscale 接口）：
- VXLAN 外层走 Tailscale 内网（10.x.y.z）
- Tailscale 自动 NAT 加密到公网
- 不需要放行任何公网端口

### 3. 为什么 init 完要手动去 taint

K8s 给控制平面节点自动加 `node-role.kubernetes.io/control-plane:NoSchedule` 污点。

**单节点集群**：去 taint，让业务 pod 也能跑。
**多节点集群**：保留 taint，业务 pod 跑在 worker。

### 4. 为什么 worker 的 kubelet 必须配 --node-ip=Tailscale IP

K8s 控制平面（apiserver/controller-manager）拿到 node 信息后，会通过 node IP 回访这个节点。如果上报的是 eth0 公网 IP，跨节点通信会断（公网不通）。

**kubelet 配置**（`/etc/default/kubelet` 或 kubelet config 文件）：

```
KUBELET_EXTRA_ARGS=--node-ip=100.x.y.z
```

然后 `sudo systemctl daemon-reload && sudo systemctl restart kubelet`。

### 5. 镜像来源

`imageRepository` 字段直接指定阿里云 ACR（`crpi-9nn64ebnbxd035lo.cn-shenzhen.personal.cr.aliyuncs.com/zhouch014ng`），kubeadm 会从这里拉：

- kube-apiserver
- kube-controller-manager
- kube-scheduler
- kube-proxy
- etcd
- pause

CNI 镜像（flannel、cni plugin）也是从同一个 ACR 拉。**`sandbox_image`** 也指向同一个 ACR。

### 6. 为什么 containerd config.toml 用 import 配置镜像 mirror

`/etc/containerd/config.toml` 用 `imports = ['/etc/containerd/conf.d/*.toml']`，这样可以在 `/etc/containerd/conf.d/` 下放多个 `*.toml` 文件单独管理镜像仓库（docker.io、registry.k8s.io、quay.io），主配置文件不污染。

## 验证清单

跑完 init 后：

```bash
# 1. 节点 Ready
kubectl get nodes -o wide
# 输出：Ready, INTERNAL-IP = Tailscale IP

# 2. 组件 Running
kubectl get pods -A
# 输出：所有 pod 1/1 Running

# 3. pod 网络通
kubectl run test --image=<阿里云防火墙放的busybox镜像> --restart=Never -- sleep 3600
sleep 10
kubectl exec test -- ping -c 3 8.8.8.8        # 0% loss
kubectl exec test -- nslookup kubernetes.default   # 解析到 10.x.x.x

# 4. 跨节点（多节点集群才有意义）
kubectl delete pod test
# 在 node2 再跑一个 test，在 node1 上的 test ping 它
```

## 已知坑

### 坑1：kubeadm v1.33 没有 node-labels 字段

报错：`InitConfiguration.NodeRegistration: nodeLabels is not a valid field`

解决：删掉 node-labels，init 完后用 `kubectl label` 加。

### 坑2：node-name 包含大写

报错：`nodeRegistration.name: invalid name`

解决：节点名必须小写，写入 `/etc/hosts`。

### 坑3：advertiseAddress 是公网 IP

后果：跨节点 pod 通信断（eth 公网 IP，Tailscale 互不通）。

解决：advertiseAddress 必须写 Tailscale IP。

### 坑4：kubelet --node-ip 没按 Tailscale IP

后果：apiserver 通过 eth0 IP 回访 node，跨节点通信断。

解决：kubelet 配置加 `--node-ip=<Tailscale IP>`。

### 坑5：cgroup driver 不一致

报错：`kubelet cgroup driver: cgroupfs is different from docker cgroup driver: systemd`

解决：containerd `SystemdCgroup = true` + kubelet `cgroupDriver: systemd`。

### 坑6：flannel 镜像拉不到

报错：`ImagePullBackOff` 或 `Failed to pull image "docker.io/flannel/flannel:..."`

解决：flannel yaml 里 image 改成你的 ACR（已经在 `flannel-tailscale.yaml` 里改成阿里云 ACR 了）。

### 坑7：taint 导致 pod Pending

报错：`0/N nodes are available: 1 node(s) had taint {node-role.kubernetes.io/control-plane: ...}, that the pod didn't tolerate`

解决：单节点集群必须去 taint。`kubectl taint nodes --all node-role.kubernetes.io/control-plane-`（init-control-plane.sh 已自动做）。

### 坑8：coredns Pending

原因：coredns pod 等 CNI 分配 IP，CNI 没起来就 Pending。CNI 起来后自动 Running。

## 下一步

集群 init 完成后的下一步：

```
kubeadm/docs/
├── DEPLOY.md             # 本文
├── step4-ingress.md       # 装 ingress-nginx
├── step5-metrics.md       # 装 metrics-server
├── step6-business.md      # 部署业务 pod
└── step7-network.md       # 配置 LoadBalancer / NodePort / ClusterIP
```