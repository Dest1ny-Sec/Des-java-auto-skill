#!/usr/bin/env python3
"""
Java 组件漏洞扫描器
支持 pom.xml, build.gradle, jar 文件的依赖提取和漏洞检测
支持按目录层级分组输出
"""

import re
import os
import sys
import json
import zipfile
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# --- 依赖检测 ---
MISSING_DEPS = []
try:
    import yaml
except ImportError:
    MISSING_DEPS.append("PyYAML")

if MISSING_DEPS:
    print("[ERROR] 缺少 Python 依赖，请运行以下命令安装：", file=sys.stderr)
    print(f"  pip3 install {' '.join(MISSING_DEPS)}", file=sys.stderr)
    print("", file=sys.stderr)
    print("如果使用 requirements.txt: pip3 install -r requirements.txt", file=sys.stderr)
    sys.exit(1)
# --- 依赖检测结束 ---


@dataclass
class Dependency:
    """依赖信息"""
    group_id: str
    artifact_id: str
    version: str
    source: str
    module: str = ""  # 所属模块路径

    @property
    def coordinate(self) -> str:
        return f"{self.group_id}:{self.artifact_id}:{self.version}"


@dataclass
class Vulnerability:
    """漏洞信息"""
    name: str
    severity: str
    function: str
    description: str
    pattern: str
    matched_dependency: Optional[Dependency] = None


@dataclass
class ModuleResult:
    """单个模块的扫描结果"""
    module_path: str
    dependencies: List[Dependency] = field(default_factory=list)
    vulnerabilities: List[Vulnerability] = field(default_factory=list)

    @property
    def severity_count(self) -> Dict[str, int]:
        count = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for v in self.vulnerabilities:
            count[v.severity] = count.get(v.severity, 0) + 1
        return count


@dataclass
class ScanResult:
    """扫描结果"""
    scan_target: str
    modules: Dict[str, ModuleResult] = field(default_factory=dict)

    @property
    def total_dependencies(self) -> int:
        return sum(len(m.dependencies) for m in self.modules.values())

    @property
    def total_vulnerabilities(self) -> int:
        return sum(len(m.vulnerabilities) for m in self.modules.values())

    @property
    def severity_count(self) -> Dict[str, int]:
        count = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for m in self.modules.values():
            for severity, c in m.severity_count.items():
                count[severity] += c
        return count

    def to_dict(self) -> dict:
        return {
            "scan_target": self.scan_target,
            "total_dependencies": self.total_dependencies,
            "total_vulnerabilities": self.total_vulnerabilities,
            "severity_count": self.severity_count,
            "modules": {
                path: {
                    "dependencies": [
                        {"coordinate": d.coordinate, "source": d.source}
                        for d in m.dependencies
                    ],
                    "vulnerabilities": [
                        {
                            "name": v.name,
                            "severity": v.severity,
                            "affected_component": v.function,
                            "description": v.description,
                            "matched_dependency": v.matched_dependency.coordinate if v.matched_dependency else None
                        }
                        for v in m.vulnerabilities
                    ]
                }
                for path, m in self.modules.items()
            }
        }


def get_module_path(file_path: str, base_path: str, group_depth: int = 2) -> str:
    """
    根据文件路径和基础路径计算模块路径
    group_depth: 分组深度，从基础路径开始计算
    """
    try:
        # 使用 os.path.relpath 确保跨平台兼容（Windows/macOS/Linux）
        rel_path_str = os.path.relpath(file_path, base_path)
        # 统一使用正斜杠分割（兼容 Windows 反斜杠）
        parts = rel_path_str.replace('\\', '/').split('/')

        # 过滤掉可能的空字符串（路径以 / 开头时）
        parts = [p for p in parts if p]

        # 查找 WEB-INF/lib 或类似的标准目录结构
        for i, part in enumerate(parts):
            if part in ('WEB-INF', 'lib', 'libs', 'target', 'build'):
                if i > 0:
                    return str(Path(*parts[:i]))
                else:
                    # i == 0：该目录就在根路径下，使用根目录作为模块
                    return '.'

        # 如果没有找到标准目录，使用指定深度
        if len(parts) > group_depth:
            return str(Path(*parts[:group_depth]))
        elif len(parts) > 1:
            return str(Path(*parts[:-1]))
        else:
            parent = str(Path(rel_path_str).parent)
            return parent if parent and parent != '.' else '.'
    except (ValueError, OSError):
        # 跨驱动器（Windows）或路径在不同卷上，回退到父目录名
        return Path(file_path).parent.name


