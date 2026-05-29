#!/usr/bin/env python3
"""
OSV.dev 批量漏洞查询脚本
从项目依赖中提取包名和版本，批量查询 OSV.dev API 获取已知漏洞。
支持在线查询和离线本地数据库两种模式。

跨平台兼容: Windows / macOS / Linux
"""
import json
import argparse
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# --- 依赖检测 ---
MISSING_DEPS = []
try:
    import requests
except ImportError:
    MISSING_DEPS.append("requests")

if MISSING_DEPS:
    print("[ERROR] 缺少 Python 依赖，请运行以下命令安装：", file=sys.stderr)
    print(f"  pip3 install {' '.join(MISSING_DEPS)}", file=sys.stderr)
    print("", file=sys.stderr)
    print("如果使用 requirements.txt: pip3 install -r requirements.txt", file=sys.stderr)
    sys.exit(1)
# --- 依赖检测结束 ---

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns"
BATCH_SIZE = 1000
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30


def extract_deps_from_pom(pom_path):
    """从 pom.xml 提取依赖列表"""
    deps = []
    ns = {"mvn": "http://maven.apache.org/POM/4.0.0"}
    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
        for dep in root.findall(".//mvn:dependency", ns):
            gid = dep.find("mvn:groupId", ns)
            aid = dep.find("mvn:artifactId", ns)
            ver = dep.find("mvn:version", ns)
            if gid is not None and aid is not None and ver is not None:
                ver_text = ver.text
                if ver_text and not ver_text.startswith("$"):
                    deps.append(f"{gid.text}:{aid.text}:{ver_text}")
    except ET.ParseError:
        pass
    return deps


def read_deps_file(filepath):
    """读取依赖文件"""
    deps = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split(":")
                if len(parts) >= 3:
                    deps.append(line)
    return deps


def build_queries(deps):
    """构建 batch query 请求体"""
    queries = []
    for dep in deps:
        parts = dep.split(":")
        if len(parts) >= 3:
            gav = f"{parts[0]}:{parts[1]}"
            ver = parts[2]
            queries.append({
                "package": {"name": gav, "ecosystem": "Maven"},
                "version": ver
            })
    return queries


def query_batch(queries):
    """批量查询 OSV API（含重试逻辑）"""
    results = []
    for i in range(0, len(queries), BATCH_SIZE):
        batch = queries[i:i + BATCH_SIZE]
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.post(
                    OSV_BATCH_URL,
                    json={"queries": batch},
                    timeout=REQUEST_TIMEOUT
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "results" in data:
                        results.extend(data["results"])
                    break  # 成功，跳出重试循环
                elif resp.status_code >= 500:
                    if attempt < MAX_RETRIES - 1:
                        print(f"[!] Server error {resp.status_code}, retry {attempt + 2}/{MAX_RETRIES}...", file=sys.stderr)
                        time.sleep(2 ** attempt)
                    else:
                        print(f"[!] Batch query failed after {MAX_RETRIES} attempts: HTTP {resp.status_code}", file=sys.stderr)
                else:
                    print(f"[!] Batch query HTTP {resp.status_code}", file=sys.stderr)
                    break
            except requests.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"[!] Network error (retry {attempt + 2}/{MAX_RETRIES}): {e}", file=sys.stderr)
                    time.sleep(2 ** attempt)
                else:
                    print(f"[!] Batch query error after {MAX_RETRIES} attempts: {e}", file=sys.stderr)
    return results


