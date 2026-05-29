# Java 文件读取方法详解

本文档详细介绍 Java 中常见的文件读取方法及其安全风险。

---

## 1. BufferedReader

### 1.1 基本用法

```java
import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStreamReader;

public class ClassicFileReadExample {
    public static void main(String[] args) {
        String filePath = "example.txt";
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(new FileInputStream(filePath)))) {
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println(line);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

### 1.2 安全漏洞

| 漏洞点 | 说明 |
|--------|------|
| **filePath 来源** | 如果 filePath 来自用户输入，存在任意文件读取漏洞 |
| **路径遍历** | 用户可以输入 `../../../etc/passwd` 读取系统文件 |
| **无校验** | 代码未对路径进行白名单或规范化校验 |

---

## 2. Scanner

### 2.1 基本用法

```java
import java.io.FileReader;
import java.util.Scanner;

public class ScannerFileReaderExample {
    public static void main(String[] args) {
        String filePath = "example.txt";
        try (Scanner scanner = new Scanner(new FileReader(filePath))) {
            while (scanner.hasNextLine()) {
                String line = scanner.nextLine();
                System.out.println(line);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

### 2.2 安全漏洞

与 BufferedReader 相同，主要漏洞点在于 filePath 参数来源。

---

## 3. Files.lines (NIO)

### 3.1 基本用法

```java
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;

public class FilesLinesExample {
    public static void main(String[] args) {
        String filePath = "example.txt";
        try (Stream<String> lines = Files.lines(Path.of(filePath))) {
            lines.forEach(System.out::println);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

### 3.2 安全漏洞

| 漏洞点 | 说明 |
|--------|------|
| **Path.of() 参数** | 接受用户输入可能导致路径遍历 |
| **流式读取** | 适合大文件，但路径遍历漏洞相同 |

---

## 4. Files.readAllLines (NIO)

### 4.1 基本用法

```java
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class FilesReadAllLinesExample {
    public static void main(String[] args) {
        String filePath = "example.txt";
        try {
            List<String> lines = Files.readAllLines(Path.of(filePath));
            lines.forEach(System.out::println);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

### 4.2 安全漏洞

**内存占用**：一次性读取所有行到内存，大文件可能导致内存溢出。

**路径安全**：与其他方法相同的路径遍历漏洞。

---

## 5. Files.readAllBytes (NIO)

### 5.1 基本用法

```java
import java.nio.file.Files;
import java.nio.file.Path;

public class FilesReadAllBytesExample {
    public static void main(String[] args) {
        String filePath = "example.bin";
        try {
            byte[] fileContent = Files.readAllBytes(Path.of(filePath));
            // 处理文件内容
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

### 5.2 安全漏洞

**二进制文件读取**：可以读取任意类型的文件，包括系统配置文件、密钥文件等。

---

## 6. FileInputStream

### 6.1 基本用法

```java
import java.io.FileInputStream;

public class FileInputStreamExample {
    public static void main(String[] args) {
        String filePath = "example.txt";
        try (FileInputStream fis = new FileInputStream(filePath)) {
            int content;
            while ((content = fis.read()) != -1) {
                System.out.print((char) content);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

### 6.2 安全漏洞

最常见的文件读取方式，路径遍历漏洞可能性最高。

---

## 安全检测规则

### 危险模式

```java
// 1. 直接使用用户输入作为路径
String filePath = request.getParameter("filePath");
FileInputStream fis = new FileInputStream(filePath);

// 2. 路径拼接未校验
String fileName = request.getParameter("fileName");
String fullPath = basePath + fileName;
Files.readAllBytes(Path.of(fullPath));

// 3. Path.of/Paths.get 未规范化
String userPath = request.getParameter("path");
Path path = Path.of(userPath);
Files.lines(path);
```

### 安全模式

```java
// 1. 使用白名单目录限制
String basePath = "/var/uploads";
String fileName = request.getParameter("fileName");
File file = new File(basePath, fileName);
String canonicalPath = file.getCanonicalPath();
if (!canonicalPath.startsWith(basePath)) {
    throw new SecurityException("Invalid path");
}

// 2. 白名单扩展名校验
String fileName = request.getParameter("fileName");
if (!fileName.endsWith(".txt") && !fileName.endsWith(".pdf")) {
    throw new SecurityException("Invalid file type");
}

// 3. 路径规范化
Path path = Paths.get(basePath, fileName).normalize();
if (!path.startsWith(basePath)) {
    throw new SecurityException("Path traversal detected");
}
```

---

## 审计检查清单

**在审计文件读取代码时，必须检查：**

- [ ] 文件路径参数是否来自用户输入
- [ ] 是否有白名单目录限制
- [ ] 是否有文件扩展名校验
- [ ] 是否使用 `getCanonicalPath()` 进行路径规范化
- [ ] 是否过滤 `../` 等路径遍历字符
- [ ] 是否记录文件访问日志
