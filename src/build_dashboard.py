"""生成月度看板（HTML + Plotly 图表）"""
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go

# 路径配置
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
DOCS_DIR.mkdir(exist_ok=True)

def load_raw_data():
    """读取原始数据文件，返回当月最新值"""
    data = {}
    
    # 1. 国债收益率
    bond_file = DATA_DIR / "raw_bond.csv"
    if bond_file.exists():
        df_bond = pd.read_csv(bond_file)
        if not df_bond.empty and "bond_yield_10y" in df_bond.columns:
            data["bond_yield_10y"] = df_bond["bond_yield_10y"].iloc[-1]
    
    # 2. CPI
    cpi_file = DATA_DIR / "raw_cpi.csv"
    if cpi_file.exists():
        df_cpi = pd.read_csv(cpi_file)
        if not df_cpi.empty:
            if "cpi_yoy" in df_cpi.columns:
                data["cpi_yoy"] = df_cpi["cpi_yoy"].iloc[-1]
            if "core_cpi_yoy" in df_cpi.columns:
                data["core_cpi_yoy"] = df_cpi["core_cpi_yoy"].iloc[-1]
    
    # 3. PPI
    ppi_file = DATA_DIR / "raw_ppi.csv"
    if ppi_file.exists():
        df_ppi = pd.read_csv(ppi_file)
        if not df_ppi.empty and "ppi_yoy" in df_ppi.columns:
            data["ppi_yoy"] = df_ppi["ppi_yoy"].iloc[-1]
    
    # 4. CPI 预期
    cpi_fc_file = DATA_DIR / "cpi_forecast.json"
    if cpi_fc_file.exists():
        with open(cpi_fc_file, "r", encoding="utf-8") as f:
            cpi_fc = json.load(f)
            data["cpi_forecast"] = cpi_fc.get("forecast_value", None)
    
    # 5. 政策修正项
    scoring_file = DATA_DIR / "auto_scoring_result.json"
    if scoring_file.exists():
        with open(scoring_file, "r", encoding="utf-8") as f:
            scoring = json.load(f)
            data["policy_adj"] = scoring.get("total_adjustment", 0.0)
    
    return data

def calculate_inflation_expectation(row):
    """计算估算通胀预期"""
    core_avg = row.get("core_cpi_12m_avg", 0)
    cpi_fc = row.get("cpi_forecast", 0)
    policy_adj = row.get("policy_adj", 0)
    
    inflation_exp = 0.5 * cpi_fc + 0.5 * core_avg + policy_adj
    return inflation_exp

def update_historical(new_data):
    """更新 historical.csv，追加或更新当月数据"""
    hist_file = DATA_DIR / "historical.csv"
    
    # 当前年月
    current_month = datetime.now().strftime("%Y-%m")
    
    # 读取历史数据
    if hist_file.exists():
        df_hist = pd.read_csv(hist_file)
    else:
        df_hist = pd.DataFrame(columns=[
            "date", "bond_yield_10y", "cpi_yoy", "core_cpi_yoy", "ppi_yoy",
            "core_cpi_12m_avg", "cpi_forecast", "policy_adj",
            "inflation_exp", "real_yield"
        ])
    
    # 构造新行
    new_row = {
        "date": current_month,
        "bond_yield_10y": new_data.get("bond_yield_10y", None),
        "cpi_yoy": new_data.get("cpi_yoy", None),
        "core_cpi_yoy": new_data.get("core_cpi_yoy", None),
        "ppi_yoy": new_data.get("ppi_yoy", None),
        "cpi_forecast": new_data.get("cpi_forecast", None),
        "policy_adj": new_data.get("policy_adj", 0.0),
    }
    
    # 计算 core_cpi_12m_avg（需要历史数据）
    if len(df_hist) >= 12:
        recent_12 = df_hist.tail(12)["core_cpi_yoy"].dropna()
        if len(recent_12) > 0:
            new_row["core_cpi_12m_avg"] = recent_12.mean()
    else:
        # 不足12个月，用现有数据均值
        if "core_cpi_yoy" in df_hist.columns:
            new_row["core_cpi_12m_avg"] = df_hist["core_cpi_yoy"].dropna().mean()
    
    # 计算估算通胀预期
    new_row["inflation_exp"] = calculate_inflation_expectation(new_row)
    
    # 计算实际收益率
    if new_row["bond_yield_10y"] is not None and new_row["inflation_exp"] is not None:
        new_row["real_yield"] = new_row["bond_yield_10y"] - new_row["inflation_exp"]
    
    # 如果当月已存在，则更新；否则追加
    if current_month in df_hist["date"].values:
        df_hist.loc[df_hist["date"] == current_month, list(new_row.keys())] = list(new_row.values())
    else:
        df_hist = pd.concat([df_hist, pd.DataFrame([new_row])], ignore_index=True)
    
    # 保存
    df_hist.to_csv(hist_file, index=False)
    print(f"✅ historical.csv 已更新（当前月份：{current_month}）")
    
    return df_hist

