"""Release-skill 五平台自动发文 · 结构化台账

双写:
- ledger/publish_ledger.csv   人工可读、Excel 可开
- ledger/publish_ledger.jsonl  机器可读、追加原子

字段: time, platform, platform_display, title, mode, status, result_url, screenshot, detail
"""
import csv
import datetime as _dt
import json
import os
import tempfile
from pathlib import Path

FIELDS = ["time", "platform", "platform_display", "title", "mode",
          "status", "result_url", "screenshot", "detail"]


class Ledger:
    def __init__(self, ledger_dir):
        self.dir = Path(ledger_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.dir / "publish_ledger.csv"
        self.jsonl_path = self.dir / "publish_ledger.jsonl"

    def append(self, record: dict) -> dict:
        row = {k: str(record.get(k, "") or "") for k in FIELDS}
        if not row.get("time"):
            row["time"] = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # JSONL 追加(原子: 单行 write with append + flush)
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        # CSV: 无则写表头,有则追加
        need_header = not self.csv_path.exists() or self.csv_path.stat().st_size == 0
        with open(self.csv_path, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if need_header:
                w.writeheader()
            w.writerow(row)
        print(f"[ledger] 已记录: {row['time']} | {row['platform']} | {row['status']}", flush=True)
        return row

    def read_all(self) -> list:
        rows = []
        if self.jsonl_path.exists():
            for line in self.jsonl_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return rows

    def stats(self) -> dict:
        rows = self.read_all()
        out = {"total": len(rows), "by_status": {}, "by_platform": {}}
        for r in rows:
            s = r.get("status", "?")
            p = r.get("platform", "?")
            out["by_status"][s] = out["by_status"].get(s, 0) + 1
            out["by_platform"][p] = out["by_platform"].get(p, 0) + 1
        return out


if __name__ == "__main__":
    import sys
    led = Ledger(sys.argv[1] if len(sys.argv) > 1 else "ledger")
    print(json.dumps(led.stats(), ensure_ascii=False, indent=2))
