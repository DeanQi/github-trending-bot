#!/usr/bin/env python3
"""
GitHub Trending 日报生成器（GitHub Actions 版）
每天抓取 GitHub Trending 日榜，筛选高星/快速增长项目，生成中文 Markdown 日报并发送到飞书。

运行环境：GitHub Actions
依赖：pip install requests beautifulsoup4 deep-translator
Secrets 配置：
  - FEISHU_WEBHOOK：飞书机器人 Webhook 地址
  - FEISHU_SECRET：飞书机器人签名校验密钥
"""

import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import hashlib
import hmac
import base64
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ============ 配置（敏感信息从 GitHub Secrets 环境变量读取）============
FEISHU_WEBHOOK = os.environ["FEISHU_WEBHOOK"]
FEISHU_SECRET = os.environ["FEISHU_SECRET"]

# GitHub API token（GitHub Actions 中自动注入，限速 5000次/小时）
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# 筛选阈值
HIGH_STAR_THRESHOLD = 5000      # 高星项目最低星数
FAST_GROW_THRESHOLD = 100       # 快速增长项目最低今日新增星数

# 输出目录
OUTPUT_DIR = os.path.join(os.environ.get("GITHUB_WORKSPACE", "."), "output")

# 编程语言中文映射表
LANG_MAP = {
    "Python": "Python",
    "JavaScript": "JavaScript",
    "TypeScript": "TypeScript",
    "Java": "Java",
    "Go": "Go",
    "Rust": "Rust",
    "C": "C",
    "C++": "C++",
    "C#": "C#",
    "Ruby": "Ruby",
    "PHP": "PHP",
    "Swift": "Swift",
    "Kotlin": "Kotlin",
    "Dart": "Dart",
    "Scala": "Scala",
    "R": "R",
    "Shell": "Shell",
    "Lua": "Lua",
    "Zig": "Zig",
    "Elixir": "Elixir",
    "Clojure": "Clojure",
    "Haskell": "Haskell",
    "OCaml": "OCaml",
    "Vue": "Vue",
    "HTML": "HTML",
    "CSS": "CSS",
    "SCSS": "SCSS",
    "Svelte": "Svelte",
    "Jupyter Notebook": "Jupyter Notebook",
    "MDX": "MDX",
    "Vim Script": "Vim Script",
    "Emacs Lisp": "Emacs Lisp",
    "Objective-C": "Objective-C",
    "Perl": "Perl",
    "TeX": "TeX",
    "Dockerfile": "Dockerfile",
    "Makefile": "Makefile",
    "CMake": "CMake",
    "Batchfile": "Batchfile",
    "PowerShell": "PowerShell",
    "Unknown": "未知",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
API_HEADERS = {"Accept": "application/vnd.github.v3+json"}
if GITHUB_TOKEN:
    API_HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def fetch_trending_page(since="daily"):
    """抓取 GitHub Trending 页面原始 HTML"""
    url = f"https://github.com/trending?since={since}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_trending_html(html):
    """
    解析 Trending 页面 HTML，提取项目列表。
    返回: list[dict]，每个 dict 包含 owner, name, description, language, total_stars, forks, stars_today
    """
    soup = BeautifulSoup(html, "html.parser")
    repos = []

    for article in soup.select("article.Box-row"):
        repo = {}

        h2_link = article.select_one("h2 a")
        if not h2_link:
            continue
        href = h2_link.get("href", "").strip()
        parts = href.strip("/").split("/")
        if len(parts) >= 2:
            repo["owner"] = parts[0]
            repo["name"] = parts[1]
        else:
            continue

        desc_el = article.select_one("p.col-9")
        repo["description"] = desc_el.get_text(strip=True) if desc_el else ""

        lang_el = article.select_one('[itemprop="programmingLanguage"]')
        repo["language"] = lang_el.get_text(strip=True) if lang_el else "Unknown"

        star_fork_links = article.select("a.Link--muted")
        repo["total_stars"] = 0
        repo["forks"] = 0
        for link in star_fork_links:
            href_s = link.get("href", "")
            text = link.get_text(strip=True).replace(",", "")
            if "/stargazers" in href_s:
                try:
                    repo["total_stars"] = int(text)
                except ValueError:
                    pass
            elif "/forks" in href_s:
                try:
                    repo["forks"] = int(text)
                except ValueError:
                    pass

        stars_today_el = article.select_one("span.d-inline-block.float-sm-right")
        if not stars_today_el:
            stars_today_el = article.select_one(".float-sm-right")
        if stars_today_el:
            txt = stars_today_el.get_text(strip=True)
            try:
                repo["stars_today"] = int(txt.split()[0].replace(",", ""))
            except (ValueError, IndexError):
                repo["stars_today"] = 0
        else:
            repo["stars_today"] = 0

        repos.append(repo)

    return repos


def translate_descriptions(repos):
    """
    将项目描述翻译为中文，同时对语言名做映射。
    使用 deep-translator (Google Translate 免费接口)，失败时保留原文。
    """
    # 收集所有非空描述
    descs = [r["description"] for r in repos if r["description"]]
    if not descs:
        return repos

    print(f"  [翻译] 共 {len(descs)} 条描述待翻译...")
    translated = {}
    batch_size = 20

    for i in range(0, len(descs), batch_size):
        batch = descs[i : i + batch_size]
        try:
            # deep-translator 单条翻译，逐条调用
            for text in batch:
                if len(text) < 3:
                    translated[text] = text
                    continue
                try:
                    result = GoogleTranslator(source="auto", target="zh-CN").translate(text)
                    translated[text] = result
                    time.sleep(0.3)  # 限速
                except Exception:
                    translated[text] = text
        except Exception as e:
            print(f"  [翻译] 批次失败: {e}，保留原文")
            for text in batch:
                if text not in translated:
                    translated[text] = text
        time.sleep(0.5)

    # 回填翻译结果
    for r in repos:
        if r["description"] and r["description"] in translated:
            r["description_cn"] = translated[r["description"]]
        else:
            r["description_cn"] = r["description"]

    # 语言名映射
    for r in repos:
        r["language_cn"] = LANG_MAP.get(r.get("language", ""), r.get("language", "未知"))

    success_count = sum(1 for k, v in translated.items() if v != k and k)
    print(f"  [翻译] 完成，成功翻译 {success_count}/{len(translated)} 条")
    return repos


def enrich_with_api(repos):
    """
    用 GitHub REST API 补充总 Star 数、Fork 数、最近更新时间、是否归档等。
    失败时静默降级。
    """
    for i, repo in enumerate(repos):
        url = f"https://api.github.com/repos/{repo['owner']}/{repo['name']}"
        try:
            resp = requests.get(url, headers=API_HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                repo["total_stars"] = data.get("stargazers_count", repo["total_stars"])
                repo["forks"] = data.get("forks_count", repo["forks"])
                repo["updated_at"] = data.get("updated_at", "")
                repo["archived"] = data.get("archived", False)
                repo["topics"] = data.get("topics", [])
            elif resp.status_code == 403:
                remaining = resp.headers.get("X-RateLimit-Remaining", "0")
                if remaining == "0":
                    print(f"  [API] 速率限制已达，停止 API 补充 (已完成 {i+1}/{len(repos)})")
                    break
            elif resp.status_code == 404:
                pass
        except Exception as e:
            print(f"  [API] 获取 {repo['owner']}/{repo['name']} 失败: {e}")
        time.sleep(0.15)
    return repos


def classify_repos(repos):
    """按高星项目和快速增长项目分类"""
    high_star = [r for r in repos if r.get("total_stars", 0) >= HIGH_STAR_THRESHOLD]
    fast_grow = [r for r in repos if r.get("stars_today", 0) >= FAST_GROW_THRESHOLD]
    high_star_names = {(r["owner"], r["name"]) for r in high_star}
    fast_grow = [r for r in fast_grow if (r["owner"], r["name"]) not in high_star_names]
    return high_star, fast_grow


def generate_md_report(repos, high_star, fast_grow):
    """生成中文 Markdown 日报"""
    now = datetime.now(timezone(timedelta(hours=8)))
    date_str = now.strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# GitHub Trending 日报 — {date_str}")
    lines.append("")
    lines.append(f"> 共收录 {len(repos)} 个热门项目 | 生成时间 {now.strftime('%H:%M')} CST")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 高星项目（总星数 ≥ 5,000）")
    lines.append("")
    lines.append(f"共 {len(high_star)} 个")
    lines.append("")
    if high_star:
        for i, r in enumerate(high_star, 1):
            lang = r.get("language_cn", r.get("language", "未知"))
            url = f"https://github.com/{r['owner']}/{r['name']}"
            desc = r.get("description_cn", r.get("description", ""))[:150]
            archived = " `[已归档]`" if r.get("archived") else ""
            lines.append(f"**{i}. [{r['owner']}/{r['name']}]({url})**{archived}")
            if desc:
                lines.append(f"   {desc}")
            lines.append(f"   `{lang}` | ⭐ {r.get('total_stars', 0):,} | 🍴 {r.get('forks', 0):,} | 📈 今日 +{r.get('stars_today', 0):,}")
            lines.append("")
    else:
        lines.append("今日无符合条件的高星项目")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 快速增长项目（今日新增 ≥ 100 Star）")
    lines.append("")
    lines.append(f"共 {len(fast_grow)} 个")
    lines.append("")
    if fast_grow:
        for i, r in enumerate(fast_grow, 1):
            lang = r.get("language_cn", r.get("language", "未知"))
            url = f"https://github.com/{r['owner']}/{r['name']}"
            desc = r.get("description_cn", r.get("description", ""))[:150]
            archived = " `[已归档]`" if r.get("archived") else ""
            lines.append(f"**{i}. [{r['owner']}/{r['name']}]({url})**{archived}")
            if desc:
                lines.append(f"   {desc}")
            lines.append(f"   `{lang}` | ⭐ {r.get('total_stars', 0):,} | 📈 今日 +{r.get('stars_today', 0):,}")
            lines.append("")
    else:
        lines.append("今日无符合条件的快速增长项目")
        lines.append("")

    lines.append("---")
    lines.append(f"*由 GitHub Trending 日报机器人自动生成 | [查看完整 Trending](https://github.com/trending?since=daily)*")

    return "\n".join(lines)


def feishu_sign(timestamp):
    """飞书签名校验"""
    string_to_sign = f"{timestamp}\n{FEISHU_SECRET}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def send_to_feishu(md_content):
    """发送消息到飞书自定义机器人"""
    timestamp = str(int(time.time()))
    sign = feishu_sign(timestamp)

    text_content = md_content[:15000]
    if len(md_content) > 15000:
        text_content = text_content + "\n\n... (已截断)"

    payload = {
        "timestamp": timestamp,
        "sign": sign,
        "msg_type": "text",
        "content": {
            "text": text_content,
        },
    }

    resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始抓取 GitHub Trending...")

    # 1. 抓取 Trending 页面
    print("  [1/6] 抓取 Trending 页面...")
    try:
        html = fetch_trending_page("daily")
    except Exception as e:
        print(f"  [ERROR] 抓取失败: {e}")
        sys.exit(1)

    # 2. 解析 HTML
    print("  [2/6] 解析 HTML...")
    repos = parse_trending_html(html)
    print(f"  解析到 {len(repos)} 个项目")

    if not repos:
        print("  [ERROR] 未解析到任何项目，可能是页面结构变化")
        debug_path = os.path.join(OUTPUT_DIR, "debug_trending.html")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  原始 HTML 已保存到 {debug_path}")
        sys.exit(1)

    # 3. 用 API 补充信息
    print("  [3/6] 调用 GitHub API 补充信息...")
    repos = enrich_with_api(repos)

    # 4. 翻译描述和语言名
    print("  [4/6] 翻译描述为中文...")
    repos = translate_descriptions(repos)

    # 5. 分类
    print("  [5/6] 分类筛选...")
    high_star, fast_grow = classify_repos(repos)
    print(f"  高星项目: {len(high_star)} | 快速增长: {len(fast_grow)}")

    # 6. 生成日报
    print("  [6/6] 生成日报并发送...")
    md_report = generate_md_report(repos, high_star, fast_grow)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, f"github_trending_{datetime.now().strftime('%Y%m%d')}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"  日报已保存: {report_path}")

    try:
        result = send_to_feishu(md_report)
        print(f"  飞书发送结果: {result}")
    except Exception as e:
        print(f"  [WARN] 飞书发送失败: {e}")

    print("\n" + "=" * 60)
    print(md_report[:1500])
    print("=" * 60)
    print("[完成]")


if __name__ == "__main__":
    main()