def extract_from_pom(pom_path: str) -> List[Dependency]:
    """从 pom.xml 提取依赖"""
    dependencies = []
    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()

        ns_prefix = ''
        if root.tag.startswith('{'):
            ns_prefix = root.tag.split('}')[0] + '}'

        properties = {}
        props_elem = root.find(f'{ns_prefix}properties')
        if props_elem is not None:
            for prop in props_elem:
                tag = prop.tag.replace(ns_prefix, '')
                properties[tag] = prop.text or ''

        deps_paths = [
            f'{ns_prefix}dependencies',
            f'{ns_prefix}dependencyManagement/{ns_prefix}dependencies',
        ]

        for deps_path in deps_paths:
            deps_elem = root.find(deps_path)
            if deps_elem is not None:
                for dep in deps_elem.findall(f'{ns_prefix}dependency'):
                    group_id_elem = dep.find(f'{ns_prefix}groupId')
                    artifact_id_elem = dep.find(f'{ns_prefix}artifactId')
                    version_elem = dep.find(f'{ns_prefix}version')

                    group_id = group_id_elem.text if group_id_elem is not None else ''
                    artifact_id = artifact_id_elem.text if artifact_id_elem is not None else ''
                    version = version_elem.text if version_elem is not None else ''

                    if version and version.startswith('${') and version.endswith('}'):
                        var_name = version[2:-1]
                        version = properties.get(var_name, version)

                    if artifact_id and version:
                        dependencies.append(Dependency(
                            group_id=group_id or '',
                            artifact_id=artifact_id,
                            version=version,
                            source=pom_path
                        ))
    except Exception as e:
        print(f"[ERROR] 解析 pom.xml 失败: {e}", file=sys.stderr)

    return dependencies


def extract_from_gradle(gradle_path: str) -> List[Dependency]:
    """从 build.gradle 提取依赖"""
    dependencies = []
    try:
        with open(gradle_path, 'r', encoding='utf-8') as f:
            content = f.read()

        patterns = [
            r"(?:implementation|compile|api|runtimeOnly|testImplementation|compileOnly)\s*['\"]([^:]+):([^:]+):([^'\"]+)['\"]",
            r"(?:implementation|compile|api|runtimeOnly|testImplementation|compileOnly)\s+group:\s*['\"]([^'\"]+)['\"],\s*name:\s*['\"]([^'\"]+)['\"],\s*version:\s*['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                dependencies.append(Dependency(
                    group_id=match[0],
                    artifact_id=match[1],
                    version=match[2],
                    source=gradle_path
                ))
    except Exception as e:
        print(f"[ERROR] 解析 build.gradle 失败: {e}", file=sys.stderr)

    return dependencies


def extract_from_jar(jar_path: str) -> List[Dependency]:
    """从 jar 文件提取依赖信息"""
    dependencies = []
    try:
        # 从文件名提取版本信息
        jar_name = Path(jar_path).stem
        # 匹配常见的 artifact-version 格式
        # 支持: artifact-1.2.3, artifact-1.2.3-RC1, artifact-1.2.3.M1, artifact-1.0 等
        match = re.match(r'^(.+?)-(\d+(?:\.\d+)*(?:[.\-]?(?:RC|M|beta|alpha|pre|SNAPSHOT)\d*)?(?:[.\-]?\d+)*)$', jar_name)
        if match:
            dependencies.append(Dependency(
                group_id='',
                artifact_id=match.group(1),
                version=match.group(2),
                source=jar_path
            ))
            return dependencies

        # 尝试从 jar 内部提取
        with zipfile.ZipFile(jar_path, 'r') as jar:
            for name in jar.namelist():
                if name.endswith('pom.properties'):
                    with jar.open(name) as f:
                        props = {}
                        for line in f.read().decode('utf-8').splitlines():
                            if '=' in line and not line.startswith('#'):
                                key, value = line.split('=', 1)
                                props[key.strip()] = value.strip()

                        if 'artifactId' in props and 'version' in props:
                            dependencies.append(Dependency(
                                group_id=props.get('groupId', ''),
                                artifact_id=props['artifactId'],
                                version=props['version'],
                                source=jar_path
                            ))
                            return dependencies

            if 'META-INF/MANIFEST.MF' in jar.namelist():
                with jar.open('META-INF/MANIFEST.MF') as f:
                    manifest = f.read().decode('utf-8')
                    impl_title = re.search(r'Implementation-Title:\s*([^\n]+)', manifest)
                    impl_version = re.search(r'Implementation-Version:\s*([^\n]+)', manifest)

                    if impl_title and impl_version:
                        dependencies.append(Dependency(
                            group_id='',
                            artifact_id=impl_title.group(1).strip(),
                            version=impl_version.group(1).strip(),
                            source=jar_path
                        ))
    except Exception as e:
        print(f"[WARN] 解析 jar 文件失败 {jar_path}: {e}", file=sys.stderr)

    return dependencies


