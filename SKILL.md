---
name: teamgent-ops
description: 通过本机 teamgentctl 和 tg-daemon 运维 Teamgent（麦麦 New）：查看 Workspace、Project、Agent、对话和 Run，发送任务，新建对话，读取事件日志，取消或重排任务，连接、检查和绑定本地 Runtime，以及排查 Agent 不响应、任务卡住、Runtime 离线等问题。用户提到 Teamgent、麦麦 New、Octopatch Agent、Teamgent Worker/Runtime、对话日志或 Teamgent 任务状态时使用。
---

# Teamgent 运维

以后使用 Teamgent，不再使用 Stewardhouse。产品 API 通过 `teamgentctl` 操作，本地 Worker 通过 `tg-daemon` 操作。

## 安全

- 不回显 `teamgent_session`、pairing token 或其他凭证。
- 不把凭证写入 Skill、项目文件或命令输出。
- `teamgentctl login` 将登录 session 存入 macOS Keychain。
- 修改 Runtime 绑定、取消任务或重新排队前，先读取当前状态。

## 登录和默认项目

首次使用或返回 401 时执行：

```bash
teamgentctl login
```

交互输入浏览器中的 `teamgent_session`，输入过程不会回显。

默认 Teamgent 地址和 Octopatch 项目已经保存在 `~/.config/teamgentctl/config.json`。若需要重设：

```bash
teamgentctl configure \
  --url https://teamgent.xaminim.com \
  --workspace <workspace_id> \
  --project <project_id>
```

## 查看平台状态

```bash
teamgentctl me
teamgentctl workspaces
teamgentctl projects
teamgentctl agents
teamgentctl runtimes
```

从 `agents` 结果使用 `project_agent_id`，从 `runtimes` 结果使用 Runtime `id`。

## 对话和任务

列出对话并查看完整时间线：

```bash
teamgentctl chats
teamgentctl timeline <conversation_id>
```

创建绑定指定 Agent 的新对话：

```bash
teamgentctl new-chat '<title>' --agent-id <project_agent_id>
```

发送消息会创建 Agent Run，记录返回的 `agent_run_id`：

```bash
teamgentctl send <conversation_id> '<message>'
```

## 查看和处理 Run

```bash
teamgentctl runs
teamgentctl runs --status queued,running
teamgentctl run <run_id>
teamgentctl events <run_id>
```

排障顺序：

1. `run` 查看状态、错误和 Runtime 快照。
2. `events` 查看实际执行轨迹。
3. `daemon-status` 和 `daemon-logs` 确认本地 Runtime 是否收到任务。
4. 确认任务确实卡住后再取消或重排。

```bash
teamgentctl cancel <run_id> --reason '<reason>'
teamgentctl requeue <run_id> --reason '<reason>'
teamgentctl cancel-all <conversation_id> --reason '<reason>'
```

## 本地 Runtime

```bash
teamgentctl daemon-status
teamgentctl daemon-logs
teamgentctl daemon-logs -f
teamgentctl daemon-stop
```

首次连接时，从 Teamgent Runtime 页面取得一次性 pairing token：

```bash
tg-daemon connect \
  --url https://teamgent.xaminim.com \
  --token '<pairing_token>' \
  -b
```

连接成功后绑定 Agent：

```bash
teamgentctl runtimes
teamgentctl bind-runtime <project_agent_id> <runtime_id>
```

## 任意 API

仅在现有子命令不覆盖目标接口、且已从 Teamgent 源码或前端确认路由和请求体时使用：

```bash
teamgentctl api GET '/api/v1/...'
teamgentctl api POST '/api/v1/...' '{"key":"value"}'
```
