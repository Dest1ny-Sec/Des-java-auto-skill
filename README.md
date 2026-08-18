<div align="center">

<table style="background: #0B0E14; padding: 48px 56px; border-radius: 8px; color: #F5F1E8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif; width: 100%; border-collapse: separate; border-spacing: 0;">
<tr>
<td style="width: 60%; vertical-align: top; padding-right: 24px;">

<h1 style="font-size: 60px; font-weight: 800; color: #F5F1E8; margin: 0 0 12px 0; letter-spacing: 0.5px; line-height: 1.1;">Des-java-auto-skill</h1>

<p style="font-size: 22px; color: #C9C5BC; margin: 0 0 4px 0; font-weight: 600;">Java Web 全链路自动化审计</p>
<p style="font-size: 16px; color: #8A93A6; margin: 0 0 8px 0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">8 漏洞 · 7 阶段 · 12 sink · 10+ 引擎</p>
<p style="font-size: 14px; color: #5C6370; margin: 0 0 24px 0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">End-to-end automated Java Web audit</p>

<p style="font-size: 20px; margin: 0 0 20px 0; line-height: 1.5;"><span style="color:#8A93A6; font-weight:400; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">给路径</span>&nbsp;&nbsp;<span style="color:#5C6370; font-weight:400; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">→</span>&nbsp;&nbsp;<span style="color:#8A93A6; font-weight:400; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">7 阶段</span>&nbsp;&nbsp;<span style="color:#5C6370; font-weight:400; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">→</span>&nbsp;&nbsp;<span style="color:#FF8C00; font-weight:700; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">跑 sink</span>&nbsp;&nbsp;<span style="color:#5C6370; font-weight:400; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">→</span>&nbsp;&nbsp;<span style="color:#8A93A6; font-weight:400; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">出报告</span></p>

<p style="font-size: 16px; color: #8A93A6; margin: 0 0 28px 0; line-height: 1.7;">给一个 Java Web 项目路径，自动跑完全流程，出一份完整审计报告。</p>

<p style="font-size: 13px; color: #5C6370; margin: 0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0.3px;">Java · Claude Code · JavaParser</p>
<p style="font-size: 13px; color: #5C6370; margin: 6px 0 0 0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0.3px;">8 漏洞类型 · 7 阶段 · 12 sink · 10+ 表达式引擎</p>

</td>
<td style="width: 40%; vertical-align: top;">

<div style="background: #10141D; border: 1.5px solid #3A4150; border-radius: 10px; padding: 14px 18px 18px 18px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 14px; line-height: 1.5;">

<div style="display: flex; align-items: center; gap: 6px; padding-bottom: 10px; border-bottom: 1px solid #1A2130; margin-bottom: 12px;">
<span style="width: 9px; height: 9px; border-radius: 50%; background: #5C6370;"></span>
<span style="width: 9px; height: 9px; border-radius: 50%; background: #5C6370;"></span>
<span style="width: 9px; height: 9px; border-radius: 50%; background: #FF8C00;"></span>
<span style="color: #5C6370; font-size: 12px; margin-left: 10px;">java-skill · audit pipeline</span>
</div>

<div style="color:#F5F1E8; font-weight:400;">$ /java-web-audit /path/to/spring-app</div><div style="color:#8A93A6; font-weight:400;">[1/7] 路由识别 ... 23 个</div><div style="color:#8A93A6; font-weight:400;">[2/7] 控制器分析 ... OK</div><div style="color:#8A93A6; font-weight:400;">[3/7] 调用链追踪 ... OK</div><div style="color:#8A93A6; font-weight:400;">[4/7] sink 匹配 ... 8 漏洞命中</div><div style="color:#8A93A6; font-weight:400;">[5/7] 利用链编排 ... 1 链</div><div style="color:#8A93A6; font-weight:400;">[6/7] 报告生成 ... OK</div><div style="color:#FF8C00; font-weight:700;">[!] 8 漏洞 · 1 利用链 · 报告 → ./report.md</div><div style="color:#F5F1E8; font-weight:400;">$ ▮</div>
</div>

</td>
</tr>
</table>

<br/>



