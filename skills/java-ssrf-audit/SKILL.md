---
name: java-ssrf-audit
description: Java Web 源码 SSRF（服务端请求伪造）漏洞审计工具。覆盖 RestTemplate/HttpClient/OkHttp/URLConnection 等所有 HTTP 调用 sink，结合云环境元数据服务利用链评估。适用于：(1) 识别所有 HTTP 请求出口点，(2) 检测 SSRF 漏洞，(3) 审计云环境元数据服务访问风险，(4) 分析 SSRF → 内网渗透利用链。**支持反编译 .class/.jar 文件**。
---

# Java SSRF 漏洞审计工具

扫描 Java Web 项目源码，识别所有 HTTP 请求出口，检测 SSRF 漏洞。

---

## 漏洞分级标准

详见 [SEVERITY_RATING.md](../java-shared/SEVERITY_RATING.md)

- 漏洞编号格式: `{C/H/M/L}-SSRF-{序号}`
- URL 完全可控 + 无鉴权 → 🔴 Critical
- Score = R × 0.40 + I × 0.35 + C × 0.25

---

## 检测范围

### 1. HTTP 客户端 Sink 矩阵

> 详细 Sink 方法、URL 来源追踪、安全/不安全代码模式见 [HTTP_CLIENTS.md](references/HTTP_CLIENTS.md)

| 框架/库 | Sink 方法 | 检测难度 |
|:--------|:----------|:---------|
| Spring RestTemplate | `getForObject(url)`, `exchange(url)`, `postForObject(url)` | 低 |
| Apache HttpClient 4.x | `HttpClient.execute(request)`, `CloseableHttpClient.execute()` | 低 |
| Apache HttpClient 5.x | `CloseableHttpClient.execute()` | 低 |
| OkHttp 3/4 | `newCall(request).execute()`, `newCall(request).enqueue()` | 低 |
| HttpURLConnection | `URL(url).openConnection()` → `HttpURLConnection` | 低 |
| AsyncHttpClient | `executeRequest(request)` | 低 |
| WebClient (Spring 5+) | `WebClient.create(url).get()` | 低 |
| Retrofit | `retrofit.create(interface).method()` | 低 |
| Jsoup | `Jsoup.connect(url).get()` | 低 |
| Unirest | `Unirest.get(url)` | 低 |
| gRPC ManagedChannel | `NettyChannelBuilder.forAddress(host, port)` | 中 |
| Socket (低级) | `new Socket(host, port)`, `new ServerSocket()` | 低 |
| URL openStream | `url.openStream()` | 低 |

### 2. 特殊 SSRF 场景

| 场景 | Sink 特征 | 影响 |
|:-----|:----------|:-----|
| 文件包含 SSRF | `XXE` → URL 引用外部 DTD | XXE + SSRF 叠加 |
| 图片处理 SSRF | `ImageIO.read(url)` | 内网探测 |
| PDF 生成 SSRF | 模板 URL 嵌入 PDF | 内网探测 |
| 邮件/SMS 回调 | webhook URL 参数 | 内网探测 |
| 云存储代理 | S3/OSS 代理 URL | 元数据访问 |

---

## 工作流程

### 1. HTTP 客户端依赖扫描

```bash
# 扫描所有 HTTP 客户端依赖
find {source_path} -name "*.jar" | grep -iE "httpclient|okhttp|retrofit|unirest|async-http|webclient|jsoup"

# 扫描 pom.xml 中的 HTTP 客户端
grep -rnE "httpclient|okhttp|retrofit|unirest" {source_path}/pom.xml 2>/dev/null

# jar 包内的 Maven 依赖
find . -name "*.jar" -exec sh -c 'jar -tf "$1" 2>/dev/null | grep "META-INF/maven"' _ {} \; 2>/dev/null
```

### 2. HTTP Sink 入口点扫描

