# 快速模式匹配规则库 — 秒级命中高危漏洞

规则按 `grep` 正则模式匹配，在完整流水线启动前先行扫描。命中后直接报告，无需等待 trace 分析。

## 规则 1: 命令执行 Sink（无鉴权直接报 RCE）

```bash
# Runtime.exec / ProcessBuilder + 无鉴权
grep -rnE "Runtime\.getRuntime\(\)\.exec\(|new ProcessBuilder\(|ProcessBuilder\.start\(" {source_path} --include="*.java"

# 命中后 → 检查鉴权状态 → 若无鉴权 → 直接报 RCE
```

**判定：**
- 命中 + ❌无鉴权 → 🔴 C-EXEC-001 RCE
- 命中 + ✅有鉴权 → 🟡 待深度分析

## 规则 2: JDBC 不安全拼接（无鉴权直接报 SQL 注入）

```bash
# Statement.executeQuery/executeUpdate 非 PreapredStatement 的拼接
grep -rnE "\.executeQuery\(|\.executeUpdate\(" {source_path} --include="*.java" | grep -vE "PreparedStatement|prepareStatement"

# SQL 字符串拼接（排除 import/注释/log 行）
grep -rnE "\+.*\"\s*(SELECT|INSERT|UPDATE|DELETE|ORDER|GROUP)\b|\"(SELECT|INSERT|UPDATE|DELETE|ORDER|GROUP).*\"\s*\+" {source_path} --include="*.java"

# MyBatis ${} 不安全占位符
grep -rnE '\$\{[^}]+\}' {source_path} --include="*.xml"

# Hibernate HQL 拼接
grep -rnE "createQuery\(\s*\"" {source_path} --include="*.java" | grep -ivE "\.setParameter"
```

**判定：**
- 命中 + ❌无鉴权 → 🔴 C-SQL-001 SQL 注入
- 命中 + ⚠️ PreparedStatement → 🟢 安全

## 规则 3: Controller 缺鉴权注解

```bash
# 第一步：找所有 Controller 类中 HTTP mapping 注解所在文件
grep -rlnE "@(Get|Post|Put|Delete|Request)Mapping" {source_path} --include="*.java"

# 第二步：在命中的文件中，排除同时包含鉴权注解的文件（保守策略）
# 单独 grep 找有鉴权注解的文件作为"安全白名单"
grep -rlnE "@PreAuthorize|@Secured|@RolesAllowed|@RequiresRoles|@RequiresPermissions|@PermitAll" {source_path} --include="*.java"

# 第三步：diff 两个结果集，仅在 mapping 文件列表但不在鉴权文件列表中的即为可疑
# 跨平台命令（macOS / Linux / Windows Git Bash）:
# 使用 grep -vFxf 做文件级差集（比 comm 更兼容）
grep -rlnE "@(Get|Post|Put|Delete|Request)Mapping" {source_path} --include="*.java" | sort > {output_path}/scripts/_routes_mapping.tmp
grep -rlnE "@PreAuthorize|@Secured|@RolesAllowed|@RequiresRoles|@RequiresPermissions|@PermitAll" {source_path} --include="*.java" | sort > {output_path}/scripts/_routes_auth.tmp
grep -vFxf {output_path}/scripts/_routes_auth.tmp {output_path}/scripts/_routes_mapping.tmp
```

**判定：**
- 仅出现在 mapping 结果中的文件 → ❌ 可能无鉴权 → P0 路由（需后续 agent-2 确认）
- 同时出现在两个结果中的文件 → 有鉴权注解 → 降低优先级
- ⚠️ 此规则为快速初筛，最终鉴权判定以 agent-2-auth-audit 深度分析为准

## 规则 4: 文件操作无路径校验

```bash
# 用户文件名 + File 构造
grep -rnE "getOriginalFilename\(\)|\.getParameter\(.*file.*name|\.getParameter\(.*path" {source_path} --include="*.java" -A 3 | \
grep -E "new File\(|FileInputStream\(|FileOutputStream\(|Files\.(read|write|copy|move)"
```

**判定：**
- 命中 + ❌无鉴权 → 🔴 C-UPLOAD-001 / C-FILE-001 文件读写漏洞

## 规则 5: 反序列化入口点

```bash
grep -rnE "ObjectInputStream|readObject\(\)|JSON\.parse\(|Yaml\.load\(|fromXML\(|readValue\(.*Object\.class" {source_path} --include="*.java"
```

**判定：**
- 命中 `JSON.parse(userInput)` + ❌无鉴权 → 🔴 C-DESERIALIZE-001 Fastjson 反序列化
- 命中 `ObjectInputStream(request.getInputStream())` + ❌无鉴权 → 🔴 C-DESERIALIZE-002 Java 原生反序列化

## 规则 6: JNDI Lookup

```bash
grep -rnE "\.lookup\(|InitialContext\(|InitialDirContext\(" {source_path} --include="*.java"
```

**判定：**
- 命中 + lookup 参数含用户输入 + ❌无鉴权 → 🔴 C-JNDI-001 JNDI 注入

## 规则 7: 表达式求值

```bash
grep -rnE "SpelExpressionParser|parseExpression\(|Ognl\.getValue|MVEL\.eval|GroovyShell\(\)\.evaluate|ScriptEngine.*eval" {source_path} --include="*.java"
```

**判定：**
- 命中 + 参数可控 + ❌无鉴权 → 🔴 C-EXPR-001 表达式注入

## 规则 8: URL openConnection (SSRF)

```bash
grep -rnE "\.openConnection\(\)|URL\(.*\)|RestTemplate.*exchange\(|HttpClient.*execute\(.*request|newCall\(.*url" {source_path} --include="*.java"
```

**判定：**
- 命中 + URL 参数可控 + ❌无鉴权 → 🔴 C-SSRF-001 SSRF

## 执行策略

```
1. 负责人启动流水线后，首先并行执行所有 8 条规则（grep 扫描）
2. 命中规则 → 立即写入 quick_hits.md
3. 同时启动正常流水线（route-mapper / auth-audit / vuln-scanner）
4. 流水线产出的深度分析结果与 quick_hits 合并去重
5. 最终报告中优先展示 quick_hits 的高危漏洞
```
