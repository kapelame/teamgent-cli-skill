#!/usr/bin/env python3
"""Portable Teamgent operations CLI using the product HTTP API."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


COOKIE_NAME = "teamgent_session"
KEYCHAIN_SERVICE = "teamgentctl"


def config_dir() -> Path:
    override = os.environ.get("TEAMGENT_CONFIG_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    return (Path(xdg).expanduser() if xdg else Path.home() / ".config") / "teamgentctl"


def config_path() -> Path:
    override = os.environ.get("TEAMGENT_CONFIG", "").strip()
    return Path(override).expanduser() if override else config_dir() / "config.json"


def credential_path() -> Path:
    override = os.environ.get("TEAMGENT_CREDENTIALS", "").strip()
    return Path(override).expanduser() if override else config_dir() / "credentials.json"


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_private_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def load_config() -> dict:
    value = load_json(config_path(), {})
    return value if isinstance(value, dict) else {}


def save_config(values: dict) -> dict:
    config = load_config()
    config.update({key: value for key, value in values.items() if value not in (None, "")})
    write_private_json(config_path(), config)
    return config


def normalize_url(value: str | None) -> str:
    raw = (value or "").strip().rstrip("/")
    if not raw:
        raise RuntimeError(
            "缺少 Teamgent URL；先执行 configure --url <teamgent_url>，"
            "或设置 TEAMGENT_URL"
        )
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("Teamgent URL 必须是完整的 http(s) URL")
    return raw


def credential_account(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    return parsed.netloc + (parsed.path.rstrip("/") or "")


def browser_origin(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def macos_keychain_available() -> bool:
    return sys.platform == "darwin" and shutil.which("security") is not None


def secret_service_available() -> bool:
    return shutil.which("secret-tool") is not None


def lookup_session(base_url: str) -> str:
    env = os.environ.get("TEAMGENT_SESSION", "").strip()
    if env:
        return env

    account = credential_account(base_url)
    if macos_keychain_available():
        proc = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                account,
                "-w",
            ],
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()

    if secret_service_available():
        proc = subprocess.run(
            ["secret-tool", "lookup", "service", KEYCHAIN_SERVICE, "account", account],
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()

    credentials = load_json(credential_path(), {})
    if isinstance(credentials, dict):
        return str(credentials.get(account, "")).strip()
    return ""


def store_session(base_url: str, value: str) -> str:
    account = credential_account(base_url)
    if macos_keychain_available():
        proc = subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                account,
                "-w",
                value,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode == 0:
            return f"macOS Keychain（service={KEYCHAIN_SERVICE}, account={account}）"

    if secret_service_available():
        proc = subprocess.run(
            [
                "secret-tool",
                "store",
                f"--label=Teamgent session for {account}",
                "service",
                KEYCHAIN_SERVICE,
                "account",
                account,
            ],
            input=value,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode == 0:
            return f"Secret Service（account={account}）"

    path = credential_path()
    credentials = load_json(path, {})
    if not isinstance(credentials, dict):
        credentials = {}
    credentials[account] = value
    write_private_json(path, credentials)
    return f"权限为 0600 的凭据文件 {path}（系统凭据存储不可用）"


def delete_session(base_url: str) -> None:
    account = credential_account(base_url)
    if macos_keychain_available():
        subprocess.run(
            [
                "security",
                "delete-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                account,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if secret_service_available():
        subprocess.run(
            ["secret-tool", "clear", "service", KEYCHAIN_SERVICE, "account", account],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    path = credential_path()
    credentials = load_json(path, {})
    if isinstance(credentials, dict) and account in credentials:
        del credentials[account]
        write_private_json(path, credentials)


def print_login_instructions(base_url: str) -> None:
    origin = browser_origin(base_url)
    print(
        f"""获取 {COOKIE_NAME}：
1. 在浏览器打开 {base_url}/login，完成该部署提供的登录流程。
2. 打开开发者工具并查看 Cookie：
   - Chrome/Edge: Application -> Storage -> Cookies
   - Firefox: Storage -> Cookies
   - Safari: Develop -> Show Web Inspector -> Storage -> Cookies
3. 选择 {origin}，找到 {COOKIE_NAME}，复制 Value。
4. 将 Value 粘贴到下面的隐藏输入框。

