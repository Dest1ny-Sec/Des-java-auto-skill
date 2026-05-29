# 增量审计策略

当项目只有少量文件变更时，无需重新运行完整流水线。

## 触发方式

```bash
/java-audit-pipeline --incremental /path/to/project
/java-audit-pipeline --incremental --since HEAD~3 /path/to/project
/java-audit-pipeline --incremental --since <commit-hash> /path/to/project
```

## 增量检测逻辑

### 阶段 0: 变更检测

```bash
# 获取变更文件列表
git diff --name-only {since_commit} HEAD
git diff --name-only HEAD           # 未提交的变更

# 分类变更文件
├── *Controller*.java         → 需要重新提取该 Controller 的路由
├── *Service*.java / *Dao*.java → 需要重新追踪受影响的调用链
├── *Config*.java             → 需要获取配置变更的安全影响
├── pom.xml / build.gradle    → 需要获取依赖变更
├── *.xml (struts/mybatis)    → 需要获取路由/SQL 变更
└── *.jar                     → 需要组件扫描
```

### 阶段 1: 增量审计（替代全量流水线）

| 变更类型 | 执行操作 | Agent |
|:---------|:---------|:------|
| Controller 变更/新增 | 只提取该 Controller 的路由 | agent-1-N (单个 worker) |
| Service/Dao 变更 | 只追踪受影响路由的调用链 | agent-5-N (单个 worker) |
| pom.xml 依赖变更 | 只扫描变更的依赖 | agent-3 (增量模式) |
| 鉴权配置变更 | 只分析变更的鉴权配置 | agent-2 (增量模式) |
| 无 Java 文件变更 | 跳过审计 | — |

### 阶段 2: 受影响路由的交叉审计

```
1. 识别受影响的 Controller → 提取变更路由
2. 检查鉴权状态是否有变化
3. 追踪变更路由的调用链
4. 若调用链命中已知 sink → 启动对应的 agent-6x
```

## 增量审计输出

```
{output_path}/incremental_audit/
├── changed_files.md          # 变更文件清单
├── affected_routes.md         # 受影响的路由
├── quick_assessment.md        # 快速评估结论
└── full_report.md             # 增量审计完整报告（仅在有必要时生成）
```
