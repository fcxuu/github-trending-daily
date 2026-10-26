# 自动化 RUNBOOK — 定时任务重建与每日执行手册

> **唯一权威流程文件**：定时任务的 prompt 只保留指针，执行细节一律以本文件为准。
> 本文件不含任何密钥；命令里的 `gh auth token` 只是占位符，由本机 gh CLI 提供。
> 固化于 2026-10-20（迁移前由旧会话 session-fe80c721 写定）。

---

## 0. 任务清单与归属

| 任务 | 计划 | 旧 id（挂在旧会话 session-fe80c721，已删） | 状态 |
|---|---|---|---|
| GitHub 日检 + 搜集播报 | daily 02:30 Asia/Shanghai | `schedule-7d3db050-e044-491b-9da4-e6f83aedeb67` | 已迁移 → 本会话 `schedule-168bce49-8b95-4c28-a29e-b13e76c8dfbf` |
| MemStack 月度记忆清理 | cron `0 2 1 * *` Asia/Shanghai | `schedule-9a5a1c79-c178-48e6-80e1-3ac83123bc37` | 已迁移 → 本会话 `schedule-34bff1f2-b12f-4dba-8db5-64c89bc2dbbf` |

**迁移规则**：`schedule_create` 永远绑定"当前会话"。因此**新会话只负责创建**（第 1 节）；**旧任务删除由旧会话完成**（第 5 节，宿主 RPC schedule/delete 支持跨会话）。新会话不要尝试删除旧任务。

> 2026-10-20 实测补记：宿主 RPC `schedule/delete` 确实支持跨会话删除——带旧任务 id + 旧会话 sessionId 调用即可（会话内 `schedule_delete` 工具则按当前会话隔离，会返回 `schedule_not_found`）。本次两条旧任务已由新会话删除完毕，第 5 节收尾。

---

## 1. 任务规格（新会话重建用，逐字使用）

### 1.1 GitHub 日检 + 搜集播报（每日 02:30）

- title: `GitHub 日检 + 搜集播报（每日 02:30）`
- kind: `daily`；time: `02:30:00.000`；timeZone: `Asia/Shanghai`
- prompt（瘦身体，逐字复制）：

```
【GitHub 日检 + 每日搜集播报——固定基础任务，无论当前主任务是什么都必须先完成】
02:30（Asia/Shanghai）触发 = 当日播报发送时刻。此时两采集仓 Actions（fcxuu/dsh-ecosystem-daily 04:00 / fcxuu/github-trending-daily 04:15，北京时间计划）尚未到点，且经常延迟数小时甚至整轮缺席 → 当日远端数据通常还不存在，一律先走本地兜底（第 2.2 节第 2 步），云端随后那轮会被守卫自动跳过，不会重复提交。
执行流程唯一权威：完整读取 /Users/fuchenxu/Desktop/💻开发/github-trending-daily/RUNBOOK.md，按第 2～3 节逐步执行（含网络绕过、本地兜底、播报格式）。
铁律：先 A 后 B；每天至少一次，不可因主任务跳过；平静日明确说"无重要更新"；每条网络命令必须带超时，防止回合挂死（2026-10-20 04:30 那轮就是挂死的）。
```

### 1.2 MemStack 月度记忆清理

- title: `MemStack 月度记忆清理`
- kind: `cron`；expression: `0 2 1 * *`；timeZone: `Asia/Shanghai`
- prompt（原样复制）：

```
【MemStack 月度清理提醒】每月 1 号到了，请用一条命令帮我过一遍记忆：

1) 先看状态：`mem status`（重点看 candidates_pending、events、index docs）
2) 审核候选：`mem candidates list --limit 40`，把不重要的 `mem candidates reject <id>`，重要的 `mem candidates accept <id>`
3) 查看事实：`mem facts list`，过期的用 `mem facts expire <id>`，要删的用 `mem facts forget <id>`
4) 归档瘦身（可选）：`mem prune-raw --keep 1`（每个会话只留最新归档）+ `mem vacuum`
5) 体检并重新取证：`mem doctor --deep`，然后 `mem backup`

请先告诉我第 1、2 步的结果，等我确认后再执行 3-5 步；不要自动删除任何东西。
```

### 1.3 创建后自检（新会话必做）

1. 用 schedule_list 核对两条任务的 title / 时间 / 时区 / prompt 与本节**逐字一致**；
2. 把两条新任务的 id 报告给用户；
3. **不要**执行第 5 节；除创建与核对外不做任何其它操作。

---

## 2. 每日执行流程（GitHub 日检 + 播报）

本地路径（2026-10-09 用户整理桌面后的新路径，勿用旧路径）：