```bash
# RestTemplate
grep -rnE "RestTemplate|restTemplate\.(get|post|put|delete|exchange|execute)" --include="*.java"

# Apache HttpClient 4/5
grep -rnE "CloseableHttpClient|HttpClients\.(create|custom)|HttpClientBuilder|HttpClient\.execute|CloseableHttpResponse" --include="*.java"

# OkHttp
grep -rnE "OkHttpClient|okhttp3\.Request|newCall\(|\.enqueue\(|\.execute\(" --include="*.java"

# HttpURLConnection
grep -rnE "HttpURLConnection|URL\(.*\)\.openConnection|url\.openConnection" --include="*.java"

# URL openStream (容易被漏掉)
grep -rnE "new URL\(|\.openStream\(\)|URL\(.*\)\.getContent" --include="*.java"

# WebClient (Spring 5+ WebFlux)
grep -rnE "WebClient\.(create|builder)" --include="*.java"

# 图片/PDF 处理函数
grep -rnE "ImageIO\.read\(|ImageIO\.createImageInputStream|PDFRenderer|ITextRenderer|Image\.getInstance" --include="*.java"

# S3/OSS 代理 URL
grep -rnE "AmazonS3|OSSClient|S3Client|putObject" --include="*.java"
```

### 3. URL 可控性分析

对每个 HTTP sink，追踪 URL 参数的来源：

| URL 来源 | 可控程度 | 风险 |
|:---------|:---------|:-----|
| `request.getParameter("url")` | ✅ 完全可控 | 🔴 高 |
| `@RequestParam("url") String url` | ✅ 完全可控 | 🔴 高 |
| `@RequestBody.url` | ✅ 完全可控 | 🔴 高 |
| `@PathVariable` 拼接 URL | ✅ 部分可控 | 🟡 中 |
| `String.format(urlTemplate, param)` | ✅ 完全可控 | 🔴 高 |
| URL 白名单前缀 + 用户后缀 | ⚠️ 条件可控 | 🟡 中 |
| `UriComponentsBuilder.fromHttpUrl(url)` | ✅ 完全可控 | 🔴 高 |
| 配置文件固定值 | ❌ 不可控 | 🟢 低 |

### 4. 常见的 SSRF 防护绕过

> 完整绕过技术（URL 解析差异、DNS 重绑定 TOCTOU、IP 进制绕过、302 重定向、协议走私、白名单绕过）见 [SSRF_BYPASS.md](references/SSRF_BYPASS.md)

```
防护措施              → 绕过方式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
host.equals() 黑名单  → DNS 重绑定、302 跳转
URL.getHost() 检查   → 解析差异 (http://127.0.0.1@evil.com)
正则校验内网 IP       → 进制绕过 (2130706433 = 127.0.0.1)
白名单域名             → 子域名接管、@ 分隔符
只校验协议头           → gopher:// dict:// file:// 协议走私
Java URL 解析差异     → new URL("http://allowed.com").openConnection() vs new URL("http://evil.com#@allowed.com")
```

### 5. 云环境元数据利用链

若 SSRF 可打到内网 HTTP，必须评估以下利用路径。

> 完整云平台利用链（AWS/GCP/Azure/阿里云/腾讯云/K8s/Docker）见 [CLOUD_METADATA.md](references/CLOUD_METADATA.md)

| 云平台 | 元数据端点 | 敏感信息 |
|:-------|:----------|:---------|
| AWS EC2 | `http://169.254.169.254/latest/meta-data/` | IAM 凭证、SSH 密钥 |
| AWS ECS | `http://169.254.170.2/v2/credentials/` | Task Role 凭证 |
| GCP | `http://metadata.google.internal/computeMetadata/v1/` | Service Account Token |
| Azure | `http://169.254.169.254/metadata/instance?api-version=2021-02-01` | Managed Identity Token |
| Aliyun ECS | `http://100.100.100.200/latest/meta-data/` | RAM Role 凭证 |
| Tencent CVM | `http://metadata.tencentyun.com/latest/meta-data/` | CAM Role 凭证 |
| Kubernetes | `https://kubernetes.default.svc/api/v1/namespaces/` | ServiceAccount Token + Pod 列表 |
| Docker | `http://172.17.0.1:2375/containers/json` | 容器管理 API |

---

### 6. 可利用性综合评估

```
可利用性 = f(URL可控性, 鉴权状态, 目标可达性, 协议支持范围)

判定规则：
├── URL完全可控 + ❌无鉴权 → 🔴 Critical
├── URL完全可控 + 🔓可绕过鉴权 → 🔴 Critical 需绕过步骤
├── URL条件可控 + 白名单绕过 → 🟡 High
├── URL完全可控 + ✅有鉴权 → 🟡 Medium
└── URL不可控 → 排除
```

