# Skills 详细说明

## java-route-mapper

**Java Web 源码路由与参数映射分析工具**

适用场景：
- 无 API 文档的项目进行接口梳理
- 生成 Burp Suite 测试请求模板
- 分析源码中的可访问端点

**支持框架：**
- Spring MVC / Spring Boot
- Servlet（web.xml、@WebServlet）
- JAX-RS（@Path、@GET、@POST 等）
- Struts 2
- CXF Web Services

**核心功能：**
1. 自动识别项目类型和框架
2. 扫描并提取 HTTP 路由（@Controller、@RequestMapping 等）
3. 解析参数结构（Path 变量、Query 参数、Body 参数、Header 参数、Cookie 参数）
4. 支持 .class 和 .jar 文件的反编译分析
5. 生成标准 HTTP 请求模板

**使用示例：**

```
输入: 项目源码路径
输出: 完整的路由清单和 Burp Suite 请求模板

=== [1] 用户登录 ===
位置: UserController.login (src/main/java/com/example/controller/UserController.java:45)
HTTP 方法: POST
URL 路径: /api/auth/login
参数结构:
  Body: LoginRequest (username: String, password: String)

Burp Suite 请求模板:
---
POST /api/auth/login HTTP/1.1
Host: {{host}}
Content-Type: application/json

{"username": "{{username}}", "password": "{{password}}"}
---
```

---

## java-route-tracer

**Java Web 源码路由多层级调用链追踪工具**

适用场景：
- 追踪指定路由的完整调用链（Controller → Service → DAO）
- 分析参数在调用链中的流向和变化
- 识别参数是否到达敏感操作点（SQL/命令/HTTP/文件等）
- 辅助其他审计技能进行漏洞判定

**支持的漏洞类型：**
- SQL 注入 - 追踪参数到 SQL 拼接点
- 命令注入 - 追踪参数到 Runtime.exec()
- SSRF - 追踪参数到 HTTP 请求
- XSS - 追踪参数到响应输出
- 文件操作 - 追踪参数到 File 操作
- XXE/反序列化/LDAP 注入/表达式注入等

**核心功能：**
1. 接收路由路径，定位入口点
2. 追踪从 Controller 到 DAO 层的完整调用链
3. 记录参数在各层中的变量名变化
4. 识别最终使用点类型（Sink）
5. 分析参数的可控性（完全可控/条件可控/不可控）
6. 支持 .class 和 .jar 文件的反编译分析

**使用示例：**

```
输入: 路由路径 + 项目路径
输出: 完整调用链追踪报告

=== 调用链追踪 ===
[L1] ImageCaptureAction.getImageCapture()
     ↓ page (含 orderBy, order), searchBean
[L2] ImageCaptureManager.getImageCaptureJson()
     ↓ page (含 orderBy, order), searchBean

[L3] ImageCaptureDao.getImageCapturePage()
     ↓ page (含 orderBy, order)
[L4] AbstractDao.findSql()
     └──→ sql = sql + " ORDER BY " + page.getOrderBy()

=== 参数可控性分析 ===
| 参数 | Sink类型 | 覆盖类型 | 可控性结论 |
|-------|---------|---------|-----------|
| page.orderBy | SQL ORDER BY | 无覆盖 | ✅ 完全可控 |
| page.order | SQL ORDER BY | 无覆盖 | ✅ 完全可控 |
```

---

## java-sql-audit

**Java Web 源码 SQL 注入漏洞审计工具**

适用场景：
- 识别 SQL 执行框架和实现方式
- 发现 SQL 注入漏洞
- 分析参数化查询使用情况
- 审计动态 SQL 拼接逻辑

**支持框架：**
- JDBC
- MyBatis
- Hibernate

**核心功能：**
1. 识别所有 SQL 执行入口点
2. 分析每个 SQL 操作的参数化情况
3. 检测所有潜在的 SQL 注入模式
4. 为每个风险点提供验证 PoC
5. 分析执行条件（避免误报）
6. 支持 .class 和 .jar 文件的反编译分析
7. 结合 java-route-tracer 进行参数流向追踪

**使用示例：**

