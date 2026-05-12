"""中国10年期实际收益率月度跟踪 - 总入口
每月自动运行：抓取数据 → 抓取CPI预期 → 打分 → 生成看板
"""
import os
import traceback

from src import fetch_data, fetch_cpi_forecast, scoring, build_dashboard

def safe_run(name, func, *args, **kwargs):
    """安全运行某个步骤，失败也不中断整个流程"""
    try:
        result = func(*args, **kwargs)
        print(f"✅ [{name}] 完成")
        return result
    except Exception as e:
        print(f"⚠️ [{name}] 失败：{e}")
        traceback.print_exc()
        return None

def main():
    print("=" * 60)
    print("中国10年期实际收益率月度跟踪 - 开始运行")
    print("=" * 60)

    # 1. 抓取宏观数据（CPI、PPI、国债、社融、M2、地产、汇率等）
    print("\n--- 步骤 1/4：抓取宏观数据 ---")
    safe_run("fetch_data", fetch_data.fetch_all)

    # 2. 抓取 CPI 一致预期（复旦-ZEW，失败则沿用旧值）
    print("\n--- 步骤 2/4：抓取 CPI 一致预期 ---")
    manual_url = os.environ.get("FDDI_ARTICLE_URL", "").strip() or None
    cpi_fc = safe_run(
        "fetch_cpi_forecast",
        fetch_cpi_forecast.fetch_and_save_safe,
        manual_url=manual_url,
    )
    if cpi_fc:
        print(f"  本月使用 CPI 预期：{cpi_fc['forecast_value']}%"
              f"（来源：{cpi_fc.get('source', 'N/A')}）")

    # 3. 政策/周期修正项打分（示例输入，实际可接入自动抓取的数据）
    print("\n--- 步骤 3/4：政策/周期修正项打分 ---")
    demo_inputs = {
        "fiscal_exp_yoy": 3.0,
        "fiscal_rev_yoy": -1.0,
        "re_sales": -12.0,
        "re_price": -4.0,
        "re_invest": -9.0,
        "shrz_yoy": 8.0,
        "m2_yoy": 7.5,
        "ppi_now": -2.5,
        "ppi_3m_ago": -2.0,
        "usdcny_now": 7.25,
        "usdcny_3m_ago": 7.15,
    }
    safe_run("scoring", scoring.calc_total_adjustment, demo_inputs)

    # 4. 生成看板（HTML 输出到 docs/index.html，供 GitHub Pages 发布）
    print("\n--- 步骤 4/4：生成看板 ---")
    safe_run("build_dashboard", build_dashboard.build)

    print("\n" + "=" * 60)
    print("✅ 全部流程结束")
    print("=" * 60)

if __name__ == "__main__":
    main()
