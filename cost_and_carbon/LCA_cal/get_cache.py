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

# ---------------- 读取 YAML → 标准化技术参数 ----------------
def load_techs(techs_yaml_path: str) -> dict:
    with open(techs_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = {}

    for tech_name, cfg in data.items():
        lca = cfg.get("lca", 0.0)
        out[tech_name] = dict(
            lca = lca
       )
    return out

# 读技术参数 & 预计算每种技术的因子
techs = load_techs('/Users/zm348/PhD/Projects/Nature-EV/LCA_cal/config/techs.yaml')
print(techs)
with open('cache.json', 'w') as f:
    json.dump(techs, f, indent=4)