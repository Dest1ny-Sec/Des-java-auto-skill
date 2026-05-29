# Auth Audit 增强检测项

本文档补充 java-auth-audit/SKILL.md 中未覆盖的高级鉴权缺陷检测。

---

## 1. Spring Security antMatcher vs mvcMatcher 语义差异

**CVE-2023-34034 的根本原因：**

```java
// 危险写法：antMatcher 把 /admin 也匹配为 /admin/**
// 但 mvcMatcher 不会，导致鉴权配置语义不一致
http
    .securityMatcher("/admin/**")  // ← antMatcher 语义
    .authorizeHttpRequests(auth -> auth
        .requestMatchers("/admin").permitAll()  // ← mvcMatcher 语义
        .anyRequest().authenticated()
    );
```

**检测规则：**

```bash
# 检测 securityMatcher + requestMatchers 混用
grep -rnE "securityMatcher.*\*\*" --include="*.java"
grep -rnE "requestMatchers\(|antMatchers\(|mvcMatchers\(" --include="*.java"

# 检测 permitAll 后还有 authenticated
grep -rnE "permitAll\(\)" --include="*.java" -A 5 | grep "authenticated\|hasRole"
```

---

## 2. Actuator 端点鉴权缺失

```
Spring Boot Actuator 默认端点：
├── /actuator/env        → 环境变量泄漏（可能含数据库密码、密钥）
├── /actuator/heapdump   → JVM 堆内存 dump（可含请求参数、session、密钥）
├── /actuator/gateway    → Spring Cloud Gateway 路由（CVE-2022-22947）
├── /actuator/mappings   → 全量路由映射
├── /actuator/configprops → 所有配置属性
├── /actuator/threaddump → 线程 dump（含调用栈信息）
└── /actuator/loggers    → 日志级别修改
```

**检测规则：**

```bash
# 检测 Actuator 依赖
grep -rnE "spring-boot-starter-actuator" {source_path}/pom.xml 2>/dev/null

# 检测 Actuator 配置
grep -rnE "management\.endpoints|management\.endpoint" --include="*.yml" --include="*.yaml" --include="*.properties"

# 检测是否有 Actuator 安全配置
grep -rnE "actuator.*authenticated|actuator.*hasRole|actuator.*SecurityFilterChain" --include="*.java"
```

**判定规则：**
- Actuator 存在 + 无 `/actuator/**` 鉴权配置 → 🔴 信息泄漏高危
- Actuator 存在 + `/actuator/health` permitAll 但其他端点无鉴权 → 🔴 信息泄漏

---

## 3. WebSocket 鉴权缺失

```
WebSocket 握手阶段的鉴权盲区：
├── SockJS 连接不走 Spring Security Filter Chain
├── STOMP CONNECT 帧的鉴权拦截器可能被绕过
├── WebSocket 升级握手仅校验一次，后续帧无鉴权
└── CORS 策略对 WebSocket 不生效（Same-Origin Policy 不适用于 ws://）
```

**检测规则：**

```bash
# 检测 WebSocket 配置
grep -rnE "@EnableWebSocket|WebSocketConfigurer|registerWebSocketHandlers|configureMessageBroker" --include="*.java"

# 检测 SockJS 使用
grep -rnE "withSockJS\(\)|SockJsService|SockJsClient" --include="*.java"

# 检测 STOMP 拦截器
grep -rnE "ChannelInterceptor|HandshakeInterceptor|beforeHandshake" --include="*.java"

# 检测 WebSocket 鉴权配置
grep -rnE "SimpUserRegistry|StompSubProtocolHandler|AbstractSecurityWebSocketMessageBrokerConfigurer" --include="*.java"
```

**判定规则：**
- WebSocket 配置存在 + 无 HandshakeInterceptor → ❌ 握手阶段无鉴权
- STOMP 存在 + 无 ChannelInterceptor → ❌ 消息通道无鉴权

---

## 4. @Async 方法的鉴权失效

```
Spring Security Context 默认不跨线程传播：

@Async
@PreAuthorize("hasRole('ADMIN')")  // ← 这个注解在异步方法上无效！
public void deleteUser(Long id) {
    SecurityContextHolder.getContext().getAuthentication();  // ← 这里拿不到认证信息
}
```

**检测规则：**

```bash
# 检测 Async + 权限注解混用
grep -rnE "@Async|@EnableAsync" --include="*.java"
# 交叉检查：Async 方法上是否标注了 @PreAuthorize/@PostAuthorize/@Secured
grep -rnE "@Async" --include="*.java" -A 3 | grep -E "@PreAuthorize|@PostAuthorize|@Secured"
```

---

## 5. Swagger/SpringDoc API 文档泄漏

```
SpringDoc / Swagger 端点：
├── /v3/api-docs          → OpenAPI 完整文档（含所有路由+参数）
├── /v3/api-docs.yaml     → OpenAPI YAML 格式
├── /swagger-ui.html      → Swagger UI
├── /swagger-ui/index.html
└── /swagger-resources
```

**检测规则：**

```bash
# 检测 Swagger 依赖
grep -rnE "springdoc-openapi|springfox|swagger" {source_path}/pom.xml 2>/dev/null

# 检测 Swagger 配置
grep -rnE "@OpenAPIDefinition|@Hidden|swagger.*enabled|springdoc.*api-docs.*enabled" --include="*.java" --include="*.yml" --include="*.properties"

# 检测是否有 Swagger 鉴权配置
grep -rnE "swagger.*authenticated|api-docs.*authenticated|swagger.*permitAll|api-docs.*permitAll" --include="*.java"
```

**判定规则：**
- Swagger 存在 + 无鉴权配置 + 非测试/开发环境 → 🟡 信息泄漏

---

## 6. 自定义 Filter 位置错位

```
Filter 添加到 FilterChainProxy 之前的风险：
├── 自定义 Filter 注册在 securityFilterChain 之前
├── 如果 Filter 中有 forward/include 操作，会绕过 securityFilterChain
└── FilterRegistrationBean.setOrder() 的数字越小越先执行
```

**检测规则：**

```bash
# 检测 Filter 注册
grep -rnE "FilterRegistrationBean|@WebFilter|addFilterBefore|addFilterAfter" --include="*.java"

# 检测 Filter order
grep -rnE "setOrder\(|@Order\(|Ordered\.(HIGHEST|LOWEST)" --include="*.java"
```

---

## 7. OAuth2 / SSO 回调 URL 未校验

```
OAuth2 登录回调 URL 的白名单漏洞：

@Bean
public ClientRegistration clientRegistration() {
    return ClientRegistration
        .withRegistrationId("google")
        .redirectUri("{baseUrl}/login/oauth2/code/{registrationId}")  // ← {baseUrl} 来自请求 Host 头！
        .build();
}
```

**检测规则：**

```bash
# 检测 OAuth2 Client 配置
grep -rnE "ClientRegistration|oauth2Login|OAuth2AuthorizedClient|redirectUri|redirect-uri" --include="*.java" --include="*.yml" --include="*.yaml"
```

**判定规则：**
- redirectUri 使用 `{baseUrl}` 或未校验 redirect_uri → 🟡 Host 头攻击 → 授权码窃取
