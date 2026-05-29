# 注解参考手册

## 目录

- [Spring 注解](#spring-注解)
- [JAX-RS 注解](#jax-rs-注解)
- [Servlet 注解](#servlet-注解)
- [参数绑定注解](#参数绑定注解)
- [验证注解](#验证注解)

---

## Spring 注解

### 路由定义

| 注解 | 作用 | 示例 |
|------|------|------|
| `@Controller` | 标记控制器类 | `@Controller public class UserCtrl {}` |
| `@RestController` | REST 控制器（=@Controller+@ResponseBody） | `@RestController public class UserApi {}` |
| `@RequestMapping` | 类/方法级别路由 | `@RequestMapping("/api/users")` |
| `@GetMapping` | GET 路由 | `@GetMapping("/users/{id}")` |
| `@PostMapping` | POST 路由 | `@PostMapping("/users")` |
| `@PutMapping` | PUT 路由 | `@PutMapping("/users/{id}")` |
| `@PatchMapping` | PATCH 路由 | `@PatchMapping("/users/{id}")` |
| `@DeleteMapping` | DELETE 路由 | `@DeleteMapping("/users/{id}")` |

### @RequestMapping 属性

```java
@RequestMapping(
    // 路径
    value = {"/path1", "/path2"},

    // HTTP 方法
    method = {RequestMethod.GET, RequestMethod.POST},

    // 请求参数条件
    params = {"action=save", "!debug"},

    // 请求头条件
    headers = {"X-Requested-With=XMLHttpRequest", "Content-Type=application/json"},

    // 可消费的 Content-Type
    consumes = {"application/json", "application/xml"},

    // 可生产的 Content-Type
    produces = {"application/json; charset=UTF-8"}
)
```

---

## JAX-RS 注解

### 路由定义

| 注解 | 作用 | 示例 |
|------|------|------|
| `@Path` | 类/方法级别路径 | `@Path("/users")` |
| `@GET` | GET 方法 | `@GET public Response list() {}` |
| `@POST` | POST 方法 | `@POST public Response create() {}` |
| `@PUT` | PUT 方法 | `@PUT public Response update() {}` |
| `@DELETE` | DELETE 方法 | `@DELETE public Response delete() {}` |
| `@HEAD` | HEAD 方法 | `@HEAD public Response head() {}` |
| `@OPTIONS` | OPTIONS 方法 | `@OPTIONS public Response options() {}` |

### 内容协商

| 注解 | 作用 | 示例 |
|------|------|------|
| `@Consumes` | 可接受的请求类型 | `@Consumes(MediaType.APPLICATION_JSON)` |
| `@Produces` | 可生成的响应类型 | `@Produces(MediaType.APPLICATION_JSON)` |

---

## Servlet 注解

| 注解 | 作用 | 示例 |
|------|------|------|
| `@WebServlet` | 定义 Servlet | `@WebServlet("/users")` |
| `@WebFilter` | 定义过滤器 | `@WebFilter(urlPatterns="/api/*")` |
| `@WebListener` | 定义监听器 | `@WebListener public class AppListener {}` |

### @WebServlet 属性

```java
@WebServlet(
    // URL 模式
    urlPatterns = {"/users", "/user/*"},

    // Servlet 名称
    name = "UserServlet",

    // 初始化参数
    initParams = {
        @WebInitParam(name = "encoding", value = "UTF-8")
    },

    // 启动时加载顺序
    loadOnStartup = 1,

    // 是否支持异步
    asyncSupported = true
)
```

---

## 参数绑定注解

### Spring 参数注解

| 注解 | 来源 | 示例 |
|------|------|------|
| `@PathVariable` | 路径变量 | `{id}` → `@PathVariable Long id` |
| `@RequestParam` | 查询参数 | `?name=xxx` → `@RequestParam String name` |
| `@RequestBody` | 请求体 | JSON Body |
| `@RequestHeader` | 请求头 | `@RequestHeader("Authorization")` |
| `@CookieValue` | Cookie | `@CookieValue("JSESSIONID")` |
| `@RequestAttribute` | 请求属性 | `@RequestAttribute("user")` |
| `@SessionAttribute` | Session 属性 | `@SessionAttribute("user")` |
| `@MatrixVariable` | 矩阵变量 | `/users;q=10;r=20` |

### @RequestParam 属性

```java
@RequestParam(
    // 参数名（可省略，默认使用方法参数名）
    value = "username",

    // 是否必需（默认 true）
    required = false,

    // 默认值
    defaultValue = "guest"
)
```

### JAX-RS 参数注解

| 注解 | 来源 | 示例 |
|------|------|------|
| `@PathParam` | 路径变量 | `{id}` → `@PathParam("id") Long id` |
| `@QueryParam` | 查询参数 | `?name=xxx` → `@QueryParam("name")` |
| `@FormParam` | 表单参数 | `@FormParam("username")` |
| `@HeaderParam` | 请求头 | `@HeaderParam("Authorization")` |
| `@CookieParam` | Cookie | `@CookieParam("JSESSIONID")` |
| `@MatrixParam` | 矩阵参数 | `;name=value` |
| `@BeanParam` | 参数封装 | `@BeanParam UserParams params` |

### @DefaultValue (JAX-RS)

```java
@QueryParam("page") @DefaultValue("0") int page
```

---

## 验证注解

### Jakarta Validation

| 注解 | 作用 | 示例 |
|------|------|------|
| `@NotNull` | 不为 null | `@NotNull String name` |
| `@NotEmpty` | 不为空 | `@NotEmpty String name` |
| `@NotBlank` | 不为空白 | `@NotBlank String name` |
| `@Size` | 长度范围 | `@Size(min=2, max=10)` |
| `@Min` / `@Max` | 数值范围 | `@Min(18) int age` |
| `@Email` | 邮箱格式 | `@Email String email` |
| `@Pattern` | 正则匹配 | `@Pattern(regexp="[A-Z]{2}")` |
| `@Valid` | 嵌套验证 | `@Valid UserDto user` |

---

## 其他常用注解

### Cross-Origin

```java
@CrossOrigin(
    origins = "http://localhost:8080",
    methods = {RequestMethod.GET, RequestMethod.POST},
    allowedHeaders = {"Content-Type", "Authorization"},
    credentials = "true",
    maxAge = 3600
)
```

### Response Body

```java
@ResponseBody  // Spring: 直接写入响应体
Response        // JAX-RS: 返回 Response 对象

// 示例
@GET
public Response getUser() {
    return Response.ok(userEntity).build();
    return Response.status(Response.Status.NOT_FOUND).build();
    return Response.status(401).entity("Unauthorized").build();
}
```

---

## 注解继承规则

### Spring

- `@RequestMapping` 在类级别可被方法级别继承
- 子类方法覆盖父类时，注解不自动继承（需重新声明）

### JAX-RS

- `@Path` 在类级别可被方法级别继承
- 子类继承父类的 `@Path`

---

## 自定义注解

```java
// 目标：定义在方法上
@Target(ElementType.METHOD)
// 运行时保留
@Retention(RetentionPolicy.RUNTIME)
// 作为 @RequestMapping 的元注解
@RequestMapping(method = RequestMethod.GET)
public @interface MyGetMapping {
    @AliasFor(annotation = RequestMapping.class)
    String[] value() default {};
}

// 使用
@MyGetMapping("/users")
public List<User> list() { }
```

---

## 注解处理器示例

```java
// 扫描特定注解
Reflections reflections = new Reflections("com.example");
Set<Class<?>> controllers = reflections.getTypesAnnotatedWith(Controller.class);

// 分析方法上的注解
for (Method method : controller.getDeclaredMethods()) {
    if (method.isAnnotationPresent(GetMapping.class)) {
        GetMapping mapping = method.getAnnotation(GetMapping.class);
        String[] paths = mapping.value();
        // 处理路径
    }
}
```
