# 多接口方法追踪策略

## 概述

当遇到包含多个业务方法的类时（如 Web Service 有多个接口方法、Controller 有多个端点方法），技能会自动识别并追踪所有方法。

## 方法发现策略（通用）

```python
def find_all_entry_methods(entry_class):
    methods = []

    if is_spring_controller(entry_class):
        methods.extend(find_spring_mapping_methods(entry_class))

    elif is_struts_action(entry_class):
        methods.extend(find_struts_methods(entry_class))

    elif is_servlet(entry_class):
        methods.extend(find_servlet_methods(entry_class))

    elif is_jaxrs_resource(entry_class):
        methods.extend(find_jaxrs_mapping_methods(entry_class))

    elif is_webservice(entry_class):
        methods.extend(find_webservice_methods(entry_class))

    return methods
```

---

## 各框架的方法识别规则

### 1. Spring MVC 多接口方法

**识别条件**: 查找所有带 `@RequestMapping` 或 HTTP 方法注解的方法

```python
def find_spring_mapping_methods(controller_class):
    spring_methods = []
    for method in controller_class.getMethods():
        has_mapping = False
        if has_annotation(method, "RequestMapping") or \
           has_annotation(method, "GetMapping") or \
           has_annotation(method, "PostMapping") or \
           has_annotation(method, "PutMapping") or \
           has_annotation(method, "DeleteMapping"):
            spring_methods.append(method)
    return spring_methods
```

### 2. Struts 2 多 Action 方法

**识别条件**: 查找符合 Struts 2 方法签名的方法

```python
def find_struts_methods(action_class):
    struts_methods = []
    for method in action_class.getMethods():
        if is_valid_struts_method(method):
            struts_methods.append(method)
    return struts_methods

def is_valid_struts_method(method):
    if method.getParameterCount() > 0:
        return False
    if method.getReturnType() != String.class and method.getReturnType() != void.class:
        return False
    if method.getName().startsWith("get") or method.getName().startsWith("set"):
        return False
    return True
```

### 3. Servlet 多请求方法

**识别条件**: 识别 doGet/doPost/doPut/doDelete 等方法

```python
def find_servlet_methods(servlet_class):
    servlet_methods = []
    for method in servlet_class.getMethods():
        if method.getName().startswith("do") and \
           method.getParameterCount() == 2 and \
           has_parameter_type(method, "HttpServletRequest") and \
           has_parameter_type(method, "HttpServletResponse"):
            servlet_methods.append(method)
    return servlet_methods
```

### 4. JAX-RS 资源方法

**识别条件**: 查找带 `@Path` 或 HTTP 方法注解的方法

```python
def find_jaxrs_mapping_methods(resource_class):
    jaxrs_methods = []
    for method in resource_class.getMethods():
        if has_annotation(method, "Path") or \
           has_annotation(method, "GET") or \
           has_annotation(method, "POST"):
            jaxrs_methods.append(method)
    return jaxrs_methods
```

### 5. Web Service 多接口方法

**识别条件**: 扫描实现类的所有 public 方法

```python
def find_webservice_methods(service_impl_class):
    methods = []
    for method in dir(service_impl_class):
        if not method.startswith('__') and method not in ['equals', 'hashCode', 'toString', 'clone']:
            method_obj = getattr(service_impl_class, method)
            if callable(method_obj):
                methods.append(method)
    return methods

def filter_webservice_methods(methods, interface_class):
    ws_methods = []
    for method in methods:
        if hasattr(interface_class, method):
            if callable(getattr(interface_class, method)):
                ws_methods.append(method)
    return ws_methods
```

---

## 执行流程优化（含接口数量优化策略）

