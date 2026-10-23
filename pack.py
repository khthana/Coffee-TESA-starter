"""Zip this agent folder for the code review, without .env or .venv, and (optionally) send it.

    python pack.py           # makes handin.zip here
    python pack.py --send    # makes it and sends it to the market (MARKET_URL and TEAM_KEY from .env)

Send only when staff call your team. You can also upload handin.zip on the page <MARKET_URL>/handin.
logs/ goes in: the reviewers compare your agent's log with what the market received.
"""
import os
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "handin.zip"
SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", ".ipynb_checkpoints", "node_modules", "site-packages"}
ENV_OK = {".env.example", ".env.sample", ".env.template"}
MAX_FILE = 5 * 1024 * 1024


def load_env(path: Path) -> None:
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def pack() -> int:
    n = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(HERE.rglob("*")):
            rel = path.relative_to(HERE)
            if not path.is_file() or any(p in SKIP_DIRS for p in rel.parts[:-1]):
                continue
            name = rel.name
            if (name.startswith(".env") and name not in ENV_OK) or name.endswith(".zip") or name.startswith("~$"):
                continue
            if path.stat().st_size > MAX_FILE:
                print(f"  ข้าม {rel} (ใหญ่เกิน 5 MB)")
                continue
            z.write(path, rel.as_posix())
            n += 1
    return n


def send() -> None:
    import httpx
    load_env(HERE / ".env")
    url, key = os.environ.get("MARKET_URL"), os.environ.get("TEAM_KEY")
    if not url or not key:
        sys.exit("ไม่พบ MARKET_URL หรือ TEAM_KEY ใน .env")
    r = httpx.post(url.rstrip("/") + "/v1/handin", content=OUT.read_bytes(), timeout=60,
                   headers={"Authorization": f"Bearer {key}", "Content-Type": "application/zip",
                            "User-Agent": "coffee-starter-pack/1.0"})
    body = r.json()
    if r.status_code != 201:
        e = body.get("error", {})
        sys.exit(f"ส่งไม่ผ่าน: {e.get('message')}\n{e.get('hint') or ''}")
    print(f"ส่งแล้ว {body['received_local']} · {body['files']} ไฟล์ · ทีม {body['team_id']}")
    if not body["has_decisions_log"]:
        print("ไม่มี logs/decisions.jsonl ใน zip: ถ้า agent ของทีมเขียน log ไว้ที่อื่น ให้บอกกรรมการ")


if __name__ == "__main__":
    n = pack()
    size = OUT.stat().st_size / 1e6
    print(f"สร้าง {OUT.name} แล้ว: {n} ไฟล์, {size:.1f} MB (ไม่มี .env และ .venv)")
    if not (HERE / "logs" / "decisions.jsonl").exists():
        print("ยังไม่มี logs/decisions.jsonl")
    if "--send" in sys.argv:
        send()
