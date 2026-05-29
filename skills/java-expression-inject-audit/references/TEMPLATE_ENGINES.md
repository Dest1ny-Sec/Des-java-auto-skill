# Java 模板引擎 SSTI 详解

## 目录

- [1. FreeMarker](#1-freemarker)
- [2. Velocity](#2-velocity)
- [3. Thymeleaf](#3-thymeleaf)
- [4. Groovy Templates](#4-groovy-templates)
- [5. Pebble](#5-pebble)
- [6. 其他模板引擎](#6-其他模板引擎)
- [7. 通用 SSTI 审计框架](#7-通用-ssti-审计框架)

---

## 1. FreeMarker

### 识别特征

```java
import freemarker.template.Configuration;
import freemarker.template.Template;
import freemarker.template.TemplateException;
import org.springframework.ui.freemarker.FreeMarkerTemplateUtils;
```

### Maven 依赖

```xml
<dependency>
    <groupId>org.freemarker</groupId>
    <artifactId>freemarker</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-freemarker</artifactId>
</dependency>
```

### 危险 Sink 方法

```java
// 模板处理
Template template = configuration.getTemplate(templateName);
template.process(dataModel, writer);          // ← 主入口

// Spring 封装
FreeMarkerTemplateUtils.processTemplateIntoString(template, model);

// 字符串模板（更危险 - 用户可直接控制模板内容）
new Template("inline", new StringReader(userInput), configuration);
Template template = Template.getPlainTextTemplate("name", userInput, configuration);
```

### 注入向量

#### 向量 1: 模板名称可控

```java
// ❌ 危险：模板名称来自用户输入
@GetMapping("/render")
public String render(@RequestParam String template, Model model) {
    // template = "user" → /templates/user.html
    // 若路径穿越: template = "../../etc/passwd"
    return template;  // Spring 自动找 templates/template.html
}
```

#### 向量 2: 模板变量名/值可控（核心 SSTI）

```java
// ❌ 危险：用户输入作为模板变量值
model.addAttribute("userInput", request.getParameter("data"));
// 若 data = "${'freemarker.template.utility.Execute'?new()('id')}"
// 安全配置下 new_builtin_class_resolver=allows_nothing → 被拦截

// ⚠️ 但若用户能控制变量名
model.addAttribute(request.getParameter("key"), value);
// 可注入 <#assign> 指令
```

#### 向量 3: 模板内容直接来自用户（最危险）

```java
// ❌ 极度危险：用户输入直接作为模板内容
String templateContent = request.getParameter("template");
Template t = new Template("inline", new StringReader(templateContent), cfg);
t.process(model, writer);  // SSTI!
```

### 沙箱机制与绕过

| 配置 | 版本 | 效果 |
|------|------|------|
| `new_builtin_class_resolver: allows_nothing` | 2.3.31+ | 禁用 `?new` — 阻断关键 RCE 链 |
| `new_builtin_class_resolver: safer_resolver` | 2.3.31+ | 仅允许白名单类 |
| `new_builtin_class_resolver: all_resolver` | 默认 | 允许所有类 — **危险** |
| `api_builtin_enabled: false` | 2.3.22+ | 禁用 `?api` 反射访问 |
| `expose-spring-macro-helpers: false` | Spring Boot | 禁用 `springMacroRequestContext` |

```
RCE 利用链:
1. Execute?new() → Runtime.exec  (≤ 2.3.30 直接可用)
2. ObjectConstructor?new() → ProcessBuilder  (2.3.31+ Execute 已移除)
3. JdbcRowSetImpl?new() → JNDI  (2.3.31+ 但需要 classpath 有对应类)
4. TemplatesImpl?new() → 字节码加载  (需要特定 class)

沙箱绕过 (UJCMS 实战经验):
- new_builtin_class_resolver: allows_nothing → 彻底阻断 ?new 攻击链
- expose-spring-macro-helpers: false → 阻断 Spring 宏助手反射
- 结论: 两者均为 allows_nothing → RCE 不可行 → 降为 Low
```

### 搜索正则

```bash
grep -rnE "Template\.process|Configuration\.getTemplate|FreeMarkerTemplateUtils|new Template\(|Template\.getPlainTextTemplate" --include="*.java"
grep -rnE "new_builtin_class_resolver|api_builtin_enabled|expose-spring-macro-helpers" --include="*.yaml" --include="*.yml" --include="*.properties"
grep -rnE "freemarker\.template\.utility\.(Execute|ObjectConstructor)" --include="*.java"
```

---

## 2. Velocity

### 识别特征

```java
import org.apache.velocity.app.Velocity;
import org.apache.velocity.app.VelocityEngine;
import org.apache.velocity.Template;
import org.apache.velocity.VelocityContext;
import org.apache.velocity.runtime.RuntimeServices;
```

### 危险 Sink 方法

```java
// VelocityEngine
VelocityEngine ve = new VelocityEngine();
ve.evaluate(context, writer, "log", userTemplate);   // ← 用户模板注入
ve.mergeTemplate(templateName, encoding, context, writer);

// 直接 Velocity 调用
Velocity.evaluate(context, writer, "log", userInput);  // ← SSTI
Velocity.mergeTemplate(templateFile, encoding, context, writer);

// RuntimeServices
RuntimeServices.evaluate(context, writer, "log", userInput);
```

### Payload

```velocity
#set($x='')##
$x.getClass().forName('java.lang.Runtime').getMethod('getRuntime',null).invoke(null,null).exec('id')
```

### 搜索正则

```bash
grep -rnE "Velocity\.(evaluate|mergeTemplate)|VelocityEngine\.evaluate|VelocityContext|VelocityEngine" --include="*.java"
```

---

## 3. Thymeleaf

### 识别特征

```java
import org.thymeleaf.TemplateEngine;
import org.thymeleaf.spring5.SpringTemplateEngine;
import org.thymeleaf.context.Context;
```

### 危险 Sink 方法

```java
// ❌ 危险：模板名称来自用户输入
@GetMapping("/page")
public String page(@RequestParam String name) {
    return name;  // 若 name = "../../admin" → 路径穿越
}

// ❌ 危险：直接使用 TemplateEngine 处理用户输入
Context ctx = new Context();
ctx.setVariable("userInput", userInput);  // ← 变量值可控
templateEngine.process(templateName, ctx, writer);

// ❌ 危险：使用 SpringTemplateEngine 处理内联模板
springTemplateEngine.process("<div th:text=\"" + userInput + "\"></div>", ctx);
```

### SSTI Payload

Thymeleaf 自身安全度较高，SSI 需要较苛刻的前置条件：

```java
// 需要 Thymeleaf 的预处理表达式
__${T(java.lang.Runtime).getRuntime().exec('id')}__::.x

// 需要 SpringTemplateEngine + 用户控制模板名称/内容
// 单独的变量值注入一般无法直接 RCE
```

### 搜索正则

```bash
grep -rnE "TemplateEngine\.process|SpringTemplateEngine|th:fragment|th:text|th:utext|__\$\{" --include="*.java"
```

---

## 4. Groovy Templates

### 识别特征

```java
import groovy.text.SimpleTemplateEngine;
import groovy.text.GStringTemplateEngine;
import groovy.text.XmlTemplateEngine;
import groovy.text.Template;
```

### 危险 Sink 方法

```java
SimpleTemplateEngine engine = new SimpleTemplateEngine();
Template template = engine.createTemplate(userInput);  // ← 模板可控
String result = template.make(binding).toString();      // 执行

GStringTemplateEngine gte = new GStringTemplateEngine();
Template t = gte.createTemplate(userInput);            // ← 模板可控
```

### Payload

```
${"id".execute()}
${Runtime.getRuntime().exec("id")}
<%= "id".execute() %>
```

### 搜索正则

```bash
grep -rnE "SimpleTemplateEngine|GStringTemplateEngine|XmlTemplateEngine|createTemplate" --include="*.java"
```

---

## 5. Pebble

### 识别特征

```java
import io.pebbletemplates.pebble.PebbleEngine;
import io.pebbletemplates.pebble.template.PebbleTemplate;
```

### 危险 Sink 方法

```java
PebbleEngine engine = new PebbleEngine.Builder().build();
PebbleTemplate template = engine.getTemplate(templateName);
template.evaluate(writer, context);
```

### 搜索正则

```bash
grep -rnE "PebbleEngine|PebbleTemplate|pebble" --include="*.java" pom.xml
```

---

## 6. 其他模板引擎

### Jade4j

```java
JadeConfiguration config = new JadeConfiguration();
JadeTemplate template = config.getTemplate(templateName);
config.renderTemplate(template, model, writer);
```

### Mustache (安全度最高)

Mustache 是"逻辑-less"模板，默认不执行代码。但需关注自定义扩展：

```java
MustacheFactory mf = new DefaultMustacheFactory();
Mustache mustache = mf.compile(templateName, userInput);  // ← 模板可控
mustache.execute(writer, scope);  // ← 一般安全，但需关注自定义函数
```

### Beetl (国产)

```java
import org.beetl.core.Configuration;
import org.beetl.core.GroupTemplate;
import org.beetl.core.Template;

GroupTemplate gt = new GroupTemplate(...);
Template t = gt.getTemplate(userInput);  // ← SSTI
t.binding("key", value);
t.renderTo(writer);
```

---

## 7. 通用 SSTI 审计框架

### 模板引擎沙箱对比

| 引擎 | 默认沙箱 | RCE 难度 | 绕过方式 |
|------|---------|---------|---------|
| FreeMarker | ⚠️ 较弱 (默认允许 ?new) | 低 | 需 `allows_nothing` 配置 |
| Velocity | ⚠️ 较弱 | 低 | 反射链 |
| Groovy Templates | ❌ 无沙箱 | 极低 | 直接执行 Groovy 代码 |
| Thymeleaf | ✅ 较强 | 高 | 需预处理表达式 |
| Pebble | ✅ 强 | 中-高 | 自定义扩展点 |
| Mustache | ✅ 极强 | 极高 | 自定义扩展点 |
| Beetl | ⚠️ 中等 | 中 | 反射 + 类型转换 |

### SSTI 注入判定矩阵

```
SSTI 风险 = f(引擎类型, 模板可控度, 变量可控度, 沙箱配置)

判定：
├── 模板内容完全可控 (new Template(userInput)) → 🔴 Critical
│   └── 例外: Mustache 默认安全 → 🟢
├── 模板名称可控 (路径穿越) → 🟡 Medium (需结合引擎)
├── 模板变量名/值可控 + 沙箱弱 (如默认 FreeMarker) → 🔴
├── 模板变量值可控 + 沙箱强 (allows_nothing) → 🟢
├── 模板变量值可控 + 沙箱一般 (safer_resolver) → 🟡 (视白名单)
└── 模板/变量均不可控 → 排除
```

### 实战经验 (UJCMS FreeMarker 审计)

从 UJCMS 项目的 FreeMarker SSTI 审计中获得的关键经验：

```yaml
# ✅ 安全配置示例 (application.yaml)
spring.freemarker.settings.new_builtin_class_resolver: allows_nothing
spring.freemarker.expose-spring-macro-helpers: false
```

**审计流程：**
1. `grep` 搜索 `freemarker` 依赖版本 → 确认版本
2. 检查 `application.yaml/.properties` 中的 `new_builtin_class_resolver` 配置
3. 扫描所有 `Template.process()` 调用点
4. 追踪每个调用点的模板数据来源（数据库、用户输入、配置文件）
5. 对用户可控的数据，评估是否能在模板中注入 FreeMarker 指令
6. 若 `allows_nothing` + `expose-spring-macro-helpers: false` → RCE 无效 → 降级
7. 若可控但沙箱强 → 标记为 Low (理论风险，无实际 RCE)

**关键认识：** 配置了 `allows_nothing` 之后，即使模板变量完全可控，也无法执行 `?new()` 进行 RCE。这是从 UJCMS 审计中确认的关键结论。
