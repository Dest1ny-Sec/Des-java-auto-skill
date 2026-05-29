# Agent-4a-risk-classifier: 高危路由分级员 - 执行指令

## 角色信息

```
角色: agent-4a-risk-classifier (高危路由分级员)
等待: 阶段1 路由子流程（agent-1-recon → agent-1-N → agent-1-merge）、agent-2-auth-audit、agent-3-vuln-scanner 全部完成
输出目录: {output_path}/cross_analysis/（已创建，直接写入）
输出文件: {output_path}/cross_analysis/high_risk_routes.md
```

## 执行步骤

1. 读取 agent-2-auth-audit 鉴权映射表，提取 ❌无鉴权 的路由
2. 读取 agent-2-auth-audit 鉴权绕过漏洞，提取 🔓可绕过鉴权 的路由
3. 读取 agent-3-vuln-scanner 漏洞报告，提取可导致鉴权绕过的组件漏洞，将受影响路由标记为 🔓可绕过
4. 读取 agent-1-merge 输出的主索引（`{output_path}/route_mapper/README.md`），通过主索引中的模块链接定位各 agent-1-N 写入的模块子目录详情文件，获取完整参数结构
5. 将剩余的 ✅有鉴权 路由（不属于 P0/P1 的全部路由）归入 P2
6. 生成路由分级清单，按优先级排序：

| 优先级 | 条件 | 说明 |
|:-------|:-----|:-----|
| P0 | ❌无鉴权 | 路由完全无鉴权保护 |
| P1 | 🔓可绕过鉴权（代码层绕过 + 组件漏洞导致绕过） | 有鉴权但存在绕过方式 |
| P2 | ✅有鉴权 | 有正常鉴权的路由，作为兜底分级（仅当 P0+P1=0 时参与追踪） |

## 输出 `high_risk_routes.md` 模板

```markdown
# 高危路由筛选清单

## 筛选概览

| 指标 | 数量 |
|:-----|:-----|
| 总路由数 | {从 agent-1-merge 主索引获取} |
| 无鉴权路由数（P0） | {从 agent-2-auth-audit 获取} |
| 可绕过鉴权路由数（P1） | {agent-2 鉴权绕过 + agent-3 组件绕过} |
| 高危路由总数 | {P0 + P1} |
| 有鉴权路由数（P2） | {总路由数 - P0 - P1} |

## P0 - 无鉴权

| 路由 | 方法 | 鉴权状态 | 参数 | 来源文件 |
|:-----|:-----|:---------|:-----|:---------|
| /api/xxx | POST | ❌无鉴权 | param1, param2 | XxxController.java:行号 |
| /api/yyy | GET | ❌无鉴权 | id, name | YyyController.java:行号 |

## P1 - 可绕过鉴权

| 路由 | 方法 | 鉴权状态 | 绕过方式 | 参数 | 来源文件 |
|:-----|:-----|:---------|:---------|:-----|:---------|
| /admin/users | GET | 🔓可绕过 | Shiro 路径穿越 (H-AUTH-001) | page, size | AdminController.java:行号 |
| /api/config | POST | 🔓可绕过 | Tomcat AJP 绕过 (CVE-2020-1938) | key, value | ConfigController.java:行号 |

## P2 - 需鉴权（兜底分级）

> P2 路由仅在 P0+P1 均为 0 时才参与阶段3调用链追踪，由 agent-5 按需拉取。

| 路由 | 方法 | 鉴权状态 | 参数 | 来源文件 |
|:-----|:-----|:---------|:-----|:---------|
| /api/user/info | GET | ✅有鉴权 | userId | UserController.java:行号 |
| /api/order/create | POST | ✅有鉴权 | productId, quantity | OrderController.java:行号 |
| ... | ... | ... | ... | ...（列出全部有鉴权路由） |

## 待追踪路由列表

⚠️ **完整性强制要求**：此列表必须包含上方 P0 和 P1 分组表格中的**全部路由**，禁止做任何筛选、去重或缩减。待追踪路由总数必须 = P0 数量 + P1 数量 = 筛选概览中的「高危路由总数」。P2 路由不进入此列表（由 agent-5 在 P0+P1=0 时按需拉取）。

以下路由必须进入阶段3调用链追踪（按 P0→P1 优先级排列）：

| 序号 | 优先级 | 路由 | 方法 | 追踪理由 |
|:-----|:-------|:-----|:-----|:---------|
| 1 | P0 | /api/xxx | POST | 无鉴权 |
| 2 | P0 | /api/yyy | GET | 无鉴权 |
| 3 | P1 | /admin/users | GET | 鉴权可绕过 |
| 4 | P1 | /api/config | POST | 鉴权可绕过 |
| ... | ... | ... | ... | ...（必须列出全部 P0+P1 路由，不得省略） |

**自检**：输出前必须验证 待追踪路由列表行数 == P0 表格行数 + P1 表格行数 == 筛选概览中「高危路由总数」。若不等则说明遗漏，必须补全后再输出。
```

## 注意事项

- **agent-4a 的职责仅为分级，不做筛选**：所有 P0+P1 路由必须全量输出到「待追踪路由列表」，P2 路由全量输出到「P2 - 需鉴权」章节，数量裁剪决策由 agent-5 负责
- 追踪理由不包含具体 CVE 编号或绕过细节，避免干扰后续 agent 的代码审计重心
- P1 的绕过方式详情在分组表格中记录，但不传递到「待追踪路由列表」