```python
def audit_route(entry_class, route_path):
    print(f"正在扫描入口类: {entry_class.getName()}")

    entry_methods = find_all_entry_methods(entry_class)

    if not entry_methods:
        print(f"❌ 未找到有效的入口方法")
        return

    method_count = len(entry_methods)
    print(f"✅ 发现 {method_count} 个入口方法")

    # 根据接口数量选择追踪策略
    use_optimization = method_count > 3

    for i, entry_method in enumerate(entry_methods, 1):
        print(f"\n--- 方法 {i}/{method_count}: {entry_method.getName()} ---")
        try:
            if i == 1:
                print(f"[策略] 完整追踪链")
                trace_single_method(entry_class, entry_method)
                generate_method_report(entry_class, entry_method, full_report=True)
            else:
                print(f"[策略] 简化追踪链 (接口数量较多优化)")
                trace_single_method(entry_class, entry_method, simplified=True)
                generate_method_report(entry_class, entry_method, full_report=False)
        except Exception as e:
            print(f"❌ 追踪失败: {entry_method.getName()} - {str(e)}")
            continue

    print(f"\n✅ 所有 {method_count} 个方法追踪完成")
    generate_all_methods_index(entry_class, entry_methods)
```

---

## 输出文件命名策略

### 单个方法报告

```
{项目名}_audit/route_tracer/{项目名}_trace_{method_name}_{时间戳}.md

示例:
myproject_audit/route_tracer/myproject_trace_getBasicQuery_20260204.md
myproject_audit/route_tracer/myproject_trace_getAdvancedQuery_20260204.md
myproject_audit/route_tracer/myproject_trace_getDetailQuery_20260204.md
```

### 总索引报告

**文件名**: `{项目名}_audit/route_tracer/{项目名}_trace_all_methods_{时间戳}.md`

**内容示例**:

```markdown
# /api/ws/userQuery Web Service 所有方法追踪索引

生成时间: 2026-02-04

## 方法清单（共10个）

| 方法名 | 参数列表 | 文件位置 |
|:-------|:---------|:---------|
| getBasicQuery | searchJson, pageJson, extend | [myproject_trace_getBasicQuery_20260204.md](myproject_trace_getBasicQuery_20260204.md) |
| getAdvancedQuery | searchJson, pageJson, extend | [myproject_trace_getAdvancedQuery_20260204.md](myproject_trace_getAdvancedQuery_20260204.md) |
| getDetailQuery | searchJson, pageJson, extend | [myproject_trace_getDetailQuery_20260204.md](myproject_trace_getDetailQuery_20260204.md) |
| getStatisticsQuery | searchJson, pageJson, extend | [myproject_trace_getStatisticsQuery_20260204.md](myproject_trace_getStatisticsQuery_20260204.md) |
| getExportQuery | searchJson, pageJson, extend | [myproject_trace_getExportQuery_20260204.md](myproject_trace_getExportQuery_20260204.md) |
| getReportQuery | searchJson, pageJson, extend | [myproject_trace_getReportQuery_20260204.md](myproject_trace_getReportQuery_20260204.md) |
| ... 更多方法 ... |
```

---

## 参数结构检查优化

对于参数结构相同的方法，可以采用通用模式检查：

```markdown
---

## 方法参数结构检查（通用）

**所有37个方法都采用相同的参数结构**:

| 参数名 | 类型 | 说明 |
|:-------|:-----|:-----|
| searchJson | String | 查询条件JSON (反序列化为 XXXQueryBean) |
| pageJson | String | 分页参数JSON (Page<XXX>类型) |
| extend | String | 扩展参数 |

### 参数流向追踪（通用模式）

```
HTTP SOAP Body → searchJson → 反序列化为 QueryBean
                                    ↓
                    [业务处理逻辑层]
                                    ↓
            → 拼接到 SQL 或 执行其他敏感操作
```

---

## 参数验证逻辑检查（通用）

所有方法都调用 `WebServiceUtil.valiatePam()` 进行参数验证：

```java
if ("error".equals(extend)) {
    json = WebServiceUtil.valiatePam(...);
}
```
```

---

## 报告生成优化

### 方法报告生成策略（支持完整/简化版）

