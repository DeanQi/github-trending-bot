---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: a09faa462e364ef9c5f711b55b4ab9b6_d44b5c886f9e11f1aabe5254007bceed
    ReservedCode1: ZvrEPDHYWggMQwcoK+9Zfpfvl17l3HUnK5ppiRnspnLZfzFeqcGxUKcaXeN3azv+bGI3JofKyMa3z+t5f2NZyQgZFGBXBPA+Kqkr+XoRQGssXcLlT03kHBE+53aFZ0kk1D33CutfmP5np7Exj8A2ZBgAPB5Wqa0MkfImEXE+bZdGCjJWFAAUTShnsCQ=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: a09faa462e364ef9c5f711b55b4ab9b6_d44b5c886f9e11f1aabe5254007bceed
    ReservedCode2: ZvrEPDHYWggMQwcoK+9Zfpfvl17l3HUnK5ppiRnspnLZfzFeqcGxUKcaXeN3azv+bGI3JofKyMa3z+t5f2NZyQgZFGBXBPA+Kqkr+XoRQGssXcLlT03kHBE+53aFZ0kk1D33CutfmP5np7Exj8A2ZBgAPB5Wqa0MkfImEXE+bZdGCjJWFAAUTShnsCQ=
---

# GitHub Trending 日报

每天自动抓取 [GitHub Trending](https://github.com/trending) 日榜，筛选高星项目和快速增长项目，生成 Markdown 日报并推送到飞书。

## 工作方式

- **调度**：GitHub Actions，每天北京时间 8:00 自动执行
- **产出**：Markdown 日报（存档到 Actions Artifact，保留 30 天）
- **推送**：飞书自定义机器人

## Secrets 配置

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名 | 值 |
|---|---|
| `FEISHU_WEBHOOK` | `https://open.feishu.cn/open-apis/bot/v2/hook/48ad1ecd-01bc-4de7-9aa2-96fcd803f3b2` |
| `FEISHU_SECRET` | `2CmB7gMN34zVxSllk5iMWb` |

## 手动触发

在仓库 Actions 页面 → "GitHub Trending 日报" → Run workflow 即可手动执行一次。
*（内容由AI生成，仅供参考）*
