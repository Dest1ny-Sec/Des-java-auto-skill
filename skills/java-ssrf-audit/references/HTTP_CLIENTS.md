# SSRF HTTP 客户端 Sink 详解

## 目录

- [1. Spring RestTemplate](#1-spring-resttemplate)
- [2. Apache HttpClient 4.x/5.x](#2-apache-httpclient-4x5x)
- [3. OkHttp 3/4](#3-okhttp-34)
- [4. HttpURLConnection](#4-httpurlconnection)
- [5. Spring WebClient (WebFlux)](#5-spring-webclient-webflux)
- [6. 其他客户端](#6-其他客户端)
- [7. 通用审计要点](#7-通用审计要点)

---

## 1. Spring RestTemplate

### 识别特征

```java
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.RestClient;
```

### 危险 Sink 方法

```java
// 所有 RestTemplate 请求方法都接受 String URL 参数
restTemplate.getForObject(url, String.class);          // GET 请求
restTemplate.getForEntity(url, String.class);           // GET 返回完整响应
restTemplate.postForObject(url, request, String.class);  // POST 请求
restTemplate.postForEntity(url, request, String.class);
restTemplate.put(url, request);                         // PUT 请求
restTemplate.delete(url);                               // DELETE 请求
restTemplate.exchange(url, HttpMethod.GET, entity, String.class);  // 通用方法
restTemplate.execute(url, HttpMethod.GET, callback, responseExtractor);  // 底层方法

// RestClient (Spring 6.1+ 替代 RestTemplate)
restClient.get().uri(url).retrieve();                   // 注意：uri(String) 接受完整 URL
restClient.post().uri(url).body(request).retrieve();
```

### URL 来源追踪

| 来源模式 | 代码示例 | 可控性 |
|---------|---------|--------|
| @RequestParam | `public void fetch(@RequestParam String url)` | ✅ 完全可控 |
| @RequestBody | `public void fetch(@RequestBody FetchRequest req)` → `req.getUrl()` | ✅ 完全可控 |
| @PathVariable | `public void fetch(@PathVariable String url)` → URL 拼接 | ⚠️ 需检查路径处理 |
| 配置文件 | `@Value("${api.url}")` → `private String apiUrl` | ❌ 不可控 |
| URI 模板变量 | `restTemplate.getForObject("http://api/{path}", ...)` → path 来自参数 | ⚠️ 部分可控 |

### 安全/不安全配置

```java
// ❌ 高危：无任何校验直接请求
@PostMapping("/fetch")
public String fetch(@RequestParam String url) {
    return restTemplate.getForObject(url, String.class);
}

// ❌ 高危：exchange 方法 + 用户可控 URI
URI uri = new URI(userInput);  // 用户完全可控
restTemplate.exchange(uri, HttpMethod.GET, null, String.class);

// ⚠️ 部分防护：URI 模板变量可能绕过
restTemplate.getForObject("http://example.com/{path}", String.class, userPath);
// 若 userPath = "@evil.com/path"，存在解析差异风险

// ✅ 安全：URL 白名单 + 域名校验
if (allowedHosts.contains(new URL(url).getHost())) {
    return restTemplate.getForObject(url, String.class);
}
```

### 搜索正则

```bash
grep -rnE "RestTemplate|restTemplate\.(get|post|put|delete|exchange|execute)" --include="*.java"
grep -rnE "RestClient\.(create|builder)" --include="*.java"
```

---

## 2. Apache HttpClient 4.x/5.x

### 识别特征

```java
// HttpClient 4.x
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;

// HttpClient 5.x
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.io.entity.EntityUtils;
```

### 危险 Sink 方法

```java
// HttpClient 4.x
CloseableHttpClient client = HttpClients.createDefault();
HttpGet httpGet = new HttpGet(url);          // ← URL 在构造函数注入
HttpResponse response = client.execute(httpGet);
// 或
HttpPost httpPost = new HttpPost(url);       // ← URL 在构造函数注入
client.execute(httpPost);
// 或
RequestBuilder.get(url).build();            // ← URL 在 Builder 注入

// HttpClient 5.x
CloseableHttpClient client = HttpClients.createDefault();
HttpGet httpGet = new HttpGet(url);
CloseableHttpResponse response = client.execute(httpGet);
```

### URL 注入点追踪

| 注入位置 | 代码模式 | 风险 |
|---------|---------|------|
| HttpGet/HttpPost 构造函数 | `new HttpGet(userUrl)` | 🔴 |
| RequestBuilder | `RequestBuilder.get(userUrl)` | 🔴 |
| URIBuilder | `new URIBuilder(userUrl).build()` | 🔴 |
| HttpHost.create | `HttpHost.create(userUrl)` → execute(target, request) | 🔴 |

### 安全/不安全配置

```java
// ❌ 高危：用户 URL 直接构建 HttpGet
String targetUrl = request.getParameter("url");
HttpGet get = new HttpGet(targetUrl);
client.execute(get);

// ✅ 安全：URL 白名单 + 域名校验
String targetUrl = request.getParameter("url");
URL url = new URL(targetUrl);
if (!allowedDomains.contains(url.getHost())) {
    throw new SecurityException("Blocked");
}
HttpGet get = new HttpGet(targetUrl);
client.execute(get);
```

### 搜索正则

```bash
grep -rnE "CloseableHttpClient|HttpClients\.(create|custom)|HttpClientBuilder|new HttpGet\(|new HttpPost\(|RequestBuilder\.(get|post)" --include="*.java"
```

---

## 3. OkHttp 3/4

### 识别特征

```java
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.Call;
```

### 危险 Sink 方法

```java
OkHttpClient client = new OkHttpClient();

// 同步请求
Request request = new Request.Builder()
    .url(userUrl)           // ← URL 在此注入
    .build();
Response response = client.newCall(request).execute();

// 异步请求
client.newCall(request).enqueue(new Callback() {
    @Override
    public void onResponse(Call call, Response response) { ... }
});
```

### URL 注入点追踪

| 注入位置 | 代码模式 | 风险 |
|---------|---------|------|
| Request.Builder.url(String) | `.url(userInput)` | 🔴 |
| Request.Builder.url(URL) | `.url(new URL(userInput))` | 🔴 |
| HttpUrl.parse() | `HttpUrl.parse(userInput)` → `.url(httpUrl)` | 🔴 |

### 安全/不安全配置

```java
// ❌ 高危：用户 URL 直接传给 Request.Builder
String webhookUrl = request.getParameter("callback");
Request req = new Request.Builder().url(webhookUrl).build();
client.newCall(req).enqueue(callback);

// ❌ 高危：HttpUrl.parse 不验证目标
HttpUrl url = HttpUrl.parse(userInput);
Request req = new Request.Builder().url(url).build();

// ✅ 安全：先解析、校验 host、再请求
URL parsed = new URL(userInput);
if (!allowedHosts.contains(parsed.getHost())) { ... }
HttpUrl url = HttpUrl.get(parsed);
```

### 搜索正则

```bash
grep -rnE "OkHttpClient|okhttp3\.Request|newCall\(|\.enqueue\(|\.execute\(|HttpUrl\.parse|Request\.Builder" --include="*.java"
```

---

## 4. HttpURLConnection

### 识别特征

```java
import java.net.HttpURLConnection;
import java.net.URL;
```

### 危险 Sink 方法

```java
// 方式 1: URL.openConnection()
URL url = new URL(userUrl);                // ← URL 可控
HttpURLConnection conn = (HttpURLConnection) url.openConnection();

// 方式 2: url.openConnection(Proxy)
URL url = new URL(userUrl);
HttpURLConnection conn = (HttpURLConnection) url.openConnection(proxy);

// 方式 3: URL.openStream() （容易被遗漏！）
URL url = new URL(userUrl);
InputStream is = url.openStream();

// 方式 4: URL.getContent()
URL url = new URL(userUrl);
Object content = url.getContent();
```

### URL 解析差异利用

Java `java.net.URL` 的解析行为存在可利用的差异：

```
new URL("http://evil.com#@allowed.com").getHost()    → "allowed.com"  （校验主机为 allowed.com）
但实际请求发送到 → evil.com                          （实际连接目标为 evil.com）

new URL("http://1.1.1.1@evil.com").getHost()          → 取决于实现版本
new URL("http://evil.com%00@allowed.com").getHost()   → 空字节注入
```

### 安全/不安全配置

```java
// ❌ 高危：最原始的 SSRF，无任何防护
String source = request.getParameter("url");
URL url = new URL(source);
HttpURLConnection conn = (HttpURLConnection) url.openConnection();

// ⚠️ 部分防护：仅校验 host 但存在解析差异
URL url = new URL(userInput);
if (url.getHost().equals("allowed.com")) {  // 可被 #@ 分隔符绕过
    url.openConnection();
}

// ✅ 安全：多层防护
URL url = new URL(userInput);
// 1. 协议白名单
if (!url.getProtocol().matches("https?")) { ... }
// 2. 端口限制
// 3. 域名白名单
// 4. DNS 解析后校验 IP
InetAddress ip = InetAddress.getByName(url.getHost());
if (ip.isSiteLocalAddress() || ip.isLoopbackAddress()) { ... }
// 5. 禁止重定向
HttpURLConnection conn = (HttpURLConnection) url.openConnection();
conn.setInstanceFollowRedirects(false);
```

### 搜索正则

```bash
grep -rnE "HttpURLConnection|new URL\(|\.openConnection\(\)|\.openStream\(\)" --include="*.java"
```

---

## 5. Spring WebClient (WebFlux)

### 识别特征

```java
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
```

### 危险 Sink 方法

```java
// 方式 1: create(url)
WebClient client = WebClient.create(userUrl);  // ← URL 可控
Mono<String> result = client.get().retrieve().bodyToMono(String.class);

// 方式 2: builder().baseUrl(url)
WebClient client = WebClient.builder().baseUrl(userUrl).build();

// 方式 3: uri(URI)
WebClient client = WebClient.create();
client.get().uri(new URI(userUrl)).retrieve();  // ← URL 可控
```

### 搜索正则

```bash
grep -rnE "WebClient\.(create|builder)\(|\.baseUrl\(|\.uri\(new URI" --include="*.java"
```

---

## 6. 其他客户端

### Retrofit

```java
// 接口定义
@GET("/api/fetch")
Call<ResponseBody> fetchUrl(@Query("url") String url);

// ❌ 若 url 参数值完全可控 → SSRF
Retrofit retrofit = new Retrofit.Builder()
    .baseUrl("http://api.example.com/")  // baseUrl 固定
    .build();
// 但若用户可指定 baseUrl → SSRF
Retrofit retrofit = new Retrofit.Builder()
    .baseUrl(userInput)  // ❌ SSRF!
    .build();
```

### Jsoup

```java
// Jsoup HTML 解析器
Document doc = Jsoup.connect(userUrl).get();   // ← SSRF
Document doc = Jsoup.connect(userUrl).post();  // ← SSRF
```

### Unirest

```java
HttpResponse<String> response = Unirest.get(userUrl).asString();    // ← SSRF
HttpResponse<String> response = Unirest.post(userUrl).asString();   // ← SSRF
```

### 图片/文件处理 (容易被漏掉!)

```java
// ImageIO
BufferedImage img = ImageIO.read(new URL(userUrl));  // ← SSRF
BufferedImage img = ImageIO.read(new URL(userUrl).openStream());

// PDF 生成 (iText/Flying Saucer)
Image.getInstance(new URL(userUrl));                  // ← SSRF
ITextRenderer renderer = new ITextRenderer();
renderer.setDocument(userUrl);                        // ← SSRF
```

### S3/OSS 代理

```java
// AWS S3
AmazonS3 s3 = AmazonS3ClientBuilder.standard()
    .withEndpointConfiguration(new AwsClientBuilder.EndpointConfiguration(userUrl, region))
    .build();

// 阿里云 OSS
OSSClient ossClient = new OSSClient(userEndpoint, ak, sk);
```

---

## 7. 通用审计要点

### URL 参数来源判定规则

```
1. 追踪 URL 变量的最终来源
2. 如果是 request.getParameter() / @RequestParam / @RequestBody → 完全可控
3. 如果是配置文件 / @Value 注入 → 不可控
4. 如果是 String.format / 拼接 → 检查变量部分是否来自用户输入
5. 如果是 URI 模板变量 → 检查变量是否可以改变 host 部分
```

### 常见遗漏点

- `URL.openStream()` — 不返回 HttpURLConnection，容易被忽略
- `ImageIO.read(URL)` — 图片处理中的 SSRF
- `Jsoup.connect(url)` — HTML 爬虫组件
- Retrofit 的 `baseUrl` 参数 — 通常认为 Retrofit 安全，但 baseUrl 可控则危险
- gRPC ManagedChannel — `forAddress(host, port)` 中的 host 可控
- WebSocket 连接 — `new WebSocket(url)` 在某些框架中

### 误判场景

| 场景 | 说明 | 判定 |
|------|------|------|
| URL 来自配置文件 | 用户不可控 | 排除 |
| URL 仅为域名拼接 | 路径可控但 host 固定 | 降为 Medium |
| URL 白名单前缀 + 用户后缀 | 可被 `@` / `#` / `..` 绕过 | 视绕过难度定级 |
| 仅校验 URL 格式 | 不校验 host 和 IP | 仍然危险 |
