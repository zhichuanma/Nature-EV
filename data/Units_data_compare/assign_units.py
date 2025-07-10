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
    else:
        df_tech = pd.read_excel(project_file, sheet_name='Data')
    df_tech = df_tech[df_tech['Country/Area'] == 'United Kingdom']

    # 2. 提取 tech 类型的单位
    if tech == 'wind':
        df_Units_tech = df_Units_modified[df_Units_modified['Technology'].str.contains('wind', case=False, na=False)].copy()
    else:
        df_Units_tech = df_Units_modified[df_Units_modified['Technology'] == tech].copy()

    # 3. 匹配最近项目
    tree = cKDTree(df_tech[["Longitude", "Latitude"]].to_numpy())
    dist, idx = tree.query(df_Units_tech[['x', 'y']].to_numpy(), k=1)

    df_Units_tech[f"nearest_{tech}_idx"] = idx
    df_Units_tech[f"nearest_{tech}_lon"] = df_tech.iloc[idx]["Longitude"].values
    df_Units_tech[f"nearest_{tech}_lat"] = df_tech.iloc[idx]["Latitude"].values
    df_Units_tech[f"nearest_{tech}_capacity"] = df_tech.iloc[idx]["Capacity (MW)"].values

    # 4. 平均分配容量
    unit_counts = df_Units_tech.groupby(f"nearest_{tech}_idx")["UnitID"].transform('count')
    df_Units_tech["capacity"] = df_Units_tech[f"nearest_{tech}_capacity"] / unit_counts

    # 5. 精简列
    df_Units_tech = df_Units_tech.loc[:, [
        'UnitID', 'name', 'type', 'Bus name', 'x', 'y',
        'capacity', 'Technology', 'Cost', f'nearest_{tech}_idx'
    ]]

    # 6. 创建新单元：那些尚未被任何单位匹配的项目
    assigned_idxs = set(df_Units_tech[f'nearest_{tech}_idx'])
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

        new_unit = {
            'UnitID': f'new_{subtype}_{index}',
            'name': f'{subtype}_{index}',
            'type': subtype,
            'x': row['Longitude'],
            'y': row['Latitude'],
            'capacity': row['Capacity (MW)'],
            'Technology': subtype,
            'Cost': None,
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

    else:
        df_new_units = pd.DataFrame(columns=df_Units_modified.columns)

    return df_new_units, df_Units_tech