def load_rules(rules_path: str) -> Dict:
    """加载漏洞规则"""
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[ERROR] 加载规则文件失败: {e}", file=sys.stderr)
        return {'rules': {}}


def scan_vulnerabilities(dependencies: List[Dependency], rules: Dict) -> List[Vulnerability]:
    """扫描依赖中的漏洞"""
    vulnerabilities = []
    rules_data = rules.get('rules', {})

    for severity, rule_list in rules_data.items():
        if not isinstance(rule_list, list):
            continue

        for rule in rule_list:
            pattern = rule.get('pattern', '')
            if not pattern:
                continue

            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error:
                continue

            for dep in dependencies:
                check_str = f"{dep.artifact_id}:{dep.version}"
                if regex.search(check_str):
                    vuln = Vulnerability(
                        name=rule.get('name', 'Unknown'),
                        severity=severity,
                        function=rule.get('function', ''),
                        description=rule.get('description', ''),
                        pattern=pattern,
                        matched_dependency=dep
                    )
                    vulnerabilities.append(vuln)

    return vulnerabilities


def scan_target(target_path: str, rules_path: str, group_depth: int = 2) -> ScanResult:
    """扫描目标文件或目录，按模块分组"""
    result = ScanResult(scan_target=target_path)
    path = Path(target_path)
    rules = load_rules(rules_path)

    # 按模块收集依赖
    module_deps: Dict[str, List[Dependency]] = defaultdict(list)

    if path.is_file():
        module = '.'
        deps = []
        if path.name == 'pom.xml' or path.name.endswith('pom.xml'):
            deps = extract_from_pom(str(path))
        elif path.name.endswith('.gradle'):
            deps = extract_from_gradle(str(path))
        elif path.suffix == '.jar':
            deps = extract_from_jar(str(path))

        for dep in deps:
            dep.module = module
        module_deps[module] = deps

    elif path.is_dir():
        base_path = str(path)

        # 扫描 pom.xml
        for pom in path.rglob('pom.xml'):
            module = get_module_path(str(pom), base_path, group_depth)
            deps = extract_from_pom(str(pom))
            for dep in deps:
                dep.module = module
            module_deps[module].extend(deps)

        # 扫描 build.gradle
        for gradle in path.rglob('*.gradle'):
            module = get_module_path(str(gradle), base_path, group_depth)
            deps = extract_from_gradle(str(gradle))
            for dep in deps:
                dep.module = module
            module_deps[module].extend(deps)

        # 扫描 jar 文件
        for jar in path.rglob('*.jar'):
            module = get_module_path(str(jar), base_path, group_depth)
            deps = extract_from_jar(str(jar))
            for dep in deps:
                dep.module = module
            module_deps[module].extend(deps)

    # 为每个模块扫描漏洞
    for module, deps in module_deps.items():
        if deps:
            vulns = scan_vulnerabilities(deps, rules)
            result.modules[module] = ModuleResult(
                module_path=module,
                dependencies=deps,
                vulnerabilities=vulns
            )

    return result


