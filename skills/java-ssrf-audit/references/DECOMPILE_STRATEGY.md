# SSRF 审计反编译策略指南

## 目录

- [何时反编译](#何时反编译)
- [HTTP 客户端类识别与定位](#http-客户端类识别与定位)
- [反编译结果检查](#反编译结果检查)
- [常见问题](#常见问题)

---

## 何时反编译

### 必须反编译的场景

1. **项目只有编译后的字节码**
   - WAR/JAR 包部署，无源码
   - 第三方依赖中的 HTTP 调用组件

2. **HTTP 客户端调用定义在 .class 文件中**
   - 自定义 HTTP 工具类 (HttpUtils, RestClientWrapper)
   - Controller/Service 中的 URL 获取和 HTTP 调用
   - Webhook/回调处理器

3. **需要检查 SSRF 防护配置**
   - 确认 URL 校验逻辑（是否设置白名单、DNS 反查）
   - 追踪 HTTP 客户端的重定向配置
   - 检查代理设置

### 不需要反编译的场景

1. 源码已存在且可读取
2. 标准 HTTP 客户端库类
3. Spring 注解配置可直接读取

---

## HTTP 客户端类识别与定位

### 按类名模式定位

```bash
# HTTP 工具类
find . -name "*Http*.class" -o -name "*HTTP*.class"
find . -name "*Rest*.class" -o -name "*Client*.class"
find . -name "*Fetch*.class" -o -name "*Download*.class"
find . -name "*Webhook*.class" -o -name "*Callback*.class"

# URL 构建类
find . -name "*Url*.class" -o -name "*URL*.class"
find . -name "*Uri*.class" -o -name "*URI*.class"

# Controller 层
find . -name "*Controller*.class" -o -name "*Handler*.class"
find . -name "*Servlet*.class"
```

### 按字节码特征定位

```bash
# 搜索包含 HTTP 客户端调用的 class 文件
find . -name "*.class" -exec strings {} \; | grep -l "RestTemplate\|HttpURLConnection\|OkHttpClient\|HttpClients"

# 搜索包含 URL 操作的类
find . -name "*.class" -exec strings {} \; | grep -l "java.net.URL\|openConnection\|openStream"

# 搜索包含 SSRF 防护的类（检查是否有防护代码）
find . -name "*.class" -exec strings {} \; | grep -l "isSiteLocalAddress\|isLoopbackAddress\|setInstanceFollowRedirects"
```

---

## 反编译结果检查

### 检查要点

反编译后重点关注：

```java
// 1. HTTP 客户端类型 — 确认使用了哪种客户端
RestTemplate restTemplate = new RestTemplate();
// 或
CloseableHttpClient client = HttpClients.createDefault();
// 或
HttpURLConnection conn = (HttpURLConnection) url.openConnection();

// 2. URL 来源 — URL 从哪里来
String targetUrl = request.getParameter("url");  // ❌ 用户可控
String targetUrl = configService.getApiUrl();     // ✅ 配置文件

// 3. 防护措施 — 是否有校验
// 检查以下防护特征：
// - 协议校验: url.getProtocol()
// - 端口校验: url.getPort()
// - 域名校验: DomainValidator
// - DNS 反查: InetAddress.getByName(...).isSiteLocalAddress()
// - 重定向: conn.setInstanceFollowRedirects(false)

// 4. 鉴权信息 — 是否有认证
@PreAuthorize("hasRole('ADMIN')")   // 有鉴权
// 或无任何注解                     // 无鉴权
```

### 示例检查

```java
// 反编译后的 ImageFetchService 示例
public class ImageFetchService {

    // ❌ 高危：无任何校验的 SSRF
    public String fetchImage(String imageUrl) {
        URL url = new URL(imageUrl);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        return IOUtils.toString(conn.getInputStream());
    }

    // ⚠️ 部分防护：仅校验了协议，有绕过可能
    public String fetchImageV2(String imageUrl) {
        URL url = new URL(imageUrl);
        if (!url.getProtocol().equals("http") && !url.getProtocol().equals("https")) {
            throw new SecurityException("Invalid protocol");
        }
        // 缺少: 端口校验、域名白名单、DNS反查、禁止重定向
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        return IOUtils.toString(conn.getInputStream());
    }

    // ✅ 安全：多层防护
    public String fetchImageV3(String imageUrl) {
        URL url = new URL(imageUrl);
        // L1: 协议
        if (!"http".equals(url.getProtocol()) && !"https".equals(url.getProtocol())) { ... }
        // L2: 端口
        if (url.getPort() != -1) { ... }
        // L4: 域名白名单
        if (!whitelist.contains(url.getHost())) { ... }
        // L5: DNS反查
        InetAddress ip = InetAddress.getByName(url.getHost());
        if (ip.isSiteLocalAddress() || ip.isLoopbackAddress()) { ... }
        // L7: 禁止重定向
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setInstanceFollowRedirects(false);
        return IOUtils.toString(conn.getInputStream());
    }
}
```

**提取信息：**

| 方法 | HTTP 客户端 | URL 来源 | 防护层级 | 漏洞判定 |
|------|-----------|---------|---------|----------|
| fetchImage | HttpURLConnection | 参数 imageUrl | 无 | **高危** |
| fetchImageV2 | HttpURLConnection | 参数 imageUrl | L1 仅协议 | **高危** (可绕过) |
| fetchImageV3 | HttpURLConnection | 参数 imageUrl | L1+L2+L4+L5+L7 | 安全 |

---

## 反编译策略

### 策略 1: Sink 优先扫描

```bash
# 步骤 1: 搜索所有 HTTP 客户端调用特征
strings_find "RestTemplate|HttpURLConnection|OkHttp|HttpClient|WebClient"

# 步骤 2: 反编译包含 HTTP 调用的类
for cls in $(find_http_classes); do
    java -jar cfr.jar "$cls" --outputdir decompiled/
done

# 步骤 3: 反编译 Controller/Servlet 层，追踪 URL 来源
for cls in $(find_controller_classes); do
    java -jar cfr.jar "$cls" --outputdir decompiled/
done

# 步骤 4: 如果发现防护代码，反编译防护逻辑类
for cls in $(find_security_classes); do
    java -jar cfr.jar "$cls" --outputdir decompiled/
done
```

### 策略 2: 层级反编译

```
第一层: HTTP 工具类
  → *Http*.class, *Rest*.class, *Client*.class, *Fetch*.class

第二层: Controller/路由层 (追踪 URL 来源)
  → *Controller*.class, *Servlet*.class, *Handler*.class, *Action*.class

第三层: 配置/安全层 (追踪防护逻辑)
  → *Config*.class, *Security*.class, *Filter*.class, *Interceptor*.class
```

### CF 反编译命令

```bash
# 单个类反编译
java -jar {CFR_JAR} /path/to/ImageService.class --outputdir {output_path}/decompiled

# 批量 HTTP 工具类反编译
find /path/to/WEB-INF/classes -name "*Http*.class" -o -name "*Fetch*.class" -o -name "*Download*.class" | \
  xargs java -jar {CFR_JAR} --outputdir {output_path}/decompiled

# Controller 层反编译
find /path/to/WEB-INF/classes -name "*Controller*.class" -o -name "*Servlet*.class" | \
  xargs java -jar {CFR_JAR} --outputdir {output_path}/decompiled
```

---

## 反编译结果记录

输出时必须标注反编译来源：

```markdown
### [SSRF-001] SSRF 漏洞 - 未防护的 HttpURLConnection

| 项目 | 信息 |
|------|------|
| 漏洞等级 | 高 |
| 位置 | ImageService.fetchImage (ImageService.java:24) |
| 来源 | **反编译 WEB-INF/classes/com/example/ImageService.class** |
| HTTP 客户端 | HttpURLConnection |

漏洞描述:
- URL 来自方法参数 imageUrl，用户完全可控
- 无任何 URL 校验（协议/域名/端口/DNS反查 均无）
- setInstanceFollowRedirects 未设置 = 默认跟随重定向

漏洞代码:
\```java
public String fetchImage(String imageUrl) {
    URL url = new URL(imageUrl);
    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    return IOUtils.toString(conn.getInputStream());
}
\```
```

---

## 常见问题

### 问题 1: HTTP 客户端通过 Spring Bean 注入

**表现：** RestTemplate 通过 `@Bean` 配置，无法在源码中直接看到配置

**处理：** 反编译 `@Configuration` 类，检查 RestTemplate Bean 的 RequestFactory 配置（是否禁用了重定向）

### 问题 2: SSRF 防护在 Interceptor/Filter 中

**表现：** HTTP 客户端调用代码本身无防护，但通过 Spring Interceptor 或 Filter 统一校验

**处理：** 反编译 Interceptor/Filter 类，追踪校验逻辑是否完善

### 问题 3: URL 通过多层封装传递

**表现：** `request.getParameter("url")` → Service → Utils → HTTP Client，URL 经过多层传递

**处理：** 逐层追踪，确保每一层都未对 URL 做额外处理（如 URL 编码/解码可能改变解析结果）
