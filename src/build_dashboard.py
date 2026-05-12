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
            
            # 核心 CPI：AkShare 没有直接提供，需要手动计算或使用其他数据源
            # 临时方案：用 CPI 同比代替（后续可以改进）
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
