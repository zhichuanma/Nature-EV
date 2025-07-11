import pandas as pd
from scipy.spatial import cKDTree

def assign_tech_units(df_Units_modified, df_Buses, tech):
    """
    分配 tech 类型单元与最近 tech 项目，并创建未匹配的项目对应的单元。

    参数:
        df_Units_modified: 已有的 units 表（包含 type、x、y、Bus name 等字段）
        df_Buses: 所有 bus 表，包含 ['x', 'y', 'Bus name']
        project_file: tech 项目数据文件路径（默认值为 2024 年 9 月的文件）

    返回:
        df_new_units: 新创建的 tech 单元 DataFrame
        df_Units_modified: 更新后的全部单位表，含新建单元
    """
    # 1. 读取 tech 项目并过滤英国
    project_file=f'Global-{tech}.xlsx'
    if tech == 'solar':
        df_solar_1 = pd.read_excel(project_file, sheet_name='20 MW+')
        df_solar_2 = pd.read_excel(project_file, sheet_name='1-20 MW')
        df_tech = pd.concat([df_solar_1, df_solar_2], ignore_index=True)
    elif tech == 'coal':
        df_tech = pd.read_excel(project_file, sheet_name='Units')
    elif tech == 'oil-gas':
        df_tech = pd.read_excel(project_file, sheet_name='Gas & Oil Units')
    else:
        df_tech = pd.read_excel(project_file, sheet_name='Data')
    df_tech = df_tech[df_tech['Country/Area'] == 'United Kingdom']

    # 2. 提取 tech 类型的单位
    if tech == 'wind':
        df_Units_tech = df_Units_modified[df_Units_modified['Technology'].str.contains('wind', case=False, na=False)].copy()
    elif tech == 'oil-gas':
        df_Units_tech = df_Units_modified[df_Units_modified['Technology'].str.contains('oil|gas', case=False, na=False)].copy()
    else:
        df_Units_tech = df_Units_modified[df_Units_modified['Technology'] == tech].copy()

    # 3. 匹配最近项目（合并同一经纬度下多个项目容量）
    tree = cKDTree(df_tech[["Longitude", "Latitude"]].to_numpy())
    dist, idx = tree.query(df_Units_tech[['x', 'y']].to_numpy(), k=1)

    # 将最近项目的索引记录下来
    df_Units_tech[f"nearest_{tech}_idx"] = idx

    # 取最近匹配项目的坐标
    nearest_coords = df_tech.iloc[idx][["Longitude", "Latitude"]].reset_index(drop=True)
    df_Units_tech[[f"nearest_{tech}_lon", f"nearest_{tech}_lat"]] = nearest_coords

    # 遍历每个 unit 的最近点坐标，查找所有相同经纬度的项目并合并容量
    merged_capacity = []
    assigned_idxs = set()

    for lon, lat in nearest_coords.itertuples(index=False):
        mask = (df_tech["Longitude"] == lon) & (df_tech["Latitude"] == lat)
        matched = df_tech[mask]
        merged_capacity.append(matched["Capacity (MW)"].sum())
        assigned_idxs.update(matched.index)

    df_Units_tech[f"nearest_{tech}_capacity"] = merged_capacity

    # 选用第一个匹配项目的属性填充其他字段（可扩展为更复杂策略）
    df_Units_tech["Start Year"] = df_tech.iloc[idx]["Start Year"].values
    df_Units_tech["Retired Year"] = df_tech.iloc[idx]["Retired Year"].values
    df_Units_tech["Status"] = df_tech.iloc[idx]["Status"].values


    # 4. 平均分配容量
    unit_counts = df_Units_tech.groupby(f"nearest_{tech}_idx")["UnitID"].transform('count')
    df_Units_tech["capacity"] = df_Units_tech[f"nearest_{tech}_capacity"] / unit_counts

    # 5. 精简列
    df_Units_tech = df_Units_tech.loc[:, [
        'UnitID', 'name', 'type', 'Bus name', 'x', 'y',
        'capacity', 'Technology', 'Cost', f'nearest_{tech}_idx', 'Start Year', 'Retired Year', 'Status'
    ]]

    # 6. 创建新单元：那些尚未被任何单位匹配的项目
    # assigned_idxs = set(df_Units_tech[f'nearest_{tech}_idx'])
    new_units = []

    for index, row in df_tech.iterrows():
        if index in assigned_idxs:
            continue

        if tech == 'wind':
            install_type = str(row.get('Installation Type', '')).lower()  # 防止缺值
            if 'offshore' in install_type:
                subtype = 'offwind'
            else:
                subtype = 'onwind'
        else:
            subtype = tech  # 其他技术原样使用

        if tech == 'oil-gas':
            fuel = str(row.get('Fuel','')).lower()
            if 'oil' in fuel:
                subtype = 'oil'
            else:
                subtype = 'gas'

        new_unit = {
            'UnitID': f'new_{subtype}_{index}',
            'name': f'{subtype}_{index}',
            'type': subtype,
            'x': row['Longitude'],
            'y': row['Latitude'],
            'capacity': row['Capacity (MW)'],
            'Technology': subtype,
            'Cost': None,
            'Status': row['Status'],
            'Start Year': row['Start Year'],
            'Retired Year': row['Retired Year']
        }
        new_units.append(new_unit)

    # 7. 为新单元分配最近的 Bus
    if new_units:
        df_new_units = pd.DataFrame(new_units)

        bus_coords = df_Buses[['x', 'y']].to_numpy()
        bus_names = df_Buses['Bus name'].values
        tree_bus = cKDTree(bus_coords)

        new_unit_coords = df_new_units[['x', 'y']].to_numpy()
        dist, idx = tree_bus.query(new_unit_coords, k=1)
        df_new_units['Bus name'] = bus_names[idx]

        # 合并新单元到总表
        df_Units_tech = pd.concat([df_Units_tech, df_new_units], ignore_index=False)
        df_Units_tech.drop(columns=f'nearest_{tech}_idx', inplace=True)

    else:
        df_new_units = pd.DataFrame(columns=df_Units_modified.columns)
        df_new_units.drop(columns=f'nearest_{tech}_idx', inplace=True)
    return df_new_units, df_Units_tech