```
输入: 项目源码路径
输出: SQL 注入审计报告

=== SQL 操作映射表 ===
| 序号 | 类名 | 方法 | 框架 | 参数化状态 | 可利用性 |
|------|------|------|------|------------|----------|
| 1 | UserMapper | findById | MyBatis | ✅ 安全 | - |
| 2 | UserMapper | findByName | MyBatis | ❌ 危险 | ⚠️ 待验证 |

=== 高危风险详情 ===
🔴 [SQL-001] ORDER BY 注入漏洞
位置: AbstractDao.java:235
框架: JDBC
拼接代码: sql = sql + " ORDER BY " + page.getOrderBy()
触发方式: page.orderBy 参数直接拼接
建议修复: 使用白名单校验或参数化查询
```

---

## java-auth-audit

**Java Web 源码鉴权机制审计工具**

适用场景：
- 识别项目中使用的鉴权框架和实现方式
- 发现鉴权绕过漏洞
- 分析越权访问风险
- 审计权限校验逻辑

**支持框架：**
- Spring Security
- Apache Shiro
- JWT 鉴权
- Session 鉴权
- Filter/Interceptor 拦截器
- 自定义鉴权实现

**核心功能：**
1. 自动识别鉴权框架类型和版本
2. 提取鉴权配置和拦截规则
3. 分析鉴权绕过模式（URL 解析绕过、权限校验绕过等）
4. 识别越权访问风险（IDOR、水平/垂直越权）
5. 检测框架版本已知漏洞
6. 支持 .class 和 .jar 文件的反编译分析

**使用示例：**

```
输入: 项目源码路径
输出: 鉴权机制分析报告、漏洞发现清单

=== 鉴权框架识别 ===
框架: Spring Security
版本: 5.7.2

=== 鉴权配置 ===
SecurityFilterChain: /api/public/** = permitAll()
SecurityFilterChain: /api/admin/** = hasRole('ADMIN')

=== 潜在漏洞 ===
[高危] URI 解析绕过漏洞
  位置: SecurityConfig.java:45
  说明: 使用 regexMatcher() 可能导致 /admin/. 接口绕过鉴权

[高危] IDOR 越权漏洞
  位置: UserController.getUserById (UserController.java:78)
  说明: /api/user/{id} 接口缺少所有权校验，可能访问其他用户数据
```

---

## java-file-upload-audit

**Java Web 源码文件上传漏洞审计工具**

适用场景：
- 识别文件上传入口和实现方式
- 发现任意文件上传、路径穿越与可执行文件上传风险
- 分析文件名/目录/类型/大小校验是否缺失或可绕过
- 审计上传目录与访问控制

**支持框架：**
- Servlet Commons FileUpload
- Spring Boot MultipartFile

**核心功能：**
1. 识别所有上传入口点（ServletFileUpload / MultipartFile）
2. 分析每个上传点的保存路径、文件名来源与校验策略
3. 检测所有潜在的上传风险模式（类型校验缺失、路径穿越、Web 根目录写入）
4. 分析文件名/目录/类型/大小校验是否缺失或可绕过
5. 支持 .class 和 .jar 文件的反编译分析

**使用示例：**

```
输入: 项目源码路径
输出: 文件上传漏洞审计报告

=== 上传点映射表 ===
| 序号 | 类名 | 方法 | 上传实现 | 文件名来源 | 保存路径 | 校验状态 | 可利用性 |
|------|------|------|----------|------------|----------|----------|----------|
| 1 | UploadController | upload | MultipartFile | getOriginalFilename | /uploads/ | ❌ 无校验 | ✅ 已确认 |

=== 高危风险详情 ===
🔴 [C-UPLOAD-001] 任意文件上传漏洞
位置: UploadController.java:45
说明: 文件名直接来自用户输入，未做路径规范化处理
风险: 可通过 ../ 实现路径穿越，写入任意位置
```

---

## java-file-read-audit

**Java Web 源码任意文件读取漏洞审计工具**

适用场景：
- 识别文件读取操作和实现方式
- 发现任意文件读取漏洞
- 分析路径遍历攻击风险
- 审计文件路径参数校验逻辑

