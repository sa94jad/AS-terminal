from __future__ import annotations
import json
import os
from pathlib import Path
import requests

token = os.environ["RUBIKA_BOT_TOKEN"].strip()
result_path = Path("result/result.json")
if not result_path.exists():
    raise SystemExit("Execution result artifact is missing.")
data = json.loads(result_path.read_text(encoding="utf-8"))
chat_id = str(data.get("chat_id", "")).strip()
status = str(data.get("status", "error"))
output = str(data.get("output", "")).strip() or "(بدون خروجی)"
if not chat_id:
    raise SystemExit("Result has no chat_id.")
label = "✅ اجرای موفق" if status == "success" else "⚠️ اجرای ناموفق"
message = f"{label}\n\n{output}"
if len(message) > 3500:
    message = message[:3450] + "\n... (خروجی کوتاه شد)"
response = requests.post(
    f"https://botapi.rubika.ir/v3/{token}/sendMessage",
    json={"chat_id": chat_id, "text": message},
    timeout=25,
)
response.raise_for_status()
print("Result delivered to Rubika.")