def get_vuln_details(vuln_ids):
    """获取漏洞详情（CVE 编号、CVSS 分数等），含重试逻辑"""
    details = {}
    for vuln_id in vuln_ids:
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(f"{OSV_VULN_URL}/{vuln_id}", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    cve = None
                    severity = None
                    fixed = None

                    if "aliases" in data:
                        for alias in data["aliases"]:
                            if alias.startswith("CVE-"):
                                cve = alias
                                break

                    if "database_specific" in data:
                        severity = data["database_specific"].get("severity", "UNKNOWN")

                    if "affected" in data:
                        for affected in data["affected"]:
                            if "ranges" in affected:
                                for r in affected["ranges"]:
                                    if r.get("type") == "ECOSYSTEM":
                                        events = r.get("events", [])
                                        for evt in reversed(events):
                                            if "fixed" in evt:
                                                fixed = evt["fixed"]
                                                break

                    details[vuln_id] = {
                        "cve": cve,
                        "summary": data.get("summary", ""),
                        "severity": severity,
                        "fixed_version": fixed,
                        "references": [ref.get("url") for ref in data.get("references", [])[:5]]
                    }
                    break  # 成功获取
                elif resp.status_code >= 500:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                    continue
                else:
                    break
            except requests.RequestException:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                continue
    return details


def merge_results(batch_results, deps):
    """合并 batch 结果与漏洞详情"""
    merged = []
    vuln_ids_to_fetch = set()

    for i, result in enumerate(batch_results):
        vulns = result.get("vulns", [])
        vuln_list = []
        for v in vulns:
            vuln_id = v.get("id")
            if vuln_id:
                vuln_ids_to_fetch.add(vuln_id)
                vuln_list.append(vuln_id)

        merged.append({
            "package": deps[i] if i < len(deps) else "unknown",
            "version": deps[i].split(":")[2] if i < len(deps) and len(deps[i].split(":")) >= 3 else "unknown",
            "vuln_ids": vuln_list
        })

    # 获取详情
    details = get_vuln_details(list(vuln_ids_to_fetch))

    # 填充详情
    for item in merged:
        item["vulns"] = []
        for vid in item["vuln_ids"]:
            d = details.get(vid, {})
            item["vulns"].append({
                "id": vid,
                "cve": d.get("cve", vid),
                "summary": d.get("summary", ""),
                "severity": d.get("severity", "UNKNOWN"),
                "fixed_version": d.get("fixed_version", None),
                "references": d.get("references", [])
            })

    return merged


def main():
    parser = argparse.ArgumentParser(description="OSV.dev vulnerability scanner")
    parser.add_argument("--pom", help="Path to pom.xml")
    parser.add_argument("--deps-file", help="Path to deps file (group:artifact:version per line)")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--offline", action="store_true", help="Offline mode (not implemented)")
    parser.add_argument("--osv-db", help="Path to local OSV database (offline mode)")
    args = parser.parse_args()

    if args.offline:
        print("[!] Offline mode is not yet implemented. Use online mode (default) or download OSV data from https://osv-vulnerabilities.storage.googleapis.com/Maven/all.zip", file=sys.stderr)
        sys.exit(1)

    # 提取依赖
    deps = []
    if args.pom:
        deps = extract_deps_from_pom(args.pom)
    elif args.deps_file:
        deps = read_deps_file(args.deps_file)
    else:
        print("[!] No dependency source specified", file=sys.stderr)
        sys.exit(1)

    if not deps:
        print("[!] No dependencies found", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Found {len(deps)} dependencies, querying OSV.dev...")

    # 查询
    queries = build_queries(deps)
    batch_results = query_batch(queries)
    merged = merge_results(batch_results, deps)

    # 统计
    vulnerable = sum(1 for item in merged if item["vulns"])
    total_vulns = sum(len(item["vulns"]) for item in merged)
    critical = sum(
        1 for item in merged
        for v in item["vulns"]
        if v.get("severity") == "CRITICAL"
    )

    output = {
        "query_time": datetime.now(timezone.utc).isoformat(),
        "total_deps_queried": len(deps),
        "vulnerable_deps": vulnerable,
        "total_vulns": total_vulns,
        "critical_vulns": critical,
        "results": merged
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[*] OSV scan complete: {vulnerable}/{len(deps)} deps vulnerable, "
          f"{total_vulns} vulns ({critical} critical)")
    print(f"[*] Results saved to {args.output}")


if __name__ == "__main__":
    main()
