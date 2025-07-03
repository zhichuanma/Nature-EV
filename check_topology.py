import pandas as pd
import os
import networkx as nx

# 读取节点和线路数据
buses = pd.read_csv('./data/Buses.csv')
lines = pd.read_csv('./data/Lines.csv')
transformers = pd.read_csv('./data/Transformers.csv')
links = pd.read_csv('./data/Links.csv')

# 合并变压器和联络线为线路，X=0.1
transformer_lines = transformers[['bus0', 'bus1']].copy()
link_lines = links[['bus0', 'bus1']].copy()

all_lines = pd.concat([
    lines[['bus0', 'bus1']],
    transformer_lines,
    link_lines
], ignore_index=True)

# 构建无向图
G = nx.Graph()
for _, row in buses.iterrows():
    G.add_node(row['Bus name'])
for _, row in all_lines.iterrows():
    G.add_edge(row['bus0'], row['bus1'])

# 检查连通性
if nx.is_connected(G):
    print('电网拓扑是连通图。')
else:
    print('电网拓扑不是连通图！')
    components = list(nx.connected_components(G))
    print(f'共找到 {len(components)} 个连通分量。每个分量节点数：', [len(c) for c in components])
    # 可选：输出每个分量的节点
    for i, comp in enumerate(components):
        print(f'分量{i+1}节点：', comp) 

