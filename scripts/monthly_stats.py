#!/usr/bin/env python3
"""从 data/index.jsonl 生成月度统计（README 里的「待加」项）。

用法:
    python3 scripts/monthly_stats.py                # 统计最新月份
    python3 scripts/monthly_stats.py 2026-10        # 指定月份
    python3 scripts/monthly_stats.py 2026-10 --markdown > report.md

指标:
    - 上榜次数: 当月出现在日报里的天数
    - 连续上榜: 当月最长连续上榜天数（按自然日）
    - 周冠军: 每个 ISO 周「今日新增」合计最高的仓库
    - 每日冠军: 当月拿过第 1 名次数最多的仓库
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "data" / "index.jsonl"


def parse_stars(raw) -> int:
    """'153,524' / '153524' / '—' -> int（无法解析记 0）。"""
    if raw is None:
        return 0
    digits = re.sub(r"[^0-9]", "", str(raw))
    return int(digits) if digits else 0


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                print(f"skip bad json at line {lineno}", file=sys.stderr)
                continue
            if row.get("date") and row.get("repo"):
                rows.append(row)
    return rows


def iso_week(day: str) -> str:
    d = date.fromisoformat(day)
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def longest_streak(days: list[str]) -> int:
    """一串 'YYYY-MM-DD'（可重复）里最长的连续自然日天数。"""
    unique = sorted({date.fromisoformat(d) for d in days})
    best = run = 0
    prev = None
    for d in unique:
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    return best


def build_report(rows: list[dict], month: str) -> str:
    month_rows = [r for r in rows if r["date"].startswith(month)]
    if not month_rows:
        return f"# {month} 月度统计\n\n（该月无数据）\n"

    days = sorted({r["date"] for r in month_rows})
    appearances: Counter[str] = Counter()
    days_by_repo: dict[str, list[str]] = defaultdict(list)
    titles: Counter[str] = Counter()
    weekly_gain: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    daily_gain: dict[str, int] = defaultdict(int)

    for r in month_rows:
        repo = r["repo"]
        appearances[repo] += 1
        days_by_repo[repo].append(r["date"])
        gain = parse_stars(r.get("stars_today"))
        daily_gain[r["date"]] += gain
        if r.get("rank") == 1:
            titles[repo] += 1
        weekly_gain[iso_week(r["date"])][repo] += gain

    lines = [
        f"# {month} 月度统计",
        "",
        f"- 覆盖 {len(days)} 天（{days[0]} ~ {days[-1]}），{len(appearances)} 个仓库上榜",
        "",
        "## 上榜次数 Top 10",
        "",
        "| # | 仓库 | 上榜天数 | 最长连续 |",
        "|---|---|---|---|",
    ]
    for i, (repo, count) in enumerate(appearances.most_common(10), 1):
        lines.append(f"| {i} | {repo} | {count} | {longest_streak(days_by_repo[repo])} |")

    lines += ["", "## 周冠军（按「今日新增」合计）", "", "| ISO 周 | 冠军 | 本周合计新增 |", "|---|---|---|"]
    for week in sorted(weekly_gain):
        repo, gain = max(weekly_gain[week].items(), key=lambda kv: kv[1])
        lines.append(f"| {week} | {repo} | {gain:,} |")

    lines += ["", "## 每日冠军", ""]
    for day, gain in sorted(daily_gain.items()):
        top = [r for r in month_rows if r["date"] == day and r.get("rank") == 1]
        if top:
            lines.append(f"- {day}: {top[0]['repo']}（当日 +{parse_stars(top[0].get('stars_today')):,}）")
        else:
            lines.append(f"- {day}: （无 rank=1 记录）")

    if titles:
        lines += ["", "## 拿过第 1 名次数", ""]
        for repo, count in titles.most_common(5):
            lines.append(f"- {repo}: {count} 次")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="月度 GitHub Trending 统计")
    parser.add_argument("month", nargs="?", help="YYYY-MM，缺省为最新数据所在月份")
    parser.add_argument("--index", default=str(INDEX), help="index.jsonl 路径")
    parser.add_argument("--out", help="写入文件（缺省打印到 stdout）")
    args = parser.parse_args()

    path = Path(args.index)
    if not path.is_file():
        print(f"index not found: {path}", file=sys.stderr)
        return 1

    rows = load_rows(path)
    if not rows:
        print("index is empty", file=sys.stderr)
        return 1

    month = args.month or max(r["date"] for r in rows)[:7]
    report = build_report(rows, month)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"written: {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