def create_charts(df):
    """生成 Plotly 图表"""
    # 确保 date 列是 datetime 类型
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    
    # 图表1：10年期国债收益率
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df["date"],
        y=df["bond_yield_10y"],
        mode="lines+markers",
        name="10年期国债收益率",
        line=dict(color="blue", width=2)
    ))
    fig1.update_layout(
        title="10年期国债收益率",
        xaxis_title="",
        yaxis_title="%",
        hovermode="x unified",
        template="plotly_white"
    )
    
    # 图表2：估算通胀预期
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df["date"],
        y=df["inflation_exp"],
        mode="lines+markers",
        name="估算通胀预期",
        line=dict(color="orange", width=2)
    ))
    fig2.update_layout(
        title="估算通胀预期",
        xaxis_title="",
        yaxis_title="%",
        hovermode="x unified",
        template="plotly_white"
    )
    
    # 图表3：估算实际收益率
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=df["date"],
        y=df["real_yield"],
        mode="lines+markers",
        name="估算实际收益率",
        line=dict(color="green", width=2)
    ))
    fig3.update_layout(
        title="估算实际收益率",
        xaxis_title="",
        yaxis_title="%",
        hovermode="x unified",
        template="plotly_white"
    )
    
    return fig1, fig2, fig3

def build():
    """主函数：更新数据 + 生成看板"""
    print("📊 开始生成看板...")
    
    # 1. 读取原始数据
    new_data = load_raw_data()
    print(f"  读取到原始数据：{new_data}")
    
    # 2. 更新 historical.csv
    df_hist = update_historical(new_data)
    
    # 3. 生成图表
    if len(df_hist) == 0:
        print("⚠️ historical.csv 为空，无法生成图表")
        return
    
    fig1, fig2, fig3 = create_charts(df_hist)
    
    # 4. 读取 CPI 预期和打分信息（用于页面展示）
    cpi_fc_file = DATA_DIR / "cpi_forecast.json"
    cpi_info = {}
    if cpi_fc_file.exists():
        with open(cpi_fc_file, "r", encoding="utf-8") as f:
            cpi_info = json.load(f)
    
    scoring_file = DATA_DIR / "auto_scoring_result.json"
    score = {}
    if scoring_file.exists():
        with open(scoring_file, "r", encoding="utf-8") as f:
            score = json.load(f)
    
    # 5. 构造打分明细表格
    score_html = ""
    if score:
        score_html = f"""
        <h2>本月政策/周期修正项明细</h2>
        <table border="1" cellpadding="8" style="border-collapse:collapse; margin: 20px 0;">
          <tr style="background:#f0f0f0"><th>分项</th><th>得分</th><th>说明</th></tr>
          <tr><td>财政</td><td>{score.get('fiscal', {}).get('score', 0):+.2f}%</td><td>{score.get('fiscal', {}).get('desc', '')}</td></tr>
          <tr><td>地产</td><td>{score.get('real_estate', {}).get('score', 0):+.2f}%</td><td>{score.get('real_estate', {}).get('desc', '')}</td></tr>
          <tr><td>信用</td><td>{score.get('credit', {}).get('score', 0):+.2f}%</td><td>{score.get('credit', {}).get('desc', '')}</td></tr>
          <tr><td>PPI</td><td>{score.get('ppi', {}).get('score', 0):+.2f}%</td><td>{score.get('ppi', {}).get('desc', '')}</td></tr>
          <tr><td>汇率</td><td>{score.get('fx', {}).get('score', 0):+.2f}%</td><td>{score.get('fx', {}).get('desc', '')}</td></tr>
          <tr style="background:#fffacd"><td><b>合计(封顶±0.5%)</b></td><td><b>{score.get('capped_total', 0):+.2f}%</b></td><td></td></tr>
        </table>
        """
    
    # 6. 生成 HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中国10年期实际收益率月度跟踪</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            text-align: center;
            color: #333;
        }}
        .info-box {{
            background: #f0f8ff;
            padding: 15px;
            border-left: 4px solid #4a90e2;
            margin: 20px 0;
        }}
        .chart {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .footer {{
            color: #888;
            font-size: 12px;
            text-align: center;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <h1>中国10年期实际收益率月度跟踪</h1>
    
    <div class="info-box">
        📊 <b>未来12个月CPI一致预期：{cpi_info.get('forecast_value', 'N/A')}%</b><br>
        来源：<a href="{cpi_info.get('source_url', '#')}" target="_blank">{cpi_info.get('source', '未知')}</a> | 
        更新：{cpi_info.get('updated', 'N/A')}
        {' ⚠️ 自动抓取失败，使用上期值' if cpi_info.get('fetch_status') == 'failed_used_cache' else ''}
    </div>
    
    <div class="chart" id="chart1"></div>
    <div class="chart" id="chart2"></div>
    <div class="chart" id="chart3"></div>
    
    {score_html}
    
    <div class="footer">
        最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>
    
    <script>
        var chart1 = {fig1.to_json()};
        Plotly.newPlot('chart1', chart1.data, chart1.layout);
        
        var chart2 = {fig2.to_json()};
        Plotly.newPlot('chart2', chart2.data, chart2.layout);
        
        var chart3 = {fig3.to_json()};
        Plotly.newPlot('chart3', chart3.data, chart3.layout);
    </script>
</body>
</html>
"""
    
    # 7. 保存 HTML
    output_file = DOCS_DIR / "index.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ 看板已生成：{output_file}")

if __name__ == "__main__":
    build()
