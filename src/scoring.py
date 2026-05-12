"""政策/周期修正项自动打分
规则：Adj = Fisc + RE + Credit + PPI + FX，每项 ±0.1%，总修正限制 ±0.5%
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def score_fiscal(exp_yoy, rev_yoy):
    """财政：支出同比 - 收入同比"""
    diff = exp_yoy - rev_yoy
    if diff >= 5:
        return 0.10, "财政扩张"
    elif diff <= -5:
        return -0.10, "财政收缩"
    return 0.0, "财政中性"

def score_real_estate(sales_yoy, price_yoy, invest_yoy):
    """地产：三指标综合打分"""
    s = (1 if sales_yoy >= 0 else (-1 if sales_yoy <= -10 else 0))
    p = (1 if price_yoy >= 0 else (-1 if price_yoy <= -3 else 0))
    i = (1 if invest_yoy >= 0 else (-1 if invest_yoy <= -8 else 0))
    total = s + p + i
    if total >= 2:
        return 0.10, f"地产改善(score={total})"
    elif total <= -2:
        return -0.10, f"地产拖累(score={total})"
    return 0.0, f"地产中性(score={total})"

def score_credit(shrz_yoy, m2_yoy):
    """信用：社融同比 - M2同比"""
    diff = shrz_yoy - m2_yoy
    if diff >= 1:
        return 0.10, "信用扩张"
    elif diff <= -1:
        return -0.10, "信用收缩"
    return 0.0, "信用中性"

def score_ppi(ppi_now, ppi_3m_ago):
    """PPI 趋势"""
    if ppi_now >= 0 and ppi_now > ppi_3m_ago:
        return 0.10, "工业再通胀"
    elif ppi_now <= -2 and ppi_now < ppi_3m_ago:
        return -0.10, "工业通缩"
    return 0.0, "PPI中性"

def score_fx(usdcny_now, usdcny_3m_ago):
    """汇率：USDCNY 3个月变化"""
    chg = usdcny_now / usdcny_3m_ago - 1
    if chg >= 0.03:
        return 0.10, f"人民币贬值({chg:.1%})"
    elif chg <= -0.03:
        return -0.10, f"人民币升值({chg:.1%})"
    return 0.0, f"汇率中性({chg:.1%})"

def calc_total_adjustment(inputs: dict):
    """汇总打分"""
    fisc, fisc_desc = score_fiscal(inputs["fiscal_exp_yoy"], inputs["fiscal_rev_yoy"])
    re, re_desc = score_real_estate(inputs["re_sales"], inputs["re_price"], inputs["re_invest"])
    credit, credit_desc = score_credit(inputs["shrz_yoy"], inputs["m2_yoy"])
    ppi, ppi_desc = score_ppi(inputs["ppi_now"], inputs["ppi_3m_ago"])
    fx, fx_desc = score_fx(inputs["usdcny_now"], inputs["usdcny_3m_ago"])
    
    raw = fisc + re + credit + ppi + fx
    capped = max(min(raw, 0.5), -0.5)
    
    result = {
        "fiscal": {"score": fisc, "desc": fisc_desc},
        "real_estate": {"score": re, "desc": re_desc},
        "credit": {"score": credit, "desc": credit_desc},
        "ppi": {"score": ppi, "desc": ppi_desc},
        "fx": {"score": fx, "desc": fx_desc},
        "raw_total": raw,
        "capped_total": capped,
    }
    
    with open(DATA_DIR / "auto_scoring_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 政策修正项 = {capped:+.2f}%")
    return result
