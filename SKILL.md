---
name: teamgent-ops
description: 通过随 Skill 提供的通用 CLI 操作任意 Teamgent 部署：配置服务地址，获取并安全保存浏览器登录 session，查看 Workspace、Project、Agent、对话、Run 和 Runtime，发送任务，新建对话，读取事件，取消或重排任务，以及排查 Agent、Run 或 Runtime 异常。用户提到 Teamgent、teamgentctl、Teamgent Agent/Worker/Runtime、对话日志、任务状态或 Teamgent 登录时使用。
---

# Teamgent CLI

使用随 Skill 提供的 `scripts/teamgentctl.py` 调用 Teamgent HTTP API。不要假设
Skill 安装在固定用户目录；从当前 `SKILL.md` 所在目录解析脚本路径：

```bash
python3 <skill-dir>/scripts/teamgentctl.py --help
```

## 安全

- 不回显或记录 `teamgent_session`、pairing token 等凭证。
- 不把凭证放入命令参数、配置文件、日志、Issue 或 Git。
- 修改 Runtime 绑定、取消任务或重新排队前，先读取当前状态。
- 写接口必须使用已确认的 Teamgent 路由和请求体；不猜测 API。

## 配置部署

首次使用先保存部署地址。URL、Workspace、Project 和 `tg-daemon` 路径均由用户
配置，不使用机器专属默认值：

```bash
python3 <skill-dir>/scripts/teamgentctl.py configure \
  --url <teamgent_url> \
  --workspace <workspace_id> \
  --project <project_id>
```

只有 `--url` 是首次登录必需项；其余值可在登录后查询再补充。配置优先级为
命令参数、环境变量、配置文件。支持：

- `TEAMGENT_URL`
- `TEAMGENT_WORKSPACE`
- `TEAMGENT_PROJECT`
- `TG_DAEMON`
- `TEAMGENT_CONFIG_DIR`

## 登录（持久鉴权）

**`login` 子命令是一次性操作**：粘贴一次 cookie 后，CLI 会自动验证并把 session
保存到系统凭据存储；之后所有命令自动读取，**不需要再次粘贴**。

`teamgent_session` 是 Teamgent 登录后设置的 HttpOnly cookie，不能通过
`document.cookie` 读取。按以下步骤获取并完成持久登录：

1. 打开 `<teamgent_url>/login` 并完成部署提供的网页登录流程。
2. 打开浏览器开发者工具。
3. Chrome/Edge：进入 **Application** -> **Storage** -> **Cookies**。
4. Firefox：进入 **Storage** -> **Cookies**。
5. Safari：进入 **Develop** -> **Show Web Inspector** -> **Storage** ->
   **Cookies**。
6. 选择 Teamgent 域名，找到 `teamgent_session`，复制它的 **Value**。
7. 执行登录并在隐藏输入框粘贴 Value：

```bash
python3 <skill-dir>/scripts/teamgentctl.py login
```

CLI 会先调用 `GET /api/v1/me` 验证凭证，再按下表优先级保存：

| 优先级 | 后端 | 适用 |
| --- | --- | --- |
| 1 | **macOS Keychain**（service `teamgentctl`） | macOS 桌面（推荐） |
| 2 | **Linux Secret Service**（`secret-tool`） | Linux 桌面（推荐） |
| 3 | **本地文件**（权限 `0600`，明确告警） | 无 keyring 的服务器 / 容器 |

成功后所有命令（`me`、`workspaces`、`agents`、`runs`、`send` 等）自动从凭据
存储读取，无需再粘贴 cookie。

### 重新登录 / 切换账号

返回 401、cookie 过期或想换账号时，重跑 `login` 即可（会覆盖旧条目）。需要清掉
当前账号的本地凭据时：

```bash
python3 <skill-dir>/scripts/teamgentctl.py logout
```

`logout` 只删除当前部署的本地凭据，不影响浏览器侧登录状态。

### 临时覆盖（不写入磁盘）

CI、临时容器或不想落盘的场景，直接设置 `TEAMGENT_SESSION` 环境变量，所有命令
会优先用它的值（**不写文件、不进 keychain**）：

```bash
TEAMGENT_SESSION=<cookie_value> python3 <skill-dir>/scripts/teamgentctl.py me
```

### 验证持久化是否生效

```bash
python3 <skill-dir>/scripts/teamgentctl.py me
```

不需要带任何环境变量。返回 `401` 表示凭据未找到或已过期，重新执行 `login`。

### 排查"明明 login 成功却还要重粘"

确认 `login` 报告的"session 已保存到 ..."是 **macOS Keychain / Secret Service**，
而不是"权限为 0600 的凭据文件"。如果是文件降级，检查：

- macOS：系统设置 -> 钥匙串访问 -> 搜索 `teamgentctl`，确认条目存在且未被锁定。
- Linux：安装 `libsecret-1-0` / `gnome-keyring` / `KeePassXC` 等能提供 Secret
  Service D-Bus 接口的服务，并确保用户会话中它在运行。

## 查询平台

```bash
python3 <skill-dir>/scripts/teamgentctl.py workspaces
python3 <skill-dir>/scripts/teamgentctl.py projects [workspace_id]
python3 <skill-dir>/scripts/teamgentctl.py agents [project_id]
python3 <skill-dir>/scripts/teamgentctl.py chats [project_id]
python3 <skill-dir>/scripts/teamgentctl.py runtimes [workspace_id]
```

从 `workspaces`、`projects` 的结果取得默认 ID 后，可再次运行 `configure` 保存。

