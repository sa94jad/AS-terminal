from __future__ import annotations
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

result = {"chat_id": os.environ["INPUT_CHAT_ID"], "request_id": os.environ["INPUT_REQUEST_ID"], "status": "error", "output": ""}
try:
    source = base64.b64decode(os.environ["INPUT_CODE_B64"], validate=True).decode("utf-8")
    if len(source.encode("utf-8")) > 12_000:
        raise ValueError("Code exceeds 12 KiB limit.")
    with tempfile.TemporaryDirectory(prefix="rubika-user-") as temp_dir:
        script = Path(temp_dir) / "main.py"
        script.write_text(source, encoding="utf-8")
        preexec = None
        if sys.platform.startswith("linux"):
            def apply_limits():
                import resource
                resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
                resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
                resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
                resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
                resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            preexec = apply_limits
        child_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "HOME": temp_dir,
            "TMPDIR": temp_dir,
        }
        completed = subprocess.run(
            [sys.executable, "-I", "-S", str(script)], cwd=temp_dir, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10,
            check=False, env=child_env, preexec_fn=preexec,
        )
        if completed.returncode == 0:
            result["status"] = "success"
            result["output"] = completed.stdout[-12_000:]
        elif completed.returncode == -9:
            result["output"] = "خطا: محدودیت زمان CPU یا منابع سیستم تمام شد."
        else:
            result["output"] = completed.stdout[-12_000:] + f"\n[exit code: {completed.returncode}]"
except subprocess.TimeoutExpired as error:
    captured = error.stdout or b""
    if isinstance(captured, bytes):
        captured = captured.decode("utf-8", errors="replace")
    result["output"] = str(captured)[-10_000:] + "\nخطا: زمان اجرای ۱۰ ثانیه تمام شد."
except Exception as error:
    result["output"] = f"{type(error).__name__}: {error}"

Path("result").mkdir(exist_ok=True)
Path("result/result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
print(f"Execution finished: {result['status']}")