<div align="center">
  <img src="https://skillicons.dev/icons?i=java,python,claude,regex,git,linux,docker,vscode" alt="stacks" />
</div>




<div align="center">
  <img src="https://skillicons.dev/icons?i=java,python,claude,regex,git,linux,docker,vscode" alt="stacks" />
</div>

<br/>

<sub>基于 Claude Code · JavaParser AST 解析 · OSV.dev CVE API</sub>


> ⚠️ **仅供学术交流与安全研究使用 · 禁止用于任何非法或盈利行为 · 请确保所有测试目标均已获得授权**

---

## 它不是简单的正则匹配，而是一个 **7 阶段流水线的智能审计**

传统 Java 审计靠人肉 grep + 反编译 + 经验，效率低。Des-java-auto-skill 跑 **7 阶段流水线**（路由识别 → 控制器分析 → 调用链追踪 → sink 匹配 → 利用链编排 → 报告 → 快速模式），把"中危"串成"Critical"，还实时查 OSV.dev 3000+ CVE 补组件漏洞。

- **路由识别 → 控制器分析 → 调用链追踪 → sink 匹配 → 利用链编排 → 报告生成 → 快速模式**
- **8** 漏洞类型 / **12** sink / **10+** 表达式引擎（OGNL / SpEL / MVEL / FreeMarker / Velocity）
- OSV.dev 实时查 **3000+ CVE**（Log4j / Fastjson / Spring / Shiro / Struts2 / Jackson / XStream）

# Des-java-auto-skill

