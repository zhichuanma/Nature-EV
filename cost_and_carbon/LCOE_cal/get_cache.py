import argparse, os, yaml, pandas as pd, numpy as np
import json

# ---------------- 工具函数 ----------------
def _parse_cf(raw) -> float:
    s = str(raw).strip()
    if s.endswith("%"):
        v = float(s[:-1]) / 100.0
    else:
        v = float(s)
        if v > 1.0:
            v = v / 100.0
    if not (0.0 <= v <= 1.0):
        raise ValueError(f"load_factor 应在 [0,1] 或百分数，当前={raw}")
    return v

def _kw_to_mw(x_per_kW: float) -> float:
    return float(x_per_kW) * 1000.0

def _safe_phase_map(raw_phase: dict, expected_len: int | None = None, name: str = "") -> dict:
    if not isinstance(raw_phase, dict):
        raise ValueError(f"{name}: 分期必须是 dict")
    vals, missing = {}, []
    for k, v in raw_phase.items():
        ki = int(k)
        if v is None:
            missing.append(ki)
        else:
            vals[ki] = float(v)
    if expected_len is not None and len(raw_phase) != expected_len:
        raise ValueError(f"{name}: 分期年数与 *_years_* 不一致 (got {len(raw_phase)}, expect {expected_len})")
    n = len(raw_phase) if len(raw_phase) > 0 else 1
    if missing:
        s_known = sum(vals.values())
        remaining = max(0.0, 1.0 - s_known)
        fill = remaining / len(missing) if remaining > 0 else 1.0 / n
        for ki in missing:
            vals[ki] = fill
    s = sum(vals.values())
    if s <= 0:
        base = 1.0 / n
        for k in raw_phase.keys():
            vals[int(k)] = base
        s = 1.0
    for ki in list(vals.keys()):
        vals[ki] = vals[ki] / s
    return vals

