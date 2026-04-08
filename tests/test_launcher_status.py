from __future__ import annotations

import json
from pathlib import Path
import subprocess


def test_launcher_status_emits_complete_json_when_stdout_is_captured(tmp_path: Path) -> None:
    home = tmp_path / "managed-home" / "runtime-home"
    runtime_root = home / "runtime"
    runtime_root.mkdir(parents=True)
    daemon_id = "daemon-status-json"
    payload = {
        "pid": 43210,
        "host": "127.0.0.1",
        "port": 65530,
        "url": "http://127.0.0.1:65530",
        "bind_url": "http://127.0.0.1:65530",
        "log_path": str(home / "runtime" / "logs" / ("z" * 240 + ".log")),
        "started_at": "2026-04-08T00:00:00.000Z",
        "home": str(home),
        "daemon_id": daemon_id,
        "note": "long-status-payload-" + "q" * 480,
    }
    (runtime_root / "daemon.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(Path(__file__).resolve().parents[1] / "bin" / "ds.js"),
            "--home",
            str(home),
            "--status",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert len(result.stdout.encode("utf-8")) > 512
    status_payload = json.loads(result.stdout)
    assert status_payload["home"] == str(home)
    assert status_payload["daemon"]["home"] == str(home)
    assert status_payload["daemon"]["daemon_id"] == daemon_id
    assert status_payload["health"] is None
