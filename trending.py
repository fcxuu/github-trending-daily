#!/usr/bin/env python3
"""github-trending-daily — 每日 Top 15 趋势索引
源:github.com/trending?since=daily 官方页面(无官方 API 的事实标准源)
产出:当月 MD(按天分节,重跑幂等替换当日) + data/index.jsonl(机器可读)
降级:页面解析失败/条目不足时,回退 GitHub Search API 近似(近30天新仓按 star 排)
"""
import json, os, re, html, urllib.request
from datetime import date, datetime, timedelta, timezone

TODAY = datetime.now(timezone(timedelta(hours=8))).date().isoformat()  # 北京时间
ROOT = os.path.dirname(os.path.abspath(__file__))
IDX = os.path.join(ROOT, "data", "index.jsonl")
UA = {"User-Agent": "Mozilla/5.0 (compatible; trending-daily/1.0)",
      "Accept-Language": "en-US,en;q=0.9"}

def fetch(url, token=None):
    req = urllib.request.Request(url, headers={**UA, **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()

def parse_trending(page, limit=15):
    out = []
    for art in re.findall(r'<article class="Box-row">(.*?)</article>', page, re.S)[:limit]:
        # 锚点:星标链接 href="/owner/repo/stargazers" 每行必有,
        # 且不会被 sponsor/topic 等干扰链接误配(GitHub 对不同客户端 A/B 微调标记,勿锚 h2)
        m = re.search(r'href="/([^/"]+/[^/"]+)/stargazers"', art)
        if not m: continue
        repo = m.group(1).strip("/")
        desc = ""
        md = re.search(r'<p class="[^"]*col-9[^"]*">\s*(.*?)\s*</p>', art, re.S)
        if md: desc = strip_tags(md.group(1))[:150]
        lang = ""
        ml = re.search(r'itemprop="programmingLanguage">([^<]+)<', art)
        if ml: lang = ml.group(1).strip()
        stars_total = stars_today = ""
        ms = re.search(r'href="/' + re.escape(repo) + r'/stargazers"[^>]*>\s*(?:<[^>]*>\s*)*([\d,]+)', art)
        if ms: stars_total = ms.group(1)
        mt = re.search(r'([\d,]+)\s*stars\s+today', art)
        if mt: stars_today = mt.group(1)
        out.append(dict(repo=repo, description=desc, language=lang,
                        stars_total=stars_total, stars_today=stars_today,
                        url=f"https://github.com/{repo}"))
    return out

def fallback_search(token, limit=15):
    since = (date.today().toordinal() - 30)
    d30 = date.fromordinal(since).isoformat()
    url = (f"https://api.github.com/search/repositories?"
           f"q=created:>={d30}+stars:>100&sort=stars&order=desc&per_page={limit}")
    data = json.loads(fetch(url, token))
    return [dict(repo=r["full_name"], description=(r.get("description") or "")[:150],
                 language=r.get("language") or "", stars_total=str(r["stargazers_count"]),
                 stars_today="", url=r["html_url"], approx=True)
            for r in data.get("items", [])[:limit]]

def build_md_section(entries):
    rows = ["| # | 仓库 | 简介 | 语言 | 总星 | 今日 |",
            "|---|---|---|---|---|---|"]
    for i, e in enumerate(entries, 1):
        rows.append(f"| {i} | [{e['repo']}]({e['url']}) | {e['description'][:80] or '—'} "
                    f"| {e['language'] or '—'} | {e['stars_total'] or '—'} | {e['stars_today'] or '—'} |")
    note = "\n> 来源:近似搜索(官方 trending 页解析失败)" if entries and entries[0].get("approx") else ""
    return f"## {TODAY}\n\n" + "\n".join(rows) + note + "\n"

def upsert_md(path, section):
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    parts, cur, kept = [], [], True
    for line in old.splitlines(keepends=True):
        if line.startswith("## "):
            parts.append("".join(cur)); cur = [line]
        else:
            cur.append(line)
    parts.append("".join(cur))
    body = "".join(p for p in parts if not p.startswith(f"## {TODAY}\n"))
    month_file = TODAY[:7] + ".md"
    header = "# GitHub Trending Daily · Top 15\n\n每日抓取官方 trending 榜前 15 名。同名小节重跑即替换(幂等)。\n\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write((body if old else header) + section + "\n")

def main():
    token = os.environ.get("GITHUB_TOKEN")
    entries, source = [], "official-trending"
    try:
        entries = parse_trending(fetch("https://github.com/trending?since=daily"))
    except Exception as e:
        print("trending 页抓取失败:", e)
    if len(entries) < 3:
        try:
            entries = fallback_search(token)
            source = "fallback-search"
        except Exception as e:
            print("fallback 也失败:", e)
    if not entries:
        print("今日无数据,跳过(不写空记录)"); return

    md_path = os.path.join(ROOT, f"{date.today().year}-{date.today().month:02d}.md")
    upsert_md(md_path, build_md_section(entries))

    os.makedirs(os.path.dirname(IDX), exist_ok=True)
    lines = []
    if os.path.exists(IDX):
        lines = [l for l in open(IDX, encoding="utf-8").read().splitlines()
                 if l and json.loads(l).get("date") != TODAY]
    for i, e in enumerate(entries, 1):
        lines.append(json.dumps(dict(date=TODAY, rank=i, **{k: v for k, v in e.items() if k != "approx"}),
                                ensure_ascii=False))
    with open(IDX, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[{source}] {TODAY}: {len(entries)} 条 → {os.path.basename(md_path)} + index.jsonl")
    for i, e in enumerate(entries[:15], 1):
        print(f"  {i:2d}. {e['repo']} ({e['language'] or '-'}) ★{e['stars_total'] or '?'} +{e['stars_today'] or '?'} today")

if __name__ == "__main__":
    main()