**支持方法：**
- BufferedReader / FileReader / FileInputStream
- Scanner
- Files.lines / Files.readAllLines / Files.readAllBytes

**核心功能：**
1. 识别所有文件读取入口点
2. 分析每个文件操作的路径来源
3. 检测所有潜在的路径遍历模式
4. 为每个风险点提供验证 PoC
5. 支持 .class 和 .jar 文件的反编译分析

**使用示例：**

```
输入: 项目源码路径
输出: 文件读取漏洞审计报告

=== 文件操作映射表 ===
| 序号 | 类名 | 方法 | 读取方法 | 路径来源 | 校验状态 | 可利用性 |
|------|------|------|----------|----------|----------|----------|
| 1 | FileController | download | FileInputStream | HTTP参数 | ❌ 无校验 | ✅ 已确认 |

=== 高危风险详情 ===
🔴 [C-FILE-001] 任意文件读取漏洞
位置: FileController.java:45
说明: filePath 参数直接传入 FileInputStream，未做路径校验
风险: 可通过 ../ 路径遍历读取系统任意文件
```

---

## java-xxe-audit

**Java Web 源码 XXE (XML External Entity) 漏洞审计工具**

适用场景：
- 识别 XML 解析器类型和实现方式
- 发现 XXE 注入漏洞
- 分析外部实体防护配置情况
- 审计 XML 输入来源与回显逻辑

**支持解析器：**
- XMLReader
- SAXBuilder (JDOM2)
- SAXReader (dom4j)
- SAXParserFactory
- DocumentBuilderFactory

**核心功能：**
1. 识别所有 XML 解析入口点（5 种主流解析器）
2. 分析每个解析器的外部实体防护配置
3. 追踪 XML 输入来源（用户可控性）
4. 检测回显点（数据是否返回给用户）
5. 支持 .class 和 .jar 文件的反编译分析

**使用示例：**

```
输入: 项目源码路径
输出: XXE 漏洞审计报告

=== XML 解析器映射表 ===
| 序号 | 类名 | 方法 | 解析器类型 | 输入来源 | 安全配置 | 可利用性 |
|------|------|------|-----------|----------|----------|----------|
| 1 | XmlParser | parse | SAXReader | getInputStream | ❌ 未配置 | ✅ 可利用 |

=== 高危风险详情 ===
🔴 [C-XXE-001] XXE 注入漏洞
位置: XmlParser.java:45
说明: SAXReader 未禁用外部实体，用户可控 XML 直接解析
风险: 可读取系统文件、SSRF、Blind XXE
```

---

## java-vuln-scanner

**Java 组件版本漏洞检测工具**

适用场景：
- Java 项目依赖安全审计
- 识别 Log4j、Fastjson、Shiro、Spring 等高危组件漏洞
- jar 包反编译后的依赖分析

**支持输入：**
- pom.xml - Maven 项目
- build.gradle - Gradle 项目
- .jar 文件 - 从文件名或 META-INF 提取依赖信息
- 目录 - 递归扫描，自动按模块分组

**漏洞规则覆盖（130+ CVE）：**

| 组件类别 | 主要漏洞 |
|---------|---------|
| Log4j | CVE-2021-44228 (Log4Shell), CVE-2021-45046 |
| Fastjson | CVE-2022-25845, CVE-2017-18349 |
| Spring | CVE-2022-22965 (Spring4Shell), CVE-2022-22963 |
| Struts2 | S2-045, S2-046, S2-057, S2-061 |
| Shiro | CVE-2016-4437, CVE-2020-11989, CVE-2020-17510 |
| Jackson | CVE-2020-36518, CVE-2019-12384 |
| XStream | CVE-2021-39144 等 15 个 CVE |
| ActiveMQ | CVE-2023-46604 |

**核心功能：**
1. 扫描项目依赖，匹配已知 CVE 规则
2. 按模块分组输出，按严重级别分类
3. AI 自动生成漏洞触发点分析
4. 支持 .class 和 .jar 文件的反编译分析

**使用示例：**

