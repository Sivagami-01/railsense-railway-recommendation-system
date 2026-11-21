import json
import os

base = r"C:\Users\shivu\OneDrive\Desktop\project_expo"
station_path = os.path.join(base, "dataset", "stations_clean.json")
train_path = os.path.join(base, "dataset", "trains.json")
out_dir = os.path.join(base, "src", "data")
os.makedirs(out_dir, exist_ok=True)

with open(station_path, "r", encoding="utf-8") as f:
    stations = json.load(f)

seen = set()
station_rows = []
for station in sorted(stations, key=lambda x: (str(x.get("name", "")).casefold(), str(x.get("code", "")))):
    code = str(station.get("code", "")).strip().upper()
    name = str(station.get("name", "")).strip()
    if not code or not name or code in seen:
        continue
    seen.add(code)
    station_rows.append({"code": code, "name": name})

with open(os.path.join(out_dir, "stations.js"), "w", encoding="utf-8") as f:
    f.write("export const stationList = " + json.dumps(station_rows, ensure_ascii=False, separators=(",", ":")) + ";\n")

with open(train_path, "r", encoding="utf-8") as f:
    trains = json.load(f)

seen_trains = set()
train_rows = []
for train in sorted(trains, key=lambda x: (str(x.get("trainNumber", "")).zfill(10), str(x.get("trainName", "")))):
    number = str(train.get("trainNumber", "")).strip()
    name = str(train.get("trainName", "")).strip()
    train_type = str(train.get("type", "")).strip()
    if not number or not name or number in seen_trains:
        continue
    seen_trains.add(number)
    train_rows.append({"number": number, "name": name, "type": train_type})

with open(os.path.join(out_dir, "trainCatalog.js"), "w", encoding="utf-8") as f:
    f.write("export const trainCatalog = " + json.dumps(train_rows, ensure_ascii=False, separators=(",", ":")) + ";\n")

print(f"stations={len(station_rows)} trains={len(train_rows)}")
