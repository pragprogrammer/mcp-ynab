"""Fresh-resolution smoke test.

Installs a built wheel into a clean venv and drives the real `mcp-ynab` entry point
through an MCP stdio handshake.

The point of this test is what it deliberately does NOT do: it never touches uv.lock,
never runs `uv sync` or `uv run`. It resolves dependencies from the constraints declared
in pyproject.toml, which is what a user gets and what the locked dev environment can
never show us. mcp-ynab 1.0.3 shipped broken for six days because every check we had ran
against a lockfile pinned to a version users would not resolve (see #21).

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --resolution lowest-direct
    python scripts/smoke_test.py --wheel dist/mcp_ynab-1.1.0-py3-none-any.whl --no-build

Exits non-zero with the server's stderr attached on any failure.
"""

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
from pathlib import Path

# Bump this when tools are added or removed. A mismatch means either the change was
# intentional (update the number) or registration silently broke (fix the bug).
EXPECTED_TOOL_COUNT = 47

# Cheap canaries across a few domain modules, so a partial registration failure is
# reported as a missing name rather than only as a count that happens to still match.
SENTINEL_TOOLS = {"get_user", "list_plans", "list_accounts", "list_transactions"}

PROTOCOL_VERSION = "2025-06-18"
READ_TIMEOUT = 30  # seconds to wait for any single JSON-RPC response


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, echoing it, and fail loudly on a non-zero exit."""
    print(f"  $ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"command failed with exit {result.returncode}: {' '.join(cmd)}")
    return result


def declared_dependencies(repo: Path) -> list[str]:
    """Read the runtime dependencies declared in pyproject.toml.

    These have to be passed to `uv pip install` explicitly for `--resolution
    lowest-direct` to mean anything. Installing only the wheel makes them transitive,
    and lowest-direct ignores transitive requirements, so the leg silently resolves
    identically to `highest` and tests nothing.
    """
    with (repo / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["dependencies"]


def venv_bin(venv: Path, name: str) -> Path:
    """Resolve an executable inside a venv on either Windows or POSIX layout."""
    if os.name == "nt":
        candidate = venv / "Scripts" / f"{name}.exe"
        return candidate if candidate.exists() else venv / "Scripts" / name
    return venv / "bin" / name


class StdioClient:
    """Minimal newline-delimited JSON-RPC client over a subprocess's stdio.

    Reads on a background thread so a server that starts but never answers fails the
    test with a timeout instead of hanging CI.
    """

    def __init__(self, argv: list[str], env: dict[str, str]):
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
        )
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()

    def _pump(self) -> None:
        for line in self.proc.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def send(self, message: dict) -> None:
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def read(self, what: str) -> dict:
        try:
            line = self._lines.get(timeout=READ_TIMEOUT)
        except queue.Empty:
            raise SystemExit(f"timed out after {READ_TIMEOUT}s waiting for {what}")
        if line is None:
            raise SystemExit(f"server closed stdout before answering {what}")
        return json.loads(line)

    def close(self) -> str:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        return self.proc.stderr.read()


def handshake(server_cmd: list[str]) -> list[dict]:
    """Run initialize + tools/list against the server, returning the tool list."""
    env = dict(os.environ, YNAB_API_KEY="smoke-test-dummy-key", PYTHONUNBUFFERED="1")
    client = StdioClient(server_cmd, env)
    try:
        client.send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "smoke-test", "version": "1"},
            },
        })
        init = client.read("initialize")
        if "result" not in init:
            raise SystemExit(f"initialize failed: {json.dumps(init)[:400]}")
        server_name = init["result"].get("serverInfo", {}).get("name", "?")
        print(f"  initialize ok (server: {server_name})")

        client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        client.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listing = client.read("tools/list")
        if "result" not in listing:
            raise SystemExit(f"tools/list failed: {json.dumps(listing)[:400]}")
        return listing["result"]["tools"]
    finally:
        stderr = client.close()
        if stderr.strip():
            print("  server stderr:")
            for line in stderr.strip().splitlines()[:20]:
                print(f"    {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", help="wheel to install (default: build one)")
    parser.add_argument("--no-build", action="store_true", help="skip uv build")
    parser.add_argument("--python", default="3.13", help="python version for the venv")
    parser.add_argument(
        "--resolution",
        choices=["highest", "lowest-direct"],
        help="pass through to uv pip install to test declared floors",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent

    print("[1/4] locating wheel")
    if not args.no_build:
        run(["uv", "build", "--wheel", "--out-dir", str(repo / "dist")], cwd=repo)
    if args.wheel:
        wheel = Path(args.wheel).resolve()
    else:
        wheels = sorted(
            (repo / "dist").glob("*.whl"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not wheels:
            raise SystemExit("no wheel found in dist/; run without --no-build")
        wheel = wheels[0]
    print(f"  {wheel.name}")

    tmp = Path(tempfile.mkdtemp(prefix="mcp-ynab-smoke-"))
    try:
        venv = tmp / "venv"
        print(f"[2/4] clean venv (python {args.python}), no lockfile")
        run(["uv", "venv", str(venv), "--python", args.python])

        py = venv_bin(venv, "python")
        install = ["uv", "pip", "install", "--python", str(py)]
        if args.resolution:
            install += ["--resolution", args.resolution]
        install.append(str(wheel))
        if args.resolution == "lowest-direct":
            # Promote the declared deps to direct requirements so their floors are
            # what actually gets resolved. See declared_dependencies().
            install += declared_dependencies(repo)
        run(install)

        print("[3/4] resolved versions")
        versions = subprocess.run(
            [
                str(py),
                "-c",
                "import importlib.metadata as m;"
                "print('\\n'.join(f'{d} {m.version(d)}' for d in "
                "['mcp','pydantic','httpx','sqlalchemy','aiosqlite']))",
            ],
            capture_output=True,
            text=True,
        )
        for line in versions.stdout.strip().splitlines():
            print(f"  {line}")

        print("[4/4] stdio handshake against the installed entry point")
        entry = venv_bin(venv, "mcp-ynab")
        if not entry.exists():
            raise SystemExit(f"entry point not installed at {entry}")
        tools = handshake([str(entry)])

        names = {t["name"] for t in tools}
        missing = SENTINEL_TOOLS - names
        if missing:
            raise SystemExit(f"tools/list is missing expected tools: {sorted(missing)}")
        if len(tools) != EXPECTED_TOOL_COUNT:
            raise SystemExit(
                f"expected {EXPECTED_TOOL_COUNT} tools, got {len(tools)}. "
                "If this change was intentional, update EXPECTED_TOOL_COUNT."
            )

        print(f"\nPASS: {len(tools)} tools registered and served over stdio")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
