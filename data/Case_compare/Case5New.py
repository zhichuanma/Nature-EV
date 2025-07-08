# """@Author: 潘湛华"""
# from market.core.CaseBase import ClearCase, DataFrame

import pandas as pd

df_Buses = pd.DataFrame(
    [[1.0, 0, 0],
     [2.0, 2, 0],
     [3.0, 4, 2],
     [4.0, 2, 2],
     [5.0, 0, 2]],
    columns=['BusID', 'x', 'y']
)

df_Buses['BusID'] = df_Buses['BusID'].astype(int)

df_Buses['Bus name'] = pd.NA
df_Buses['voltage'] = pd.NA
df_Buses['RegionName'] = pd.NA
df_Buses['color'] = pd.NA

df_Units = pd.DataFrame(
    [[1.0, 1.0, 0.0, 0.0, 10.0, 600.0, 100.0],
     [2.0, 2.0, 0.0, 0.0, 10.0, 600.0, 100.0],
     [3.0, 3.0, 0.0, 0.0, 10.0, 600.0, 100.0],
     [4.0, 4.0, 0.0, 0.0, 10.0, 600.0, 100.0],
     [5.0, 5.0, 0.0, 0.0, 10.0, 600.0, 100.0]],
    columns=['id', 'bus_id', 'mc_a', 'mc_b', 'mc_c', 'p_max', 'p_min']
)
df_Lines = pd.DataFrame(
    [[1.0, 1.0, 2.0, 0.0281, -400.0, 400.0],
     [2.0, 1.0, 4.0, 0.0304, 0.0, 0.0],
     [3.0, 1.0, 5.0, 0.0064, 0.0, 0.0],
     [4.0, 2.0, 3.0, 0.0108, 0.0, 0.0],
     [5.0, 3.0, 4.0, 0.0297, 0.0, 0.0],
     [6.0, 4.0, 5.0, 0.0297, -240.0, 240.0]],
    columns=['id', 'from', 'to', 'x', 'floor', 'cap']
)

df_Loads = pd.DataFrame(
    [[1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
     [2.0, 2.0, 0.0, 0.0, 0.0, 500.0, 300.0],
     [3.0, 3.0, 0.0, 0.0, 0.0, 600.0, 300.0],
     [4.0, 4.0, 0.0, 0.0, 0.0, 400.0, 400.0],
     [5.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0]],
    columns=['id', 'bus_id', 'mc_a', 'mc_b', 'mc_c', 'd_max', 'd_min']
)

df_Buses.to_csv('./Case5/Buses.csv', index=False)
df_Units.to_csv('./Case5/Units.csv', index=False)
df_Lines.to_csv('./Case5/Lines.csv', index=False)
df_Loads.to_csv('./Case5/Loads.csv', index=False)