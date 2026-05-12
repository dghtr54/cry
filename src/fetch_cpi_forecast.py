"""抓取复旦-ZEW 中国经济景气调查中的未来12个月CPI一致预期
方案 A：自动抓 PDF + 文本解析；失败时沿用旧值并写日志（配合方案C的Issue提醒人工核对）
"""
import re
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import pdfplumber
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CPIForecastBot/1.0)"}

# 复旦-ZEW 报告候选来源
SOURCES = [
    # ZEW 官网英文版（结构相对稳定，海外服务器访问无障碍）
    "https://www.zew.de/en/publications/zew-expertise-research-reports/research-reports/financial-market-survey-china",
    # 复旦经济学院（备用）
    "https://econ.fudan.edu.cn/",
]

def find_latest_pdf_url():
    """遍历候选来源，找出最新一期 PDF 链接"""
    for url in SOURCES:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(".pdf") and \
                   ("china" in href.lower() or "cep" in href.lower() or "zew" in href.lower()):
                    if href.startswith("/"):
                        from urllib.parse import urljoin
                        href = urljoin(url, href)
                    print(f"  找到 PDF：{href}")
                    return href
        except Exception as e:
            print(f"  ⚠️ {url} 访问失败：{e}")
            continue
    return None

def download_pdf(url, save_path):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    save_path.write_bytes(r.content)
    return save_path

def extract_cpi_forecast(pdf_path):
    """从复旦-ZEW PDF 提取未来12个月 CPI 通胀预期"""
    text_all = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:5]:   # 前5页通常包含汇总表
            text_all += (page.extract_text() or "") + "\n"

    # 多个正则候选（中英文 + 不同表述）
    patterns = [
        r"未来\s*12\s*个月.*?CPI.*?([+-]?\d+\.\d+)\s*%?",
        r"CPI.*?未来\s*12\s*个月.*?([+-]?\d+\.\d+)\s*%?",
        r"通[货胀].*?预期.*?12\s*个月.*?([+-]?\d+\.\d+)",
        r"inflation\s+rate.*?(?:next\s+)?12\s*months?.*?([+-]?\d+\.\d+)",
        r"CPI.*?(?:next\s+)?12\s*months?.*?([+-]?\d+\.\d+)",
        r"12.month.*?CPI.*?([+-]?\d+\.\d+)",
    ]

    for pat in patterns:
        m = re.search(pat, text_all, re.IGNORECASE | re.DOTALL)
        if m:
            val = float(m.group(1))
            if -5 < val < 10:   # 合理性检查
                return val, pat

    # 调试：保存提取到的文本片段，便于失败时人工排查
    debug_path = DATA_DIR / "fudan_zew_extracted_text.txt"
    debug_path.write_text(text_all, encoding="utf-8")
    raise ValueError(f"未匹配到合理 CPI 数值，文本已保存到 {debug_path} 供人工核查")

def load_cached():
    path = DATA_DIR / "cpi_forecast.json"
    if path.exists():
        return json.load(open(path, encoding="utf-8"))
    return {"forecast_value": 1.0, "source": "default", "updated": "N/A"}

def fetch_and_save():
    print("📥 抓取复旦-ZEW CPI 一致预期...")
    pdf_url = find_latest_pdf_url()
    if not pdf_url:
        raise RuntimeError("所有候选来源都未找到 PDF 链接")

    pdf_path = DATA_DIR / "fudan_zew_latest.pdf"
    download_pdf(pdf_url, pdf_path)
    print(f"  PDF 已下载：{pdf_path}")

    cpi_value, matched_pattern = extract_cpi_forecast(pdf_path)

    result = {
        "forecast_value": cpi_value,
        "source": "复旦-ZEW 中国经济景气调查",
        "source_url": pdf_url,
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "matched_pattern": matched_pattern,
    }
    with open(DATA_DIR / "cpi_forecast.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ CPI 一致预期 = {cpi_value}%")
    return result

def fetch_and_save_safe():
    """容错版：失败时沿用旧值 + 写日志"""
    try:
        return fetch_and_save()
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
    fetch_and_save_safe()
