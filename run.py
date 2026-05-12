"""月度运行总入口"""
from src import fetch_data, fetch_cpi_forecast, scoring, build_dashboard

def main():
    print("=" * 50)
    print("中国10年期实际收益率月度跟踪 - 开始运行")
    print("=" * 50)

    # 1. 抓取宏观数据
    fetch_data.fetch_all()

    # 2. 抓取 CPI 一致预期（复旦-ZEW，失败则沿用旧值）
import os
    manual_url = os.environ.get("FDDI_ARTICLE_URL", "").strip() or None
    cpi_fc = fetch_cpi_forecast.fetch_and_save_safe(manual_url=manual_url)

    # 3. 打分（示例输入，后续可接入真实抓取结果）
    demo_inputs = {
        "fiscal_exp_yoy": 3.0, "fiscal_rev_yoy": -1.0,
        "re_sales": -12.0, "re_price": -4.0, "re_invest": -9.0,
        "shrz_yoy": 8.0, "m2_yoy": 7.5,
        "ppi_now": -2.5, "ppi_3m_ago": -2.0,
        "usdcny_now": 7.25, "usdcny_3m_ago": 7.15,
    }
    scoring.calc_total_adjustment(demo_inputs)

    # 4. 生成看板
    build_dashboard.build()

    print("=" * 50)
    print("✅ 全部完成！查看 docs/index.html")
    print("=" * 50)

if __name__ == "__main__":
    main()
