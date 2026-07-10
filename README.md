# teamgent-cli-skill

[Codex](https://github.com/openai/codex) skill：通过自带的 Python CLI 操作任意 Teamgent 部署，管理 Workspace、Project、Agent、对话、Run 和 Runtime。

CLI 脚本路径解析基于 `SKILL.md` 所在目录，不绑定任何特定部署或机器路径，克隆到任意位置都可直接使用。

## 仓库内容

| 文件 | 说明 |
| --- | --- |
| `SKILL.md` | 给 Codex agent 使用的 skill 元数据与说明 |
| `agents/openai.yaml` | Codex agent 展示配置（display_name、default_prompt 等） |
| `scripts/teamgentctl.py` | 通用 Teamgent CLI，零第三方依赖（仅使用 Python 标准库） |
| `.gitignore` | Python 忽略项 |

## 前置

- Python ≥ 3.10
- 一个可访问的 Teamgent 部署（含有效的登录方式）
- 如需操作本地 Runtime：`tg-daemon` 已在 `PATH` 或通过 `TG_DAEMON` 指定
- 如需 Linux Secret Service：`secret-tool`（可选）

## 快速开始

```bash
# 1. 配置部署地址
python3 scripts/teamgentctl.py configure --url https://your-teamgent.example.com

# 2. 登录并保存 session（按提示粘贴浏览器中的 teamgent_session cookie）
python3 scripts/teamgentctl.py login

# 3. 验证登录
python3 scripts/teamgentctl.py me

# 4. 查询平台资源
python3 scripts/teamgentctl.py workspaces
python3 scripts/teamgentctl.py projects <workspace_id>
python3 scripts/teamgentctl.py agents <project_id>
```

## 命令一览

完整列表运行 `python3 scripts/teamgentctl.py --help`，常用分组：

- **配置 / 登录**：`configure`、`login`、`logout`
- **查询**：`me`、`workspaces`、`projects`、`agents`、`chats`、`runtimes`、`runs`、`run`、`timeline`、`events`
- **写操作**：`new-chat`、`send`、`cancel`、`requeue`、`cancel-all`、`bind-runtime`
- **Runtime**：`daemon-status`、`daemon-logs`、`daemon-stop`
- **逃生口**：`api`（直接调用已确认的 Teamgent 路由，仅在子命令未覆盖时使用）

## 凭证安全

`teamgent_session` 是 HttpOnly cookie，CLI 不会通过命令行参数、配置文件、日志、Issue 或 Git 记录它。`login` 子命令使用隐藏输入读取 cookie，并按以下优先级保存：

1. **macOS Keychain**（`security find-generic-password`，service = `teamgentctl`）
2. **Linux Secret Service**（`secret-tool`）
3. **本地文件降级**（路径由 `TEAMGENT_CREDENTIALS` 或 `TEAMGENT_CONFIG_DIR` 决定，权限强制 `0600`，并明确告警）

CI 或临时环境可直接设置 `TEAMGENT_SESSION` 环境变量，避免落盘。

## 环境变量

| 变量 | 用途 |
| --- | --- |
| `TEAMGENT_URL` | 默认部署 URL |
| `TEAMGENT_WORKSPACE` | 默认 Workspace ID |
| `TEAMGENT_PROJECT` | 默认 Project ID |
| `TEAMGENT_SESSION` | 临时 session（覆盖已保存的凭据） |
| `TG_DAEMON` | `tg-daemon` 二进制路径 |
| `TEAMGENT_CONFIG_DIR` | 配置目录覆盖（默认 `$XDG_CONFIG_HOME/teamgentctl` 或 `~/.config/teamgentctl`） |
| `TEAMGENT_CONFIG` | 配置文件路径覆盖 |
| `TEAMGENT_CREDENTIALS` | 凭据文件路径覆盖 |

## 安装到 Codex skill 目录

把仓库克隆到 Codex 的 skill 加载路径即可，例如：

```bash
git clone https://github.com/kapelame/teamgent-cli-skill.git \
  ~/.codex/skills/teamgent-ops
```

或软链接：

```bash
ln -s /path/to/teamgent-cli-skill ~/.codex/skills/teamgent-ops
```

## 排障

| 现象 | 检查顺序 |
| --- | --- |
| `未找到登录 session` | 先执行 `login`，或临时设 `TEAMGENT_SESSION` |
| `HTTP 401` | session 失效，重新 `login` |
| `无法连接 Teamgent` | `configure --url` 是否正确；网络/DNS 是否通 |
| 找不到 `tg-daemon` | 加进 `PATH`，或 `configure --tg-daemon`，或 `TG_DAEMON` |
| Linux 上没有 keyring | 安装 `secret-tool`（libsecret），否则降级到 0600 凭据文件 |
| API 调用失败 | `api` 子命令仅在子命令未覆盖时使用；先 `GET` 读对象再最小修改 |

## 开发

- 仅依赖 Python 标准库；新增功能前先确认是否真有必要引入第三方依赖。
- 写接口必须基于已确认的 Teamgent 路由和请求体；不允许猜测。
- 修改 `Runtime` 绑定、`cancel`、`requeue` 前应先读取当前状态。
- 本地验证：`python3 scripts/teamgentctl.py --help`、`configure --help`、`me` 等子命令。

## 许可

MIT