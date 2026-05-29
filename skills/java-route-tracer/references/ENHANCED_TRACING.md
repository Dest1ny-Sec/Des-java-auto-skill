# Route Tracer 增强 — 安全函数白名单 & 反射/异步追踪

本文档补充 java-route-tracer 的追踪能力增强规则。

---

## 1. 安全函数白名单（误报消除）

### 1.1 自动安全处理函数识别

tracer 在追踪参数流向时，若参数经过以下模式的函数，**自动降级风险**：

```java
// SQL 安全函数（参数化查询自动标记为安全）
PreparedStatement.setString()
PreparedStatement.setInt()
PreparedStatement.setLong()
NamedParameterJdbcTemplate.update()
JdbcTemplate.query(sql, Object[], RowMapper)
MyBatis #{param} 占位符  // 注意：仅 #{} 安全，${} 仍危险

// 编码/转义函数
StringEscapeUtils.escapeHtml4()
StringEscapeUtils.escapeJava()
HtmlUtils.htmlEscape()
URLEncoder.encode()
Encode.forHtml()
ESAPI.encoder().encodeForSQL()
OwaspEncoder.forSql()

// 输入清洗函数（命名模式识别，而非具体调用）
*escape*(*)      // 方法名含 escape
*sanitize*(*)    // 方法名含 sanitize
*validate*(*)    // 方法名含 validate（返回 boolean 则标记为校验函数）
*encode*(*)      // 方法名含 encode
*filter*(*)      // 方法名含 filter
```

### 1.2 安全函数对风险等级的影响

| 安全函数覆盖 | 风险调整 |
|:------------|:---------|
| 经过 PreparedStatement.setXxx | SQL注入 → 🟢 安全 |
| 经过 StringEscapeUtils.escapeHtml4 | XSS → 🟢 安全 |
| 经过 validator.validate() 且后置 check | ✅ 有效防御 |
| 经过 regex.replaceAll("[^a-zA-Z0-9]", "") | ✅ 有效防御（白名单过滤） |
| 经过 startsWith("/safe/path/") 前缀校验 | ⚠️ 条件防御（需检查是否可绕过） |

---

## 2. 反射调用解析

### 2.1 反射模式识别

tracer 遇到以下模式时**不中断追踪，而是展开分析**：

```java
// 模式1: Map 路由分发
Map<String, Handler> handlerMap = ...;
Handler handler = handlerMap.get(actionName);  // ← actionName 来自用户输入
Object result = handler.execute(params);       // ← params 可能来自用户输入
```

**分析策略：**
1. 识别 `handlerMap` 的初始化位置（通常在 `@PostConstruct` 或构造函数中）
2. 提取所有已注册的 handler key → value 映射
3. 对每个 handler 对应的实际方法继续追踪

```java
// 模式2: Method.invoke 反射
Method method = clazz.getMethod(methodName, paramTypes);
Object result = method.invoke(target, args);
```

**分析策略：**
1. 若 `methodName` 来自用户输入 → 报告 `🔴 方法名完全可控`
2. 若 `methodName` 来自静态常量/MAP KEY → 展开该方法的调用链
3. 若 `args` 来自用户输入 → 标记参数流向

```java
// 模式3: Spring AOP 代理
@Around("@annotation(Audited)")
public Object audit(ProceedingJoinPoint pjp) {
    Object[] args = pjp.getArgs();   // ← 原始参数
    return pjp.proceed(args);         // ← 透传
}
```

**分析策略：**
1. 识别 `@Around` 和 `@Before` 切面中的 `ProceedingJoinPoint.proceed()`
2. AOP 代理是参数透传，不改变可控性
3. 继续追踪被代理方法的内部实现

### 2.2 反射 sink 检测

