# github-trending-daily

每天自动抓取 **GitHub 官方 Trending 榜（daily）前 15 名**，归档为 Markdown 月报 + 机器可读索引。

## 产出

```
2026-10.md            # 当月日报,每天一节(表格:排名/仓库/简介/语言/总星/今日新增星)
data/index.jsonl      # 每日每条一行 JSON,便于后续统计
```

- **重跑幂等**：同一天重跑会替换当日小节与索引行,不会重复追加
- **降级策略**：官方页解析失败或条目不足时,回退 GitHub Search API 近似(近 30 天新仓按 star 排),并在日报标注"近似来源"
- **月度统计**：`data/index.jsonl` 可直接算"连续上榜王"/"周冠军"——每月 1 号顺手跑个统计脚本即可(待加)

## 运行

- 自动：GitHub Actions 每天 07:30(北京时间)跑一次并自动 commit
- 手动:`GITHUB_TOKEN=$(gh auth token) python trending.py`
- 手动触发:Actions 页 → daily-trending → Run workflow

## 已知边界

- GitHub trending 页面是事实标准源但无官方 API,HTML 结构变更会导致解析降级到搜索近似(日报会标注,便于发现)
- trending 只反映"今日热度",不代表长期趋势;长期榜用 `data/index.jsonl` 自行聚合
