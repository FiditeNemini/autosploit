#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-autonomous-scenario-fixture-setup.json"
FIXTURE_ROOT = Path("/tmp/exploitbot-autonomous-scenario-fixtures")


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def read_url(url: str, timeout: float = 4.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


class SQLiHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/routes":
            return self._text("GET /\nGET /login\nGET /search?q=1\n")
        if parsed.path == "/login":
            return self._text("<title>ExploitBot SQLi Lab Login</title>\n", "text/html")
        if parsed.path == "/search":
            query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            body = "EXPLOITBOT_SQLI_PROOF_USER=alice\nparameter=q\n" if "'" in query or "1=1" in query else "no rows\n"
            return self._text(body)
        return self._text("<title>ExploitBot SQLi Lab</title>EXPLOITBOT_WEBAPP_LAB_OK\n", "text/html")

    def _text(self, body: str, content_type: str = "text/plain") -> None:
        raw = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class SSRFHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/routes":
            return self._text("GET /fetch?url=\nGET /download?path=fixture-note.txt\nGET /canary\n")
        if parsed.path == "/canary":
            return self._text("EXPLOITBOT_SSRF_CANARY_OK\n")
        if parsed.path == "/fetch":
            url = urllib.parse.parse_qs(parsed.query).get("url", [""])[0]
            if url.startswith("http://127.0.0.1:") and url.endswith("/canary"):
                return self._text("fetched: EXPLOITBOT_SSRF_CANARY_OK\n")
            return self._text("blocked external fetch\n", status=403)
        if parsed.path == "/download":
            requested = urllib.parse.parse_qs(parsed.query).get("path", [""])[0]
            if requested == "fixture-note.txt":
                return self._text("EXPLOITBOT_FILE_READ_CANARY_OK\n")
            return self._text("blocked path\n", status=403)
        return self._text("<title>ExploitBot SSRF Lab</title>\n", "text/html")

    def _text(self, body: str, content_type: str = "text/plain", status: int = 200) -> None:
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class NetworkHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/banner":
            return self._text("ExploitBot demo service 1.0\n")
        if parsed.path == "/login":
            params = urllib.parse.parse_qs(parsed.query)
            if params.get("user", [""])[0] == "demo" and params.get("pass", [""])[0] == "demo":
                return self._text("EXPLOITBOT_NETWORK_LOGIN_OK\n")
            return self._text("invalid demo credential\n", status=401)
        if parsed.path == "/post-check":
            return self._text("EXPLOITBOT_LINPEAS_FIXTURE_OK\n")
        return self._text("ExploitBot network fixture\n")

    def _text(self, body: str, content_type: str = "text/plain", status: int = 200) -> None:
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def start_server(handler: type[BaseHTTPRequestHandler]) -> tuple[ThreadingHTTPServer, str]:
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def create_repo_fixture(root: Path) -> Path:
    repo = root / "synthetic-vulnerable-repo"
    repo.mkdir(parents=True)
    (repo / "package.json").write_text(
        json.dumps(
            {
                "name": "exploitbot-supply-chain-lab",
                "version": "1.0.0",
                "dependencies": {"lodash": "4.17.11", "minimist": "0.0.8"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "package-lock.json").write_text(
        json.dumps(
            {
                "name": "exploitbot-supply-chain-lab",
                "lockfileVersion": 2,
                "packages": {
                    "": {"dependencies": {"lodash": "4.17.11"}},
                    "node_modules/lodash": {"version": "4.17.11"},
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / ".env.example").write_text("EXPLOITBOT_FAKE_TOKEN_DO_NOT_USE=sk_live_local_fixture_canary\n", encoding="utf-8")
    (repo / "VULNERABILITIES.md").write_text("lodash@4.17.11 maps to CVE-2021-23337 and GHSA-35jh-r3h4-6jhm.\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    subprocess.run(
        ["git", "-c", "user.email=fixture@example.local", "-c", "user.name=ExploitBot Fixture", "commit", "-m", "seed vulnerable fixture"],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return repo


def create_codebase_fixture(root: Path) -> Path:
    codebase = root / "synthetic-codebase-review"
    codebase.mkdir(parents=True)
    (codebase / "app.py").write_text(
        "\n".join(
            [
                "from flask import Flask, request",
                "from pathlib import Path",
                "",
                "app = Flask(__name__)",
                "BASE_DIR = Path('/tmp/exploitbot-codebase-fixture/files')",
                "",
                "@app.route('/download')",
                "def download():",
                "    # EXPLOITBOT_PATH_TRAVERSAL_PROOF vulnerable sink for local fixture only",
                "    return open(request.args['path']).read()",
                "",
                "def fixed_download(path):",
                "    resolved = (BASE_DIR / path).resolve()",
                "    if BASE_DIR.resolve() not in resolved.parents:",
                "        raise ValueError('pathlib resolve allowlist')",
                "    return resolved.read_text()",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (codebase / "README.md").write_text("Local codebase fixture. Expected patch: pathlib resolve allowlist.\n", encoding="utf-8")
    return codebase


def create_container_iac_fixture(root: Path) -> Path:
    repo = root / "synthetic-container-iac"
    (repo / "k8s").mkdir(parents=True)
    (repo / "Dockerfile").write_text(
        "\n".join(
            [
                "FROM nginx:1.16",
                "LABEL proof=EXPLOITBOT_CONTAINER_IAC_PROOF",
                "USER root",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "docker-compose.yml").write_text("services:\n  web:\n    image: nginx:1.16\n", encoding="utf-8")
    (repo / "k8s" / "deployment.yaml").write_text(
        "\n".join(
            [
                "apiVersion: apps/v1",
                "kind: Deployment",
                "metadata:",
                "  name: exploitbot-container-iac-proof",
                "spec:",
                "  template:",
                "    spec:",
                "      containers:",
                "        - name: web",
                "          image: nginx:1.16",
                "          securityContext:",
                "            allowPrivilegeEscalation: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return repo


def file_contains(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def row(scenario_id: str, setup_mode: str, target: str, markers: list[str], checks: dict[str, bool]) -> dict[str, Any]:
    status = {name: "PASS" if value else "FAIL" for name, value in checks.items()}
    return {
        "scenarioId": scenario_id,
        "setupMode": setup_mode,
        "target": target,
        "proofMarkers": markers,
        "checks": status,
        "ok": all(value == "PASS" for value in status.values()),
    }


@dataclass
class FixtureSession:
    root: Path
    servers: list[ThreadingHTTPServer]
    rows: list[dict[str, Any]]

    def close(self) -> None:
        for server in self.servers:
            server.shutdown()
            server.server_close()

    def target_for(self, scenario_id: str) -> str:
        for item in self.rows:
            if item.get("scenarioId") == scenario_id:
                return str(item.get("target") or "")
        raise KeyError(scenario_id)

    def row_for(self, scenario_id: str) -> dict[str, Any]:
        for item in self.rows:
            if item.get("scenarioId") == scenario_id:
                return item
        raise KeyError(scenario_id)


def build_fixture_session(root: Path = FIXTURE_ROOT, *, reset: bool = True) -> FixtureSession:
    if reset and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    session = FixtureSession(root=root, servers=[], rows=[])
    try:
        sqli_server, sqli_url = start_server(SQLiHandler)
        session.servers.append(sqli_server)
        sqli_root = read_url(f"{sqli_url}/")
        sqli_search = read_url(f"{sqli_url}/search?q=1%27%20OR%201%3D1--")
        session.rows.append(
            row(
                "webserver_auth_sqli_report_chain",
                "loopback_http_server",
                sqli_url,
                ["EXPLOITBOT_WEBAPP_LAB_OK", "EXPLOITBOT_SQLI_PROOF_USER=alice"],
                {
                    "rootMarker": "EXPLOITBOT_WEBAPP_LAB_OK" in sqli_root,
                    "sqlInjectionMarker": "EXPLOITBOT_SQLI_PROOF_USER=alice" in sqli_search,
                    "loopbackOnly": sqli_url.startswith("http://127.0.0.1:"),
                },
            )
        )

        ssrf_server, ssrf_url = start_server(SSRFHandler)
        session.servers.append(ssrf_server)
        ssrf_fetch = read_url(f"{ssrf_url}/fetch?url={urllib.parse.quote(ssrf_url + '/canary', safe=':/?=&')}")
        ssrf_file = read_url(f"{ssrf_url}/download?path=fixture-note.txt")
        session.rows.append(
            row(
                "webserver_ssrf_file_read_chain",
                "loopback_http_server",
                ssrf_url,
                ["EXPLOITBOT_SSRF_CANARY_OK", "EXPLOITBOT_FILE_READ_CANARY_OK"],
                {
                    "ssrfCanary": "EXPLOITBOT_SSRF_CANARY_OK" in ssrf_fetch,
                    "fileReadCanary": "EXPLOITBOT_FILE_READ_CANARY_OK" in ssrf_file,
                    "loopbackOnly": ssrf_url.startswith("http://127.0.0.1:"),
                },
            )
        )

        repo = create_repo_fixture(root)
        session.rows.append(
            row(
                "github_repo_secret_dependency_chain",
                "local_git_repo",
                str(repo),
                ["EXPLOITBOT_FAKE_TOKEN_DO_NOT_USE", "lodash@4.17.11", "CVE-2021-23337"],
                {
                    "gitRepo": (repo / ".git").is_dir(),
                    "fakeSecretCanary": file_contains(repo / ".env.example", "EXPLOITBOT_FAKE_TOKEN_DO_NOT_USE"),
                    "dependencyPin": file_contains(repo / "package.json", '"lodash": "4.17.11"'),
                    "cveHint": file_contains(repo / "VULNERABILITIES.md", "CVE-2021-23337"),
                },
            )
        )

        codebase = create_codebase_fixture(root)
        session.rows.append(
            row(
                "codebase_static_to_patch_review_chain",
                "local_codebase",
                str(codebase),
                ["EXPLOITBOT_PATH_TRAVERSAL_PROOF", "app.py:17", "pathlib resolve allowlist"],
                {
                    "appFile": (codebase / "app.py").is_file(),
                    "pathTraversalMarker": file_contains(codebase / "app.py", "EXPLOITBOT_PATH_TRAVERSAL_PROOF"),
                    "patchHint": file_contains(codebase / "app.py", "pathlib resolve allowlist"),
                },
            )
        )

        container = create_container_iac_fixture(root)
        session.rows.append(
            row(
                "container_iac_supply_chain_chain",
                "local_container_iac_repo",
                str(container),
                ["EXPLOITBOT_CONTAINER_IAC_PROOF", "allowPrivilegeEscalation: true", "nginx:1.16"],
                {
                    "dockerfile": file_contains(container / "Dockerfile", "EXPLOITBOT_CONTAINER_IAC_PROOF"),
                    "vulnerableImageTag": file_contains(container / "Dockerfile", "nginx:1.16"),
                    "iacRisk": file_contains(container / "k8s" / "deployment.yaml", "allowPrivilegeEscalation: true"),
                },
            )
        )

        network_server, network_url = start_server(NetworkHandler)
        session.servers.append(network_server)
        login = read_url(f"{network_url}/login?user=demo&pass=demo")
        post_check = read_url(f"{network_url}/post-check")
        session.rows.append(
            row(
                "network_service_credential_post_chain",
                "loopback_network_service",
                network_url,
                ["EXPLOITBOT_NETWORK_LOGIN_OK", "EXPLOITBOT_LINPEAS_FIXTURE_OK"],
                {
                    "loginCanary": "EXPLOITBOT_NETWORK_LOGIN_OK" in login,
                    "postCheckCanary": "EXPLOITBOT_LINPEAS_FIXTURE_OK" in post_check,
                    "loopbackOnly": network_url.startswith("http://127.0.0.1:"),
                },
            )
        )
        return session
    except Exception:
        session.close()
        raise


def run() -> None:
    started = timestamp()
    session: FixtureSession | None = None
    try:
        session = build_fixture_session()
        rows = session.rows
    finally:
        if session is not None:
            session.close()

    ok = all(item["ok"] for item in rows) and len(rows) == 6
    report = {
        "ok": ok,
        "proofType": "autonomous-scenario-fixture-setup",
        "proofLevel": "local-fixture-materialization-no-model-load",
        "status": "PASS" if ok else "FAIL",
        "startedAt": started,
        "finishedAt": timestamp(),
        "generatedAt": timestamp(),
        "fixtureRoot": str(FIXTURE_ROOT),
        "scenarioCount": len(rows),
        "scenarios": rows,
        "serverLifecycle": "loopback HTTP services are proof-run-only and are stopped before artifact write",
        "recreateCommand": "python3 scripts/autonomous-scenario-fixture-setup-proof.py",
        "notes": [
            "No model inference is started by this proof.",
            "All targets are loopback services or local files under /tmp; fake credentials and tokens are canaries only.",
        ],
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not ok:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"autonomous scenario fixture setup proof passed: {ARTIFACT}")


if __name__ == "__main__":
    run()
