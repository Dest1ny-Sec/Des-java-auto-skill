# SQL 注入检测规则详解

本文档提供通用的 SQL 注入检测策略，基于行为识别而非固定命名模式，覆盖多种数据库类型。

---

## 核心原则

**不要问"这个方法叫什么名字"，而要问"这个方法做了什么事情"**

| 错误方式（依赖命名） | 正确方式（识别行为） |
|:---------------------|:---------------------|
| 搜索 `addOrderBy()` 方法 | 搜索包含 `order by` 字符串拼接的代码 |
| 搜索 `*Pagination*` 类 | 搜索包含分页逻辑的类 |
| 检查 `page.getOrderBy()` | 检查任何 String 字段是否拼接到 SQL |

---

## 1. 行为检测策略

### 1.1 SQL 关键字拼接检测

**搜索 SQL 关键字与变量拼接的行为：**

```bash
# ORDER BY 拼接检测
grep -ri "order by" --include="*.java" | grep -E "\+|\.append|format"

# GROUP BY 拼接检测
grep -ri "group by" --include="*.java" | grep -E "\+|\.append|format"

# WHERE 条件拼接检测
grep -ri "where.*=" --include="*.java" | grep -E "\+|\.append"

# LIKE 拼接检测
grep -ri "like\s" --include="*.java" | grep -E "\+|\.append"
```

### 1.2 危险行为特征

| 危险行为 | 代码特征 | 检测正则 |
|:---------|:---------|:---------|
| 字符串拼接 | `"order by " + xxx` | `".*order by.*"\s*\+` |
| StringBuilder | `.append("order by").append(xxx)` | `\.append\(.*order` |
| String.format | `format("...%s", xxx)` | `format\(.*order by` |
| MessageFormat | `MessageFormat.format()` | `MessageFormat\.format` |

### 1.3 数据流追踪

```
步骤1: 识别所有 String 类型的类字段/方法参数
步骤2: 追踪这些 String 是否被用于 SQL 拼接
步骤3: 检查拼接前是否有白名单校验
```

**危险模式：**
```java
sql + variable           // String 拼接
sql.append(variable)     // StringBuilder 拼接
String.format(sql, var)  // 格式化拼接
MessageFormat.format()   // 消息格式化
```

**安全模式：**
```java
pstmt.setString(1, var)              // 参数化查询
if (whitelist.contains(var)) { }     // 白名单校验
var.matches("[a-zA-Z_]+")            // 正则校验
```

---

## 2. 多数据库分页语法检测

不同数据库使用不同的分页语法，检测时需全部覆盖：

### 2.1 分页语法对比

| 数据库 | 分页语法 | 检测关键字 |
|:-------|:---------|:-----------|
| MySQL | `LIMIT offset, count` | `limit` |
| PostgreSQL | `LIMIT count OFFSET offset` | `limit`, `offset` |
| Oracle | `ROWNUM`, `ROW_NUMBER()` | `rownum`, `row_number` |
| SQL Server | `TOP`, `OFFSET FETCH` | `top`, `offset`, `fetch` |
| DB2 | `FETCH FIRST n ROWS` | `fetch first`, `rows only` |
| SQLite | `LIMIT count OFFSET offset` | `limit`, `offset` |

### 2.2 分页检测命令

```bash
# MySQL / PostgreSQL / SQLite
grep -ri "limit\s" --include="*.java" | grep -v "//\|/\*"
grep -ri "offset\s" --include="*.java" | grep -v "//\|/\*"

# Oracle
grep -ri "rownum\|row_number" --include="*.java"

# SQL Server
grep -ri "\stop\s\|offset.*fetch" --include="*.java"

# DB2
grep -ri "fetch first\|rows only" --include="*.java"
```

### 2.3 分页拼接风险点

| 参数 | 可注入性 | 说明 |
|:-----|:---------|:-----|
| limit/count | 低 | 通常是 int 类型 |
| offset/start | 低 | 通常是 int 类型 |
| orderBy/sortColumn | **高** | String 类型，可注入 |
| order/direction | **高** | String 类型，可注入 |

---

## 3. 排序注入检测（高频漏报）

ORDER BY 注入是最容易被遗漏的 SQL 注入类型。

### 3.1 各数据库 ORDER BY 语法

| 数据库 | ORDER BY 语法 | 特殊注入点 |
|:-------|:--------------|:-----------|
| 通用 | `ORDER BY column ASC/DESC` | column 名称 |
| Oracle | `ORDER BY column NULLS FIRST/LAST` | NULLS 处理 |
| MySQL | `ORDER BY column` | 可用数字索引 |
| PostgreSQL | `ORDER BY column USING operator` | USING 子句 |

### 3.2 检测命令

```bash
# 搜索 order by 拼接
grep -ri "order by" --include="*.java" | grep -E "\+|\.append|format"

# 搜索排序相关 getter（语义检测）
grep -ri "\.get.*order\|\.get.*sort\|\.get.*by" --include="*.java" -i

# 搜索排序方向
grep -ri "asc\|desc" --include="*.java" | grep -E "\+|\.append"
```

### 3.3 危险模式示例

```java
// 危险：直接拼接
sql.append(" ORDER BY ").append(orderBy);
sql.append(" ").append(order);

// 危险：字符串拼接
String sql = baseSql + " ORDER BY " + column + " " + direction;

// 危险：格式化
String.format("%s ORDER BY %s %s", sql, orderBy, order);
```