```
输入: 项目源码路径
输出: 漏洞扫描报告

📊 扫描摘要:
   模块数量: 4
   依赖总数: 262
   漏洞总数: 80
   🔴 严重: 24

=== 漏洞详情 ===
🔴 Critical - log4j-core 2.14.1
   CVE-2021-44228 (Log4Shell)
   影响: 远程代码执行
   修复版本: >= 2.17.1
```

---

## java-audit-pipeline

**Java Web 全链路自动化安全审计流水线**

> **前置条件（Agent Teams）：**
> - Claude Code 版本 >= 2.1.32
> - 在 `~/.claude/settings.json` 的 `env` 中添加 `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"`：
>   ```json
>   {
>     "env": {
>       "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
>     }
>   }
>   ```
> - 也可通过环境变量临时启用：`export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
> - （可选）安装 tmux 以获得分屏可视化效果，使用 `Shift+Up/Down` 切换 teammate 视图
>
> 注：Agent Teams 为 research preview 实验性功能，随 Opus 4.6（2026-02-05）发布。

适用场景：
- 一键启动 Java 项目全量安全审计
- 自动识别无鉴权高危路由并精准分析漏洞
- 基于调用链的精准漏洞审计（减少误报）
- 自动校验每个 skill 输出质量

**核心功能：**
1. 使用 agent team 编排多个 agent（含动态扩展的调用链追踪 worker），分 5 个阶段自动完成完整安全审计
2. 阶段1：信息收集（路由分析 + 鉴权审计 + 组件漏洞扫描，并行执行）
3. 阶段2：交叉分析（风险分级 + 漏洞汇总，并行执行）
4. 阶段3：调用链追踪（分批并行追踪高危路由参数流向，含鉴权风险透传）
5. 阶段4：漏洞深度分析（根据 sink 类型选择对应审计 skill，含可利用前置条件，按需并行）
6. 阶段5：质量校验（每阶段完成后立即校验，不合格则重做，通过后关闭 agent 释放资源）

**流程总览：**

```
阶段1: 信息收集（并行）
  ├─ agent-1-route-mapper: /java-route-mapper   → 全量路由+参数  → agent-7 校验 → 通过后关闭
  ├─ agent-2-auth-audit: /java-auth-audit     → 路由鉴权映射    → agent-7 校验 → 通过后关闭
  └─ agent-3-vuln-scanner: /java-vuln-scanner   → 组件漏洞        → agent-7 校验 → 通过后关闭
        ↓ 三个校验全部通过后
阶段2: 交叉分析（并行）
  ├─ agent-4a-risk-classifier: 路由分级（P0/P1/P2） → agent-7 校验 → 通过后关闭
  └─ agent-4b-vuln-aggregator: 漏洞汇总（组件漏洞+鉴权绕过） → agent-7 校验 → 通过后关闭
        ↓ 两个校验全部通过后
阶段3: 调用链追踪（分批并行）
  ├─ agent-5-route-tracer: 读取 P0+P1 全部高危路由（P0+P1=0 时启用 P2 兜底），分批创建追踪任务 → 通过后关闭
  └─ agent-5-1/5-2/.../5-N: /java-route-tracer 并行追踪各批次路由（含鉴权风险透传） → agent-7 校验 → 通过后关闭
        ↓
阶段4: 漏洞深度分析（按需并行）
  ├─ agent-6a-sql-auditor: /java-sql-audit         → SQL注入分析（含可利用前置条件） → agent-7 校验 → 通过后关闭
  ├─ agent-6b-xxe-auditor: /java-xxe-audit         → XXE注入分析（含可利用前置条件） → agent-7 校验 → 通过后关闭
  ├─ agent-6c-upload-auditor: /java-file-upload-audit  → 文件上传分析（含可利用前置条件） → agent-7 校验 → 通过后关闭
  └─ agent-6d-fileread-auditor: /java-file-read-audit   → 文件读取分析（含可利用前置条件） → agent-7 校验 → 通过后关闭
        ↓
阶段5: 汇总报告
  └─ agent-7-quality-checker: 整合所有校验结果，生成最终 quality_report.md → 完成后关闭
```

**使用示例：**

```
/java-audit-pipeline /path/to/project