> 一行命令，挖完整个 Java Web 项目。基于 [java-audit-skills](https://github.com/RuoJi6/java-audit-skills) 深度二次开发。

<p align="center">
  <a href="https://github.com/Dest1ny-Sec/Des-java-auto-skill/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Dest1ny-Sec/Des-java-auto-skill?style=flat-square&color=7B2CBF&labelColor=0d1117" alt="License" /></a>
  <a href="https://github.com/Dest1ny-Sec/Des-java-auto-skill/stargazers"><img src="https://img.shields.io/github/stars/Dest1ny-Sec/Des-java-auto-skill?style=flat-square&color=FF006E&labelColor=0d1117" alt="Stars" /></a>
  <a href="https://github.com/Dest1ny-Sec/Des-java-auto-skill/actions"><img src="https://img.shields.io/github/actions/workflow/status/Dest1ny-Sec/Des-java-auto-skill/ci.yml?style=flat-square&color=00D4AA&labelColor=0d1117&label=CI" alt="CI" /></a>
  <a href="https://claude.ai/code"><img src="https://img.shields.io/badge/Claude%20Code-%3E%3D%202.1.32-FF6B35?style=flat-square&labelColor=0d1117" alt="Claude Code" /></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-3DDC84?style=flat-square&labelColor=0d1117" alt="Platform" />
</p>

<br/>

---

---

## 这是什么

一个 Claude Code 技能包。输入一个 Java Web 项目路径，自动跑完 **7 阶段流水线**——识别路由、追踪调用链、检测漏洞、编排利用链——最终产出一份完整的审计报告。

**不需要你懂安全。** 启动之后去喝杯咖啡，回来看报告就行。

## 它能挖到什么

| 漏洞类型 | 能发现什么 | 示例 |
|:---------|:-----------|:-----|
| 🔴 **SQL 注入** | ORDER BY 拼接、MyBatis ${}、HQL 注入 | `sql + " ORDER BY " + page.getOrderBy()` |
| 🔴 **反序列化** | ObjectInputStream、Fastjson、Jackson、Hessian、JNDI | `JSON.parse(userInput)` + classpath 含 CC1 链 |
| 🔴 **SSRF** | RestTemplate、HttpClient、OkHttp 等 12 种 sink | `restTemplate.getForObject(userUrl)` → 打云元数据 |
| 🔴 **表达式注入** | OGNL、SpEL、MVEL、FreeMarker、Velocity 等 10+ 引擎 | Struts2 S2-045 Content-Type 注入 |
| 🟠 **XXE** | 5 种 XML 解析器外部实体注入 | `SAXReader` 未禁用 DOCTYPE |
| 🟠 **文件上传** | 任意文件上传、路径穿越、Web 目录写入 | `getOriginalFilename()` 直接拼路径 |
| 🟠 **文件读取** | 任意文件读取、路径遍历 | `new FileInputStream(userPath)` 无校验 |
| 🟠 **鉴权绕过** | Shiro/Spring Security 绕过、越权、Actuator 暴露 | `/admin;.js` 绕过 Filter |

**组件漏洞**：通过 OSV.dev API 实时查询 3000+ CVE，覆盖 Log4j、Fastjson、Spring、Shiro、Struts2、Jackson、XStream 等。

**利用链编排**：自动把零散的"中危"漏洞串起来。比如「文件读取 → Shiro 密钥 → RememberMe RCE」→ 从 Medium 升级到 Critical。

## 5 分钟快速体验

### 1. 安装

```bash
# 克隆到 Claude Code skills 目录
git clone https://github.com/Dest1ny-Sec/Des-java-auto-skill.git ~/.claude/skills/Des-java-auto-skill

# 安装 Python 依赖（三平台通用）
pip3 install -r ~/.claude/skills/Des-java-auto-skill/requirements.txt
```

**启用 Agent Teams（必须，按你的系统选一个）：**

```bash
# macOS / Linux — 加到 shell 配置文件
echo 'export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1' >> ~/.zshrc  # zsh
echo 'export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1' >> ~/.bashrc # bash

# Windows PowerShell
[Environment]::SetEnvironmentVariable('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS','1','User')

# Windows CMD
setx CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS 1
```

### 2. 跑起来

```bash
# 进入 Claude Code，对一个 Java 项目执行：
/java-audit-pipeline --quick /path/to/your-java-project
```

3-5 分钟后，打开 `{项目名}_audit/quality_report.md` 看结果。

### 3. 三种模式

```bash
# 🚀 快速模式 — 小项目、首次体验、快速排查（3-5 分钟）
/java-audit-pipeline --quick /path/to/project

# 🏗️ 标准模式 — 正式审计、中大型项目（10-60 分钟）
/java-audit-pipeline /path/to/project

# 🔄 增量模式 — 只审计 git diff 变更的文件
/java-audit-pipeline --incremental /path/to/project
```

| | 🚀 快速 | 🏗️ 标准 | 🔄 增量 |
|:--|:-------|:-------|:-------|
| 适用 | < 50 路由的小项目 | 正式审计交付 | 日常迭代 |
| 并发 | 1 agent 串行 | 5-10 agent 并行 | 同标准 |
| 质检 | 自检 | 独立 QA 池 | 同标准 |
| 耗时 | **3-5 分钟** | 10-60 分钟 | 按变更量 |

> **不确定用哪个？** 先 `--quick` 看概况，满意了再跑标准模式深挖。

## 流水线做了什么

```
你的 Java 项目
      │
      ▼
┌─────────────────────────────────────────────────┐
│ 阶段 0 · 快速匹配（秒级）                        │
│ 8 条 grep 规则扫描 Runtime.exec / JNDI / 反序列化 │
│ 命中立即报告，不等待后续阶段                      │
├─────────────────────────────────────────────────┤
│ 阶段 1 · 信息收集（并行）                        │
│ ├─ 路由提取：识别所有 HTTP 端点 + 参数结构       │
│ ├─ 鉴权审计：每条路由的鉴权状态 + 绕过检测        │
│ └─ 组件扫描：OSV.dev 3000+ CVE + 130 条本地规则  │
├─────────────────────────────────────────────────┤
│ 阶段 2 · 交叉筛选                               │
│ ├─ 路由分级：P0（无鉴权） / P1（可绕过） / P2     │
│ └─ 漏洞汇总：组件漏洞 + 鉴权绕过合并去重          │
├─────────────────────────────────────────────────┤
│ 阶段 3 · 调用链追踪（分批并行）                  │
│ Controller → Service → DAO 完整链路              │
│ 标注参数是否真正到达 Sink（消除误报）             │
├─────────────────────────────────────────────────┤
│ 阶段 4 · 漏洞深度检测（按 Sink 类型并行）         │
│ SQL / XXE / Upload / FileRead / Deserialize       │
│ SSRF / ExprInject — 只启动有对应 Sink 的检测      │
├─────────────────────────────────────────────────┤
│ 阶段 5 · 利用链编排                              │
│ 匹配 8 种利用链模板，中危漏洞组合升级为 RCE       │
├─────────────────────────────────────────────────┤
│ 阶段 6 · 汇总报告                                │
│ quality_report.md 一键可读                       │
└─────────────────────────────────────────────────┘
```

## 为什么用它

### vs 手工审计
- 一个中型项目（300+ 路由），手工看完所有 Controller → Service → DAO 至少要 **2-3 天**
- 这个工具标准模式 **10-60 分钟**跑完，还不漏

### vs 商用 SAST（Fortify/Checkmarx）
- 商用工具动辄六位数/年，部署配置复杂
- 这个是**免费的**，而且能理解业务逻辑——不是简单的模式匹配
- 商用工具漏报的 ORDER BY 注入、鉴权绕过、利用链组合，这个能抓到

### vs 原版 java-audit-skills
| 维度 | 原版 | Des-java-auto-skill |
|:-----|:-----|:--------------------|
| 漏洞类型 | 5 种 | **8 种** (+反序列化/SSRF/表达式注入) |
| CVE 覆盖 | 130 条硬编码 | **3000+ 条** OSV.dev 实时查询 |
| 利用链 | 无 | **8 种模板**，中危自动升级 RCE |
| 增量审计 | 无 | **git diff**，只扫变更 |
| 快速匹配 | 无 | **秒级 grep** 先出 P0 高危 |
| 快速模式 | 无 | **--quick**，3 分钟看概况 |

## 输出报告

```
{项目名}_audit/
├── quality_report.md          ← 📄 从这里开始看（最终汇总）
├── PARTIAL_RESULTS.md         ← ⚠️ 如果流水线中断会生成这个
├── quick_hits/                ← ⚡ 秒级高危命中
├── route_mapper/              ← 🗺️ 所有 HTTP 路由 + 参数
├── auth_audit/                ← 🔐 鉴权分析 + 绕过 PoC
├── vuln_report/               ← 📦 组件 CVE 清单
├── route_tracer/              ← 🔗 调用链追踪
├── sql_audit/                 ← 💉 SQL 注入详情
├── xxe_audit/                 ← 📋 XXE 详情
├── file_upload_audit/         ← 📤 文件上传详情
├── file_read_audit/           ← 📥 文件读取详情
├── deserialization_audit/     ← ⛓️ 反序列化 + gadget 链
├── ssrf_audit/                ← 🌐 SSRF + 云元数据利用链
├── expr_inject_audit/         ← 🧩 表达式注入 + 沙箱绕过
├── cross_analysis/            ← 📊 交叉分析（P0/P1 路由分级）
└── decompiled/                ← 🔧 CFR 反编译产物
```

> **拿到报告看哪里？** 打开 `quality_report.md`，顶部是漏洞总览面板。每个漏洞都有位置、PoC、修复建议。

## 单独使用某个 Skill

不用流水线也可以单独跑某个检测：

```bash
# 只提取路由
/java-route-mapper /path/to/project

# 只做 SQL 注入审计
/java-sql-audit /path/to/project

# 只扫描组件漏洞
/java-vuln-scanner /path/to/project

# 只分析鉴权
/java-auth-audit /path/to/project
```

所有 skill 独立可用，输出格式一致。

## 环境要求

| 依赖 | 用途 | 检查命令 |
|:-----|:-----|:---------|
| **Claude Code ≥ 2.1.32** | 运行平台 | `claude --version` |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | Agent 并发（必须） | `echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` |
| **Java** | CFR 反编译 .class/.jar | `java -version` |
| **Python 3** | 漏洞扫描脚本 | `python3 --version` |
| **pip 依赖** | PyYAML + requests | `pip3 install -r requirements.txt` |

### 平台支持

| 平台 | 状态 |
|:-----|:-----|
| macOS | ✅ 完整支持 |
| Linux | ✅ 完整支持 |
| Windows (WSL2) | ✅ 完整支持 |
| Windows (原生) | ⚠️ Python 脚本可用；shell 命令（grep/find）需 Git Bash |

## 常见问题

**Q: 对大型项目（1000+ 路由）效果如何？**
标准模式会自动分片——recon 侦查 → N 个 worker 并行提取路由 → 合并索引。单个 agent 硬上界 200 路由，大项目会自动拆成多个 agent。

**Q: 只有 .class / .jar 没有源码能跑吗？**
能。内置 CFR 反编译器，会自动反编译后分析。不过源码审计结果会更精确。

**Q: 流水线跑到一半断了怎么办？**
会自动生成 `PARTIAL_RESULTS.md`，列出已完成和未完成的阶段，已产出的结果不会丢。用 `--incremental` 可以跳过已完成的阶段续跑。

**Q: 会不会有误报？**
调用链追踪阶段会检查参数是否真正到达 Sink 点。如果参数被硬编码覆盖、被安全函数白名单过滤，会被排除。比单纯的 grep 匹配准确得多。

**Q: 跑一次要多少 token？**
快速模式约 50-100k token。标准模式下中型项目（300 路由）约 300-800k token，大型项目（1000+ 路由）可能上百万。

## 技能清单

| Skill | 干什么的 | 状态 |
|:------|:---------|:----:|
| `java-route-mapper` | 提取所有 HTTP 路由 + 参数结构 | 增强 |
| `java-route-tracer` | Controller→DAO 调用链追踪 | 增强 |
| `java-auth-audit` | 鉴权机制分析 + 绕过检测 | 增强 |
| `java-vuln-scanner` | 组件 CVE 扫描（OSV.dev） | 增强 |
| `java-sql-audit` | SQL 注入检测 | — |
| `java-xxe-audit` | XXE 外部实体注入检测 | — |
| `java-file-upload-audit` | 文件上传漏洞检测 | — |
| `java-file-read-audit` | 任意文件读取检测 | — |
| `java-deserialization-audit` | 反序列化 + gadget 链分析 | 🆕 |
| `java-ssrf-audit` | SSRF + 云元数据利用链 | 🆕 |
| `java-expression-inject-audit` | 表达式/模板注入 + 沙箱绕过 | 🆕 |
| `java-audit-pipeline` | 全链路自动化编排 | 🆕 重写 |

## 目录结构

```
Des-java-auto-skill/
├── README.md
├── requirements.txt
├── .gitignore
├── .claude/
│   └── settings.local.json          # 权限预设（减少弹窗）
└── skills/
    ├── java-shared/                  # 共享规范（评级标准/输出模板/反编译策略）
    ├── java-audit-pipeline/          # 流水线编排（7 阶段 + agent team）
    ├── java-route-mapper/            # 路由提取
    ├── java-route-tracer/            # 调用链追踪
    ├── java-sql-audit/               # SQL 注入
    ├── java-auth-audit/              # 鉴权审计
    ├── java-file-upload-audit/       # 文件上传
    ├── java-file-read-audit/         # 文件读取
    ├── java-xxe-audit/               # XXE
    ├── java-deserialization-audit/   # 🆕 反序列化
    ├── java-ssrf-audit/              # 🆕 SSRF
    ├── java-expression-inject-audit/ # 🆕 表达式注入
    └── java-vuln-scanner/            # 组件 CVE 扫描
```

## 致谢 & 许可

本项目基于 [java-audit-skills](https://github.com/RuoJi6/java-audit-skills) 二次开发，在此基础上新增 3 种漏洞类型（反序列化/SSRF/表达式注入）、OSV.dev 3000+ CVE 覆盖、利用链编排、增量审计、快速模式等能力。

仅供学习和授权安全研究使用。

## ⚠️ 免责声明

**本工具仅供学术交流与安全研究使用。** 严禁用于任何非法活动、未授权测试或盈利行为。使用者需自行确保所有测试目标已获得明确授权，并对自身行为及其后果承担全部责任。

## 📜 License

[MIT](LICENSE) — 基于 [java-audit-skills](https://github.com/RuoJi6/java-audit-skills) 深度二次开发。