def get_relative_source(source: str, scan_target: str) -> str:
    """将文件路径转换为相对于扫描目标的路径（跨平台兼容）"""
    try:
        source_path = os.path.abspath(source)
        target_path = os.path.abspath(scan_target)
        if os.path.isfile(target_path):
            target_path = os.path.dirname(target_path)
        rel_path = os.path.relpath(source_path, target_path)
        # 统一使用正斜杠
        return rel_path.replace('\\', '/')
    except (ValueError, OSError):
        # 无法计算相对路径（如跨驱动器），返回文件名
        return os.path.basename(source)


def format_markdown_report(result: ScanResult, show_deps: bool = True) -> str:
    """生成按模块分组的 Markdown 格式报告"""
    lines = [
        f"# Java 组件漏洞扫描报告",
        f"",
        f"**扫描目标**: `{result.scan_target}`",
        f"",
        f"## 扫描概览",
        f"",
        f"| 指标 | 数量 |",
        f"|------|------|",
        f"| 模块数量 | {len(result.modules)} |",
        f"| 依赖总数 | {result.total_dependencies} |",
        f"| 漏洞总数 | {result.total_vulnerabilities} |",
    ]

    severity_count = result.severity_count
    lines.extend([
        f"| 🔴 严重 (Critical) | {severity_count['critical']} |",
        f"| 🟠 高危 (High) | {severity_count['high']} |",
        f"| 🟡 中危 (Medium) | {severity_count['medium']} |",
        f"| 🔵 低危 (Low) | {severity_count['low']} |",
        f"",
    ])

    # 模块风险摘要
    if len(result.modules) > 1:
        lines.append("## 模块风险摘要")
        lines.append("")
        lines.append("| 模块 | 依赖数 | 严重 | 高危 | 中危 | 低危 | 总漏洞 |")
        lines.append("|------|--------|------|------|------|------|--------|")

        # 按漏洞数量排序
        sorted_modules = sorted(
            result.modules.items(),
            key=lambda x: (x[1].severity_count['critical'], x[1].severity_count['high'], len(x[1].vulnerabilities)),
            reverse=True
        )

        for module_path, module in sorted_modules:
            sc = module.severity_count
            total_vulns = len(module.vulnerabilities)
            lines.append(
                f"| `{module_path}` | {len(module.dependencies)} | "
                f"{sc['critical']} | {sc['high']} | {sc['medium']} | {sc['low']} | {total_vulns} |"
            )
        lines.append("")

    # 按模块输出详细漏洞信息
    if result.total_vulnerabilities > 0:
        lines.append("## 漏洞详情（按模块分组）")
        lines.append("")

        # 按严重程度排序模块
        sorted_modules = sorted(
            result.modules.items(),
            key=lambda x: (x[1].severity_count['critical'], x[1].severity_count['high']),
            reverse=True
        )

        for module_path, module in sorted_modules:
            if not module.vulnerabilities:
                continue

            lines.append(f"### 📁 {module_path}")
            lines.append("")

            # 按严重级别分组漏洞
            for severity in ['critical', 'high', 'medium', 'low']:
                vulns = [v for v in module.vulnerabilities if v.severity == severity]
                if not vulns:
                    continue

                severity_label = {
                    'critical': '🔴 严重',
                    'high': '🟠 高危',
                    'medium': '🟡 中危',
                    'low': '🔵 低危'
                }[severity]

                lines.append(f"#### {severity_label}")
                lines.append("")
                lines.append("| 组件 | 版本 | 来源文件 | 漏洞名称 | 描述 |")
                lines.append("|------|------|----------|----------|------|")

                # 去重显示
                seen = set()
                for v in vulns:
                    if v.matched_dependency:
                        key = (v.matched_dependency.artifact_id, v.matched_dependency.version, v.name)
                        if key in seen:
                            continue
                        seen.add(key)
                        desc = v.description
                        source_file = get_relative_source(v.matched_dependency.source, result.scan_target)
                        lines.append(
                            f"| {v.matched_dependency.artifact_id} | {v.matched_dependency.version} | "
                            f"{source_file} | {v.name} | {desc} |"
                        )
                lines.append("")

    else:
        lines.append("## 扫描结果")
        lines.append("")
        lines.append("✅ 未发现已知漏洞")
        lines.append("")

    # 依赖列表（按模块分组）
    if show_deps and result.total_dependencies > 0:
        lines.append("## 依赖列表（按模块分组）")
        lines.append("")

        for module_path, module in sorted(result.modules.items()):
            if not module.dependencies:
                continue

            lines.append(f"### 📁 {module_path}")
            lines.append("")
            lines.append("| 组件 | 版本 |")
            lines.append("|------|------|")

            # 去重并排序
            seen = set()
            for dep in sorted(module.dependencies, key=lambda x: x.artifact_id):
                key = (dep.artifact_id, dep.version)
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"| {dep.artifact_id} | {dep.version} |")

            lines.append("")

    return "\n".join(lines)


