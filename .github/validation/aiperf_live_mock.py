"""Run the prepared YAML calibration patch against the real local mock server.

AI-assisted validation infrastructure; this is not an upstream contribution or
a personal DCO/review attestation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

import psutil

repo = Path(os.environ["AIPERF_REPO"])
receipt = Path(os.environ["RUNNER_TEMP"]) / "aiperf-mock"
receipt.mkdir()
scripts = repo / ".venv/bin"
env = {
    key: value for key, value in os.environ.items()
    if not key.endswith(("_API_KEY", "_TOKEN"))
}
env.update(
    HF_HUB_OFFLINE="1", AIPERF_SERVICE_REGISTRATION_TIMEOUT="120",
    AIPERF_SERVICE_START_TIMEOUT="120",
)
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
config = receipt / "benchmark.yaml"
config.write_text(f'''schemaVersion: "2.0"
benchmark:
  model: mock-model
  tokenizer:
    name: builtin
  endpoint:
    url: http://127.0.0.1:{port}
    type: chat
    streaming: true
  dataset:
    type: synthetic
    entries: 10
    prompts:
      isl: 32
      osl: 16
  phases:
    type: concurrency
    concurrency: 1
    requests: 12
  networkLatency:
    enabled: true
    pingInterval: 0.05
''', encoding="utf-8")
server_command = [
    str(scripts / "aiperf-mock-server"), "--host", "127.0.0.1",
    "--port", str(port), "--tokenizer", "builtin", "--ttft", "100",
]
client_command = [
    str(scripts / "aiperf"), "profile", "--config", str(config),
    "--ui", "none", "--output-artifact-dir", str(receipt / "artifacts"),
    "--no-gpu-telemetry", "--no-server-metrics",
]


def stop_owned(process: subprocess.Popen[bytes]) -> None:
    """Clean up only this validation process and its descendants."""
    try:
        root = psutil.Process(process.pid)
        children = root.children(recursive=True) + [root]
    except psutil.NoSuchProcess:
        return
    for child in children:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(children, timeout=5)
    for child in alive:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass


server = None
client = None
result: dict[str, object] = {
    "network_latency_cli_flags": [],
    "server_command": server_command, "client_command": client_command,
    "provider": "localhost mock; builtin tokenizer; no credentials/model downloads",
}
start = time.monotonic()
try:
    with (receipt / "server.log").open("w", encoding="utf-8") as output:
        server = subprocess.Popen(server_command, cwd=repo, env=env, stdout=output, stderr=subprocess.STDOUT)
    deadline = time.monotonic() + 90
    while True:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=1) as response:
                assert response.status == 200
            break
        except OSError:
            if server.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("Local mock server did not become ready")
            time.sleep(0.2)
    with (receipt / "client.log").open("w", encoding="utf-8") as output:
        client = subprocess.Popen(client_command, cwd=repo, env=env, stdout=output, stderr=subprocess.STDOUT)
        code = client.wait(timeout=300)
    result["client_exit_code"] = code
    assert code == 0, f"CLI failed with exit code {code}"
    exports = list((receipt / "artifacts").rglob("profile_export_aiperf.json"))
    assert len(exports) == 1, exports
    payload = json.loads(exports[0].read_text(encoding="utf-8"))
    keys: set[str] = set()
    latency_configs: list[dict[str, object]] = []

    def walk(value: object) -> None:
        """Inspect exported configs and metric dictionaries."""
        if isinstance(value, dict):
            keys.update(value)
            for key, item in value.items():
                if key in ("network_latency", "networkLatency") and isinstance(item, dict):
                    latency_configs.append(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    assert any(value.get("enabled") is True for value in latency_configs), latency_configs
    assert {"network_rtt", "network_adjusted_request_latency"} <= keys, sorted(keys)
    result.update(
        status="passed", export=str(exports[0]),
        network_latency_configs=latency_configs,
        network_metrics=sorted(key for key in keys if key.startswith("network_")),
    )
except Exception as error:
    result.update(status="failed", error=repr(error))
    raise
finally:
    for process in (client, server):
        if process is not None and process.poll() is None:
            stop_owned(process)
    result["elapsed_seconds"] = round(time.monotonic() - start, 2)
    (receipt / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result), flush=True)
