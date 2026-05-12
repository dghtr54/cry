"""抓取宏观数据"""
import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def fetch_cpi_ppi():
    """抓取 CPI、核心CPI、PPI 同比"""
    print("  抓取 CPI/PPI...")
    
    # CPI 月度数据（包含同比）
    cpi = ak.macro_china_cpi_monthly()
    # 列名通常是：月份, 全国-当月, 全国-同比, 全国-环比, 城市-当月, 城市-同比, ...
    
    # PPI 年度数据（同比）
    ppi = ak.macro_china_ppi_yearly()
    # 列名通常是：月份, 当月, 同比, 环比, 累计
    
    return cpi, ppi

def fetch_bond_yield():
    """抓取10年期国债到期收益率"""
    print("  抓取 10年期国债收益率...")
    df = ak.bond_china_yield(start_date="20200101",
                             end_date=datetime.now().strftime("%Y%m%d"))
    df = df[df["曲线名称"] == "中债国债收益率曲线"]
    return df[["日期", "10年"]]

def fetch_real_estate():
    """抓取地产数据：销售、二手房价、投资"""
    print("  抓取 地产数据...")
    sales = ak.macro_china_real_estate()  # 房地产开发投资等
    return sales

def fetch_social_finance():
    """社融、M2"""
    print("  抓取 社融/M2...")
    shrzgm = ak.macro_china_shrzgm()  # 社融存量
    m2 = ak.macro_china_money_supply()  # 货币供应
    return shrzgm, m2

def fetch_fx():
    """USDCNY 汇率"""
    print("  抓取 汇率...")
    fx = ak.currency_boc_safe()
    return fx

def fetch_fiscal():
    """财政收支"""
    print("  抓取 财政数据...")
    fiscal_rev = ak.macro_china_fiscal_revenue()
    fiscal_exp = ak.macro_china_fiscal_expenditure()
    return fiscal_rev, fiscal_exp

def fetch_all():
    """统一抓取，保存到 raw_*.csv"""
    print("📥 开始抓取数据...")
    
    results = {}
    
    # 1. CPI/PPI
    try:
        cpi, ppi = fetch_cpi_ppi()
        results["cpi"] = cpi
        results["ppi"] = ppi
        print("✅ CPI/PPI")
    except Exception as e:
        print(f"⚠️ CPI/PPI 抓取失败：{e}")
    
    # 2. 国债收益率
    try:
        results["bond"] = fetch_bond_yield()
        print("✅ 10年期国债收益率")
    except Exception as e:
        print(f"⚠️ 国债收益率抓取失败：{e}")
    
    # 3. 地产
    try:
        results["real_estate"] = fetch_real_estate()
        print("✅ 地产数据")
    except Exception as e:
        print(f"⚠️ 地产数据抓取失败：{e}")
    
    # 4. 社融/M2
    try:
        shrzgm, m2 = fetch_social_finance()
        results["social_finance"] = shrzgm
        results["m2"] = m2
        print("✅ 社融/M2")
    except Exception as e:
        print(f"⚠️ 社融/M2 抓取失败：{e}")
    
    # 5. 汇率
    try:
        results["fx"] = fetch_fx()
        print("✅ 汇率")
    except Exception as e:
        print(f"⚠️ 汇率抓取失败：{e}")
    
    # 6. 财政
    try:
        fiscal_rev, fiscal_exp = fetch_fiscal()
        results["fiscal_revenue"] = fiscal_rev
        results["fiscal_expenditure"] = fiscal_exp
        print("✅ 财政数据")
    except Exception as e:
        print(f"⚠️ 财政数据抓取失败：{e}")
    
    # 保存所有数据
    for name, df in results.items():
        if df is not None and not df.empty:
            output_file = DATA_DIR / f"raw_{name}.csv"
            df.to_csv(output_file, index=False, encoding="utf-8-sig")
            print(f"  → 已保存：{output_file.name}")
    
    print("✅ 原始数据已保存到 data/raw_*.csv")
    return results

if __name__ == "__main__":
    fetch_all()
