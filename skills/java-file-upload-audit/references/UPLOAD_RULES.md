# Java 文件上传审计规则速查

本文件整理来自 Notion 的关键实现特征与审计规则。用于在识别上传入口后快速判断风险点。

## 一、上传实现识别

### 1) Servlet / Commons FileUpload

**典型代码特征：**
- `ServletFileUpload.isMultipartContent(request)`
- `DiskFileItemFactory` / `ServletFileUpload`
- `upload.parseRequest(request)` → `List<FileItem>`
- `item.getName()` 作为文件名
- `item.write(storeFile)` 写入文件
- `getServletContext().getRealPath("/uploads")` 作为保存目录

**Notion 记录要点：**
- 示例未校验表单字段名（`name="file"` 不会被校验）。
- 设置了大小限制（如 `upload.setSizeMax(5 * 1024 * 1024)`），但未见扩展名/类型/路径校验。

### 2) Spring Boot MultipartFile

**典型代码特征：**
- `@RequestParam("file") MultipartFile file`
- `file.getOriginalFilename()`
- `file.transferTo(filePath)`
- 固定上传目录 `uploadDir = "/uploads/"`

**Notion 记录要点：**
- `@RequestParam("file")` 会校验表单字段名，需要 `name="file"`。
- 示例未见文件名净化、类型白名单或目录隔离。

---

## 二、常见高危模式

| 模式 | 代码特征 | 风险 |
|:-----|:---------|:-----|
| 原始文件名直写 | `getOriginalFilename()` / `item.getName()` | 文件名可控、路径穿越 |
| Web 根目录写入 | `getRealPath("/uploads")` / `/uploads/` | 可执行文件上传 |
| 无类型校验 | 无扩展名或 Content-Type 白名单 | 任意文件上传 |
| 无路径规范化 | 直接拼接 `new File(dir + fileName)` | 路径穿越/文件覆盖 |
| 无重命名 | 不生成随机名 | 文件覆盖/可预测路径 |

---

## 三、要求的安全校验点

| 校验点 | 建议 |
|:-------|:-----|
| 文件名 | 去除路径分隔符、只保留文件名 |
| 目录限制 | 固定基础目录 + `getCanonicalPath()` 校验 |
| 类型校验 | 扩展名白名单 + Content-Type/魔数校验 |
| 上传目录 | 非 Web 根目录，或严格访问控制 |
| 重命名 | 使用随机名或哈希名 |
| 大小限制 | 全局 & 单文件限制 |

---

## 四、快速检查项

- 是否使用 `getOriginalFilename()` / `item.getName()` 作为最终文件名？
- 上传目录是否在 Web 可访问路径下？
- 是否缺少扩展名/Content-Type 白名单？
- 是否存在路径规范化与目录限制？
- 是否存在文件覆盖风险（固定文件名/不重命名）？
