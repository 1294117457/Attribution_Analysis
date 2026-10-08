# kubeadm 部署配置（参数化模板）

> 适用于：单节点 / 多节点 kubeadm 集群，支持 Tailscale 内网，可在新服务器上一键复用。
> 部署目标路径：`/home/project/k8s/`

## 目录结构

```
k8s/
├── public/                     # 入口（部署相关）
│   ├── public.env              #   公共参数（按环境修改）
│   ├── public.env.example      #   参数模板（脱敏版）
│   ├── deploy.sh               #   一键部署
│   ├── reset.sh                #   一键重置
│   ├── README.md               #   本文件
│   ├── MANUAL.md               #   手动部署步骤（不走脚本也能照做）
│   └── .gitignore              #   忽略渲染产物
├── etc/                        # OS / kubeadm 配置
│   ├── kubernetes/
│   │   └── kubeadm-config.yaml #   kubeadm init 配置
│   └── containerd/
│       └── config.toml         #   containerd 配置（含 pause 镜像、cgroup driver）
├── cni/
│   └── flannel-tailscale.yaml  # Flannel CNI（可选 tailscale0/eth0 接口）
└── addons/
    └── dashboard.yaml          # Kubernetes Dashboard（NodePort 30080）
```

## 快速开始（新环境部署）

```bash
# 0. 上传目录到主节点
scp -r k8s/ user@<主节点>:/home/project/

# 1. 在主节点上首次配置
cd /home/project/k8s/public
cp public.env.example public.env
vim public.env          # 改 TAILSCALE_IP / NODE_NAME / ACR_PREFIX

# 2. 部署
source public.env
./deploy.sh

# 3. 出问题要重置
./reset.sh
```

## public.env 参数说明

### 必改项

| 变量 | 含义 | 示例 |
|------|------|------|
| `TAILSCALE_IP` | 节点 Tailscale IP | `100.103.49.22`（或公网 IP） |
| `NODE_NAME` | 节点 hostname | `node1`（`hostname` 命令输出） |
| `ACR_PREFIX` | 阿里云 ACR 个人版地址 | `crpi-9xxxxxxxxx.cn-shenzhen.personal.cr.aliyuncs.com/zhouch0149` |

### 视情况改

| 变量 | 含义 | 默认 | 何时改 |
|------|------|------|--------|
| `FLANNEL_IFACE` | flannel 出口网卡 | `tailscale0` | 不用 Tailscale 时改 `eth0` |
| `DASHBOARD_NODEPORT` | dashboard NodePort | `30080` | 端口冲突时改 |

### 一般不改

| 变量 | 值 | 说明 |
|------|----|----|
| `K8S_VERSION` | `v1.33.13` | K8s 版本 |
| `PAUSE_VERSION` | `3.10.2` | pause 镜像版本 |
| `FLANNEL_VERSION` | `v0.28.9` | flannel 主程序版本 |
| `FLANNEL_CNI_PLUGIN_VERSION` | `v1.9.1-flannel3` | flannel cni plugin 版本 |
| `DASHBOARD_VERSION` | `v2.7.0` | dashboard 版本 |
| `DASHBOARD_METRICS_SCRAPER_VERSION` | `v1.0.8` | metrics-scraper 版本 |
| `POD_SUBNET` | `10.244.0.0/16` | pod 网段（flannel 默认） |
| `SERVICE_SUBNET` | `10.96.0.0/12` | service 网段（K8s 默认） |

## 部署流程（简版）

```
1. 装 containerd、写入配置、重启
2. 写 /etc/kubernetes/kubeadm-config.yaml
3. kubeadm init
5. 拷贝 admin.conf 到 ~/.kube/config
6. 单节点：去掉 control-plane taint
7. apply flannel.yaml
8. apply dashboard.yaml
```

详细见 `MANUAL.md`。

## dashboard 访问

```
https://<TAILSCALE_IP>:30080
```

获取 token：
```bash
kubectl -n kubernetes-dashboard create token admin-user
```

admin-user 已绑定 `cluster-admin`，**生产环境慎用**。

## 新增节点加入集群

```bash
# 在 node1 上生成 join 命令
kubeadm token create --print-join-command

# 在新节点上执行该命令
```

新节点加入后会自动 follow in flannel daemonset、coredns、kube-proxy 等。

## 已知约束 / 注意事项

1. **Tailscale 可选**：不用 Tailscale 时把 `FLANNEL_IFACE=eth0`（甚至可以删掉这个参数）。
2. **dashboard admin-user** 直接绑 `cluster-admin`，仅适合测试/单人环境。生产请用 RBAC 细粒度授权。
3. **imagePullPolicy** 默认 `IfNotPresent`（dashboard 原本是 `Always`，已改）。如果你 ACR 镜像会被强制 invalidate，可改回 `Always`。
4. **`kubeadm-config.yaml`** 每次 `kubeadm reset` 都会被删。所以 deploy.sh 每次都重新渲染、推送。

## 进阶：定制 Kustomize patch / 多集群

如果以后要支持多套环境（dev / staging / prod），可以：
- 每个环境一个 `public.<env>.env`（source 切换）
- 用 `kubectl kustomize` 替代 `envsubst`（更强大但也更复杂）

目前单文件参数化方案对单人 / 单集群足够用。