该 Cookie 是 HttpOnly，不能用 document.cookie 读取。不要把它写进命令参数、
配置文件、日志、Issue 或 Git。""",
        file=sys.stderr,
    )


class Client:
    def __init__(self, base_url: str, session: str):
        self.base_url = base_url
        self.session = session

    def request(self, method: str, path: str, body=None, query=None):
        if not path.startswith("/"):
            path = "/" + path
        url = self.base_url + path
        if query:
            filtered = {key: value for key, value in query.items() if value not in (None, "")}
            if filtered:
                url += ("&" if "?" in url else "?") + urllib.parse.urlencode(filtered)

        headers = {"Accept": "application/json", "User-Agent": "teamgentctl/1"}
        if self.session:
            headers["Cookie"] = f"{COOKIE_NAME}={self.session}"
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                if not raw:
                    return None
                if "application/json" in response.headers.get("content-type", ""):
                    return json.loads(raw)
                return raw.decode(errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace").strip()
            if exc.code == 401:
                detail = "登录 session 无效或已过期，请重新执行 login"
            raise RuntimeError(f"HTTP {exc.code}: {detail or exc.reason}") from None
        except urllib.error.URLError as exc:
            raise RuntimeError(f"无法连接 Teamgent: {exc.reason}") from None


def require(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"缺少 {name}；通过参数、环境变量或 configure 设置")
    return value


def print_result(value) -> None:
    if value is None:
        print("ok")
    elif isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False, indent=2))
    else:
        print(value)


def parse_json(raw: str | None):
    if raw in (None, ""):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON 无效: {exc}") from None


def daemon_binary(config: dict) -> str:
    configured = os.environ.get("TG_DAEMON", "").strip() or str(config.get("tg_daemon", "")).strip()
    candidate = configured or shutil.which("tg-daemon") or ""
    if not candidate:
        raise RuntimeError("找不到 tg-daemon；将它加入 PATH，或设置 TG_DAEMON")
    return candidate


def run_daemon(config: dict, args: list[str]) -> None:
    raise SystemExit(subprocess.run([daemon_binary(config), *args]).returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="teamgentctl", description="Teamgent 运维命令")
    parser.add_argument("--url", help="Teamgent 部署 URL")
    parser.add_argument("--workspace", help="默认 Workspace ID")
    parser.add_argument("--project", help="默认 Project ID")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="验证并安全保存浏览器 session")
    sub.add_parser("logout", help="删除当前部署的本地 session")

    configure = sub.add_parser("configure", help="保存部署和默认资源配置")
    configure.add_argument("--url")
    configure.add_argument("--workspace")
    configure.add_argument("--project")
    configure.add_argument("--tg-daemon")

    sub.add_parser("me", help="查看当前登录用户")
    sub.add_parser("workspaces", help="列出可见 Workspace")
    projects = sub.add_parser("projects", help="列出 Workspace 的 Project")
    projects.add_argument("workspace_id", nargs="?")
    agents = sub.add_parser("agents", help="列出 Project Agent")
    agents.add_argument("project_id", nargs="?")
    chats = sub.add_parser("chats", help="列出 Project 对话")
    chats.add_argument("project_id", nargs="?")
    chats.add_argument("--agent-id")

    new_chat = sub.add_parser("new-chat", help="创建绑定 Agent 的对话")
    new_chat.add_argument("title")
    new_chat.add_argument("--agent-id", required=True, help="Project Agent ID")
    new_chat.add_argument("--project", dest="command_project")
    timeline = sub.add_parser("timeline", help="查看对话消息与 Run")
    timeline.add_argument("conversation_id")
    send = sub.add_parser("send", help="向对话发消息并触发 Run")
    send.add_argument("conversation_id")
    send.add_argument("message")

    runs = sub.add_parser("runs", help="列出 Project Run")
    runs.add_argument("project_id", nargs="?")
    runs.add_argument("--status")
    runs.add_argument("--limit", type=int, default=50)
    run = sub.add_parser("run", help="查看 Run 详情")
    run.add_argument("run_id")
    events = sub.add_parser("events", help="查看 Run 事件")
    events.add_argument("run_id")
    events.add_argument("--project", dest="command_project")
    cancel = sub.add_parser("cancel", help="取消 Run")
    cancel.add_argument("run_id")
    cancel.add_argument("--reason")
    requeue = sub.add_parser("requeue", help="重新排队 Run")
    requeue.add_argument("run_id")
    requeue.add_argument("--reason")
    cancel_all = sub.add_parser("cancel-all", help="取消对话中的所有活跃 Run")
    cancel_all.add_argument("conversation_id")
    cancel_all.add_argument("--reason")

    runtimes = sub.add_parser("runtimes", help="列出 Workspace Runtime")
    runtimes.add_argument("workspace_id", nargs="?")
    bind = sub.add_parser("bind-runtime", help="给 Agent 绑定 Runtime")
    bind.add_argument("project_agent_id")
    bind.add_argument("runtime_id")
    bind.add_argument("--workspace", dest="command_workspace")

    api = sub.add_parser("api", help="调用已确认的 Teamgent API")
    api.add_argument("method")
    api.add_argument("path")
    api.add_argument("json", nargs="?")

    sub.add_parser("daemon-status", help="查看本机 tg-daemon 状态")
    logs = sub.add_parser("daemon-logs", help="查看本机 tg-daemon 日志")
    logs.add_argument("-f", action="store_true")
    logs.add_argument("-n", type=int, default=100)
    sub.add_parser("daemon-stop", help="停止本机 tg-daemon")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()

    if args.command == "configure":
        result = save_config(
            {
                "url": args.url,
                "workspace": args.workspace,
                "project": args.project,
                "tg_daemon": args.tg_daemon,
            }
        )
        print_result(result)
        return 0

    base_url = normalize_url(
        args.url or os.environ.get("TEAMGENT_URL") or config.get("url")
    )
    workspace = args.workspace or os.environ.get("TEAMGENT_WORKSPACE") or config.get("workspace")
    project = args.project or os.environ.get("TEAMGENT_PROJECT") or config.get("project")

    if args.command == "login":
        print_login_instructions(base_url)
        try:
            session = getpass.getpass(f"{COOKIE_NAME}: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise RuntimeError("登录已取消") from None
        if not session:
            raise RuntimeError("session 不能为空")
        result = Client(base_url, session).request("GET", "/api/v1/me")
        backend = store_session(base_url, session)
        print_result(result)
        print(f"session 已保存到 {backend}", file=sys.stderr)
        return 0

    if args.command == "logout":
        delete_session(base_url)
        print("已删除当前 Teamgent 部署的本地 session")
        return 0

    if args.command == "daemon-status":
        run_daemon(config, ["status"])
    if args.command == "daemon-logs":
        run_daemon(config, ["logs", "-n", str(args.n), *(["-f"] if args.f else [])])
    if args.command == "daemon-stop":
        run_daemon(config, ["stop"])

    session = lookup_session(base_url)
    if not session:
        raise RuntimeError("未找到登录 session；先执行 login，或设置 TEAMGENT_SESSION")
    client = Client(base_url, session)
    command = args.command

    if command == "me":
        result = client.request("GET", "/api/v1/me")
    elif command == "workspaces":
        result = client.request("GET", "/api/v1/me/workspaces")
    elif command == "projects":
        workspace_id = require(args.workspace_id or workspace, "Workspace ID")
        result = client.request("GET", f"/api/v1/workspaces/{workspace_id}/projects")
    elif command == "agents":
        project_id = require(args.project_id or project, "Project ID")
        result = client.request("GET", f"/api/v1/projects/{project_id}/agents")
    elif command == "chats":
        project_id = require(args.project_id or project, "Project ID")
        result = client.request(
            "GET",
            f"/api/v1/projects/{project_id}/conversations",
            query={"limit": 200, "agent_id": args.agent_id},
        )
    elif command == "new-chat":
        project_id = require(args.command_project or project, "Project ID")
        result = client.request(
            "POST",
            f"/api/v1/projects/{project_id}/conversations",
            {
                "title": args.title,
                "surface": "web",
                "form": "thread",
                "agent_id": args.agent_id,
            },
        )
    elif command == "timeline":
        result = client.request(
            "GET",
            f"/api/v1/conversations/{args.conversation_id}/timeline",
            query={"limit": 100},
        )
    elif command == "send":
        result = client.request(
            "POST",
            f"/api/v1/conversations/{args.conversation_id}/messages",
            {"content": args.message},
        )
    elif command == "runs":
        project_id = require(args.project_id or project, "Project ID")
        result = client.request(
            "GET",
            f"/api/v1/projects/{project_id}/agent-runs",
            query={"limit": args.limit, "status": args.status},
        )
    elif command == "run":
        result = client.request("GET", f"/api/v1/agent-runs/{args.run_id}")
    elif command == "events":
        project_id = require(args.command_project or project, "Project ID")
        result = client.request(
            "GET", f"/api/v1/projects/{project_id}/agent-runs/{args.run_id}/events"
        )
    elif command == "cancel":
        result = client.request(
            "POST",
            f"/api/v1/agent-runs/{args.run_id}/cancel",
            {"reason": args.reason} if args.reason else {},
        )
    elif command == "requeue":
        result = client.request(
            "POST",
            f"/api/v1/agent-runs/{args.run_id}/requeue",
            {"reason": args.reason} if args.reason else {},
        )
    elif command == "cancel-all":
        result = client.request(
            "POST",
            f"/api/v1/conversations/{args.conversation_id}/cancel-all",
            {"reason": args.reason} if args.reason else {},
        )
    elif command == "runtimes":
        workspace_id = require(args.workspace_id or workspace, "Workspace ID")
        result = client.request("GET", f"/api/v1/workspaces/{workspace_id}/runtimes")
    elif command == "bind-runtime":
        workspace_id = require(args.command_workspace or workspace, "Workspace ID")
        result = client.request(
            "PUT",
            f"/api/v1/workspaces/{workspace_id}/project-agents/"
            f"{args.project_agent_id}/runtime",
            {"runtime_id": args.runtime_id},
        )
    elif command == "api":
        result = client.request(args.method, args.path, parse_json(args.json))
    else:
        parser.error(f"unknown command: {command}")
        return 2

    print_result(result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"teamgentctl: {exc}", file=sys.stderr)
        raise SystemExit(1)