---

### 7. 输出模板

```markdown
# Java SSRF 漏洞审计报告

## 📊 扫描概览

| 指标 | 数量 |
|:-----|:-----|
| HTTP sink 总数 | X |
| URL 完全可控 | Y |
| URL 完全可控 + 无鉴权 | Z |
| 可打内网 (无代理/防火墙限制) | W |

## 🔴 高危风险详情

### [C-SSRF-001] RestTemplate SSRF 可打内网

- **位置**: `WebhookController.callback() (WebhookController.java:45)`
- **Sink 类型**: RestTemplate
- **触发方式**: POST `/api/webhook/callback`
- **参数**: `@RequestParam("callbackUrl") String callbackUrl`
- **鉴权状态**: ❌ 无鉴权
- **防护措施**: ❌ 无任何 URL 校验
- **内网可达性**: ✅ 应用未配置 HTTP 代理，可直接访问内网
- **利用链**:

```
Step 1: POST /api/webhook/callback?callbackUrl=http://169.254.169.254/latest/meta-data/iam/security-credentials/
Step 2: 获取 IAM Role 临时凭证
Step 3: 使用凭证操作 AWS 资源
```

- **PoC**:

```http
POST /api/webhook/callback?callbackUrl=http://169.254.169.254/latest/meta-data/ HTTP/1.1
Content-Type: application/json

{}
```

- **修复建议**: 
  1. URL 白名单校验（域名级别，非字符串前缀）
  2. 禁止访问内网 IP 段 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, 127.0.0.0/8)
  3. 配置 HTTP 代理隔离内网
```

---

## 核心要求

- ✅ 识别所有 12 种 HTTP 客户端 sink
- ✅ 追踪 URL 参数来源判定可控性
- ✅ 检测防护绕过的可能性
- ✅ 评估云环境元数据利用链
- ✅ 结合鉴权状态评估实际风险
- ❌ 禁止忽略 URL 白名单的绕过分析
- ❌ 禁止跳过内网可达性评估

---

## 反编译阶段（CRITICAL）

**当源码不可用时，必须使用 CFR 反编译器反编译 HTTP 客户端相关类。**

详细策略参见 [DECOMPILE_STRATEGY.md](references/DECOMPILE_STRATEGY.md)

```bash
# 反编译 HTTP 客户端工具类
java -jar {CFR_JAR} /path/to/HttpUtils.class --outputdir {output_path}/decompiled

# 批量反编译
find /path/to/WEB-INF/classes -name "*Http*.class" -o -name "*Fetch*.class" -o -name "*Download*.class" | \
  xargs java -jar {CFR_JAR} --outputdir {output_path}/decompiled
```

---

## 输出格式

**严格按照 [references/OUTPUT_TEMPLATE.md](references/OUTPUT_TEMPLATE.md) 中的填充式模板生成输出文件。**

- 文件名格式: `{project_name}_ssrf_audit_{YYYYMMDD_HHMMSS}.md`
- 不得修改模板结构、不得增删章节、不得调整顺序
- 所有【填写】占位符必须替换为实际内容
- 通用规范参考: [java-shared/OUTPUT_STANDARD.md](../java-shared/OUTPUT_STANDARD.md)

---

## 参考资料

| 文档 | 用途 | 何时加载 |
|------|------|---------|
| [HTTP_CLIENTS.md](references/HTTP_CLIENTS.md) | 12 种 HTTP 客户端 Sink 详解 + URL 来源追踪 + 解析差异利用 | 识别 HTTP sink 时参考 |
| [SSRF_BYPASS.md](references/SSRF_BYPASS.md) | 7 层防护绕过技术 + 判定矩阵 + 实战绕过链 | 评估防护绕过可能性时必读 |
| [CLOUD_METADATA.md](references/CLOUD_METADATA.md) | 云环境元数据端点 + 利用链 + 内网渗透路径 | 评估内网可达性和云凭证获取时参考 |
| [OUTPUT_TEMPLATE.md](references/OUTPUT_TEMPLATE.md) | 填充式输出报告模板 | 生成最终报告时严格对照 |
| [DECOMPILE_STRATEGY.md](references/DECOMPILE_STRATEGY.md) | 反编译策略 + HTTP 客户端类定位指南 | 源码不可用时必读 |
