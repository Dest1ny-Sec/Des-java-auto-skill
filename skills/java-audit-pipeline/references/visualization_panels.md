# 可视化进度面板格式参考

> 本文档包含流水线中所有可视化面板的 ANSI 格式模板。负责人按需加载此文档生成面板，不常驻上下文。

## 颜色代码常量

```
GREEN  = \x1b[32m  已完成/通过
YELLOW = \x1b[33m  运行中/警告
RED    = \x1b[31m  失败/阻塞
CYAN   = \x1b[36m  信息/阶段标题
BLUE   = \x1b[34m  进度条/链接
RESET  = \x1b[0m   重置颜色
BOLD   = \x1b[1m   加粗标题
DIM    = \x1b[2m   灰色次要信息
```

---

## 1. 阶段启动面板

```
\x1b[1m\x1b[36m╔══════════════════════════════════════════════════════╗
║  Stage N: 阶段名称                                    ║
╚══════════════════════════════════════════════════════╝\x1b[0m
\x1b[2m  Worker 池: {used}/{max}  |  QA 池: {qa_used}/{qa_max}  |  队列: {queued}\x1b[0m

  启动 agent:
  \x1b[33m⟳\x1b[0m agent-X-name   → 模块/范围描述
  \x1b[33m⟳\x1b[0m agent-Y-name   → 模块/范围描述
  ...
```

## 2. Worker 池状态面板

```
\x1b[1m  Worker Pool (Stage N)\x1b[0m
  ┌──────────────┬──────────┬──────────┬──────────────────────────┐
  │ Agent        │ 状态     │ 进度     │ 当前任务                 │
  ├──────────────┼──────────┼──────────┼──────────────────────────┤
  │ agent-6f     │ \x1b[32m已完成\x1b[0m  │ \x1b[34m████████\x1b[0m │ SSRF sink 分析完成       │
  │ agent-6g     │ \x1b[33m运行中\x1b[0m  │ \x1b[34m████░░░░\x1b[0m │ 扫描 FTL 模板文件        │
  │ agent-6c     │ \x1b[33m运行中\x1b[0m  │ \x1b[34m██░░░░░░\x1b[0m │ 分析 UploadController    │
  │ agent-6d     │ \x1b[37m等待中\x1b[0m  │ \x1b[2m────────\x1b[0m │ —                        │
  └──────────────┴──────────┴──────────┴──────────────────────────┘
```

## 3. Agent 完成通知

```
\x1b[32m✓\x1b[0m agent-X-name 完成 → {关键发现一句话}
```

## 4. 阶段完成面板

```
\x1b[1m\x1b[32m═══ Stage N 完成 ═══\x1b[0m
  agent-X: \x1b[32m✓\x1b[0m {C}个Critical {H}个High {M}个Medium
  agent-Y: \x1b[32m✓\x1b[0m {C}个Critical {H}个High {M}个Medium
  QA:     \x1b[32m{passed}/{total} 通过\x1b[0m
  → 进入 Stage N+1...
```

## 5. TaskCreate 规则

- 每个 worker agent → 1 个 `pending` 任务
- spawn agent 时立即 TaskUpdate 标记为 `in_progress`，activeForm 设为简要描述
- agent 完成后标记 `completed`
- worker 池满时排队 agent 保持 `pending`

## 6. Agent 子任务要求

传递给每个 agent 的 prompt 中必须包含：

```
⚠️ 进度可视化要求（使用 TaskCreate/TaskUpdate）：
- 启动后立即使用 TaskCreate 创建 3-8 个子任务
- 每个子任务必须设置 activeForm 为当前正在做的事（如"正在扫描 UploadController.java 的上传校验逻辑"）
- 开始子任务时用 TaskUpdate 标记 in_progress（CLI 自动显示 spinner）
- 完成子任务时标记 completed
- 子任务的 activeForm 使用进行时态中文描述
```

## 7. 全流水线完成面板

```
\x1b[1m\x1b[36m╔══════════════════════════════════════════════════════════╗
║  \x1b[1m\x1b[37mDes-Java-Auto-Skill 全链路审计流水线 — 完成\x1b[0m\x1b[1m\x1b[36m            ║
╚══════════════════════════════════════════════════════════╝\x1b[0m

\x1b[1m  漏洞总览\x1b[0m
  \x1b[31mCritical: {N}\x1b[0m  \x1b[33mHigh: {N}\x1b[0m  \x1b[34mMedium: {N}\x1b[0m  \x1b[2mLow: {N}\x1b[0m

\x1b[1m  阶段完成情况\x1b[0m
  \x1b[32m✓\x1b[0m Stage 0 快速匹配    — {N} 条 grep 规则命中
  \x1b[32m✓\x1b[0m Stage 1 信息收集    — {N} 路由 / {N} CVE / {N} 鉴权发现
  \x1b[32m✓\x1b[0m Stage 2 交叉分析    — {N} P0 / {N} P1 风险路由
  \x1b[32m✓\x1b[0m Stage 3 调用链追踪  — {N}/{N} 路由已追踪
  \x1b[32m✓\x1b[0m Stage 4 深度检测    — {N} 个模块审计完成
  \x1b[32m✓\x1b[0m Stage 5 利用链编排  — {N} 条可达利用链
  \x1b[32m✓\x1b[0m Stage 6 汇总报告    — quality_report.md + observer 复盘

  \x1b[1m\x1b[32m✓ 流水线全部完成\x1b[0m
```

## 8. 禁止行为

- **禁止** spawn agent 后不做任何 TaskUpdate 直接等待结果
- **禁止** 在多个 agent 同时完成时逐条转发原始报告内容（刷屏）
- **禁止** 跳过阶段启动/完成面板
- **禁止** Worker Pool 状态变化时不更新面板
