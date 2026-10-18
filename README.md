# github-trending-daily

每天自动抓取 **GitHub 官方 Trending 榜（daily）前 15 名**，归档为 Markdown 月报 + 机器可读索引。

## 产出

```
2026-10.md            # 当月日报,每天一节(表格:排名/仓库/简介/语言/总星/今日新增星)
data/index.jsonl      # 每日每条一行 JSON,便于后续统计
```

- **重跑幂等**：同一天重跑会替换当日小节与索引行,不会重复追加
- **降级策略**：官方页解析失败或条目不足时,回退 GitHub Search API 近似(近 30 天新仓按 star 排),并在日报标注"近似来源"
- **月度统计**：`python3 scripts/monthly_stats.py [YYYY-MM]` 直接从 `data/index.jsonl` 产出「上榜次数 Top10 / 最长连续上榜 / 周冠军 / 每日冠军」Markdown 报告，缺省统计最新月份

## 运行

- 自动：GitHub Actions 每天 07:30(北京时间)跑一次并自动 commit
- 手动:`GITHUB_TOKEN=$(gh auth token) python trending.py`
- 手动触发:Actions 页 → daily-trending → Run workflow

## 已知边界

- GitHub trending 页面是事实标准源但无官方 API,HTML 结构变更会导致解析降级到搜索近似(日报会标注,便于发现)
- trending 只反映"今日热度",不代表长期趋势;长期榜用 `data/index.jsonl` 自行聚合

## 数据说明与已知偏差

- 榜单只反映 GitHub 官方趋势页的当日快照；仓库可能因官方轮换或反刷星降权而暂时缺席日榜（例：2026-10-17 的 morluto/rea 仓库一切正常、star 仍在增长，但已不在全语言日榜）。
- 官方页解析失败时回退到 Search API 近似数据，日报会在小节末尾标注「来源:近似搜索」。
- 「今日新增」等于当日快照 star 数与上一日快照之差，受快照时间漂移影响，仅供参考；跨日对比时以 data/index.jsonl 的原始记录为准。
