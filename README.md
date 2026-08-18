<div align="center">

<!-- Banner: Java 经典配色（深红→红→橙→金） + waving -->
<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:1a0000,30:8B0000,70:DC143C,100:FF8C00&height=240&section=header&text=Des-java-auto-skill&fontSize=64&fontColor=ffffff&fontAlignY=40&desc=Java%20Web%20%E5%85%A8%E9%93%BE%E8%B7%AF%E8%87%AA%E5%8A%A8%E5%8C%96%E5%AE%A1%E8%AE%A1&descSize=18&descColor=FFD700&animation=twinkling" />

<br/>

<!-- 暗红底：打字机 + 关键指标 -->
<div style="background: #1a0000; padding: 32px 40px; border-radius: 0 0 16px 16px; margin: -8px 0 24px 0; text-align: center;">
  <img src="https://readme-typing-svg.herokuapp.com/?font=Fira+Code&size=24&weight=600&duration=2800&pause=1800&color=FF8C00&center=true&vCenter=true&repeat=true&width=900&height=60&lines=8%20%E7%A7%8D%E6%BC%8F%E6%B4%9E%E7%B1%BB%E5%9E%8B;7%20%E9%98%B6%E6%AE%B5%E6%B5%81%E6%B0%B4%E7%BA%BF;OSV%203000%2B%20CVE%20%E5%AE%9E%E6%97%B6%E6%9F%A5;%E5%8E%BB%E5%96%9D%E6%9D%AF%E5%92%96%E5%95%A1%2C%E5%9B%9E%E6%9D%A5%E7%9C%8B%E6%8A%A5%E5%91%8A" alt="" />
  <p style="color: #FFB3D9; font-size: 14px; letter-spacing: 3px; font-family: 'Fira Code', monospace; margin: 12px 0 0; font-weight: 300;">
    <strong style="color: #fff;">8</strong> 漏洞 &nbsp;·&nbsp; <strong style="color: #fff;">7</strong> 阶段 &nbsp;·&nbsp; <strong style="color: #fff;">12</strong> sink &nbsp;·&nbsp; <strong style="color: #fff;">10+</strong> 表达式引擎
  </p>
</div>

</div>

## 🛠️ stacks

<div align="center">
  <img src="https://skillicons.dev/icons?i=java,python,claude,regex,git,linux,docker,vscode" alt="stacks" />
</div>

<br/>

<sub>基于 Claude Code · JavaParser AST 解析 · OSV.dev CVE API</sub>

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