输入: 源码目录路径 + 输出目录路径（可选，默认 {source_path}_audit）
输出: 完整审计报告目录，包含所有阶段结果和质量检查报告
```

---

## java-deserialization-audit 🆕

**Java Web 源码反序列化漏洞审计工具**

适用场景：
- 识别反序列化入口点
- 检测 classpath 中已知 gadget 链
- 结合鉴权状态评估可利用性

**支持类型：**
- Java 原生反序列化（ObjectInputStream）
- Fastjson (JSON.parse)
- Jackson (enableDefaultTyping)
- XStream (fromXML)
- Hessian/Hessian2
- JNDI 注入 (InitialContext.lookup)
- SnakeYAML (Yaml.load)

---

## java-ssrf-audit 🆕

**Java Web 源码 SSRF 漏洞审计工具**

适用场景：
- 识别 HTTP 请求出口点
- 检测 SSRF 漏洞
- 分析云环境元数据利用链

**支持 Sink：**
- RestTemplate、HttpClient、OkHttp、URLConnection 等 12 种
- 云环境元数据端点（AWS/GCP/Azure/阿里云/腾讯云/K8s）

---

## java-expression-inject-audit 🆕

**Java Web 源码表达式/模板注入漏洞审计工具**

适用场景：
- 识别表达式求值入口
- 检测模板注入 SSTI
- 评估沙箱绕过可行性

**支持引擎：**
- OGNL (Struts2)、SpEL (Spring)、MVEL、Groovy
- FreeMarker、Velocity、Thymeleaf
- ScriptEngine (Nashorn/Rhino)、JEXL

---

## 增强说明

### java-vuln-scanner
- ✅ 接入 OSV.dev API，CVE 覆盖从 130+ 条扩展到 3000+ 条
- ✅ 新增 `scripts/osv_query.py` 批量查询脚本
- ✅ 支持间接依赖检测和 fat jar 分析

### java-auth-audit
- ✅ 新增 `references/ADVANCED_CHECKS.md` 增强检测项
- ✅ CVE-2023-34034 antMatcher vs mvcMatcher 语义差异
- ✅ Actuator/WebSocket/@Async/Swagger 鉴权缺失检测

### java-route-tracer
- ✅ 新增 `references/ENHANCED_TRACING.md` 增强追踪能力
- ✅ 安全函数白名单消除误报
- ✅ 反射调用解析（method.invoke/Map路由分发）
- ✅ 异步/线程池追踪（ExecutorService/@Async/CompletableFuture）

### java-audit-pipeline
- ✅ 新增阶段0 快速匹配（8 条 grep 规则秒出 P0 高危）
- ✅ 新增 agent-6e/f/g 三个漏洞审计员
- ✅ 新增 agent-8 漏洞利用链编排
- ✅ 新增增量审计模式


所有技能的输出统一到 `{项目名}_audit/` 目录下：

```
{project_name}_audit/
├── route_mapper/              # java-route-mapper 输出（含按模块划分的子目录，主索引在根目录）
├── route_tracer/              # java-route-tracer 输出
├── sql_audit/                 # java-sql-audit 输出
├── auth_audit/                # java-auth-audit 输出
├── file_upload_audit/         # java-file-upload-audit 输出
├── file_read_audit/           # java-file-read-audit 输出
├── xxe_audit/                 # java-xxe-audit 输出
├── deserialization_audit/     # 🆕 java-deserialization-audit 输出
├── ssrf_audit/                # 🆕 java-ssrf-audit 输出
├── expr_inject_audit/         # 🆕 java-expression-inject-audit 输出
├── vuln_report/               # java-vuln-scanner 输出
├── quick_hits/                # 阶段0 快速匹配命中
├── cross_analysis/            # java-audit-pipeline 交叉分析结果
│   ├── high_risk_routes.md              # agent-4a 输出
│   ├── trace_batch_plan.md              # agent-5 分批方案
│   ├── component_vulnerabilities.md     # agent-4b 输出
│   └── auth_bypass_vulnerabilities.md   # agent-4b 输出
├── decompiled/                # 反编译输出（多 agent 共享）
└── quality_report.md          # java-audit-pipeline 质量检查报告
```
