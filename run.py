"""月度运行总入口"""
from src import fetch_data, scoring, build_dashboard
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

def main():
    print("=" * 50)
    print("中国10年期实际收益率月度跟踪 - 开始运行")
    print("=" * 50)
    
    # 1. 抓取数据
    fetch_data.fetch_all()
    
    # 2. 计算打分（这里用示例输入，实际应从抓取结果中解析）
    # TODO：根据 data/raw_*.csv 解析出真实指标值后传入
    demo_inputs = {
        "fiscal_exp_yoy": 3.0, "fiscal_rev_yoy": -1.0,
        "re_sales": -12.0, "re_price": -4.0, "re_invest": -9.0,
        "shrz_yoy": 8.0, "m2_yoy": 7.5,
        "ppi_now": -2.5, "ppi_3m_ago": -2.0,
        "usdcny_now": 7.25, "usdcny_3m_ago": 7.15,
    }
    scoring.calc_total_adjustment(demo_inputs)
    
    # 3. 生成看板
    build_dashboard.build()
    
    print("=" * 50)
    print("✅ 全部完成！查看 docs/index.html")
    print("=" * 50)

if __name__ == "__main__":
    main()
