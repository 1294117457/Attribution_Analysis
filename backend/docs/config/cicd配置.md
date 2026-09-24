1.acr创建命名空间，镜像仓库
  https://cr.console.aliyun.com/cn-shenzhen/instance/credentials
2.服务器配置密钥
  ssh-keygen -t ed25519 -C "github-actions-deploy" -f C:\Users\zhouch2\.ssh\deploy_key
  cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
3.在github仓库配置secret
  对应仓库-settings-secrets
    配置acr相关：ALIYUN_REGISTRY，ALIYUN_NAMESPACE，ALIYUN_REGISTRY_USERNAME，ALIYUN_REGISTRY_PASSWORD（步骤1）
    配置服务器ssh相关：SERVER_HOST，SERVER_USER，SERVER_SSH_KEY（步骤2），SERVER_PROJECT_PATH
    

