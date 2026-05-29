# Hibernate SQL 注入审计详解

## 目录

- [Hibernate 基础概念](#hibernate-基础概念)
- [HQL 注入检测](#hql-注入检测)
- [Native SQL 注入检测](#native-sql-注入检测)
- [Criteria API 检查](#criteria-api-检查)
- [JPA 注解检查](#jpa-注解检查)
- [常见漏洞场景](#常见漏洞场景)

---

## Hibernate 基础概念

### 识别特征

**依赖识别：**
```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.hibernate</groupId>
    <artifactId>hibernate-core</artifactId>
</dependency>

<!-- 或 Spring Data JPA -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>
```

**配置文件：**
- `hibernate.cfg.xml` - Hibernate 配置
- `persistence.xml` - JPA 配置
- `application.yml` - Spring Boot 配置

**代码特征：**
```java
// 实体类
@Entity
@Table(name = "users")
public class User { ... }

// Session 使用
Session session = sessionFactory.openSession();
Query query = session.createQuery(hql);

// EntityManager 使用
EntityManager em = entityManagerFactory.createEntityManager();
Query query = em.createQuery(jpql);
```

### 查询方式

| 方式 | 说明 | 是否可注入 |
|------|------|-----------|
| HQL/JPQL | Hibernate/JPA 查询语言 | 取决于是否参数化 |
| Native SQL | 原生 SQL | 取决于是否参数化 |
| Criteria API | 类型安全的查询构建器 | 否（推荐） |
| QueryDSL | 类型安全的查询 DSL | 否（推荐） |

---

## HQL 注入检测

### 危险模式（字符串拼接）

```java
// ❌ 高危：HQL 字符串拼接
String username = request.getParameter("username");
String hql = "FROM User WHERE username = '" + username + "'";
Query query = session.createQuery(hql);
List<User> users = query.list();

// ❌ 高危：StringBuilder 拼接
StringBuilder hql = new StringBuilder("FROM User WHERE 1=1");
if (name != null) {
    hql.append(" AND name = '" + name + "'");
}
Query query = session.createQuery(hql.toString());

// ❌ 高危：String.format
String hql = String.format("FROM User WHERE id = %s", id);
```

### 安全模式（参数绑定）

```java
// ✅ 安全：命名参数
String hql = "FROM User WHERE username = :username";
Query query = session.createQuery(hql);
query.setParameter("username", username);
List<User> users = query.list();

// ✅ 安全：位置参数
String hql = "FROM User WHERE id = ?1";
Query query = session.createQuery(hql);
query.setParameter(1, id);

// ✅ 安全：JPA 风格
String jpql = "SELECT u FROM User u WHERE u.name = :name";
TypedQuery<User> query = em.createQuery(jpql, User.class);
query.setParameter("name", name);
```

### 检测正则

```bash
# 搜索 HQL/JPQL 拼接
grep -rn 'createQuery.*+' --include="*.java"
grep -rn 'FROM.*+.*WHERE' --include="*.java"
grep -rn 'SELECT.*+.*FROM' --include="*.java"
```

---

## Native SQL 注入检测

### 危险模式

```java
// ❌ 高危：Native SQL 拼接
String sql = "SELECT * FROM users WHERE id = " + id;
Query query = session.createNativeQuery(sql, User.class);

// ❌ 高危：SQLQuery 拼接（旧版 API）
String sql = "SELECT * FROM users WHERE name = '" + name + "'";
SQLQuery query = session.createSQLQuery(sql);

// ❌ 高危：EntityManager Native Query
String sql = "DELETE FROM users WHERE id = " + id;
Query query = em.createNativeQuery(sql);
```

### 安全模式

```java
// ✅ 安全：命名参数
String sql = "SELECT * FROM users WHERE id = :id";
Query query = session.createNativeQuery(sql, User.class);
query.setParameter("id", id);

// ✅ 安全：位置参数
String sql = "SELECT * FROM users WHERE id = ?1";
Query query = em.createNativeQuery(sql, User.class);
query.setParameter(1, id);
```

---

## Criteria API 检查

### 老版 Criteria API（Hibernate 5.x 之前）

```java
// ⚠️ 注意：Restrictions.sqlRestriction 有注入风险
Criteria criteria = session.createCriteria(User.class);

// ❌ 高危：sqlRestriction 拼接
String filter = "name = '" + name + "'";
criteria.add(Restrictions.sqlRestriction(filter));

// ✅ 安全：使用类型安全的 Restrictions
criteria.add(Restrictions.eq("name", name));
criteria.add(Restrictions.like("name", name, MatchMode.ANYWHERE));
criteria.add(Restrictions.in("id", ids));
```

### JPA Criteria API（推荐）

```java
// ✅ 安全：CriteriaBuilder 类型安全
CriteriaBuilder cb = em.getCriteriaBuilder();
CriteriaQuery<User> cq = cb.createQuery(User.class);
Root<User> root = cq.from(User.class);

// 等值查询
cq.where(cb.equal(root.get("username"), username));

// LIKE 查询
cq.where(cb.like(root.get("name"), "%" + keyword + "%"));

// IN 查询
cq.where(root.get("id").in(ids));

TypedQuery<User> query = em.createQuery(cq);
List<User> users = query.getResultList();
```

### 危险的 Criteria 方法

| 方法 | 风险 | 说明 |
|------|------|------|
| `Restrictions.sqlRestriction(sql)` | **高危** | 直接执行 SQL 片段 |
| `Restrictions.sqlRestriction(sql, value, type)` | 中 | 带参数但需检查 |
| `Expression.sql()` | **高危** | 直接 SQL 表达式 |

---

## JPA 注解检查

### @Query 注解

```java
// ✅ 安全：使用参数绑定
@Query("SELECT u FROM User u WHERE u.name = :name")
List<User> findByName(@Param("name") String name);

// ✅ 安全：位置参数
@Query("SELECT u FROM User u WHERE u.id = ?1")
User findById(Long id);

// ❌ 高危：SpEL 表达式拼接
@Query("SELECT u FROM User u WHERE u.name = '#{#name}'")  // 危险！
List<User> findByNameUnsafe(@Param("name") String name);

// ⚠️ nativeQuery 需要特别注意
@Query(value = "SELECT * FROM users WHERE id = :id", nativeQuery = true)
User findByIdNative(@Param("id") Long id);
```

### @NamedQuery 注解

```java
@Entity
@NamedQueries({
    // ✅ 安全：预定义查询
    @NamedQuery(name = "User.findByName",
                query = "SELECT u FROM User u WHERE u.name = :name"),
    @NamedQuery(name = "User.findByAge",
                query = "SELECT u FROM User u WHERE u.age = :age")
})
public class User { ... }
```

### 检查 @Query 注解

```bash
# 搜索所有 @Query 注解
grep -rn '@Query' --include="*.java"

# 搜索 nativeQuery
grep -rn 'nativeQuery.*=.*true' --include="*.java"

# 搜索 SpEL 表达式
grep -rn '@Query.*#\{' --include="*.java"
```

---

## 常见漏洞场景

### 场景 1：动态 HQL 构建

```java
// ❌ 高危：动态条件拼接
public List<User> search(String name, Integer age) {
    StringBuilder hql = new StringBuilder("FROM User WHERE 1=1");
    if (name != null) {
        hql.append(" AND name = '" + name + "'");  // 注入点
    }
    if (age != null) {
        hql.append(" AND age = " + age);  // 注入点
    }
    return session.createQuery(hql.toString()).list();
}

// ✅ 安全：使用参数化
public List<User> search(String name, Integer age) {
    StringBuilder hql = new StringBuilder("FROM User WHERE 1=1");
    Map<String, Object> params = new HashMap<>();

    if (name != null) {
        hql.append(" AND name = :name");
        params.put("name", name);
    }
    if (age != null) {
        hql.append(" AND age = :age");
        params.put("age", age);
    }

    Query query = session.createQuery(hql.toString());
    params.forEach(query::setParameter);
    return query.list();
}
```

### 场景 2：ORDER BY 注入

```java
// ❌ 高危：ORDER BY 拼接
String orderBy = request.getParameter("sort");
String hql = "FROM User ORDER BY " + orderBy;
Query query = session.createQuery(hql);

// ⚠️ ORDER BY 无法参数化，必须白名单
String orderBy = request.getParameter("sort");
if (!ALLOWED_COLUMNS.contains(orderBy)) {
    orderBy = "id";
}
String hql = "FROM User ORDER BY " + orderBy;
```

### 场景 3：IN 子句

```java
// ❌ 高危：IN 拼接
String ids = request.getParameter("ids");  // "1,2,3"
String hql = "FROM User WHERE id IN (" + ids + ")";

// ✅ 安全：使用 setParameterList
List<Long> idList = Arrays.asList(1L, 2L, 3L);
String hql = "FROM User WHERE id IN (:ids)";
Query query = session.createQuery(hql);
query.setParameterList("ids", idList);
```

### 场景 4：LIKE 查询

```java
// ❌ 高危：LIKE 拼接
String keyword = request.getParameter("keyword");
String hql = "FROM User WHERE name LIKE '%" + keyword + "%'";

// ✅ 安全：参数化 LIKE
String hql = "FROM User WHERE name LIKE :keyword";
Query query = session.createQuery(hql);
query.setParameter("keyword", "%" + keyword + "%");
```

### 场景 5：存储过程调用

```java
// ❌ 高危：存储过程参数拼接
String sql = "CALL sp_get_user('" + username + "')";
Query query = session.createNativeQuery(sql);

// ✅ 安全：使用 StoredProcedureQuery
StoredProcedureQuery query = em.createStoredProcedureQuery("sp_get_user");
query.registerStoredProcedureParameter("username", String.class, ParameterMode.IN);
query.setParameter("username", username);
```

---

## 检查清单

### HQL/JPQL 检查

- [ ] 搜索所有 `createQuery()` 调用
- [ ] 检查 HQL 字符串是否有拼接
- [ ] 确认使用 `setParameter()` 绑定参数
- [ ] ORDER BY 是否有白名单校验

### Native SQL 检查

- [ ] 搜索所有 `createNativeQuery()` 调用
- [ ] 搜索所有 `createSQLQuery()` 调用
- [ ] 检查 SQL 字符串是否有拼接
- [ ] 确认使用参数绑定

### Criteria 检查

- [ ] 搜索 `Restrictions.sqlRestriction()` 使用
- [ ] 检查 `Expression.sql()` 使用
- [ ] 确认使用类型安全的 Criteria 方法

### @Query 注解检查

- [ ] 搜索所有 `@Query` 注解
- [ ] 检查 `nativeQuery = true` 的查询
- [ ] 检查 SpEL 表达式使用

---

## 修复要求

### 必须遵守的规范

1. **始终使用参数绑定**（`:paramName` 或 `?1`）
2. **优先使用 Criteria API**（类型安全）
3. **禁止使用 Native SQL 字符串拼接**，必须使用时改为参数化
4. **ORDER BY 使用白名单**校验
5. **禁止使用 Restrictions.sqlRestriction()**

### 代码修复示例

```java
// 修复前（危险）
public User findByUsername(String username) {
    String hql = "FROM User WHERE username = '" + username + "'";
    return session.createQuery(hql, User.class).uniqueResult();
}

// 修复后（安全）
public User findByUsername(String username) {
    String hql = "FROM User WHERE username = :username";
    return session.createQuery(hql, User.class)
                  .setParameter("username", username)
                  .uniqueResult();
}

// 更安全：使用 Criteria API
public User findByUsername(String username) {
    CriteriaBuilder cb = em.getCriteriaBuilder();
    CriteriaQuery<User> cq = cb.createQuery(User.class);
    Root<User> root = cq.from(User.class);
    cq.where(cb.equal(root.get("username"), username));
    return em.createQuery(cq).getSingleResult();
}
```