- 生态仓 = `/Users/fuchenxu/Desktop/💻开发/dsh-ecosystem-daily`
- trending 仓 = `/Users/fuchenxu/Desktop/💻开发/github-trending-daily`

### 2.0 网络前置（先于一切 GitHub 调用）

2026-10-18 起 GitHub 链路严重抖动：`gh api` 大响应挂起、curl 报 `Error in the HTTP2 framing layer`、git pull 长时间卡死。已验证的绕过：

- API 探测：`curl -sS --http1.1 -m 25 -H "Authorization: Bearer $(gh auth token)" https://api.github.com/...`
- 数据文件直接取 raw：
  `curl -sS --http1.1 -m 25 [-H "Authorization: Bearer $(gh auth token)"] https://raw.githubusercontent.com/fcxuu/<repo>/main/<path>`
- git 一律加：`git -c http.version=HTTP/1.1 pull/push`（2–4 秒完成）
- `gh` 短命令可用（notifications / search issues）；**gh 的 contents API 大 JSON 不可靠，弃用**
- 任何网络命令挂起超过 25 秒按失败处理，换绕过重试，**绝不无限等待**
- `gh run view` / `gh run list` 在链路抖动时同样会挂（2026-10-23 实测挂死）→ 改用 curl Actions API：`curl -sS --http1.1 -m 25 -H "Authorization: Bearer $(gh auth token)" https://api.github.com/repos/fcxuu/<repo>/actions/runs/<id>[/jobs]`
- **run 顶层 status 会滞后**：顶层可能长期停在 `in_progress`，但 `/jobs` 里各步骤已 `completed success` → 以 **jobs 步骤** 判读成败；云端守卫生效的表现是「Run collector」「Commit & push」两步 `skipped`
- 两个采集仓都是 **private**：raw 取数必须带 `Authorization` 头，否则一律伪装成 404（易误判成"数据不存在"）

### 2.1 A 段：GitHub 账号日检

1. 通知：`gh api notifications --jq '.[] | {repo: .repository.full_name, reason, title: .subject.title}'`（空数组 = 无）
2. 提及：`gh search issues --mentions @fcxuu --limit 10`
3. 仓库动态：两采集仓最近提交（`repos/fcxuu/<repo>/commits?per_page=2`）；6 仓 open issue / PR 计数（search API：`repo:fcxuu/<R> type:issue state:open` 与 `type:pr`）
   6 仓 = dsh-ecosystem-daily / github-trending-daily / dsh-balance-meter / memstack / playground / computer-vision-projects

### 2.2 B 段：搜集播报

1. **先查远端当日数据是否已存在**：
   - 生态：`raw .../dsh-ecosystem-daily/main/data/digests/<当日YYYY-MM-DD>.md`（HTTP 200 = 在）
   - trending：`raw .../github-trending-daily/main/<当月YYYY-MM>.md` 里是否有 `^## <当日>$` 小节
2. 数据在 → 直接第 3 步；**不在 → 本地兜底**（顺序铁律：**先 commit 再 pull**，否则 pull 直接 Aborting）：

   ```
   cd "/Users/fuchenxu/Desktop/💻开发/dsh-ecosystem-daily" && GITHUB_TOKEN=$(gh auth token) python3 collector.py && git add -A && git commit -m "daily <日期> (本地兜底)" && git -c http.version=HTTP/1.1 pull --no-rebase -X ours origin main && git -c http.version=HTTP/1.1 push
   ```

   trending 仓同理（跑 `trending.py`）。推完两仓各 `gh workflow run daily.yml -R fcxuu/<repo>` 手动派发云端补一轮（云端守卫会自动跳过已有数据，不会重复提交），再用 `/jobs` 复核守卫是否 skipped；**推送结果一律以 git 侧 `origin/main` 为准**，raw 可能有数分钟 CDN 缓存滞后（带 cache-buster query 再验）。

3. 拉取当日数据（raw 地址同 2.0；trending 若显示"来源:近似搜索/官方页解析失败"，播报里注明数据为近似值）。
4. 按第 3 节格式交付播报。

### 2.3 活跃度守护

- 已验证：云端 commit（约 07:3x +08）与 02:30 本地兜底 commit 都会正确落到**当日**贡献格子。
- 若用户当日格子仍空：做一次**真实**的小提交（README 数据说明补充、`scripts/monthly_stats.py` 输出登记等），**禁止空提交/垃圾提交**。

---

## 3. 播报格式（精炼，勿倾倒原始数据）

