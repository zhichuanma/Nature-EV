import pandas as pd
def capacity_by_bus(df: pd.DataFrame, tech: str) -> pd.DataFrame:
    """
    针对给定技术solar / onwind / offwind
    返回按 Bus name 聚合的装机量和占比。
    """
    sub = df[df["Technology"].str.lower() == tech.lower()].copy()

    total_cap = sub["capacity"].sum()

    out = (
        sub.groupby("Bus name", as_index=False)["capacity"]
           .sum()
           .rename(columns={"capacity": "bus_capacity"})
    )

    out["percentage"] = out["bus_capacity"] / total_cap * 100

    return out.sort_values("bus_capacity", ascending=False)