# ---------------- 读取 YAML → 标准化技术参数 ----------------
def load_techs(techs_yaml_path: str) -> dict:
    with open(techs_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = {}

    for tech_name, cfg in data.items():
        # 1) 基本参数
        load_factor  = _parse_cf(cfg["load_factor"])
        lifetime     = int(cfg["operating_lifetime"])
        hurdle_rate  = float(cfg["hurdle_rate"])  # 视为 real
        availability  = float(cfg.get("availability", 1.0))

        # 2) 成本：£/kW → £/MW
        pre_costs_mw  = _kw_to_mw(cfg["pre_development_costs_per_kw_medium"])
        cons_costs_mw = _kw_to_mw(cfg["construction_cost_medium_per_kw"])

        # ✅ infra 为“项目总额”，不并入每MW
        infra_costs_lump = float(cfg.get("infrastructure_costs", 0.0))  # £/项目

        capex_per_mw = pre_costs_mw + cons_costs_mw  # ✅ 不含 infra（项目级）

        # 3) 分期
        pre_phase_raw  = cfg["pre_development_phasing"]
        cons_phase_raw = cfg["construction_phasing_medium"]
        pre_phase = _safe_phase_map(
            pre_phase_raw,
            expected_len=int(cfg.get("pre_development_years_medium", len(pre_phase_raw))),
            name=f"{tech_name}.pre_development_phasing",
        )
        cons_phase = _safe_phase_map(
            cons_phase_raw,
            expected_len=int(cfg.get("construction_years_medium", len(cons_phase_raw))),
            name=f"{tech_name}.construction_phasing_medium",
        )

        # 4) OPEX（常量版）
        fixed_om    = float(cfg.get("fixed_OM", 0.0))
        insurance   = float(cfg.get("insurance_costs", 0.0))
        conn_charge = float(cfg.get("connection_use_of_charge", 0.0))
        fixed_opex_per_mw_year = fixed_om + insurance + conn_charge
        var_opex_per_mwh       = float(cfg.get("variable_OM", 0.0))

        # 5) 燃料与碳成本（仅热电等需燃料机组）
        eff = float(cfg.get("fuel_efficiency", 0.0) or 0.0)  # 电/燃料
        cal = float(cfg.get("fuel_calorific_value", cfg.get("fuel_calorific_value_mwh_per_therm", 0.0)) or 0.0)  # MWh/therm
        fuel_price_per_therm = float(cfg.get("fuel_price_per_therm", 0.0) or 0.0)
        carbon_price_per_tCO2 = float(cfg.get("carbon_price_per_tCO2", 0.0) or 0.0)
        fuel_carb_kg_per_therm = float(cfg.get("fuel_carbon_content_kgCO2_per_therm", 0.0) or 0.0)

        if eff > 0 and cal > 0:
            therm_per_MWh = 1.0 / (eff * cal)  # therm/MWh_e
            fuel_cost_per_mwh_base = fuel_price_per_therm * therm_per_MWh
            carbon_cost_per_mwh_base = carbon_price_per_tCO2 * (fuel_carb_kg_per_therm / 1000.0) * therm_per_MWh
        else:
            therm_per_MWh = 0.0
            fuel_cost_per_mwh_base = 0.0
            carbon_cost_per_mwh_base = 0.0


        out[tech_name] = dict(
            # 口径参数
            lifetime=lifetime,
            hurdle_rate=hurdle_rate,

            # 发电性能
            load_factor=load_factor,
            capacity_factor_degradation=0.0,
            availability=availability,
            curtailment=0.0,

            # OPEX（常量）
            fixed_opex_per_mw_year=fixed_opex_per_mw_year,
            var_opex_per_mwh=var_opex_per_mwh,

            # CAPEX（每 MW）与分期
            capex_per_mw=capex_per_mw,
            pre_cost_per_mw=pre_costs_mw,
            construction_cost_per_mw=cons_costs_mw,
            pre_phase=pre_phase,     # 0..(n_pre-1)
            cons_phase=cons_phase,   # 0..(n_cons-1)

            # ✅ 项目级基础设施总额
            infra_costs=infra_costs_lump,

            # 燃料与碳成本参数
            fuel_efficiency=eff,
            fuel_calorific_value_MWh_per_therm=cal,
            therm_per_MWh=therm_per_MWh,
            fuel_price_per_therm=fuel_price_per_therm,
            fuel_carbon_content_kgCO2_per_therm=fuel_carb_kg_per_therm,
            carbon_price_per_tCO2=carbon_price_per_tCO2,
            fuel_cost_per_mwh_base=fuel_cost_per_mwh_base,     # 每MWh燃料基准单价
            carbon_cost_per_mwh_base=carbon_cost_per_mwh_base, # 每MWh碳基准单价

        )
    return out

# ---------------- 计算：期初折现 + 逐年乘积求和 + 逐年明细 ----------------
def build_factors(tech: dict) -> dict:
    r    = float(tech["hurdle_rate"])
    life = int(tech["lifetime"])

    pre_phase  = {int(k): float(v) for k, v in tech.get("pre_phase", {}).items()}
    cons_phase = {int(k): float(v) for k, v in tech.get("cons_phase", {}).items()}

    # 归一化（稳妥）
    def _norm(d):
        s = sum(d.values()) or 1.0
        return {k: v / s for k, v in d.items()}
    pre_phase  = _norm(pre_phase)
    cons_phase = _norm(cons_phase)

    n_pre, n_cons = len(pre_phase), len(cons_phase)

    # 每 MW 的“前期/建设”金额（不含 infra）
    pre_cost_per_mw  = float(tech["pre_cost_per_mw"])
    cons_cost_per_mw = float(tech["construction_cost_per_mw"])

    # 绝对年：前期 0..n_pre-1；建设 n_pre..n_pre+n_cons-1
    pre_abs_cost_per_mw  = {k: pre_phase[k] * pre_cost_per_mw for k in pre_phase.keys()}
    cons_abs_cost_per_mw = {n_pre + k: cons_phase[k] * cons_cost_per_mw for k in cons_phase.keys()}

    # 期初折现：运营首年指数 = COD-1
    build_years  = n_pre + n_cons                 # COD 年号
    t_oper_start = build_years
    t_oper       = np.arange(t_oper_start, t_oper_start + life, dtype=float)
    df_oper      = 1.0 / ((1.0 + r) ** t_oper)

    # 全时轴折现因子
    last_oper_idx = int(t_oper_start + life - 1)
    all_years     = list(range(0, last_oper_idx + 1))
    df_all        = {t: 1.0 / ((1.0 + r) ** t) for t in all_years}

    # 发电（每 MW）
    y  = np.arange(1, life + 1, dtype=float)

    base_cf = float(tech["load_factor"]) * float(tech.get("availability", 1.0))
    eff_cf = np.clip(np.full(life, base_cf, dtype=float), 0.0, 1.0)

    mwh_per_mw_series = 8760.0 * eff_cf
    discounted_gen    = mwh_per_mw_series * df_oper
    pv_energy_per_mw  = float(np.sum(discounted_gen))

    # 固定/可变 O&M 逐年折现（常量）
    F0  = float(tech["fixed_opex_per_mw_year"])
    c0  = float(tech["var_opex_per_mwh"])
    F_t = np.full(life, F0, dtype=float)
    c_t = np.full(life, c0, dtype=float)
    pv_fixed_opex_per_mw    = float(np.sum(F_t * df_oper))
    pv_variable_opex_per_mw = float(np.sum(c_t * mwh_per_mw_series * df_oper))

    # ——CAPEX（每 MW，不含 infra）逐年折现——
    # 单独计算：pre 与 construction
    pv_pre_capex_per_mw = 0.0
    pv_construction_capex_per_mw = 0.0
    for t in all_years:
        pv_pre_capex_per_mw         += pre_abs_cost_per_mw.get(t, 0.0)  * df_all[t]
        pv_construction_capex_per_mw += cons_abs_cost_per_mw.get(t, 0.0) * df_all[t]

    pv_capex_per_mw = pv_pre_capex_per_mw + pv_construction_capex_per_mw

    # 纯时间因子 capex_df（现值 / 未折现每MW CAPEX）
    denom_capex_per_mw = pre_cost_per_mw + cons_cost_per_mw
    capex_df = pv_capex_per_mw / denom_capex_per_mw if denom_capex_per_mw > 0 else 0.0


    # ✅ 基础设施（项目级）按建设分期折现，不乘容量
    infra_lump = float(tech.get("infra_costs", 0.0))  # £/项目
    infra_phase = _norm(cons_phase) if infra_lump > 0 else {}
    pv_infra_lump_total = 0.0
    discounted_infra_by_year = {}
    for k, frac in infra_phase.items():
        t = n_pre + int(k)
        disc = infra_lump * frac * df_all[t]
        pv_infra_lump_total += disc
        discounted_infra_by_year[t] = disc

    # ==== 新增：燃料与碳 —— 逐年相乘后求现值 ====
    fc0 = float(tech.get("fuel_cost_per_mwh_base", 0.0))
    cc0 = float(tech.get("carbon_cost_per_mwh_base", 0.0))
    # 每年单价恒定（如需增长，改成每年数组）
    c_fuel_t   = np.full_like(mwh_per_mw_series, fc0, dtype=float)
    c_carbon_t = np.full_like(mwh_per_mw_series, cc0, dtype=float)

    pv_fuel_per_mw   = float(np.sum(c_fuel_t   * mwh_per_mw_series * df_oper))
    pv_carbon_per_mw = float(np.sum(c_carbon_t * mwh_per_mw_series * df_oper))


    # 逐年明细
    yearly = []
    for t in all_years:
        is_oper = (t_oper_start <= t <= t_oper_start + life - 1)
        idx = int(t - t_oper_start) if is_oper else None
        disc_factor = df_all[t]
        disc_pre  = pre_abs_cost_per_mw.get(t, 0.0) * disc_factor
        disc_cons = cons_abs_cost_per_mw.get(t, 0.0) * disc_factor
        disc_fix  = (F_t[idx] * disc_factor) if is_oper else 0.0
        disc_var  = (c_t[idx] * mwh_per_mw_series[idx] * disc_factor) if is_oper else 0.0
        disc_gen  = discounted_gen[idx] if is_oper else 0.0
        disc_fuel = (c_fuel_t[idx]   * mwh_per_mw_series[idx] * disc_factor) if is_oper else 0.0
        disc_co2  = (c_carbon_t[idx] * mwh_per_mw_series[idx] * disc_factor) if is_oper else 0.0
        infra_disc_total = discounted_infra_by_year.get(t, 0.0)
        yearly.append(dict(
            abs_year=t,
            stage=("operation" if is_oper else ("construction" if t >= n_pre else "pre_dev")),
            discount_factor=disc_factor,
            discounted_pre_dev_per_mw=disc_pre,
            discounted_construction_per_mw=disc_cons,
            discounted_fixed_om_per_mw=disc_fix,
            discounted_variable_om_per_mw=disc_var,
            discounted_fuel_per_mw=disc_fuel,          
            discounted_carbon_per_mw=disc_co2,         
            discounted_total_cost_per_mw=disc_pre + disc_cons + disc_fix + disc_var+ disc_fuel + disc_co2,
            discounted_mwh_per_mw=disc_gen,
            discounted_infra_lump_total=infra_disc_total,  # £/项目
            
        ))

    return dict(
        build_years=int(build_years),
        capex_df=float(capex_df),
        pv_capex_per_mw=float(pv_capex_per_mw),
        pv_fixed_opex_per_mw=float(pv_fixed_opex_per_mw),
        pv_variable_opex_per_mw=float(pv_variable_opex_per_mw),
        pv_energy_per_mw=float(pv_energy_per_mw),
        pv_infra_lump_total=float(pv_infra_lump_total),
        pv_pre_capex_per_mw=float(pv_pre_capex_per_mw),
        pv_construction_capex_per_mw=float(pv_construction_capex_per_mw),
        pv_fuel_per_mw=float(pv_fuel_per_mw),           
        pv_carbon_per_mw=float(pv_carbon_per_mw),       

        yearly=yearly,
    )

# 读技术参数 & 预计算每种技术的因子
techs = load_techs('/Users/zm348/PhD/Projects/Nature-EV/cost_and_carbon/LCOE_cal/config/techs.yaml')
cache = {name: build_factors(tcfg) for name, tcfg in techs.items()}
print(cache)
with open('cache.json', 'w') as f:
    json.dump(cache, f, indent=4)