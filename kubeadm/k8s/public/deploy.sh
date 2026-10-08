#!/usr/bin/env bash
# deploy.sh — kubeadm 集群一键部署
#
# 流程：
#   1. source public.env
#   2. 把 k8s/etc / k8s/cni / k8s/addons 里的 ${VAR} 用 envsubst 渲染到 .rendered/
#   3. 在本机执行：
#        - 写 containerd config.toml
#        - kubeadm init
#        - kubectl apply flannel
#        - kubectl apply dashboard
#
# 目标部署路径：/home/project/k8s/
# 用法：
#   cd /home/project/k8s/public
#   cp public.env.example public.env   # 第一次
#   vim public.env                     # 改 TAILSCALE_IP / NODE_NAME / ACR_PREFIX
#   source public.env
#   ./deploy.sh
#
# 注意：
#   - 当前脚本默认"在本地"部署（即 kubeadm 就在当前机器上）
#   - 如需推到远端，把下面 scp/ssh 段取消注释，并填 SSH_USER / TAILSCALE_IP

set -euo pipefail

# === 路径 ===
PUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$(dirname "$PUB_DIR")"           # 上层目录：/home/project/k8s
RENDER_DIR="$K8S_DIR/.rendered"

# === 加载参数 ===
if [[ -f "$PUB_DIR/public.env" ]]; then
    source "$PUB_DIR/public.env"
else
    echo "[!] public.env 不存在，请先："
    echo "    cp $PUB_DIR/public.env.example $PUB_DIR/public.env"
    echo "    vim $PUB_DIR/public.env"
    exit 1
fi

# === 校验必填 ===
: "${TAILSCALE_IP:?TAILSCALE_IP 未设置}"
: "${NODE_NAME:?NODE_NAME 未设置}"
: "${ACR_PREFIX:?ACR_PREFIX 未设置}"
: "${K8S_VERSION:?K8S_VERSION 未设置}"
: "${PAUSE_VERSION:?PAUSE_VERSION 未设置}"
: "${FLANNEL_VERSION:?FLANNEL_VERSION 未设置}"
: "${DASHBOARD_VERSION:?DASHBOARD_VERSION 未设置}"

# === 检查 envsubst ===
if ! command -v envsubst >/dev/null 2>&1; then
    echo "[!] envsubst 未安装，请执行："
    echo "    sudo apt install -y gettext-base    # Debian/Ubuntu"
    echo "    sudo dnf install -y gettext         # Fedora/RHEL"
    exit 1
fi

echo "[1/5] 渲染 yaml 到 $RENDER_DIR"
mkdir -p "$RENDER_DIR"
envsubst < "$K8S_DIR/etc/kubernetes/kubeadm-config.yaml" > "$RENDER_DIR/kubeadm-config.yaml"
envsubst < "$K8S_DIR/etc/containerd/config.toml"       > "$RENDER_DIR/config.toml"
envsubst < "$K8S_DIR/cni/flannel-tailscale.yaml"       > "$RENDER_DIR/flannel.yaml"
envsubst < "$K8S_DIR/addons/dashboard.yaml"            > "$RENDER_DIR/dashboard.yaml"

# === 本机部署 =======================================
echo "[2/5] 配置 containerd"
sudo cp "$RENDER_DIR/config.toml" /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd

echo "[3/5] kubeadm init"
sudo cp "$RENDER_DIR/kubeadm-config.yaml" /etc/kubernetes/kubeadm-config.yaml
sudo kubeadm init --config="$RENDER_DIR/kubeadm-config.yaml" --skip-phases=preflight

echo "[4/5] 配置 kubectl"
mkdir -p "$HOME/.kube"
sudo cp -f /etc/kubernetes/admin.conf "$HOME/.kube/config"
sudo chown "$(id -u)":"$(id -g)" "$HOME/.kube/config"

# === 单节点集群：去掉 control-plane taint ===
echo "[5/5] 单节点集群：去掉 control-plane taint"
kubectl taint nodes "${NODE_NAME}" node-role.kubernetes.io/control-plane- || true

# === 部署 flannel + dashboard ===
echo "[+] apply flannel"
kubectl apply -f "$RENDER_DIR/flannel.yaml"

echo "[+] apply dashboard"
kubectl apply -f "$RENDER_DIR/dashboard.yaml"

echo
echo "============================================"
echo " 部署完成"
echo "============================================"
echo "dashboard 访问： https://${TAILSCALE_IP}:${DASHBOARD_NODEPORT}"
echo "获取登录 token："
echo "    kubectl -n kubernetes-dashboard create token admin-user"
echo
echo "其他节点加入集群："
echo "    sudo kubeadm join ${TAILSCALE_IP}:6443 --token <token> --discovery-token-ca-cert-hash <hash>"
echo "    （token 通过 'kubeadm token create --print-join-command' 生成）"