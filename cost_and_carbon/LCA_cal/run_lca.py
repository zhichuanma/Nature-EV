#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, os, yaml, pandas as pd, numpy as np
import json
import time

t1 = time.time()
with open('cache.json', 'r') as f:
    cache = json.load(f)
t2 = time.time()
print(f"Load cache time: {t2 - t1} seconds")

# ---------------- 主流程：汇总 + 明细输出 ----------------
def lca_for_units(units_csv: str, out_csv: str,
                   detail_csv: str | None = "results_yearly.csv"):
    # 读机组清单
    t3 = time.time()
    units = pd.read_csv(units_csv)
    for col in ("id", "tech", "capacity_mw"):
        if col not in units.columns:
            raise ValueError(f"units 缺少列 '{col}'")
    t4 = time.time()
    print(f"Load units time: {t4 - t3} seconds")

    # 清空旧的逐年文件
    if detail_csv and os.path.exists(detail_csv):
        os.remove(detail_csv)

    rows = []
    tech_name = units['tech']

    t5 = time.time()

    all_lcoe_rows = []

    for tech_name,fac in cache.items():
        lca = float(fac.get("lca", 0.0))
        if tech_name == "PV":
            pv_bins = ["PV(<4kW)", "PV(4-10kW)", "PV(10-50kW)", "PV(50kW+)"]
            tech_units = units[units["tech"].isin(pv_bins)]
        else:
            tech_units = units[units['tech'] == tech_name]
        cap = tech_units['capacity_mw']
        ids = tech_units['id']
        lca = lca * 1000 # 转为 kgCO2e/MWh

        df_lcoe = pd.DataFrame({
            'id': ids,
            'tech': tech_units['tech'],
            'capacity_mw': cap,
            'lca': lca,
            })
        all_lcoe_rows.append(df_lcoe)
    out_df = pd.concat(all_lcoe_rows, ignore_index=True)

    # 可选：按原 units 的 id 顺序重排
    order = units[["id"]].assign(_ord=np.arange(len(units)))
    out_df = out_df.merge(order, on="id", how="left").sort_values("_ord").drop(columns="_ord")

    # 导出：id 为第一列，且不写索引列
    out_df.to_csv("lca_by_unit.csv", index=False)
    t6 = time.time()
    print(f"Computation time: {t6 - t5} seconds")   


# ---------------- CLI ----------------
def main():

    detail_path = 'results_lca_yearly.csv'

    unit_path = 'data/units_test.csv'
    out = 'results_lca.csv'

    lca_for_units(unit_path, out, detail_path)
    # print(f"完成：\n- 汇总: {args.out}\n- 明细: {detail_path or '(未输出)'}\n- 总折现发电量: {summary_path or '(仅终端打印)'}")

if __name__ == "__main__":
    main()
