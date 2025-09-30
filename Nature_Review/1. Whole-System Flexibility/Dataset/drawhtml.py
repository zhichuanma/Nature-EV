import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Geo
from pyecharts.globals import ChartType
from pyecharts.commons.utils import JsCode

# ——— 1. 读取数据 & 归一化 ———
df = pd.read_csv('data_merge.csv')

def safe_normalize(x: pd.Series) -> pd.Series:
    rng = x.max() - x.min()
    return pd.Series(1.0, index=x.index) if rng == 0 else (x - x.min()) / rng

# 分组归一化
df['norm_capacity'] = df.groupby('type')['capacity_mw'].transform(safe_normalize)
min_area, max_area = 5, 30
df['area'] = df['norm_capacity'] * (max_area - min_area) + min_area
# 固定大小
df.loc[df['type']=='CCUS', 'area'] = 15
df.loc[df['type']=='Data Center', 'area'] = 15

# ——— 2. 构建 Geo（世界轮廓），设置画布大小 ———
geo = (
    Geo(init_opts=opts.InitOpts(width="2000px", height="1000px"))
    .add_schema(
        maptype="world",
        itemstyle_opts=opts.ItemStyleOpts(
            area_color="#dddddd",
            border_color="white",
        ),
        label_opts=opts.LabelOpts(is_show=False),
        zoom=1.2,
        is_roam=False
    )
)

# ——— 3. 注册坐标 & 分组 ———
groups: dict[str, list[tuple[str, float]]] = {}
for idx, row in df.iterrows():
    name = f"{row['type']}_{idx}"
    geo.add_coordinate(name, row['longitude'], row['latitude'])
    groups.setdefault(row['type'], []).append((name, row['area']))

# 回调：取 val[2] 作为 symbol_size
size_func = JsCode("function (val) { return val[2]; }")

# ——— 4. 添加 scatter 系列 ———
for t, data_pair in groups.items():
    geo.add(
        series_name=t,
        data_pair=data_pair,
        type_=ChartType.SCATTER,
        symbol_size=size_func,
        label_opts=opts.LabelOpts(is_show=False),
    )

# ——— 5. 全局配置：删除geo_opts参数 & 渲染 ———
geo.set_global_opts(
    title_opts=opts.TitleOpts(
        # title="SMR Capacities on World Map",
        # subtitle="circle size ∼ normalized capacity by type",
        pos_left="center",
    ),
    legend_opts=opts.LegendOpts(pos_left="left", pos_top="bottom"),
)

# 输出 HTML
geo.render('smr_world_map.html')
print("已生成：smr_world_map.html（禁止缩放和平移）")