| 反射模式 | Sink 类型 | 风险 |
|:---------|:----------|:-----|
| `Class.forName(userInput)` | 动态类加载 | 🔴 可加载恶意类 |
| `clazz.getMethod(userInput, ...)` | 方法名可控 | 🟡 可调用任意方法 |
| `method.invoke(target, userInput)` | 参数可控 | 🔴 |
| `ClassLoader.loadClass(userInput)` | 动态类加载 | 🔴 |
| `Thread.currentThread().getContextClassLoader().loadClass(userInput)` | 动态类加载 | 🔴 |

---

## 3. 异步/线程池追踪

### 3.1 异步模式识别

```java
// 模式1: ThreadPoolExecutor / ExecutorService
executorService.submit(() -> {
    dangerousFunction(userData);  // ← tracer 必须追踪到
});

// 模式2: @Async
@Async
public void process(String userData) {
    dangerousFunction(userData);  // ← tracer 必须追踪到
}

// 模式3: CompletableFuture
CompletableFuture.supplyAsync(() -> dangerousFunction(userData));

// 模式4: 响应式 (Reactor/RxJava)
Mono.just(userData).map(data -> dangerousFunction(data));
```

### 3.2 追踪策略

```
对于 ExecutorService.submit / @Async / CompletableFuture：
1. 识别 lambda 或方法引用内的参数
2. 检查参数是否来自 Controller 入参
3. 若是 → 继续追踪 lambda 体内的调用链
4. 在报告中标注 "⚠️ 异步执行"（因为线程上下文切换可能导致鉴权失效）

对于 Reactor：
1. 识别 Mono.just() / Flux.just() 的数据来源
2. 追踪 .map() / .flatMap() 中的操作
3. 检查 .subscribe() 时的 SecurityContext
```

---

## 4. 跨方法数据流不中断规则

### 4.1 对象包装器追踪

```java
// Controller
public Result query(UserQuery query) {
    query.setKeyword(userInput);  // ← tracer 追踪 query.keyword
    return service.search(query);  // ← 进入 Service
}

// Service
public Result search(UserQuery query) {
    return dao.search(query.getKeyword());  // ← keyword 来源是 query 对象
}
```

**追踪规则：**
- 当参数是对象（非基本类型）时，追踪其在调用链中的所有 setter 调用
- getter 的结果（=`query.getKeyword()`）直接继承对应 setter 的参数可控性
- 禁止在对象边界处断链

### 4.2 集合/Map 容器追踪

```java
Map<String, Object> params = new HashMap<>();
params.put("keyword", userInput);  // ← tracer 追踪 Map.put
String sql = "SELECT * FROM users WHERE name = '" + params.get("keyword") + "'";  // ← 此处标记
```

**追踪规则：**
- `Map.put(key, userInput)` → 记录 key 对应的值为可控
- `List.add(userInput)` → 记录该位置元素为可控
- `Map.get(key)` / `List.get(index)` → 向前查找对应的 put/add 操作

---

## 5. tracer 增强输出

在现有的调用链报告基础上，新增以下章节：

```markdown
## 安全函数分析
| 参数 | 经过的安全函数 | 防御有效性 | 剩余风险 |
|:-----|:--------------|:-----------|:---------|
| keyword | PreparedStatement.setString(1, keyword) | ✅ 有效 | 🟢 无 |
| orderBy | 无 | ❌ 无防御 | 🔴 SQL注入 |

## 反射/动态调用分析
| 调用点 | 模式 | 可控性 | 展开结果 |
|:-------|:-----|:-------|:---------|
| handlerMap.get(actionName) | Map路由分发 | ✅ actionName可控 | 已展开3个Handler |
| method.invoke(target, id) | 反射调用 | ⚠️ id可控 | 已追踪到DAO层 |

## 异步执行标记
| 调用点 | 异步方式 | SecurityContext传播 | 鉴权风险 |
|:-------|:---------|:-------------------|:---------|
| executorService.submit() | 线程池 | ❌ 不传播 | ⚠️ @Async方法内鉴权失效 |
```
