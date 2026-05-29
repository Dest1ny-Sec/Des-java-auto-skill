# XML 解析器 XXE 审计详解

## 目录

- [1. XMLReader](#1-xmlreader)
- [2. SAXBuilder (JDOM2)](#2-saxbuilder-jdom2)
- [3. SAXReader (dom4j)](#3-saxreader-dom4j)
- [4. SAXParserFactory](#4-saxparserfactory)
- [5. DocumentBuilderFactory](#5-documentbuilderfactory)
- [6. 其他 XML 组件](#6-其他-xml-组件)
- [7. 通用审计要点](#7-通用审计要点)

---

## 1. XMLReader

### 识别特征

```java
import org.xml.sax.XMLReader;
import org.xml.sax.InputSource;
import org.xml.sax.helpers.XMLReaderFactory;
```

### 危险模式

```java
// ❌ 高危：未设置任何安全特性
XMLReader xmlReader = XMLReaderFactory.createXMLReader();
InputSource inputSource = new InputSource(request.getInputStream());
xmlReader.parse(inputSource);
```

### 安全模式

```java
// ✅ 安全：禁止 DOCTYPE
XMLReader xmlReader = XMLReaderFactory.createXMLReader();
xmlReader.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
xmlReader.parse(inputSource);

// ✅ 安全：分别禁用外部实体
XMLReader xmlReader = XMLReaderFactory.createXMLReader();
xmlReader.setFeature("http://xml.org/sax/features/external-general-entities", false);
xmlReader.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
xmlReader.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
xmlReader.parse(inputSource);
```

### 检测规则

| 检查项 | 安全 | 危险 |
|--------|------|------|
| `setFeature("disallow-doctype-decl", true)` | ✅ | 未调用 |
| `setFeature("external-general-entities", false)` | ✅ | 未调用 |
| `setFeature("external-parameter-entities", false)` | ✅ | 未调用 |

### 搜索正则

```bash
grep -rn "XMLReaderFactory.createXMLReader\|XMLReader.*parse" --include="*.java"
```

---

## 2. SAXBuilder (JDOM2)

### 识别特征

```java
import org.jdom2.input.SAXBuilder;
import org.jdom2.Document;
import org.jdom2.Element;
```

### Maven 依赖

```xml
<dependency>
    <groupId>org.jdom</groupId>
    <artifactId>jdom2</artifactId>
</dependency>
```

### 危险模式

```java
// ❌ 高危：默认构造函数，未设置安全特性
SAXBuilder saxBuilder = new SAXBuilder();
Document doc = saxBuilder.build(new StringReader(xml));
```

### 安全模式

```java
// ✅ 安全：禁止 DOCTYPE
SAXBuilder saxBuilder = new SAXBuilder();
saxBuilder.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
Document doc = saxBuilder.build(new StringReader(xml));

// ✅ 安全：分别禁用
SAXBuilder saxBuilder = new SAXBuilder();
saxBuilder.setFeature("http://xml.org/sax/features/external-general-entities", false);
saxBuilder.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
Document doc = saxBuilder.build(new StringReader(xml));
```

### 注意事项

- JDOM2 2.0.6+ 默认禁用外部实体，但仍建议显式设置
- 旧版本 JDOM (1.x) 使用 `org.jdom.input.SAXBuilder`，默认不安全

### 搜索正则

```bash
grep -rn "new SAXBuilder\|SAXBuilder.*build" --include="*.java"
```

---

## 3. SAXReader (dom4j)

### 识别特征

```java
import org.dom4j.io.SAXReader;
import org.dom4j.Document;
import org.dom4j.Element;
```

### Maven 依赖

```xml
<dependency>
    <groupId>org.dom4j</groupId>
    <artifactId>dom4j</artifactId>
</dependency>
```

### 危险模式

```java
// ❌ 高危：默认构造函数，未设置安全特性
SAXReader reader = new SAXReader();
Document document = reader.read(new StringReader(xml));
Element root = document.getRootElement();
```

### 安全模式

```java
// ✅ 安全：禁止 DOCTYPE
SAXReader reader = new SAXReader();
reader.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
Document document = reader.read(new StringReader(xml));

// ✅ 安全：分别禁用
SAXReader reader = new SAXReader();
reader.setFeature("http://xml.org/sax/features/external-general-entities", false);
reader.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
Document document = reader.read(new StringReader(xml));
```

### 回显检测要点

dom4j 提供丰富的节点操作 API，解析结果常被用于回显：

```java
// 常见回显路径
root.element("user").getText()          // 获取子元素文本
root.elementText("user")               // 获取子元素文本（简写）
root.attributeValue("id")              // 获取属性值
root.selectSingleNode("//user").getText()  // XPath 查询
```

### 搜索正则

```bash
grep -rn "new SAXReader\|SAXReader.*read\|\.getRootElement\|\.elementText" --include="*.java"
```

---

## 4. SAXParserFactory

### 识别特征

```java
import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import org.xml.sax.XMLReader;
import org.xml.sax.helpers.DefaultHandler;
```

### 危险模式

```java
// ❌ 高危：未设置安全特性
SAXParserFactory factory = SAXParserFactory.newInstance();
XMLReader xmlReader = factory.newSAXParser().getXMLReader();
xmlReader.parse(new InputSource(new StringReader(xml)));

// ❌ 高危：使用 DefaultHandler
SAXParserFactory factory = SAXParserFactory.newInstance();
SAXParser parser = factory.newSAXParser();
parser.parse(inputStream, new DefaultHandler());
```

### 安全模式

```java
// ✅ 安全：在 factory 上设置特性
SAXParserFactory factory = SAXParserFactory.newInstance();
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
XMLReader xmlReader = factory.newSAXParser().getXMLReader();
xmlReader.parse(new InputSource(new StringReader(xml)));

// ✅ 安全：分别禁用
SAXParserFactory factory = SAXParserFactory.newInstance();
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
```

### 注意事项

- `setFeature` 必须在 `factory` 上调用，不是在 `parser` 或 `xmlReader` 上
- 注意区分 `SAXParserFactory.setFeature()` 和 `XMLReader.setFeature()` 的设置位置

### 搜索正则

```bash
grep -rn "SAXParserFactory.newInstance\|newSAXParser\|getXMLReader" --include="*.java"
```

---

## 5. DocumentBuilderFactory

### 识别特征

```java
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.DocumentBuilder;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
```

### 危险模式

```java
// ❌ 高危：未设置安全特性
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
DocumentBuilder builder = factory.newDocumentBuilder();
Document document = builder.parse(new InputSource(new StringReader(xml)));
Element root = document.getDocumentElement();

// ❌ 高危：仅设置 setValidating(false) 不能防 XXE
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.setValidating(false);  // 这不能防止 XXE！
DocumentBuilder builder = factory.newDocumentBuilder();
```

### 安全模式

```java
// ✅ 安全：禁止 DOCTYPE
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
DocumentBuilder builder = factory.newDocumentBuilder();
Document document = builder.parse(inputSource);

// ✅ 安全：分别禁用
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
factory.setExpandEntityReferences(false);
DocumentBuilder builder = factory.newDocumentBuilder();
```

### 回显检测要点

DOM 解析产生完整文档树，回显方式多样：

```java
// 常见回显路径
root.getElementsByTagName("user").item(0).getTextContent()
root.getAttribute("id")
document.getElementsByTagName("*")  // 遍历所有元素

// Transformer 输出（可能整体回显）
TransformerFactory.newInstance().newTransformer()
    .transform(new DOMSource(document), new StreamResult(response.getOutputStream()));
```

### 搜索正则

```bash
grep -rn "DocumentBuilderFactory.newInstance\|newDocumentBuilder\|\.parse.*InputSource\|getTextContent\|getElementsByTagName" --include="*.java"
```

---

## 6. 其他 XML 组件

### TransformerFactory

```java
// ❌ 危险
TransformerFactory tf = TransformerFactory.newInstance();
tf.newTransformer(new StreamSource(xmlInput));

// ✅ 安全
TransformerFactory tf = TransformerFactory.newInstance();
tf.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
tf.setAttribute(XMLConstants.ACCESS_EXTERNAL_STYLESHEET, "");
```

### XMLInputFactory (StAX)

```java
// ❌ 危险
XMLInputFactory factory = XMLInputFactory.newInstance();
XMLStreamReader reader = factory.createXMLStreamReader(inputStream);

// ✅ 安全
XMLInputFactory factory = XMLInputFactory.newInstance();
factory.setProperty(XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, false);
factory.setProperty(XMLInputFactory.SUPPORT_DTD, false);
```

### SchemaFactory

```java
// ❌ 危险
SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
factory.newSchema(new StreamSource(xmlInput));

// ✅ 安全
SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
factory.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
factory.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
```

### JAXB Unmarshaller

```java
// ❌ 危险：直接从 StreamSource 解析
JAXBContext context = JAXBContext.newInstance(User.class);
Unmarshaller unmarshaller = context.createUnmarshaller();
User user = (User) unmarshaller.unmarshal(new StreamSource(inputStream));

// ✅ 安全：先用安全的 DocumentBuilderFactory 解析，再传给 JAXB
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
DocumentBuilder db = dbf.newDocumentBuilder();
Document doc = db.parse(inputStream);
User user = (User) unmarshaller.unmarshal(doc);
```

---

## 7. 通用审计要点

### 安全配置有效性判断

| 配置 | 防护效果 | 备注 |
|------|----------|------|
| `disallow-doctype-decl = true` | **完全防护** | 拒绝所有 DOCTYPE，最安全 |
| `external-general-entities = false` | 部分防护 | 仅禁用通用外部实体 |
| `external-parameter-entities = false` | 部分防护 | 仅禁用参数外部实体 |
| `load-external-dtd = false` | 部分防护 | 仅禁止加载外部 DTD |
| `setValidating(false)` | **无防护** | 验证与外部实体无关 |
| `setNamespaceAware(true)` | **无防护** | 命名空间与外部实体无关 |
| `setExpandEntityReferences(false)` | 部分防护 | 仅 DocumentBuilderFactory 有效 |

### 完整防护要求

**至少满足以下之一：**

1. 设置 `disallow-doctype-decl = true`（推荐）
2. 同时设置 `external-general-entities = false` **且** `external-parameter-entities = false`

### 常见误判场景

| 场景 | 说明 | 判定 |
|------|------|------|
| 仅设置 `setValidating(false)` | 不能防 XXE | **仍然危险** |
| 设置了一个但缺另一个外部实体禁用 | 不完整防护 | **仍然危险** |
| 在 catch 中设置 feature | 正常流程不会执行 | **仍然危险** |
| 工厂方法复用但配置在特定分支 | 其他分支未防护 | **部分危险** |

### 版本相关安全差异

| 组件/版本 | 默认行为 |
|-----------|----------|
| JDK 8u191+ | 部分限制外部实体，但不完全安全 |
| JDOM2 2.0.6+ | 默认禁用外部实体 |
| dom4j 2.1.1+ | 仍需手动设置安全特性 |
| Woodstox 5.0+ | 默认禁用外部实体 |
