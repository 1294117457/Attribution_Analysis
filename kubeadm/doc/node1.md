node1
    管理节点，control-plane,
    管理集群状态、调度、自愈、api网关
    需要装k8s，+dashboard

业务pod跑在node2/3

所有机器都安装了
    kubeadm，kubelet,kubectl,kube-proxy,containerd
    tailscale,CNI-flannel

control-pannel只在node1
    node2，3只跑业务pod

是 K8s 集群启动后，两件事同时需要：
    1. 机器连机器（Tailscale 提供）
    2. pod 连 pod（Flannel 提供），（Flannel VXLAN 包外层走 Tailscale）



##### 统一镜像源

```
# 1. 重新生成 containerd 基础配置（覆盖旧的）
sudo containerd config default | sudo tee /etc/containerd/config.toml > /dev/null

# 2. 开启 SystemdCgroup
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# 3. 追加统一镜像源
sudo tee -a /etc/containerd/config.toml > /dev/null <<'EOF'
[plugins."io.containerd.grpc.v1.cri".registry.mirrors]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
    endpoint = ["https://docker.mirrors.ustc.edu.cn", "https://hub-mirror.c.163.com"]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."registry.k8s.io"]
    endpoint = ["https://registry.cn-hangzhou.aliyuncs.com/google_containers"]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."quay.io"]
    endpoint = ["https://quay-mirror.qiniu.io"]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."ghcr.io"]
    endpoint = ["https://ghcr.mirrors.ustc.edu.cn"]
EOF

# 4. 重启 containerd
sudo systemctl restart containerd

# 5. 验证（每个终端单独跑，看结果）
cat /etc/containerd/config.toml | grep -A 5 "registry.mirrors"
```