```python
def generate_method_report(entry_class, entry_method, full_report=True):
    if full_report:
        report_content = generate_full_report(entry_class, entry_method)
    else:
        report_content = generate_simplified_report(entry_class, entry_method)

    report_filename = f"{get_project_name()}_trace_{entry_method.getName()}_{get_timestamp()}.md"
    write_to_file(report_filename, report_content)
    print(f"[报告] {'完整' if full_report else '简化'}版已生成: {report_filename}")

def generate_full_report(entry_class, entry_method):
    report_content = f"# {entry_method.getName()} 调用链追踪报告\n\n"
    report_content += f"**方法签名**: {entry_method.getName()}{format_parameter_types(entry_method)}\n"
    report_content += f"**文件位置**: {entry_class.getName()}:{entry_method.getLineNumber()}\n"

    # 收集完整追踪数据
    call_chain = trace_single_method(entry_class, entry_method, simplified=False)
    for level, method_call in enumerate(call_chain, 1):
        report_content += format_level_content(level, method_call, full=True)

    return report_content

def generate_simplified_report(entry_class, entry_method):
    report_content = f"# {entry_method.getName()} 调用链追踪报告（简化版）\n\n"
    report_content += f"**方法签名**: {entry_method.getName()}{format_parameter_types(entry_method)}\n"
    report_content += f"**文件位置**: {entry_class.getName()}:{entry_method.getLineNumber()}\n"
    report_content += f"**报告类型**: 简化版（接口数量较多优化）\n\n"

    # 收集简化追踪数据
    call_chain = trace_single_method(entry_class, entry_method, simplified=True)
    for level, method_call in enumerate(call_chain, 1):
        report_content += format_level_content(level, method_call, full=False)

    return report_content

def format_level_content(level, method_call, full=True):
    content = f"### [Level {level}] {method_call['class']}.{method_call['method']()}\n"
    content += f"**文件**: `{method_call['file']}`\n"

    if full:
        content += f"**完整代码**:\n```java\n{method_call['code']}\n```\n"
        content += f"**分支判定**:\n{format_branch_analysis(method_call['branches'])}\n"
    else:
        content += f"**调用关系**: {method_call['description']}\n"

    content += "\n---\n"
    return content
```

---

## 常见问题处理

### 1. 超类继承的方法

对于继承自超类的方法，需要检查超类的注解信息：

```python
def find_inherited_methods(entry_class):
    inherited_methods = []
    current_class = entry_class

    while current_class != object:
        for method in current_class.getMethods():
            if method.getDeclaringClass() != entry_class:
                if is_entry_method(method):
                    inherited_methods.append(method)
        current_class = current_class.getSuperclass()

    return inherited_methods
```

### 2. 接口默认方法

对于 Java 8+ 的接口默认方法，需要特殊处理：

```python
def find_interface_default_methods(entry_class):
    default_methods = []

    for iface in entry_class.getInterfaces():
        for method in iface.getMethods():
            if has_annotation(method, "Default"):
                default_methods.append(method)

    return default_methods
```

---

## 性能优化

### 1. 并发执行追踪

```python
from concurrent.futures import ThreadPoolExecutor

def audit_route_parallel(entry_class, route_path):
    entry_methods = find_all_entry_methods(entry_class)

    with ThreadPoolExecutor(max_workers=min(len(entry_methods), 4)) as executor:
        futures = []
        for entry_method in entry_methods:
            future = executor.submit(audit_single_method, entry_class, entry_method)
            futures.append(future)

        for future in futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"审计失败: {e}")
```

### 2. 结果缓存

```python
import hashlib
import os

def get_report_cache_key(entry_class, entry_method):
    method_signature = f"{entry_class.getName()}:{entry_method.getName()}"
    return hashlib.md5(method_signature.encode()).hexdigest()

def get_cached_report(cache_key):
    cache_dir = "cache/reports"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    cache_file = os.path.join(cache_dir, f"{cache_key}.md")
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def save_report_to_cache(cache_key, content):
    cache_dir = "cache/reports"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    cache_file = os.path.join(cache_dir, f"{cache_key}.md")
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(content)
```

---

## 工具集成

### 与 java-route-mapper 的配合

```python
# 使用 java-route-mapper 提取接口信息
def extract_interface_info(project_path):
    route_map = run_java_route_mapper(project_path)

    interface_info = []
    for route in route_map:
        class_info = find_class_by_route(route)
        if class_info:
            interface_info.append({
                "route": route,
                "class": class_info["class"],
                "methods": find_all_entry_methods(class_info["class"])
            })

    return interface_info

def run_java_route_mapper(project_path):
    # 调用 java-route-mapper 提取路由信息
    result = subprocess.run(
        ["java-route-mapper", project_path],
        capture_output=True,
        text=True,
        check=True
    )

    return parse_route_mapper_output(result.stdout)
```
