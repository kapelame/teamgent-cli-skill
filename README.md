# teamgent-cli-skill

Vendor-neutral agent skill：通过自带的 Python CLI 操作任意 Teamgent 部署，管理 Workspace、Project、Agent、对话、Run 和 Runtime。`SKILL.md` 的 front matter 兼容主流 agent runtime（Codex CLI、Claude Code、OpenCode 等），克隆到任意位置都可直接加载。

CLI 脚本路径解析基于 `SKILL.md` 所在目录，不绑定任何特定部署或机器路径。

## 仓库内容

| 文件 | 说明 |
| --- | --- |
| `SKILL.md` | Skill 元数据与使用说明（带 front matter） |
| `scripts/teamgentctl.py` | 通用 Teamgent CLI，零第三方依赖（仅使用 Python 标准库） |
| `.gitignore` | Python 忽略项 |

## 前置

- Python ≥ 3.10
- 一个可访问的 Teamgent 部署（含有效的登录方式）
- 如需操作本地 Runtime：`tg-daemon` 已在 `PATH` 或通过 `TG_DAEMON` 指定
- 如需 Linux Secret Service：`secret-tool`（可选）

## 快速开始

```bash
# 1. 配置部署地址（仅首次需要）
python3 scripts/teamgentctl.py configure --url https://your-teamgent.example.com

# 2. 登录 — 粘贴一次 cookie，CLI 自动存到系统凭据存储（keychain / Secret Service / 0600 文件）
python3 scripts/teamgentctl.py login

# 3. 之后所有命令自动读取，**不需要再粘贴**
python3 scripts/teamgentctl.py me
python3 scripts/teamgentctl.py workspaces
python3 scripts/teamgentctl.py projects <workspace_id>
python3 scripts/teamgentctl.py agents <project_id>
```

`login` 是**一次性**操作：粘贴 cookie 后 CLI 先 `GET /api/v1/me` 验证，再写到 macOS Keychain / Linux Secret Service / 0600 文件。之后所有 `me`、`workspaces`、`agents`、`runs`、`send` 等都自动读取，**不再需要粘贴或带环境变量**。

## 命令一览

完整列表运行 `python3 scripts/teamgentctl.py --help`，常用分组：

- **配置 / 登录**：`configure`、`login`、`logout`
- **查询**：`me`、`workspaces`、`projects`、`agents`、`chats`、`runtimes`、`runs`、`run`、`timeline`、`events`
- **写操作**：`new-chat`、`send`、`cancel`、`requeue`、`cancel-all`、`bind-runtime`
- **Runtime**：`daemon-status`、`daemon-logs`、`daemon-stop`
- **逃生口**：`api`（直接调用已确认的 Teamgent 路由，仅在子命令未覆盖时使用）

## 持久鉴权机制

`login` 子命令会按下表优先级自动保存 `teamgent_session`，后续所有命令无需任何环境变量即可鉴权：

| 优先级 | 后端 | 适用 | 验证命令 |
| --- | --- | --- | --- |
| 1 | **macOS Keychain**（service `teamgentctl`） | macOS 桌面（推荐） | `security find-generic-password -s teamgentctl` |
| 2 | **Linux Secret Service**（`secret-tool`） | Linux 桌面（推荐） | `secret-tool lookup service teamgentctl account <url>` |
| 3 | **本地文件降级**（`0600`，明确告警） | 无 keyring 的服务器 / 容器 | `cat $(TEAMGENT_CREDENTIALS 优先) ~/.config/teamgentctl/credentials.json` |

常见操作：

```bash
# 持久登录（粘贴 cookie，自动存到 keychain / secret-tool / 0600 文件）
python3 scripts/teamgentctl.py login

# 验证：返回 401 表示凭据不存在或已过期 → 重跑 login
python3 scripts/teamgentctl.py me

# 重新登录 / 切换账号（覆盖旧条目）
python3 scripts/teamgentctl.py login

# 清掉当前部署的本地凭据（不影响浏览器侧登录）
python3 scripts/teamgentctl.py logout
```

**临时覆盖**（CI / 容器 / 不想落盘）：直接设 `TEAMGENT_SESSION` 环境变量，所有命令优先用它（不会写文件或 keychain）：

```bash
TEAMGENT_SESSION=<cookie_value> python3 scripts/teamgentctl.py me
```

## 安全约束

CLI 不会通过命令行参数、配置文件、日志、Issue 或 Git 记录 cookie。`login` 子命令用隐藏输入（`getpass`）读取；存储强制 `0600`（文件降级路径）；`logout` 只清当前部署的本地凭据。

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

## 安装（加载到 agent runtime）

将仓库克隆或软链接到你的 agent runtime 的 skill 加载目录即可。`SKILL.md` 里的 `name: teamgent-ops` 决定了 skill 的注册名。

常见 agent runtime 的默认加载路径：

| Agent runtime | 默认 skill 目录 |
| --- | --- |
| Codex CLI | `~/.codex/skills/teamgent-ops` |
| Claude Code | `~/.claude/skills/teamgent-ops` |
| OpenCode / OhMyOpenCode | `~/.config/opencode/skills/teamgent-ops` 或项目内 `.opencode/skills/teamgent-ops` |

示例（Codex CLI，其他 runtime 替换路径即可）：

```bash
git clone https://github.com/kapelame/teamgent-cli-skill.git \
  ~/.codex/skills/teamgent-ops
```

或软链接到已存在的克隆：

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