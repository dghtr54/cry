"""抓取复旦-ZEW 中国经济景气调查 中的未来12个月CPI一致预期
数据来源：复旦发展研究院金融研究中心（HTML 网页版）
示例：https://fddi.fudan.edu.cn/d7/28/c40448a775976/page.htm
"""
import re
import json
import os
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 复旦发展研究院 - 金融研究中心 报告列表页（可能需根据实际页面调整）
FDDI_LIST_URLS = [
    "https://fddi.fudan.edu.cn/jrjyzx/list.htm",
    "https://fddi.fudan.edu.cn/main.htm",
]

def find_latest_article_url():
    """在复旦 FDDI 列表页中找最新一期含"复旦-ZEW"或"CEP"的文章链接"""
    for list_url in FDDI_LIST_URLS:
        try:
            r = requests.get(list_url, headers=HEADERS, timeout=20)
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                title = (a.get_text() or "").strip()
                if ("复旦-ZEW" in title or "CEP" in title or "经济景气" in title) \
                   and ("解读" in title or "调查" in title or "报告" in title):
                    href = urljoin(list_url, a["href"])
                    print(f"  找到文章：{title}")
                    print(f"  URL：{href}")
                    return href, title
        except Exception as e:
            print(f"  ⚠️ 列表页 {list_url} 失败：{e}")
    return None, None

def fetch_article_html(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.encoding = r.apparent_encoding
    r.raise_for_status()
    return r.text

def extract_cpi_forecast(html):
    """从 HTML 中提取未来12个月CPI一致预期
    复旦报告典型表述："未来一年的通胀率为 0.71%"
    """
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator="\n")

    patterns = [
        r"未来\s*一\s*年.*?通[货胀]?[率涨胀]?.*?为\s*([+-]?\d+\.\d+)\s*%",
        r"未来\s*1\s*年.*?通[货胀]?[率涨胀]?.*?为\s*([+-]?\d+\.\d+)\s*%",
        r"未来\s*12\s*个月.*?通[货胀]?[率涨胀]?.*?为\s*([+-]?\d+\.\d+)\s*%",
        r"未来\s*一\s*年.*?CPI.*?([+-]?\d+\.\d+)\s*%",
        r"1\s*年.*?通胀率.*?([+-]?\d+\.\d+)\s*%",
        r"长期[通预].*?([+-]?\d+\.\d+)\s*%",  # 长期预测兜底
    ]

    for pat in patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            val = float(m.group(1))
            if -5 < val < 10:
                return val, pat, text

    # 调试用：保存全文，便于失败时人工排查
    debug_path = DATA_DIR / "fudan_zew_extracted_text.txt"
    debug_path.write_text(text, encoding="utf-8")
    raise ValueError(f"未匹配到 CPI 数值，原文已保存到 {debug_path}")

def load_cached():
    path = DATA_DIR / "cpi_forecast.json"
    if path.exists():
        return json.load(open(path, encoding="utf-8"))
    return {"forecast_value": 1.0, "source": "default", "updated": "N/A"}

def fetch_and_save(manual_url=None):
    """主流程
    manual_url: 可选，手动指定文章 URL（最稳，从 GitHub Action 输入或环境变量传入）
    """
    print("📥 抓取复旦-ZEW CPI 一致预期...")
    
    if manual_url:
        print(f"  使用手动指定 URL：{manual_url}")
        article_url = manual_url
        title = "手动指定"
    else:
        article_url, title = find_latest_article_url()
        if not article_url:
            raise RuntimeError("自动查找文章链接失败，请通过 workflow_dispatch 手动传入 article_url")

    html = fetch_article_html(article_url)
    cpi_value, matched_pattern, _ = extract_cpi_forecast(html)

    result = {
        "forecast_value": cpi_value,
        "source": "复旦-ZEW 中国经济景气调查（复旦发展研究院）",
        "source_url": article_url,
        "article_title": title,
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "matched_pattern": matched_pattern,
    }
    with open(DATA_DIR / "cpi_forecast.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ CPI 一致预期 = {cpi_value}%")
    return result

def fetch_and_save_safe(manual_url=None):
    try:
        return fetch_and_save(manual_url=manual_url)
    except Exception as e:
        print(f"⚠️ 自动抓取失败：{e}")
        cached = load_cached()
        print(f"   → 沿用旧值 {cached['forecast_value']}%（更新于 {cached.get('updated')}）")
        log_path = DATA_DIR / "cpi_forecast_alerts.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] 失败：{e}；沿用 {cached['forecast_value']}%\n")
        cached["fetch_status"] = "failed_used_cache"
        return cached

if __name__ == "__main__":
    # 支持环境变量传入手动 URL：FDDI_ARTICLE_URL=https://... python -m src.fetch_cpi_forecast
    manual = os.environ.get("FDDI_ARTICLE_URL", "").strip() or None
    fetch_and_save_safe(manual_url=manual)
