# Struts 2 路由分析

## 目录

- [项目识别](#项目识别)
- [配置文件](#配置文件)
- [路由定义](#路由定义)
- [参数处理](#参数处理)
- [常见模式](#常见模式)

---

## 项目识别

**特征文件：**
```
struts.xml - 主配置文件
struts.properties - 属性配置
web.xml - Struts 过滤器配置
```

**特征类：**
```java
extends ActionSupport
implements Action
```

**特征包：**
```
org.apache.struts2.*
com.opensymphony.xwork2.*
```

---

## 配置文件

### web.xml 配置

```xml
<filter>
    <filter-name>struts2</filter-name>
    <filter-class>org.apache.struts2.dispatcher.filter.StrutsPrepareAndExecuteFilter</filter-class>
</filter>
<filter-mapping>
    <filter-name>struts2</filter-name>
    <url-pattern>/*</url-pattern>
</filter-mapping>
```

**提取要点：**
- 过滤器 URL 模式决定 Struts 处理的路径范围

### struts.xml 配置

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE struts PUBLIC
    "-//Apache Software Foundation//DTD Struts Configuration 2.5//EN"
    "http://struts.apache.org/dtds/struts-2.5.dtd">

<struts>
    <constant name="struts.devMode" value="true" />
    <constant name="struts.action.extension" value="action,," />

    <package name="default" extends="struts-default" namespace="/">
        <action name="login" class="com.example.action.LoginAction" method="login">
            <result name="success">/home.jsp</result>
            <result name="input">/login.jsp</result>
        </action>
    </package>
</struts>
```

---

## 路由定义

### action 标签属性

```xml
<action name="user_*" class="com.example.action.UserAction" method="{1}">
    <!-- user_* 匹配 user_list、user_detail 等 -->
    <!-- {1} 会被替换为 * 匹配的内容 -->
</action>
```

| 属性 | 说明 | 示例 |
|------|------|------|
| `name` | Action 名称（路径） | `"user_list"` |
| `class` | Action 类全限定名 | `"com.example.action.UserAction"` |
| `method` | 执行的方法名 | `"list"` |
| `namespace` | 命名空间 | `"/api"` |

### namespace - 命名空间

```xml
<package name="user" extends="struts-default" namespace="/user">
    <action name="list" class="com.example.action.UserAction" method="list">
    </action>
</package>
```

**完整路径：** `/user/list.action`（默认扩展名）

### 通配符映射

```xml
<!-- 匹配 user_list、user_create、user_delete 等 -->
<action name="user_*" class="com.example.action.UserAction" method="{1}">
</action>

<!-- 匹配所有 *_user 操作 -->
<action name="*_user" class="com.example.action.UserAction" method="do{1}">
</action>

<!-- 多级通配 -->
<action name="*_*" class="com.example.action.{1}Action" method="{2}">
</action>
```

**提取要点：**
- 记录通配符模式
- 列举通配符模板的展开结果（如 user_list、user_detail）

---

## 参数处理

### 参数提交

**表单提交：**
```html
<form action="login.action" method="post">
    <input name="username" />
    <input name="password" />
</form>
```

**URL 参数：**
```
/user/list.action?page=1&size=10
```

### ModelDriven 模式

```java
public class UserAction extends ActionSupport implements ModelDriven<User> {
    private User user = new User();

    public User getModel() {
        return user;
    }

    public String save() {
        // user.username、user.password 自动填充
    }
}
```

**请求参数：** `username=admin&password=123456`

### DriverAware 模式

```java
public class UserAction extends ActionSupport implements Preparable {
    private User user;

    public void prepare() throws Exception {
        user = new User();
    }

    public String save() {
        // 参数自动绑定到 user
    }
}
```

### 对象图导航

```java
public class UserAction extends ActionSupport {
    private User user;

    // getter/setter
}
```

**请求参数：**
```
user.username=admin
user.password=123456
user.profile.email=test@example.com
```

---

## 常见模式

### REST 插件

```xml
<package name="user" extends="rest-default" namespace="/user">
    <action name="user" class="com.example.action.UserController">
        <!-- 自动映射 HTTP 方法到 Action 方法 -->
        <!-- GET    /user/      → index() -->
        <!-- GET    /user/1     → show() -->
        <!-- POST   /user/      → create() -->
        <!-- PUT    /user/1     → update() -->
        <!-- DELETE /user/1     → delete() -->
    </action>
</package>
```

**方法映射：**

| HTTP 方法 | 路径 | Action 方法 |
|-----------|------|-------------|
| GET | /user | `index()` |
| GET | /user/1 | `show()` |
| POST | /user | `create()` |
| PUT | /user/1 | `update()` |
| DELETE | /user/1 | `delete()` |
| POST | /user/1?_method=DELETE | `delete()` |

### 约定优于配置

```xml
<constant name="struts.convention.action.packages" value="com.example.action" />
<constant name="struts.convention.action.suffix" value="Action" />
<constant name="struts.convention.package.locators" value="action" />
```

**约定规则：**
- 类名：`XxxAction` → 路径：`xxx`
- 包名：`com.example.action.user.UserAction` → 命名空间：`/user`
- 方法名：`execute()` → 默认执行方法

### JSON 插件

```xml
<package name="user" extends="json-default" namespace="/api/user">
    <action name="list" class="com.example.action.UserAction" method="list">
        <result type="json">
            <param name="root">userList</param>
        </result>
    </action>
</package>
```

---

## 结果类型

### 结果类型

| 类型 | 说明 | Content-Type |
|------|------|--------------|
| `dispatcher` | 转发到 JSP | text/html |
| `redirect` | 重定向 | - |
| `redirectAction` | 重定向到 Action | - |
| `json` | JSON 输出 | application/json |
| `stream` | 文件下载 | application/octet-stream |

```xml
<action name="download" class="com.example.action.FileAction" method="download">
    <result name="success" type="stream">
        <param name="contentType">application/octet-stream</param>
        <param name="inputName">inputStream</param>
        <param name="contentDisposition">attachment;filename="${filename}"</param>
    </result>
</action>
```

---

## 拦截器

### 拦截器栈

```xml
<interceptors>
    <interceptor name="auth" class="com.example.interceptor.AuthInterceptor" />
    <interceptor-stack name="authStack">
        <interceptor-ref name="auth" />
        <interceptor-ref name="defaultStack" />
    </interceptor-stack>
</interceptors>

<default-interceptor-ref name="authStack" />
```

**提取要点：**
- 记录拦截器路径规则
- 影响请求可达性，需记录拦截规则

---

## 常见漏洞模式

### 参数绑定

```java
public class UserAction extends ActionSupport {
    private User user;  // 直接绑定，可能允许修改敏感字段
}
```

### 动态方法调用

```xml
<constant name="struts.enable.DynamicMethodInvocation" value="true" />
```

**访问方式：** `/user!list.action`

---

## 扩展名配置

```xml
<constant name="struts.action.extension" value="action,," />
```

**提取要点：**
- 空字符串表示允许无扩展名
- 影响路由路径格式
