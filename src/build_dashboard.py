"""生成可视化看板"""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs"
DOCS_DIR.mkdir(exist_ok=True)

def load_raw_data():
    """读取原始数据文件，返回当月最新值（适配 AkShare 格式）"""
    data = {}
    
    # 1. 国债收益率（raw_bond.csv 列名：日期,10年）
    bond_file = DATA_DIR / "raw_bond.csv"
    if bond_file.exists():
        df_bond = pd.read_csv(bond_file)
        if not df_bond.empty and "10年" in df_bond.columns:
            # 取最后一行的值
            data["10年期国债收益率"] = float(df_bond["10年"].iloc[-1])
    
    # 2. CPI（raw_cpi.csv 列名：月份, 全国-当月, 全国-同比, 全国-环比, ...）
    cpi_file = DATA_DIR / "raw_cpi.csv"
    if cpi_file.exists():
        df_cpi = pd.read_csv(cpi_file)
        if not df_cpi.empty:
            # 找到"全国-同比"列（CPI 同比）
            if "全国-同比" in df_cpi.columns:
                data["CPI同比"] = float(df_cpi["全国-同比"].iloc[-1])
            elif "同比" in df_cpi.columns:
                data["CPI同比"] = float(df_cpi["同比"].iloc[-1])
            
            # 核心 CPI：优先从 raw_core_cpi.csv 读取
            core_cpi_file = DATA_DIR / "raw_core_cpi.csv"
            if core_cpi_file.exists():
                df_core = pd.read_csv(core_cpi_file)
                if not df_core.empty and "核心CPI同比" in df_core.columns:
                    data["核心CPI同比"] = float(df_core["核心CPI同比"].iloc[-1])
            else:
                # 如果没有核心 CPI 数据，临时用 CPI 同比代替
                data["核心CPI同比"] = data.get("CPI同比", None)
    
    # 3. PPI（raw_ppi.csv 列名：月份, 当月, 同比, 环比, 累计）
    ppi_file = DATA_DIR / "raw_ppi.csv"
    if ppi_file.exists():
        df_ppi = pd.read_csv(ppi_file)
        if not df_ppi.empty and "同比" in df_ppi.columns:
            data["PPI同比"] = float(df_ppi["同比"].iloc[-1])
    
    # 4. CPI 预期
    cpi_fc_file = DATA_DIR / "cpi_forecast.json"
    if cpi_fc_file.exists():
        with open(cpi_fc_file, "r", encoding="utf-8") as f:
            cpi_fc = json.load(f)
            data["未来1年CPI一致预期"] = cpi_fc.get("forecast_value", None)
    
    # 5. 政策修正项
    scoring_file = DATA_DIR / "auto_scoring_result.json"
    if scoring_file.exists():
        with open(scoring_file, "r", encoding="utf-8") as f:
            scoring = json.load(f)
            data["政策修正项"] = scoring.get("total_adjustment", 0.0)
    
    return data

def calculate_inflation_expectation(data):
    """计算估算通胀预期和实际收益率"""
    # 计算过去12个月核心CPI均值
    hist_file = DATA_DIR / "historical.csv"
    if hist_file.exists():
        df_hist = pd.read_csv(hist_file)
        if len(df_hist) >= 12 and "核心CPI同比" in df_hist.columns:
            data["12M核心CPI均值"] = df_hist["核心CPI同比"].tail(12).mean()
        else:
            # 如果历史数据不足12个月，用当前核心CPI
            data["12M核心CPI均值"] = data.get("核心CPI同比", 0.0)
    else:
        data["12M核心CPI均值"] = data.get("核心CPI同比", 0.0)
    
    # 估算通胀预期 = 0.5 × 未来1年CPI预期 + 0.5 × 12M核心CPI均值 + 政策修正项
    cpi_forecast = data.get("未来1年CPI一致预期", 0.0)
    core_cpi_avg = data.get("12M核心CPI均值", 0.0)
    policy_adj = data.get("政策修正项", 0.0)
    
    data["估算通胀预期"] = 0.5 * cpi_forecast + 0.5 * core_cpi_avg + policy_adj
    
    # 估算实际收益率 = 10年期国债收益率 - 估算通胀预期
    bond_yield = data.get("10年期国债收益率", 0.0)
    data["估算实际收益率"] = bond_yield - data["估算通胀预期"]
    
    return data

def update_historical_data(data):
    """更新 historical.csv"""
    hist_file = DATA_DIR / "historical.csv"
    
    # 当前月份
    current_month = datetime.now().strftime("%Y-%m")
    
    # 准备新行数据
    new_row = {
        "月份": current_month,
        "10年期国债收益率": data.get("10年期国债收益率", None),
        "CPI同比": data.get("CPI同比", None),
        "核心CPI同比": data.get("核心CPI同比", None),
        "PPI同比": data.get("PPI同比", None),
        "12M核心CPI均值": data.get("12M核心CPI均值", None),
        "未来1年CPI一致预期": data.get("未来1年CPI一致预期", None),
        "政策修正项": data.get("政策修正项", None),
        "估算通胀预期": data.get("估算通胀预期", None),
        "估算实际收益率": data.get("估算实际收益率", None)
    }
    
    # 读取或创建历史数据
    if hist_file.exists():
        df = pd.read_csv(hist_file)
        # 如果当前月份已存在，更新；否则追加
        if current_month in df["月份"].values:
            df.loc[df["月份"] == current_month] = pd.Series(new_row)
        else:
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        df = pd.DataFrame([new_row])
    
    # 保存
    df.to_csv(hist_file, index=False, encoding="utf-8-sig")
    print(f"✅ 已更新 historical.csv（当前月份：{current_month}）")

