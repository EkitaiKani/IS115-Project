"""Test order_stops on the baseline's own trips for one day.

Run from the project root, after running the baseline for that day:
    python test_order_stops.py day_001
"""
import csv
import json
import sys

from solution.policies.helpers import order_stops, route_distance

day = sys.argv[1] if len(sys.argv) > 1 else "day_001"

# Distance table as a nested dict, like context["travel_distance"]
dist = {}
with open("data/dist.csv", newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        dist.setdefault(r["location_1"], {})[r["location_2"]] = float(r["dist"])

# Parcel records in the same shape dispatch() receives (only the fields needed)
parcel = {}
with open(f"data/demand/{day}.csv", newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        parcel[r["parcel_id"]] = {"delivery_location_id": r["delivery_location_id"]}

# Rebuild the baseline's trips from its log
trips = {}
with open(f"results/baseline/{day}/log.txt", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            e = json.loads(line)
            if e["event_type"] == "delivery":
                trips.setdefault((e["vehicle_id"], e["trip_id"]), []).append(e["parcel_id"])

before = after = 0.0
for route in trips.values():
    new_route = order_stops(route, parcel, dist)
    assert sorted(new_route) == sorted(route), "order_stops lost or added a parcel"
    before += route_distance(route, parcel, dist)
    after += route_distance(new_route, parcel, dist)

print(f"Baseline trips, original order: {before:8.1f} km")
print(f"Same trips after order_stops:  {after:8.1f} km  ({(1 - after / before) * 100:.1f}% shorter)")