1. A 段一行带过（通知 / 提及 / 6 仓 issue+PR，全 0 就一句话）
2. 表格：插件索引、技能索引（今日 / 昨日 / 新增 / 变更 / 消失；昨日基准直接用当日 md 里的"昨日"字段）
   - ⚠️ **口径说明（2026-10-23 体检确认）**：表格里的「消失」= 本日未进入采集快照（条目仍保留在索引、仅 last_seen 停更），**不等于被删除/下架**，不可当作生态崩塌指标。
   - 根因：采集上限 —— 技能源每个 topic 只取 top-100（`sort=updated&per_page=100`），当日技能快照上限约 300；索引是历史累计，所以技能「消失」≈ 存量 − 当日快照（近几日 2179 → 2278 → 2378，属口径现象）。
   - 插件侧同源但幅度小：当日快照 ~7072 / 存量 8040，真掉出（近 2 日活跃 → 今日未出现）仅 90。
   - 播报写法：技能「消失」一栏要么改称「本日未进快照」并注明，要么补一句「当日活跃 N 条」；当日活跃数可由 `data/index/*.jsonl` 中 `last_seen` 为今日的条目数直接算出（**不需要改 collector**）。
3. 来源健康度一行（npm / github-topics / awesome-catalog）
4. 版本亮点 3–5 个（优先：版本跳变、与 DSH/Agent 生态直接相关）
5. trending Top5 + 一句话点评
6. 异常如实报：某源 error、工作流失败、路径/口径变化
7. 平静日明确说"无重要更新"

---

## 4. MemStack 月度清理（每月 1 号 02:00）

- 流程即 1.2 的任务 prompt（1 状态 → 2 候选 → 3 事实 → 4 归档瘦身 → 5 体检备份）；**必须**先报第 1、2 步结果等用户确认，再执行 3–5。
- 红线（祖训）：不准修改 MemStack 源码（`~/Desktop/memstack`）、数据根（`~/Library/Application Support/memstack`）、`config.toml`、launchd 定时任务；只读不受限。
- 若 `mem` 不在 PATH：`"$HOME/Library/Application Support/memstack/bin/mem" ...`
- 已知状态：launchd 扫描 last exit code=1（partial_parse 警告），不影响 mem 命令使用。

---

## 5. 旧任务清理（2026-10-20 已执行完毕）

新任务创建并核对无误后，由旧会话通过宿主 RPC `schedule/delete` 删除：

- `schedule-7d3db050-e044-491b-9da4-e6f83aedeb67`（daily 04:30）——已删
- `schedule-9a5a1c79-c178-48e6-80e1-3ac83123bc37`（cron 0 2 1 * *）——已删

流程：先 `schedule/catalog` 双确认新旧并存 → 逐条 delete → catalog 复查只剩新任务。

2026-10-20 实测：新会话直接调宿主 RPC `schedule/delete`（payload = 旧任务 id + 旧会话 sessionId），两条均返回 `deleted: true`，旧会话 `schedule/list` 归零。

## 6. 变更记录

- 2026-10-26 v4：用户决定**撤销 rea 哨兵**（不再重点关注任何单一 repo）。删除原 §4「rea 哨兵」，原 §5/§6/§7 顺延为 §4/§5/§6；§1.1 prompt 改为「按第 2～3 节逐步执行」并去掉「rea 哨兵」；§3 播报格式去掉「rea 状态行」；定时任务 schedule-168bce49-8b95-4c28-a29e-b13e76c8dfbf 的 prompt 同步更新。历史 v1 记录保留原样。
- 2026-10-20 v1：由旧会话 session-fe80c721 固化。触发时间 07:30→04:30（2026-10-19 用户要求）；新增网络绕过（2.0）、rea 哨兵（4）、活跃度守护（2.3）、跨会话迁移规则（0/6）。
- 2026-10-23 v3：08:57 全链路体检（用户「再检查一下还有什么问题」）。结论：6 仓 0 failed run；两仓工作区干净、与 origin/main 0/0；索引无坏行（plugins 8040 / skills 2667 / trending index.jsonl 238）；10-04~10-23 产出连续 20 天、无重复；raw CDN 已追上（trending 10-23 小节 = 1、eco digest 200）；贡献格子 10-20/21/22/23 = L2/L2/L3/L1；本会话两条定时任务存活（下次 2026-10-24 02:30 日检、2026-11-01 02:00 MemStack 清理）。唯一真问题：技能「消失」口径失真（快照上限 ~300/天 vs 存量 2667 → 每日虚高约 89%），用户决定**先不动 collector.py**，仅在 §3 播报格式补口径免责说明与「当日活跃」写法。
- 2026-10-20 v2：触发时间 04:30→02:30（2026-10-20 用户要求）。§1.1 的 title / time / prompt 与 §0 / §2.3 同步；prompt 第 2 行改为「Actions 尚未到点 → 一律本地兜底优先」语义（02:30 时两仓 Actions 计划 04:00 / 04:15 还没开始，当日远端数据通常还不存在）；旧任务清理（§5）已由新会话跨会话 RPC 执行完毕。
