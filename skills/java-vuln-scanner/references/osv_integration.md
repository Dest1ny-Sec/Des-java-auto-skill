# OSV.dev API 批量查询脚本

查询 Maven/Gradle 项目依赖的已知漏洞，使用 Google OSV.dev 开源漏洞库。

## 使用方式

```bash
# 从依赖文件查询（支持自定义路径）
python3 {output_path}/scripts/osv_query.py --deps-file {deps_file} --output {output_path}/vuln_report/osv_results.json

# 从 pom.xml 自动提取依赖后查询
python3 {output_path}/scripts/osv_query.py --pom {source_path}/pom.xml --output {output_path}/vuln_report/osv_results.json

# 离线模式（使用本地 OSV 数据）
python3 {output_path}/scripts/osv_query.py --offline --osv-db {osv_db_path} --deps-file {deps_file}
```

## 依赖文件格式

每行一个依赖，格式: `groupId:artifactId:version`

```
org.springframework:spring-core:5.3.20
org.apache.logging.log4j:log4j-core:2.14.1
com.alibaba:fastjson:1.2.24
org.apache.shiro:shiro-core:1.4.0
```

## 输出格式

```json
{
  "query_time": "2026-05-21T12:00:00Z",
  "total_deps_queried": 262,
  "vulnerable_deps": 42,
  "total_vulns": 80,
  "results": [
    {
      "package": "org.apache.logging.log4j:log4j-core",
      "version": "2.14.1",
      "vulns": [
        {
          "id": "GHSA-jfh8-c2jp-5v3q",
          "cve": "CVE-2021-44228",
          "summary": "Remote code injection in Log4j",
          "severity": "CRITICAL",
          "cvss": "10.0",
          "fixed_version": "2.17.1",
          "references": ["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"]
        }
      ]
    }
  ]
}
```