def create_charts(df):
    """创建三个图表"""
    # 确保月份列是字符串格式
    df["月份"] = df["月份"].astype(str)
    
    # 图表1：名义收益率 vs 估算实际收益率
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df["月份"], 
        y=df["10年期国债收益率"],
        mode='lines+markers',
        name='10年期国债收益率',
        line=dict(color='#1f77b4', width=2)
    ))
    fig1.add_trace(go.Scatter(
        x=df["月份"], 
        y=df["估算实际收益率"],
        mode='lines+markers',
        name='估算实际收益率',
        line=dict(color='#ff7f0e', width=2)
    ))
    fig1.update_layout(
        title="中国10年期国债收益率拆解",
        xaxis_title="月份",
        yaxis_title="收益率 (%)",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    # 图表2：通胀预期拆解
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df["月份"], 
        y=df["估算通胀预期"],
        mode='lines+markers',
        name='估算通胀预期',
        line=dict(color='#2ca02c', width=2)
    ))
    fig2.add_trace(go.Scatter(
        x=df["月份"], 
        y=df["未来1年CPI一致预期"],
        mode='lines+markers',
        name='未来1年CPI预期',
        line=dict(color='#d62728', width=2, dash='dash')
    ))
    fig2.add_trace(go.Scatter(
        x=df["月份"], 
        y=df["12M核心CPI均值"],
        mode='lines+markers',
        name='12M核心CPI均值',
        line=dict(color='#9467bd', width=2, dash='dash')
    ))
    fig2.update_layout(
        title="通胀预期拆解",
        xaxis_title="月份",
        yaxis_title="通胀率 (%)",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    # 图表3：CPI vs PPI
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=df["月份"], 
        y=df["CPI同比"],
        mode='lines+markers',
        name='CPI同比',
        line=dict(color='#e377c2', width=2)
    ))
    fig3.add_trace(go.Scatter(
        x=df["月份"], 
        y=df["核心CPI同比"],
        mode='lines+markers',
        name='核心CPI同比',
        line=dict(color='#7f7f7f', width=2)
    ))
    fig3.add_trace(go.Scatter(
        x=df["月份"], 
        y=df["PPI同比"],
        mode='lines+markers',
        name='PPI同比',
        line=dict(color='#bcbd22', width=2)
    ))
    fig3.update_layout(
        title="CPI vs PPI 同比",
        xaxis_title="月份",
        yaxis_title="同比增速 (%)",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig1, fig2, fig3

def generate_html(df):
    """生成完整的 HTML 看板"""
    fig1, fig2, fig3 = create_charts(df)
    
    # 获取最新数据
    latest = df.iloc[-1]
    
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中国10年期实际收益率月度跟踪</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 10px;
        }}
        .info-box {{
            background-color: #f8f9fa;
            border-left: 4px solid #1f77b4;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .info-box h3 {{
            margin-top: 0;
            color: #1f77b4;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric {{
            background-color: #fff;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .chart {{
            margin: 30px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🇨🇳 中国10年期实际收益率月度跟踪</h1>
        
        <div class="info-box">
            <h3>📊 最新数据（{latest['月份']}）</h3>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">10年期国债收益率</div>
                    <div class="metric-value">{latest['10年期国债收益率']:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">估算实际收益率</div>
                    <div class="metric-value">{latest['估算实际收益率']:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">估算通胀预期</div>
                    <div class="metric-value">{latest['估算通胀预期']:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">CPI同比</div>
                    <div class="metric-value">{latest['CPI同比']:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">核心CPI同比</div>
                    <div class="metric-value">{latest['核心CPI同比']:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">PPI同比</div>
                    <div class="metric-value">{latest['PPI同比']:.2f}%</div>
                </div>
            </div>
        </div>
        
        <div class="chart" id="chart1"></div>
        <div class="chart" id="chart2"></div>
        <div class="chart" id="chart3"></div>
        
        <div class="footer">
            <p>数据来源：AkShare、国家统计局、复旦-ZEW 中国经济景气调查</p>
            <p>更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </div>
    
    <script>
        var chart1 = {fig1.to_json()};
        var chart2 = {fig2.to_json()};
        var chart3 = {fig3.to_json()};
        
        Plotly.newPlot('chart1', chart1.data, chart1.layout);
        Plotly.newPlot('chart2', chart2.data, chart2.layout);
        Plotly.newPlot('chart3', chart3.data, chart3.layout);
    </script>
</body>
</html>
"""
    
    output_file = DOCS_DIR / "index.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ 看板已生成：{output_file}")

def main():
    """主流程"""
    # 1. 读取原始数据
    data = load_raw_data()
    
    # 2. 计算通胀预期和实际收益率
    data = calculate_inflation_expectation(data)
    
    # 3. 更新 historical.csv
    update_historical_data(data)
    
    # 4. 读取完整历史数据
    hist_file = DATA_DIR / "historical.csv"
    if hist_file.exists():
        df = pd.read_csv(hist_file)
        
        # 5. 生成看板
        generate_html(df)
    else:
        print("⚠️ historical.csv 不存在，无法生成看板")

if __name__ == "__main__":
    main()
build = main  # 或者 build = generate，取决于实际函数名
