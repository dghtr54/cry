"""生成可视化看板 docs/index.html"""
import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
DOCS_DIR.mkdir(exist_ok=True)

def build():
    # 读取历史数据
    hist_path = DATA_DIR / "historical.csv"
    if not hist_path.exists():
        # 初始化空模板
        df = pd.DataFrame(columns=[
            "月份", "10年期国债收益率", "CPI同比", "核心CPI同比", "PPI同比",
            "12M核心CPI均值", "未来1年CPI一致预期", "政策修正项",
            "估算通胀预期", "估算实际收益率"
        ])
        df.to_csv(hist_path, index=False)
    else:
        df = pd.read_csv(hist_path)
    
    # 读取打分结果
    score_path = DATA_DIR / "auto_scoring_result.json"
    score = json.load(open(score_path, encoding="utf-8")) if score_path.exists() else {}
    
    # 三张图：名义收益率、通胀预期、实际收益率
    fig = make_subplots(rows=3, cols=1,
                        subplot_titles=("10年期国债收益率", "估算通胀预期", "估算实际收益率"))
    
    if not df.empty:
        fig.add_trace(go.Scatter(x=df["月份"], y=df["10年期国债收益率"],
                                 mode="lines+markers", name="名义"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["月份"], y=df["估算通胀预期"],
                                 mode="lines+markers", name="通胀预期"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["月份"], y=df["估算实际收益率"],
                                 mode="lines+markers", name="实际"), row=3, col=1)
    
    fig.update_layout(height=900, title_text="中国10年期实际收益率月度跟踪", showlegend=False)
    
    # 构造 HTML
    score_html = ""
    if score:
        score_html = f"""
        <h2>本月政策/周期修正项明细</h2>
        <table border="1" cellpadding="8" style="border-collapse:collapse">
          <tr><th>分项</th><th>得分</th><th>说明</th></tr>
          <tr><td>财政</td><td>{score['fiscal']['score']:+.2f}%</td><td>{score['fiscal']['desc']}</td></tr>
          <tr><td>地产</td><td>{score['real_estate']['score']:+.2f}%</td><td>{score['real_estate']['desc']}</td></tr>
          <tr><td>信用</td><td>{score['credit']['score']:+.2f}%</td><td>{score['credit']['desc']}</td></tr>
          <tr><td>PPI</td><td>{score['ppi']['score']:+.2f}%</td><td>{score['ppi']['desc']}</td></tr>
          <tr><td>汇率</td><td>{score['fx']['score']:+.2f}%</td><td>{score['fx']['desc']}</td></tr>
          <tr><td><b>合计(封顶±0.5%)</b></td><td><b>{score['capped_total']:+.2f}%</b></td><td></td></tr>
        </table>
        """
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>中国10年期实际收益率跟踪</title>
<style>body{{font-family:Arial;max-width:1100px;margin:20px auto;padding:20px}}</style>
</head><body>
<h1>中国10年期实际收益率月度跟踪</h1>
{fig.to_html(include_plotlyjs="cdn", full_html=False)}
{score_html}
<p style="color:#888;font-size:12px">最后更新：{pd.Timestamp.now():%Y-%m-%d %H:%M}</p>
</body></html>"""
    
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"✅ 看板已生成：{DOCS_DIR / 'index.html'}")

if __name__ == "__main__":
    build()