## 对话和任务

```bash
python3 <skill-dir>/scripts/teamgentctl.py new-chat '<title>' --agent-id <project_agent_id>
python3 <skill-dir>/scripts/teamgentctl.py send <conversation_id> '<message>'
python3 <skill-dir>/scripts/teamgentctl.py timeline <conversation_id>
python3 <skill-dir>/scripts/teamgentctl.py runs --status queued,running
python3 <skill-dir>/scripts/teamgentctl.py run <run_id>
python3 <skill-dir>/scripts/teamgentctl.py events <run_id>
```

排障时依次读取 `run`、`events`、`daemon-status` 和 `daemon-logs`。确认任务确实
异常后再执行：

```bash
python3 <skill-dir>/scripts/teamgentctl.py cancel <run_id> --reason '<reason>'
python3 <skill-dir>/scripts/teamgentctl.py requeue <run_id> --reason '<reason>'
python3 <skill-dir>/scripts/teamgentctl.py cancel-all <conversation_id> --reason '<reason>'
```

## Runtime

`tg-daemon` 必须位于 `PATH`，或通过 `TG_DAEMON`/`configure --tg-daemon` 指定。
首次连接所需的一次性 pairing token 从目标 Teamgent 部署的 Runtime 页面获取：

```bash
tg-daemon connect --url <teamgent_url> --token '<pairing_token>' -b
python3 <skill-dir>/scripts/teamgentctl.py daemon-status
python3 <skill-dir>/scripts/teamgentctl.py daemon-logs
python3 <skill-dir>/scripts/teamgentctl.py bind-runtime <project_agent_id> <runtime_id>
```

## 任意 API

仅在现有子命令不覆盖目标接口、且已从 Teamgent API 文档或源码确认路由和请求体
时使用：

```bash
python3 <skill-dir>/scripts/teamgentctl.py api GET '/api/v1/...'
python3 <skill-dir>/scripts/teamgentctl.py api POST '/api/v1/...' '{"key":"value"}'
```

## 创建 Project Agent

`agents` 子命令**只支持 list**，创建 Project Agent 必须走 `api POST` escape hatch。
以下是已确认可用的 schema（来自 Teamgent 后端 `routes.go` 的 `createAgent`）：

```bash
python3 <skill-dir>/scripts/teamgentctl.py api POST \
  "/api/v1/workspaces/<workspace_id>/projects/<project_id>/agents" \
  '{
    "name": "<agent_name>",
    "connector_type": "agent_daemon",
    "default_model_id": "<model_uuid>",
    "system_prompt": "<可选>",
    "description": "<可选>",
    "visibility": "workspace",
    "config": {
      "agent_kind": "codex",
      "daemon_mode": "local",
      "device_id": "<runtime_uuid>",
      "work_dir": "/root/workspace/"
    }
  }'
```

### 必填与陷阱

| 字段 | 是否必填 | 说明 |
| --- | --- | --- |
| `name` | **必填** | 缺则 `400: name and connector_type are required` |
| `connector_type` | **必填** | 当前常用 `agent_daemon` |
| `default_model_id` | 可选 | 注意是 `default_model_id`，**不是** `model_id` |
| `Runtime` | **禁传** | 传了直接 `422: runtime is no longer accepted; use config.daemon_mode, config.device_id, and config.agent_kind for agent_daemon agents` |
| `config.daemon_mode` | 必填 | `local` = 用开发机 tg-daemon；`sandbox` = server 自动 Acquire |
| `config.device_id` | local 必填 | **同时也是 `runtime.id`**；server 收到 `daemon_mode=local` 后会自动 mirror 到 `project_agents.runtime_id` |
| `config.agent_kind` | 必填 | `codex` / `claude_code` / `opencode` —— 必须和 model 的 provider 类型匹配 |
| `config.work_dir` | 可选 | local daemon 上的工作目录 |
| `slug` | 留空 | server 自动生成 `agent-<8hex>` |

### 路径陷阱：POST 比 GET 多一层 workspace

- `GET /api/v1/projects/<project_id>/agents` — 列表，200
- `POST /api/v1/projects/<project_id>/agents` — 405（不允许）
- `POST /api/v1/workspaces/<workspace_id>/projects/<project_id>/agents` — 201（创建）

如果只记住了 GET 路径去 POST，会拿到 405 而非 404，需要切到完整路径。

### server 会丢弃的 config 字段

POST 后 server 只保留它 schema 关心的 config 字段。即使 payload 里写了
`model_id` / `profile.model_id` / `profile.skills` / `profile.capabilities`，
这些**不会**被持久化；server 用的是 `default_model_id`（顶层）和 `config.agent_kind`。
要修改 model 或绑定 skill，走 `PATCH` 路由（见 Teamgent 后端 `updateAgent`）。

### 失败排查

| 响应 | 原因 | 处理 |
| --- | --- | --- |
| `400: name and connector_type are required` | 缺 name 或 connector_type | 补字段 |
| `405 Method Not Allowed` | 用了 GET 路径 | 切到 `/api/v1/workspaces/<ws>/projects/<p>/agents` |
| `422: runtime is no longer accepted` | payload 顶层有 `runtime` 字段 | 删掉，移到 `config.daemon_mode` + `config.device_id` |
| `422: visibility/binding inconsistent` | `visibility=public` 时带了个人凭证 | 改 `visibility=workspace` 或移除个人 credential |
| `401: unauthenticated` | cookie 失效 | 重跑 `login` |
