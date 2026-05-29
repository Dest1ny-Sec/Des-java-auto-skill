# MyBatis SQL 注入审计详解

## 目录

- [MyBatis 基础概念](#mybatis-基础概念)
- [#{} vs ${} 核心区别](#-vs--核心区别)
- [危险模式检测](#危险模式检测)
- [安全模式识别](#安全模式识别)
- [常见漏洞场景](#常见漏洞场景)
- [XML Mapper 检查](#xml-mapper-检查)
- [注解方式检查](#注解方式检查)

---

## MyBatis 基础概念

### 识别特征

**依赖识别：**
```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.mybatis</groupId>
    <artifactId>mybatis</artifactId>
</dependency>

<!-- 或 MyBatis-Spring -->
<dependency>
    <groupId>org.mybatis.spring.boot</groupId>
    <artifactId>mybatis-spring-boot-starter</artifactId>
</dependency>
```

**代码特征：**
```java
// Mapper 接口
@Mapper
public interface UserMapper { ... }

// 注解式 SQL
@Select("SELECT * FROM users WHERE id = #{id}")

// SqlSession 使用
SqlSession session = sqlSessionFactory.openSession();
```

**配置文件：**
- `mybatis-config.xml` - 全局配置
- `*Mapper.xml` - SQL 映射文件
- `application.yml` - Spring Boot 配置

---

## #{} vs ${} 核心区别

### #{} - 预编译参数（安全）

```java
// #{} 会被转换为 ? 占位符
@Select("SELECT * FROM users WHERE id = #{id}")
User findById(int id);

// 实际执行的 SQL
// SELECT * FROM users WHERE id = ?
// 参数 id 通过 PreparedStatement.setXxx() 绑定
```

**特点：**
- 自动转义特殊字符
- 防止 SQL 注入
- 类型安全

### ${} - 字符串替换（危险）

```java
// ${} 直接替换为参数值
@Select("SELECT * FROM users WHERE id = ${id}")
User findById(String id);

// 如果 id = "1 OR 1=1"
// 实际执行的 SQL: SELECT * FROM users WHERE id = 1 OR 1=1
```

**特点：**
- 直接字符串拼接
- 存在 SQL 注入风险
- 用于动态表名/列名

---

## 危险模式检测

### 检测规则

```bash
# 搜索所有 ${} 使用
grep -rn '\${' --include="*.xml" --include="*.java"

# 搜索注解中的 ${}
grep -rn '@Select.*\${' --include="*.java"
grep -rn '@Update.*\${' --include="*.java"
grep -rn '@Insert.*\${' --include="*.java"
grep -rn '@Delete.*\${' --include="*.java"
```

### 危险模式清单

| 模式 | 示例 | 注入危害等级 |
|------|------|------------|
| 直接使用 ${} | `WHERE id = ${id}` | **高危** |
| LIKE 拼接 | `LIKE '%${keyword}%'` | **高危** |
| ORDER BY | `ORDER BY ${column}` | **高危** |
| IN 子句 | `IN (${ids})` | **高危** |
| 表名动态 | `FROM ${tableName}` | **高危** |
| 列名动态 | `SELECT ${columns}` | **高危** |

---

## 安全模式识别

### 1. 使用 #{}

```xml
<!-- ✅ 安全：使用 #{} -->
<select id="findById" resultType="User">
    SELECT * FROM users WHERE id = #{id}
</select>

<!-- ✅ 安全：多参数 -->
<select id="findByNameAndAge" resultType="User">
    SELECT * FROM users WHERE name = #{name} AND age = #{age}
</select>
```

### 2. LIKE 安全写法

```xml
<!-- ✅ 安全：CONCAT 函数 -->
<select id="search" resultType="User">
    SELECT * FROM users WHERE name LIKE CONCAT('%', #{keyword}, '%')
</select>

<!-- ✅ 安全：bind 标签 -->
<select id="search" resultType="User">
    <bind name="pattern" value="'%' + keyword + '%'" />
    SELECT * FROM users WHERE name LIKE #{pattern}
</select>
```

### 3. IN 子句安全写法

```xml
<!-- ✅ 安全：foreach 标签 -->
<select id="findByIds" resultType="User">
    SELECT * FROM users WHERE id IN
    <foreach collection="ids" item="id" open="(" separator="," close=")">
        #{id}
    </foreach>
</select>
```

### 4. 动态 SQL 安全写法

```xml
<!-- ✅ 安全：使用 if/choose 标签 -->
<select id="findUsers" resultType="User">
    SELECT * FROM users
    <where>
        <if test="name != null">
            AND name = #{name}
        </if>
        <if test="age != null">
            AND age = #{age}
        </if>
    </where>
</select>
```

---

## 常见漏洞场景

### 场景 1：ORDER BY 注入

```xml
<!-- ❌ 高危：ORDER BY 使用 ${} -->
<select id="findAll" resultType="User">
    SELECT * FROM users ORDER BY ${orderColumn} ${orderDir}
</select>

<!-- ⚠️ 必须白名单校验 -->
<!-- 在 Java 代码中校验 orderColumn -->
public List<User> findAll(String orderColumn) {
    if (!ALLOWED_COLUMNS.contains(orderColumn)) {
        orderColumn = "id";  // 默认值
    }
    return userMapper.findAll(orderColumn);
}
```

### 场景 2：LIKE 注入

```xml
<!-- ❌ 高危：LIKE 使用 ${} -->
<select id="search" resultType="User">
    SELECT * FROM users WHERE name LIKE '%${keyword}%'
</select>

<!-- ✅ 修复：使用 CONCAT + #{} -->
<select id="search" resultType="User">
    SELECT * FROM users WHERE name LIKE CONCAT('%', #{keyword}, '%')
</select>
```

### 场景 3：IN 子句注入

```xml
<!-- ❌ 高危：IN 使用 ${} -->
<select id="findByIds" resultType="User">
    SELECT * FROM users WHERE id IN (${ids})
</select>

<!-- ✅ 修复：使用 foreach -->
<select id="findByIds" resultType="User">
    SELECT * FROM users WHERE id IN
    <foreach collection="ids" item="id" open="(" separator="," close=")">
        #{id}
    </foreach>
</select>
```

### 场景 4：动态表名

```xml
<!-- ❌ 高危：动态表名 -->
<select id="findFromTable" resultType="Map">
    SELECT * FROM ${tableName} WHERE id = #{id}
</select>

<!-- ⚠️ 必须白名单校验 -->
public List<Map> findFromTable(String tableName, int id) {
    if (!ALLOWED_TABLES.contains(tableName)) {
        throw new IllegalArgumentException("Invalid table name");
    }
    return mapper.findFromTable(tableName, id);
}
```

### 场景 5：批量更新

```xml
<!-- ❌ 高危：批量更新使用 ${} -->
<update id="batchUpdate">
    UPDATE users SET status = #{status} WHERE id IN (${ids})
</update>

<!-- ✅ 修复：使用 foreach -->
<update id="batchUpdate">
    UPDATE users SET status = #{status} WHERE id IN
    <foreach collection="ids" item="id" open="(" separator="," close=")">
        #{id}
    </foreach>
</update>
```

---

## XML Mapper 检查

### 检查步骤

1. **定位所有 Mapper XML 文件**
   ```bash
   find . -name "*Mapper.xml" -o -name "*Dao.xml"
   ```

2. **搜索 ${} 使用**
   ```bash
   grep -n '\${' *Mapper.xml
   ```

3. **分析每个 ${} 的上下文**
   - 是否用于 ORDER BY/LIKE/IN
   - 参数是否来自用户输入
   - 是否有白名单校验

### XML 标签速查

| 标签 | 作用 | 注入风险 |
|------|------|----------|
| `<select>` | 查询 | 取决于参数使用 |
| `<insert>` | 插入 | 取决于参数使用 |
| `<update>` | 更新 | 取决于参数使用 |
| `<delete>` | 删除 | 取决于参数使用 |
| `<if>` | 条件判断 | 低 |
| `<choose>` | 多条件选择 | 低 |
| `<foreach>` | 循环 | 安全（使用 #{}） |
| `<where>` | WHERE 子句 | 低 |
| `<set>` | SET 子句 | 低 |
| `<bind>` | 变量绑定 | 取决于使用 |

---

## 注解方式检查

### 常用注解

```java
@Select("SELECT * FROM users WHERE id = #{id}")
@Insert("INSERT INTO users (name, age) VALUES (#{name}, #{age})")
@Update("UPDATE users SET name = #{name} WHERE id = #{id}")
@Delete("DELETE FROM users WHERE id = #{id}")
```

### 检查步骤

1. **搜索所有 SQL 注解**
   ```bash
   grep -rn '@Select\|@Insert\|@Update\|@Delete' --include="*.java"
   ```

2. **检查 ${} 使用**
   ```bash
   grep -rn '@.*\${' --include="*.java"
   ```

3. **动态 SQL Provider**
   ```java
   // 注意 @SelectProvider 等
   @SelectProvider(type = UserSqlProvider.class, method = "findByCondition")
   List<User> findByCondition(Map<String, Object> params);

   // 需要检查 Provider 类中的 SQL 构建逻辑
   public class UserSqlProvider {
       public String findByCondition(Map<String, Object> params) {
           // 检查这里是否有拼接
       }
   }
   ```

---

## 修复要求

### 必须遵守的规范

1. **始终使用 #{}**，除非确实需要动态标识符
2. **动态标识符使用白名单**校验
3. **LIKE 使用 CONCAT + #{}**
4. **IN 使用 foreach 标签**
5. **定期检查 Mapper 文件**

### ${} 合法使用场景

| 场景 | 条件 | 示例 |
|------|------|------|
| 动态表名 | 白名单校验 | `FROM ${tableName}` |
| 动态列名 | 白名单校验 | `SELECT ${columns}` |
| ORDER BY | 白名单校验 | `ORDER BY ${column}` |

### 代码修复示例

```xml
<!-- 修复前（危险） -->
<select id="search" resultType="User">
    SELECT * FROM users
    WHERE name LIKE '%${keyword}%'
    ORDER BY ${orderBy}
</select>

<!-- 修复后（安全） -->
<select id="search" resultType="User">
    SELECT * FROM users
    WHERE name LIKE CONCAT('%', #{keyword}, '%')
    ORDER BY
    <choose>
        <when test="orderBy == 'name'">name</when>
        <when test="orderBy == 'age'">age</when>
        <otherwise>id</otherwise>
    </choose>
</select>
```
