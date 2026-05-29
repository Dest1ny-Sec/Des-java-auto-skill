# JDBC SQL 注入审计详解

## 目录

- [JDBC 基础概念](#jdbc-基础概念)
- [危险模式检测](#危险模式检测)
- [安全模式识别](#安全模式识别)
- [代码检查要点](#代码检查要点)
- [常见漏洞场景](#常见漏洞场景)

---

## JDBC 基础概念

### 核心类

| 类 | 作用 | 参数化支持 |
|---|------|-----------|
| `Statement` | 执行静态 SQL | 不支持（高危注入点） |
| `PreparedStatement` | 执行预编译 SQL | 支持（安全） |
| `CallableStatement` | 执行存储过程 | 部分支持（取决于使用方式） |

### 识别特征

```java
// JDBC 导入
import java.sql.Connection;
import java.sql.Statement;
import java.sql.PreparedStatement;
import java.sql.DriverManager;
import java.sql.ResultSet;
```

---

## 危险模式检测

### 1. 字符串拼接（+ 号）

```java
// ❌ 高危：直接拼接用户输入
String id = request.getParameter("id");
String sql = "SELECT * FROM users WHERE id = " + id;
Statement stmt = conn.createStatement();
ResultSet rs = stmt.executeQuery(sql);

// ❌ 高危：拼接字符串参数
String name = request.getParameter("name");
String sql = "SELECT * FROM users WHERE name = '" + name + "'";
```

**检测正则：**
```regex
(executeQuery|executeUpdate|execute)\s*\(\s*[^)]*\+
```

### 2. StringBuilder/StringBuffer 拼接

```java
// ❌ 高危：使用 StringBuilder 构建 SQL
StringBuilder sb = new StringBuilder();
sb.append("SELECT * FROM users WHERE name = '");
sb.append(name);
sb.append("'");
stmt.executeQuery(sb.toString());

// ❌ 高危：使用 StringBuffer
StringBuffer sql = new StringBuffer("DELETE FROM users WHERE id = ");
sql.append(userId);
stmt.executeUpdate(sql.toString());
```

**检测正则：**
```regex
(StringBuilder|StringBuffer).*append.*execute
```

### 3. String.format 拼接

```java
// ❌ 高危：使用 String.format
String sql = String.format("SELECT * FROM users WHERE id = %s", id);
stmt.executeQuery(sql);

// ❌ 高危：使用 MessageFormat
String sql = MessageFormat.format("SELECT * FROM users WHERE id = {0}", id);
```

### 4. concat 方法拼接

```java
// ❌ 高危：使用 concat
String sql = "SELECT * FROM users WHERE id = ".concat(id);
```

---

## 安全模式识别

### 1. PreparedStatement + 占位符

```java
// ✅ 安全：使用 ? 占位符
String sql = "SELECT * FROM users WHERE id = ?";
PreparedStatement pstmt = conn.prepareStatement(sql);
pstmt.setInt(1, userId);  // 参数绑定
ResultSet rs = pstmt.executeQuery();

// ✅ 安全：多参数绑定
String sql = "SELECT * FROM users WHERE name = ? AND age = ?";
PreparedStatement pstmt = conn.prepareStatement(sql);
pstmt.setString(1, name);
pstmt.setInt(2, age);
```

### 2. 参数类型方法

| 方法 | 数据类型 |
|------|----------|
| `setInt(index, value)` | 整数 |
| `setString(index, value)` | 字符串 |
| `setLong(index, value)` | 长整数 |
| `setDouble(index, value)` | 浮点数 |
| `setDate(index, value)` | 日期 |
| `setTimestamp(index, value)` | 时间戳 |
| `setObject(index, value)` | 对象 |

---

## 代码检查要点

### 检查流程

```
1. 搜索所有 Statement/PreparedStatement 使用
     ↓
2. 检查 SQL 字符串构建方式
     ↓
3. 追踪参数来源（是否用户可控）
     ↓
4. 判断是否使用参数化
     ↓
5. 标记风险等级
```

### 搜索关键字

```bash
# 查找 SQL 执行点
grep -rn "executeQuery\|executeUpdate\|execute(" --include="*.java"

# 查找 Statement 创建
grep -rn "createStatement\|prepareStatement" --include="*.java"

# 查找字符串拼接
grep -rn "\"SELECT\|\"INSERT\|\"UPDATE\|\"DELETE" --include="*.java" | grep "+"
```

### 漏洞判断矩阵

| Statement 类型 | SQL 构建方式 | 参数来源 | 注入判定结果 |
|---------------|-------------|----------|------------|
| Statement | 字符串拼接 | 用户输入 | **高危注入点** |
| Statement | 字符串拼接 | 硬编码 | 无注入风险 |
| PreparedStatement | 占位符 | 用户输入 | 安全 |
| PreparedStatement | 拼接 + 占位符混用 | 用户输入 | **高危注入点** |

---

## 常见漏洞场景

### 场景 1：动态表名/列名

```java
// ❌ 高危：动态表名无法使用占位符
String table = request.getParameter("table");
String sql = "SELECT * FROM " + table;  // 无法参数化

// ⚠️ 必须白名单校验
String table = request.getParameter("table");
if (!ALLOWED_TABLES.contains(table)) {
    throw new IllegalArgumentException("Invalid table");
}
String sql = "SELECT * FROM " + table;
```

### 场景 2：ORDER BY 子句

```java
// ❌ 高危：ORDER BY 无法使用占位符
String orderBy = request.getParameter("sort");
String sql = "SELECT * FROM users ORDER BY " + orderBy;

// ⚠️ 必须白名单校验
String orderBy = request.getParameter("sort");
if (!ALLOWED_COLUMNS.contains(orderBy)) {
    orderBy = "id";  // 默认值
}
String sql = "SELECT * FROM users ORDER BY " + orderBy;
```

### 场景 3：IN 子句

```java
// ❌ 高危：IN 子句拼接
String ids = request.getParameter("ids");  // "1,2,3"
String sql = "SELECT * FROM users WHERE id IN (" + ids + ")";

// ✅ 安全：动态生成占位符
String[] idArray = ids.split(",");
String placeholders = String.join(",", Collections.nCopies(idArray.length, "?"));
String sql = "SELECT * FROM users WHERE id IN (" + placeholders + ")";
PreparedStatement pstmt = conn.prepareStatement(sql);
for (int i = 0; i < idArray.length; i++) {
    pstmt.setInt(i + 1, Integer.parseInt(idArray[i]));
}
```

### 场景 4：LIKE 子句

```java
// ❌ 高危：LIKE 拼接
String keyword = request.getParameter("keyword");
String sql = "SELECT * FROM users WHERE name LIKE '%" + keyword + "%'";

// ✅ 安全：LIKE 使用占位符
String sql = "SELECT * FROM users WHERE name LIKE ?";
PreparedStatement pstmt = conn.prepareStatement(sql);
pstmt.setString(1, "%" + keyword + "%");  // 通配符在参数中
```

### 场景 5：批量操作

```java
// ❌ 高危：批量 SQL 拼接
for (String id : ids) {
    String sql = "DELETE FROM users WHERE id = " + id;
    stmt.addBatch(sql);
}
stmt.executeBatch();

// ✅ 安全：批量使用 PreparedStatement
String sql = "DELETE FROM users WHERE id = ?";
PreparedStatement pstmt = conn.prepareStatement(sql);
for (String id : ids) {
    pstmt.setString(1, id);
    pstmt.addBatch();
}
pstmt.executeBatch();
```

---

## 修复要求

### 必须遵守的规范

1. **始终使用 PreparedStatement**，避免 Statement
2. **使用 ? 占位符**，避免字符串拼接
3. **动态标识符使用白名单**（表名、列名、ORDER BY）
4. **输入验证作为补充**，不能替代参数化

### 代码示例

```java
// 修复前（危险）
public User findById(String id) {
    String sql = "SELECT * FROM users WHERE id = " + id;
    Statement stmt = conn.createStatement();
    ResultSet rs = stmt.executeQuery(sql);
    // ...
}

// 修复后（安全）
public User findById(String id) {
    String sql = "SELECT * FROM users WHERE id = ?";
    PreparedStatement pstmt = conn.prepareStatement(sql);
    pstmt.setString(1, id);
    ResultSet rs = pstmt.executeQuery();
    // ...
}
```