### 3.4 安全模式示例

```java
// 安全：白名单校验
Set<String> allowedColumns = Set.of("id", "name", "create_time");
Set<String> allowedOrders = Set.of("asc", "desc");

if (!allowedColumns.contains(orderBy.toLowerCase())) {
    throw new IllegalArgumentException("Invalid column");
}
if (!allowedOrders.contains(order.toLowerCase())) {
    throw new IllegalArgumentException("Invalid order");
}
```

---

## 4. 常见命名模式（仅作参考）

以下是常见命名，**但不能仅依赖这些模式检测**：

### 4.1 常见方法名

| 方法名模式 | 行为特征（真正的检测依据） |
|:-----------|:---------------------------|
| `addOrderBy`, `appendSort`, `buildOrder` | 包含 `order by` 字符串拼接 |
| `addGroupBy`, `appendGroup` | 包含 `group by` 字符串拼接 |
| `addLimit`, `buildPagination`, `addPage` | 包含分页 SQL 拼接 |
| `buildWhere`, `appendCondition` | 包含 WHERE 条件拼接 |

### 4.2 常见类名

| 类名模式 | 行为特征（真正的检测依据） |
|:---------|:---------------------------|
| `*Pagination*`, `*PageHelper*`, `*Pager*` | 包含分页 SQL 构建逻辑 |
| `*Support*`, `*Template*`, `*Helper*` | 包含通用 SQL 执行方法 |
| `Abstract*Dao*`, `Base*Dao*`, `*BaseMapper*` | 包含 SQL 执行的父类方法 |
| `*SqlBuilder*`, `*QueryBuilder*` | 动态构建 SQL |

### 4.3 常见字段名

| 字段名模式 | 类型 | 风险 |
|:-----------|:-----|:-----|
| `orderBy`, `sortBy`, `sortField`, `sortColumn` | String | **高** |
| `order`, `sortOrder`, `direction`, `sortType` | String | **高** |
| `groupBy`, `groupColumn`, `groupField` | String | **高** |
| `limit`, `pageSize`, `size`, `count` | int | 低 |
| `offset`, `start`, `firstResult`, `skip` | int | 低 |

---

## 5. 完整检测流程

```
1. 行为检测（必须执行）
   ├─ 搜索 "order by" + 变量拼接
   ├─ 搜索 "group by" + 变量拼接
   ├─ 搜索各数据库分页语法拼接
   ├─ 搜索 WHERE 条件动态拼接
   └─ 追踪所有 String 参数到 SQL 的数据流

2. 命名模式辅助（可选加速）
   ├─ 搜索常见方法名
   ├─ 搜索常见类名
   └─ 检查常见字段名
   （找到后仍需验证行为特征）

3. 白名单校验检查
   ├─ 检查拼接前是否有 contains() 校验
   ├─ 检查是否有允许值 Set/List
   ├─ 检查是否有正则校验
   └─ 检查是否有枚举限制

4. 执行条件判断
   ├─ 检查数据库类型分支（isOracle/isMySQL）
   ├─ 检查代码路径是否存在可控参数
   └─ 标注注入可达性（是/否）
```

---

## 6. 各数据库注入 Payload 参考

### 6.1 通用 Payload

| 注入类型 | Payload | 说明 |
|:---------|:--------|:-----|
| 错误注入 | `'` | 触发语法错误 |
| 布尔盲注 | `1' AND '1'='1` | 条件为真 |
| 注释截断 | `--`, `#`, `/* */` | 注释后续内容 |

### 6.2 Oracle 特有

| 注入类型 | Payload |
|:---------|:--------|
| 时间盲注 | `1' AND DBMS_PIPE.RECEIVE_MESSAGE('a',5)='a` |
| UNION | `UNION SELECT NULL,NULL FROM DUAL--` |
| 错误注入 | `1' AND 1=CTXSYS.DRITHSX.SN(1,'~')--` |

### 6.3 MySQL 特有

| 注入类型 | Payload |
|:---------|:--------|
| 时间盲注 | `1' AND SLEEP(5)--` |
| UNION | `UNION SELECT 1,2,3--` |
| 错误注入 | `1' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))--` |

### 6.4 PostgreSQL 特有

| 注入类型 | Payload |
|:---------|:--------|
| 时间盲注 | `1'; SELECT PG_SLEEP(5)--` |
| 堆叠查询 | `1'; DROP TABLE test--` |
| 错误注入 | `1' AND 1=CAST((SELECT version()) AS INT)--` |

### 6.5 SQL Server 特有

| 注入类型 | Payload |
|:---------|:--------|
| 时间盲注 | `1'; WAITFOR DELAY '0:0:5'--` |
| 堆叠查询 | `1'; EXEC xp_cmdshell('whoami')--` |
| 错误注入 | `1' AND 1=CONVERT(INT,@@VERSION)--` |

---

## 7. 检测优先级

| 优先级 | 检测目标 | 原因 |
|:-------|:---------|:-----|
| P0 | ORDER BY / GROUP BY 拼接 | 最常被遗漏，无法参数化 |
| P1 | 动态表名/列名拼接 | 无法参数化，必须白名单 |
| P2 | WHERE 条件拼接 | 常见漏洞点 |
| P3 | LIKE 模糊查询拼接 | 需要特殊处理通配符 |
| P4 | IN 子句动态拼接 | 需要正确使用 foreach |
