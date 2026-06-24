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
