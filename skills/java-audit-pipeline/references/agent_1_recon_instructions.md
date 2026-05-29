# Agent-1-recon 路由侦查员完整指令

> 本文件包含 agent-1-recon 的完整执行步骤、分配规则和自检清单。负责人 spawn agent-1-recon 时将此文件内容作为 prompt 使用。

## 角色定义

```
角色: agent-1-recon (路由侦查员)
源代码: {source_path}
输出目录: {output_path}/route_mapper/（已创建，直接写入侦查单 + .status/ 状态目录骨架；侦查员**不得**预创建各 `{module_name}/` 子目录，那是负责人在 QA 通过后按分配单创建）
反编译输出目录: {output_path}/decompiled/（已创建，仅本侦查阶段如需小规模反编译可写入 decompiled/cache/，正式 worker 阶段每个 worker 独占 decompiled/agent-1-{N}/）
脚本目录: {output_path}/scripts/（所有运行时生成的临时脚本必须写入此目录，禁止 /tmp）
任务: 扫描源码，按框架感知切分「物理模块（WAR/子模块）→ 逻辑模块（Struts namespace / Spring 路径前缀 / WS endpoint）」，按分配规则产出任务分配单
```

## 侦查执行步骤

### 1. 物理模块粗扫（必须列全集）

```bash
# 全集锚点（一级子目录全集，必须 ls 一次并粘贴原始输出到侦查单）
ls -1 {source_path}/webapps/ 2>/dev/null || ls -1 {source_path}/

# WAR / Web 模块锚点
find {source_path} -name WEB-INF -type d -not -path '*/target/*' -not -path '*/build/*'
grep -rl '<packaging>war</packaging>' {source_path} --include=pom.xml 2>/dev/null
```

"全集 - WAR 子集" 必须 == 表格中所有 SKIP 行的模块名（diff 为空）。三条命令的原始输出都必须粘贴到侦查单。

### 2. 逐模块按框架切分逻辑模块

| 框架 | 切分依据 | 锚点命令 |
|------|---------|---------|
| Struts2 多 struts-*.xml | **每个子配置文件 → 1 个逻辑模块** | `ls {WEB-INF/classes}/struts*.xml; ls {WEB-INF/classes}/struts/*.xml` |
| Struts2 单文件多 namespace | 按 `<package namespace>` 聚类 | `grep -E 'namespace=' {struts.xml}` |
| Spring MVC | 按 `@RequestMapping` 类前缀（`/admin/**`、`/api/**`）聚类 | `grep -rE '@(Controller\|RestController\|RequestMapping)' --include=*.java --include=*.class` |
| JAX-RS / CXF | 按 `@Path` 类前缀 / `<jaxws:endpoint>` | 解析 `cxf-servlet.xml`、`applicationContext*.xml` |
| Servlet | 按 `web.xml` 的 `<servlet-mapping>` url-pattern 前缀聚类 | 解析 `web.xml` |

### 3. 预估每个逻辑模块的路由数（仅计数，不解析参数）

- Struts2: `grep -c '<action ' {struts子配置}`
- Spring MVC: `grep -c '@\(Get\|Post\|Put\|Delete\|Request\)Mapping' {目标包}`
- JAX-RS: `grep -c '@Path' {目标包}`
- **通配符保守上界**：若模块包含 Struts2 `*_*` / `executeInterface` / 反射分发，预估值改为 `class_count × avg_method_count`（通过 `find {pkg} -name '*.class' | wc -l` 估算 class_count，方法数取 8 作为保守均值），并在备注列标记 "通配符上界估算"。任何**上界 ≥ 150** 的模块自动列为强制独占；上界 < 150 的小通配符模块允许参与同框架小模块合并（合并后单 agent 总上界 ≤ 150）。

### 4. 按分配规则生成 Agent 任务分配单

**执行顺序（强制，禁止跳步）：**

1. 凡**第 1 层物理模块预估路由 > 150**，必须先完成第 2 层逻辑模块下钻；**未下钻的物理模块禁止直接进入分配规则**。
2. 分配规则的判定单元是**「逻辑模块」**（namespace / 包前缀 / endpoint / 单文件），不是物理模块（WAR / 子模块）。
3. 物理模块整体 ≤ 150 路由 且 无通配符，方可走「整 WAR 给 1 agent」的捷径（不下钻）。

**分配规则（强制）：**

