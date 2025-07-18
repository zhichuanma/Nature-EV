import requests
import pandas as pd

# Request JSON instead of CSV
url = "https://api.openchargemap.io/v3/poi/"
params = {
    "output": "json",
    "countrycode": "GB",
    "maxresults": 50000,
    "key": "5be57c4b-dd03-4ea8-800d-1b4b37f5cbd8"
}

resp = requests.get(url, params=params)
resp.raise_for_status()
data = resp.json()

# Flatten the nested Connections for CSV export
rows = []
for station in data:
    base = {
        "StationID": station["ID"],
        "Title": station["AddressInfo"].get("Title"),
        "AddressLine1": station["AddressInfo"].get("AddressLine1"),
        "Town": station["AddressInfo"].get("Town"),
        "Latitude": station["AddressInfo"].get("Latitude"),
        "Longitude": station["AddressInfo"].get("Longitude"),
        "UsageCost": station.get("UsageCost"),
        "Status": station["StatusType"]["Title"] if station.get("StatusType") else None,

    }
    for conn in station.get("Connections", []):
        row = base.copy()
        row["PowerKW"] = conn.get("PowerKW")
        row["Voltage"] = conn.get("Voltage")
        row["Amps"] = conn.get("Amps")
        
        current_type = conn.get("CurrentType")
        row["CurrentType"] = current_type.get("Title") if current_type else None

        row["ConnectionType"] = conn.get("ConnectionType", {}).get("Title")
        
        level = conn.get("Level")
        row["Level"] = level.get("Title") if level else None
        
        row["Quantity"] = conn.get("Quantity")
        rows.append(row)

# Convert to DataFrame and save
df = pd.DataFrame(rows)
print("UK charging connector count:", len(df))
df.to_csv("UK_charging_stations_with_capacity.csv", index=False)
