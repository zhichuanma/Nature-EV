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
def lcoe_for_units(units_csv: str, out_csv: str,
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
        # ——每 MW 的现值（来自 build_factors）
        pv_pre_capex_mw  = float(fac.get("pv_pre_capex_per_mw", 0.0))
        pv_cons_capex_mw = float(fac.get("pv_construction_capex_per_mw", 0.0))
        pv_fixed_mw      = float(fac.get("pv_fixed_opex_per_mw", 0.0))
        pv_var_mw        = float(fac.get("pv_variable_opex_per_mw", 0.0))
        pv_energy_mw     = float(fac.get("pv_energy_per_mw", 0.0))
        if tech_name == "onshore_wind":
            onwind_bins = ["onshore_wind(>3MW)", "onshore_wind(1-3MW)", "onshore_wind(<1MW)"]
            tech_units = units[units["tech"].isin(onwind_bins)]
        else:
            tech_units = units[units['tech'] == tech_name]
        cap = tech_units['capacity_mw']
        ids = tech_units['id']
        # —机组总额（乘容量）；基础设施为项目级（不乘容量）
        pv_pre_capex   = cap * pv_pre_capex_mw
        pv_construction= cap * pv_cons_capex_mw
        pv_fixed       = cap * pv_fixed_mw
        pv_var         = cap * pv_var_mw
        pv_infra       = float(fac.get("pv_infra_lump_total", 0.0))  # £/项目

        pv_capex  = pv_pre_capex + pv_construction
        pv_energy = cap * pv_energy_mw

        pv_fuel   = cap * fac["pv_fuel_per_mw"]
        pv_carbon = cap * fac["pv_carbon_per_mw"]
        pv_total  = pv_capex + pv_fixed + pv_var + pv_fuel + pv_carbon + pv_infra  # 视你的项目级项而定

        lcoe       = pv_total / pv_energy
        lcoe_pre   = pv_pre_capex    / pv_energy
        lcoe_cons  = pv_construction / pv_energy
        lcoe_fixed = pv_fixed        / pv_energy
        lcoe_var   = pv_var          / pv_energy
        lcoe_infra = pv_infra        / pv_energy
        lcoe_fuel  = pv_fuel         / pv_energy
        lcoe_carbon= pv_carbon       / pv_energy    

        df_lcoe = pd.DataFrame({
            'id': ids,
            'tech': tech_units['tech'],
            'capacity_mw': cap,
            'lcoe_total': lcoe,
            'lcoe_pre': lcoe_pre,
            'lcoe_cons': lcoe_cons,
            'lcoe_fixed': lcoe_fixed,
            'lcoe_var': lcoe_var,
            'lcoe_infra': lcoe_infra,
            'lcoe_fuel': lcoe_fuel,
            'lcoe_carbon': lcoe_carbon,
            })
        all_lcoe_rows.append(df_lcoe)
    out_df = pd.concat(all_lcoe_rows, ignore_index=True)

    # 可选：按原 units 的 id 顺序重排
    order = units[["id"]].assign(_ord=np.arange(len(units)))
    out_df = out_df.merge(order, on="id", how="left").sort_values("_ord").drop(columns="_ord")

    # 导出：id 为第一列，且不写索引列
    out_df.to_csv("lcoe_by_unit.csv", index=False)
    t6 = time.time()
    print(f"Computation time: {t6 - t5} seconds")   


# ---------------- CLI ----------------
def main():

    detail_path = 'results_yearly.csv'

    unit_path = 'data/units_test.csv'
    out = 'results_lcoe.csv'

    lcoe_for_units(unit_path, out, detail_path)
    # print(f"完成：\n- 汇总: {args.out}\n- 明细: {detail_path or '(未输出)'}\n- 总折现发电量: {summary_path or '(仅终端打印)'}")

if __name__ == "__main__":
    main()
