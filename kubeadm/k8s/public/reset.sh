#!/usr/bin/env bash
# reset.sh — kubeadm 集群一键重置
#
# 用途：把当前节点完全恢复成"未部署 k8s"的状态
# 警告：会删除所有集群数据！慎用！
#
# 用法：
#   cd /home/project/k8s/public
#   source public.env
#   ./reset.sh

set -euo pipefail

PUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$(dirname "$PUB_DIR")"
RENDER_DIR="$K8S_DIR/.rendered"

if [[ -f "$PUB_DIR/public.env" ]]; then
    source "$PUB_DIR/public.env"
fi

echo "[!] 即将重置 kubeadm 集群，本节点所有 K8s 资源会被删除"
echo "[!] 5 秒后开始，按 Ctrl+C 取消..."
sleep 5

echo "[1/3] kubeadm reset"
sudo kubeadm reset -f --cri-socket unix:///run/containerd/containerd.sock || true

echo "[2/3] 清理残留"
sudo rm -rf /etc/kubernetes/manifests /etc/kubernetes/pki /var/lib/etcd
sudo rm -rf /var/lib/cni/ /var/run/flannel /run/flannel
sudo rm -f  /etc/kubernetes/kubeadm-config.yaml /etc/kubernetes/admin.conf

# 清理 iptables/ipvs/flannel 网桥
sudo iptables -F && sudo iptables -t nat -F && sudo iptables -t mangle -F && sudo iptables -X || true
sudo ipvsadm -C || true
sudo ip link delete cbr0 2>/dev/null || true
sudo ip link delete flannel.1 2>/dev/null || true

echo "[3/3] 清理渲染产物"
rm -rf "$RENDER_DIR"

echo
echo "============================================"
echo " 集群已重置"
echo "============================================"
echo "如需重新部署：./deploy.sh"
echo "如需彻底重装 containerd：sudo apt purge -y containerd.io && sudo apt install -y containerd.io"