def get_output_path(target_path: str, ext: str = 'md') -> Tuple[str, str]:
    """
    根据扫描目标生成输出目录和文件路径
    返回: (输出目录, 输出文件路径)
    格式: {项目名}_audit/vuln_report/{项目名}_vuln_report_{timestamp}.{ext}
    """
    from datetime import datetime

    target_abs = os.path.abspath(target_path)

    # 获取项目名称
    if os.path.isfile(target_abs):
        project_name = os.path.basename(os.path.dirname(target_abs))
    else:
        project_name = os.path.basename(target_abs)

    # 清理项目名称（移除特殊字符）
    project_name = re.sub(r'[^\w\u4e00-\u9fff-]', '_', project_name)

    # 生成输出目录名: {项目名}_audit/vuln_report/
    output_dir = os.path.join(f"{project_name}_audit", "vuln_report")

    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{project_name}_vuln_report_{timestamp}.{ext}"

    return output_dir, os.path.join(output_dir, filename)


def main():
    parser = argparse.ArgumentParser(description='Java 组件漏洞扫描器（支持按模块分组）')
    parser.add_argument('target', help='扫描目标 (pom.xml, build.gradle, jar文件或目录)')
    parser.add_argument('--rules', '-r', required=True, help='漏洞规则文件路径')
    parser.add_argument('--format', '-f', choices=['json', 'markdown'], default='markdown', help='输出格式')
    parser.add_argument('--output', '-o', help='输出文件路径（不指定则自动生成到 {项目名}_vuln_scanner/ 目录）')
    parser.add_argument('--depth', '-d', type=int, default=2, help='模块分组深度 (默认: 2)')
    parser.add_argument('--no-deps', action='store_true', help='不显示依赖列表')
    parser.add_argument('--no-save', action='store_true', help='不保存文件，仅输出到终端')

    args = parser.parse_args()

    if not os.path.exists(args.target):
        print(f"[ERROR] 目标不存在: {args.target}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.rules):
        print(f"[ERROR] 规则文件不存在: {args.rules}", file=sys.stderr)
        sys.exit(1)

    result = scan_target(args.target, args.rules, args.depth)

    # 生成报告内容
    ext = 'json' if args.format == 'json' else 'md'
    if args.format == 'json':
        output = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    else:
        output = format_markdown_report(result, show_deps=not args.no_deps)

    # 确定输出路径
    if args.no_save:
        # 仅输出到终端
        print(output)
    elif args.output:
        # 使用用户指定的路径
        output_path = args.output
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"[INFO] 报告已保存到: {output_path}")
    else:
        # 自动生成到 {项目名}_vuln_scanner/ 目录
        output_dir, output_path = get_output_path(args.target, ext)

        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"[INFO] 创建输出目录: {output_dir}")

        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)

        print(f"[INFO] 报告已保存到: {output_path}")

        # 打印摘要信息
        print(f"\n📊 扫描摘要:")
        print(f"   模块数量: {len(result.modules)}")
        print(f"   依赖总数: {result.total_dependencies}")
        print(f"   漏洞总数: {result.total_vulnerabilities}")
        sc = result.severity_count
        if sc['critical'] > 0:
            print(f"   🔴 严重: {sc['critical']}")
        if sc['high'] > 0:
            print(f"   🟠 高危: {sc['high']}")
        if sc['medium'] > 0:
            print(f"   🟡 中危: {sc['medium']}")
        if sc['low'] > 0:
            print(f"   🔵 低危: {sc['low']}")


if __name__ == '__main__':
    main()
