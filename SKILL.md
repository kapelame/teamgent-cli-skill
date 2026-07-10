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

## 获取登录 Session

`teamgent_session` 是 Teamgent 登录后设置的 HttpOnly cookie。按以下步骤获取：

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

HttpOnly cookie 不能通过 `document.cookie` 读取。CLI 会先调用 `GET /api/v1/me`
验证凭证，再优先保存到 macOS Keychain 或 Linux Secret Service；两者都不可用时，
保存到权限为 `0600` 的本地凭据文件并明确告警。CI 或临时环境可只设置
`TEAMGENT_SESSION`，避免落盘。

验证登录：

```bash
python3 <skill-dir>/scripts/teamgentctl.py me
```

返回 401 时重新执行 `login`。执行 `logout` 只删除当前部署的本地凭据。

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
