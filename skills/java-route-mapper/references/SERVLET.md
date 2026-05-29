# Servlet 路由分析

## 目录

- [项目识别](#项目识别)
- [配置方式](#配置方式)
- [路由注解](#路由注解)
- [参数获取](#参数获取)
- [常见模式](#常见模式)

---

## 项目识别

**特征文件：**
```
web.xml - 传统 Servlet 配置
包含 @WebServlet 注解的类
```

**特征类：**
```
extends HttpServlet
implements Servlet
```

---

## 配置方式

### web.xml 配置

```xml
<?xml version="1.0" encoding="UTF-8"?>
<web-app xmlns="http://xmlns.jcp.org/xml/ns/javaee"
         version="4.0">

    <servlet>
        <servlet-name>UserServlet</servlet-name>
        <servlet-class>com.example.servlet.UserServlet</servlet-class>
    </servlet>

    <servlet-mapping>
        <servlet-name>UserServlet</servlet-name>
        <url-pattern>/users/*</url-pattern>
    </servlet-mapping>

</web-app>
```

**提取规则：**
- `servlet-name` + `url-pattern` → 路由映射
- `url-pattern` 支持通配符：`/path/*`、`*.ext`、`/`

### 注解配置 @WebServlet

```java
@WebServlet("/users")
public class UserServlet extends HttpServlet { }

@WebServlet(urlPatterns = {"/users", "/user/list"})
public class UserServlet extends HttpServlet { }

@WebServlet(name = "UserServlet", urlPatterns = "/users/*",
            initParams = {@WebInitParam(name = "encoding", value = "UTF-8")})
public class UserServlet extends HttpServlet { }
```

**提取规则：**
- `urlPatterns` 或 `value` 属性定义路径
- 支持多个路径模式
- 支持通配符

---

## 路由注解

### @WebServlet 属性

| 属性 | 说明 | 示例 |
|------|------|------|
| `urlPatterns` / `value` | URL 模式 | `"/users/*"` |
| `name` | Servlet 名称 | `"UserServlet"` |
| `initParams` | 初始化参数 | `@WebInitParam` |
| `asyncSupported` | 是否支持异步 | `true` |
| `loadOnStartup` | 启动时加载顺序 | `1` |

### URL 模式匹配

```java
@WebServlet("/users")           // 精确匹配: /users
@WebServlet("/users/*")          // 路径匹配: /users/123, /users/abc
@WebServlet("*.do")              // 扩展名匹配: /list.do, /save.do
@WebServlet("/")                 // 默认 Servlet（匹配所有）
@WebServlet("/users/*")           // 但不匹配: /users（需要精确模式）
```

---

## 参数获取

### Servlet 方法分发

```java
@Override
protected void doGet(HttpServletRequest req, HttpServletResponse resp) { }

@Override
protected void doPost(HttpServletRequest req, HttpServletResponse resp) { }

@Override
protected void doPut(HttpServletRequest req, HttpServletResponse resp) { }

@Override
protected void doDelete(HttpServletRequest req, HttpServletResponse resp) { }
```

**识别方法：**
- 检查覆盖的 `doXxx` 方法
- 确定支持的 HTTP 方法

### 查询参数

```java
String id = req.getParameter("id");
String[] ids = req.getParameterValues("id");
Map<String, String[]> params = req.getParameterMap();
```

**提取要点：**
- 检查 `getParameter` 调用，提取参数名
- 检查 `getParameterMap` 遍历，提取所有参数使用

### 路径参数

```java
// 路径: /users/123
String pathInfo = req.getPathInfo();  // 返回 /123
String requestURI = req.getRequestURI();  // 返回 /users/123

// 手动解析路径参数
String[] parts = pathInfo.split("/");
String id = parts[1];
```

**提取要点：**
- `getPathInfo()` 获取相对于 Servlet 的路径
- 需要手动解析路径结构

### Body 参数

```java
// JSON Body
BufferedReader reader = req.getReader();
StringBuilder sb = new StringBuilder();
String line;
while ((line = reader.readLine()) != null) {
    sb.append(line);
}
String jsonBody = sb.toString();

// 表单参数
req.getParameter("username");
```

**提取要点：**
- 检查 `getReader()`、`getInputStream()` 调用
- 检查 Content-Type 处理逻辑

### Header 参数

```java
String authHeader = req.getHeader("Authorization");
Enumeration<String> headers = req.getHeaders("header-name");
```

### Cookie 参数

```java
Cookie[] cookies = req.getCookies();
if (cookies != null) {
    for (Cookie cookie : cookies) {
        if ("JSESSIONID".equals(cookie.getName())) {
            String sessionId = cookie.getValue();
        }
    }
}
```

---

## 常见模式

### RESTful 风格

```java
@WebServlet("/users/*")
public class UserServlet extends HttpServlet {

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) {
        String pathInfo = req.getPathInfo();
        // /users/123 → pathInfo = /123
        // /users → pathInfo = null
        if (pathInfo == null || pathInfo.equals("/")) {
            // 列表查询
        } else {
            // 单个查询: /users/123
            String id = pathInfo.substring(1);
        }
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) {
        // 创建用户
    }

    @Override
    protected void doPut(HttpServletRequest req, HttpServletResponse resp) {
        // 更新用户: /users/123
    }

    @Override
    protected void doDelete(HttpServletRequest req, HttpServletResponse resp) {
        // 删除用户: /users/123
    }
}
```

**提取要点：**
- 通过 `getPathInfo()` 区分列表和详情
- HTTP 方法通过不同的 `doXxx` 处理

### 前端控制器模式

```java
@WebServlet("/app/*")
public class FrontController extends HttpServlet {

    private Map<String, Action> actions = new HashMap<>();

    @Override
    public void init() {
        actions.put("/user/list", new UserListAction());
        actions.put("/user/detail", new UserDetailAction());
    }

    @Override
    protected void service(HttpServletRequest req, HttpServletResponse resp) {
        String path = req.getPathInfo(); // /user/list
        Action action = actions.get(path);
        action.execute(req, resp);
    }
}
```

**提取要点：**
- 需要分析 Action 注册逻辑
- 路径可能通过配置或约定定义

### JSP + Servlet

```xml
<!-- web.xml -->
<servlet>
    <servlet-name>jsp</servlet-name>
    <servlet-class>org.apache.jasper.servlet.JspServlet</servlet-class>
</servlet>
<servlet-mapping>
    <servlet-name>jsp</servlet-name>
    <url-pattern>*.jsp</url-pattern>
</servlet-mapping>
```

---

## 过滤器

### web.xml 配置

```xml
<filter>
    <filter-name>AuthFilter</filter-name>
    <filter-class>com.example.filter.AuthFilter</filter-class>
</filter>
<filter-mapping>
    <filter-name>AuthFilter</filter-name>
    <url-pattern>/api/*</url-pattern>
</filter-mapping>
```

### 注解配置

```java
@WebFilter(urlPatterns = "/api/*",
           filterName = "AuthFilter",
           initParams = {@WebInitParam(name = "excluded", value = "/api/public")})
public class AuthFilter implements Filter { }
```

**提取要点：**
- 记录过滤器路径
- 影响请求可达性，需记录拦截规则