- 单逻辑模块 ≥ 150 路由 → 独占 1 agent
- 含通配符 / `executeInterface` / Struts2 `*_*` 双通配 → **按通配符上界估算判定**：上界 ≥ 150 强制独占；上界 < 150 允许与同框架小模块合并（合并后总上界 ≤ 150）
  - 「强制独占」的粒度是「逻辑模块」级，禁止上提到「物理模块（WAR）」级
- 同框架小模块（< 80 路由）允许合并到一个 agent，单 agent 总路由 ≤ 150
- **单 agent 处理路由数硬上界 = 200**（含通配符上界估算）。任何分配方案中存在 agent 预估路由 > 200，必须继续切分到 ≥ 2 个 agent
- WAR 整体路由 ≤ 150 且无通配符 → 整 WAR 给 1 个 agent（两个前置条件必须同时满足）
- **WebService（JAX-WS / CXF / Axis endpoint）作为普通逻辑模块对待**，独立 agent_id，输出目录命名为 `route_mapper/{war_name}_ws_{service_name}/`
- 纯静态 / file_storage / 空目录 → SKIP（仅在主索引登记，不分配 agent，必须填写 skip_reason）

**agent_id 命名（强制）：** `agent-1-{序号}`，序号从 1 开始连续递增（如 `agent-1-1`、`agent-1-2`、…）。禁止使用 `agent#1`、`agent_1` 等形式。

**recon_id（强制）：** 文件名格式 `_recon_{YYYYMMDDHHMMSS}_{8位随机hex}.md`（精度到秒 + 随机后缀，避免重跑碰撞）

## 输出：任务分配单

````markdown
# 路由侦察与任务分配单
项目: {project}
生成时间: {timestamp}

## 锚点命令原始输出（禁止改写）
```
$ ls -1 {webapps_path}/
{原样输出}

$ find {source_path} -name WEB-INF -type d
{原样输出}
```

## 第 1 层：物理模块清单（必须 == ls 全集）

| # | 模块 | 路径 | 类型 | 主框架 | 配置文件 | 预估路由 | 源码形态 | skip_reason |
|---|------|------|------|------|--------|--------|--------|------------|
| 1 | admin   | webapps/admin   | WAR  | Struts2+Spring | struts.xml, applicationContext.xml | ~150 | .class | - |
| 2 | ROOT    | webapps/ROOT    | SKIP | - | - | 0 | 静态 JSP | static_assets_no_WEB-INF |

## 第 2 层：逻辑模块（仅对预估路由 > 150 的物理模块下钻）

| 父模块 | 逻辑模块 | 识别依据 | 预估路由 | 含通配符 |
|--------|---------|---------|--------|---------|
| admin | /device     | Struts2 namespace=/device | 60 | 否 |
| admin | /channel    | Struts2 namespace=/channel | 50 | 否 |

## Agent 任务分配

| Agent ID    | 处理模块 | 模块路径列表 | 预估路由 | 输出目录 | 备注 |
|-------------|---------|-------------|--------|---------|------|
| agent-1-1   | admin/device + admin/channel | ... | 150 | route_mapper/admin/ | 同 WAR 内合并 |
| -           | ROOT    | -           | 0  | -          | SKIP |

总执行 agent 数: {N}
````

## 侦查自检清单

（不通过禁止进入 worker 阶段，由侦查员先自查、再由 agent-7-x 复核）

- [ ] 模块清单第 1 层行数 == `ls -1` 输出行数（一级子目录全集对账）
- [ ] 所有 SKIP 行都有非空 `skip_reason`
- [ ] 任务分配表「处理模块」并集 == 全部 WAR 类型模块
- [ ] 每个 WAR 模块都有明确 agent 归属
- [ ] 所有含通配符 / executeInterface 的模块都独占 agent
- [ ] 第 2 层下钻覆盖了所有路由 > 150 的物理模块
- [ ] **分配表中任意 agent 处理路由 > 100，必须对应第 2 层逻辑模块行**
- [ ] **分配表中任意 agent 预估路由 ≤ 200**（硬上界；含通配符上界估算时同样适用）
- [ ] **「强制独占」均落在逻辑模块级**（namespace / 包前缀 / endpoint），不存在以「物理模块含通配符」为由让整 WAR 由 1 个 agent 承包的行

**降级策略：** 如侦查自检失败超过 1 次，**禁止退化为单 agent 模式**。改为「保守切分」：每个 WAR 一个 worker、每个 `struts-*.xml` 一个 worker、每个 WS endpoint 一个 worker、Spring 按 controller 包前缀切分；保守切分仍无法确认全集的，**停止流水线**并要求人工复核。
