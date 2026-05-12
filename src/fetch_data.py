"""抓取宏观数据"""
import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def fetch_cpi_ppi():
    """抓取 CPI、核心CPI、PPI 同比"""
    cpi = ak.macro_china_cpi_monthly()  # CPI 月度
    ppi = ak.macro_china_ppi_yearly()   # PPI 同比
    return cpi, ppi

def fetch_bond_yield():
    """抓取10年期国债到期收益率"""
    df = ak.bond_china_yield(start_date="20200101",
                             end_date=datetime.now().strftime("%Y%m%d"))
    df = df[df["曲线名称"] == "中债国债收益率曲线"]
    return df[["日期", "10年"]]

def fetch_real_estate():
    """抓取地产数据：销售、二手房价、投资"""
    sales = ak.macro_china_real_estate()  # 房地产开发投资等
    return sales

def fetch_social_finance():
    """社融、M2"""
    shrzgm = ak.macro_china_shrzgm()  # 社融存量
    m2 = ak.macro_china_money_supply()  # 货币供应
    return shrzgm, m2

def fetch_fx():
    """USDCNY 汇率"""
    fx = ak.currency_boc_safe()
    return fx

def fetch_fiscal():
    """财政收支"""
    fiscal_rev = ak.macro_china_fiscal_revenue()
    fiscal_exp = ak.macro_china_fiscal_expenditure()
    return fiscal_rev, fiscal_exp

def fetch_all():
    """统一抓取，合并到 historical.csv"""
    print("📥 开始抓取数据...")
    
    results = {}
    try:
        results["cpi"], results["ppi"] = fetch_cpi_ppi()
        print("✅ CPI/PPI")
    except Exception as e:
        print(f"⚠️ CPI/PPI 抓取失败：{e}")
    
    try:
        results["bond"] = fetch_bond_yield()
        print("✅ 10年期国债收益率")
    except Exception as e:
        print(f"⚠️ 国债收益率抓取失败：{e}")
    
    # ... 其余指标
    
    # 简化版：把每个 DataFrame 保存
    for name, df in results.items():
        if df is not None:
            df.to_csv(DATA_DIR / f"raw_{name}.csv", index=False)
    
    print("✅ 原始数据已保存到 data/raw_*.csv")
    return results

if __name__ == "__main__":
    fetch_all()
