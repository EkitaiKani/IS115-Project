"""Calculate performance metrics from one simulation run's event log."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from simulator.loaders import day_input_paths

from solution.policies.helpers import to_minutes

# ---------------------------------------------------------------
# Cost assumptions for delivery cost per parcel (in SGD).
# The data has no prices, so these are our own assumptions.
# Change them here and every day's cost updates.
# ---------------------------------------------------------------
ENERGY_COST_PER_KM = 0.10       # EV electricity cost for 1 km of driving
DRIVER_COST_PER_HOUR = 20.0     # driver wage per hour
SPEED_KMH = 60.0                # vehicles travel at 60 km/h (from the brief)
LOADING_MINUTES = 30.0          # driver time spent loading at the hub per trip (30-min departure delay)


def calculate_metrics(
    parcels: List[Dict[str, str]],
    distances: List[Dict[str, str]],
    config: Dict[str, Any],
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for the chosen performance metric.

    parcels and distances are the rows of the day's CSV files, config is the
    contents of config.json, and events are the records from the run's log.
    CSV values are strings, so convert them before calculating. In particular,
    parcel times are "HH:MM" strings while event times are minutes after
    midnight: "17:00" is 17 * 60 = 1020.
    """

    # ---------------------------------------------------------------
    # Count trips: each hub_departure event is one trip leaving the hub
    # ---------------------------------------------------------------
    number_of_trips = 0
    for event in events:
        if event["event_type"] == "hub_departure":
            number_of_trips += 1

    # ---------------------------------------------------------------
    # Store each parcel's hub arrival time and delivery window
    # ---------------------------------------------------------------
    T_END = 1080.0              # 18:00 in minutes; undelivered parcels are counted as delivered at this time
    total_delivery_time = 0     # running sum of (delivery time - hub arrival time) over all parcels
    delivered = set()           # IDs of parcels that were delivered
    parcel_time = {}            # parcel_id -> hub arrival time ("HH:MM" string)
    window = {}                 # parcel_id -> (window start, window end) in minutes
    for parcel in parcels:
        pid = parcel["parcel_id"]
        parcel_time[pid] = parcel["arrival_time"]
        window[pid] = (to_minutes(parcel["delivery_window_start"]),
                       to_minutes(parcel["delivery_window_end"]))

    # ---------------------------------------------------------------
    # Go through every delivery: add its delivery time and check it
    # against the parcel's preferred window
    # ---------------------------------------------------------------
    on_time = 0                 # delivered inside the window
    late = 0                    # delivered after the window ended
    early = 0                   # delivered before the window started
    total_lateness = 0.0        # total minutes late, summed over late parcels
    for event in events:
        if event["event_type"] == "delivery" and event["parcel_id"] in parcel_time:
            pid = event["parcel_id"]
            t = event["time"]   # delivery time in minutes after midnight

            # Time from arriving at the hub to being delivered
            total_delivery_time += t - to_minutes(parcel_time[pid])
            delivered.add(pid)

            # Classify the delivery against the preferred window
            start, end = window[pid]
            if t < start:
                early += 1
            elif t > end:
                late += 1
                total_lateness += t - end
            else:
                on_time += 1

    # ---------------------------------------------------------------
    # Undelivered parcels: count them as delivered at 18:00 so that a
    # policy cannot improve the average by skipping parcels
    # ---------------------------------------------------------------
    for id, time in parcel_time.items():
        if id not in delivered:
            total_delivery_time += T_END - to_minutes(time)

    # ---------------------------------------------------------------
    # Metric 1: average delivery time over ALL parcels (lower is better)
    # ---------------------------------------------------------------
    total = len(parcel_time)    # number of parcels that day
    avg_time_taken = total_delivery_time / total if total else 0.0   # 0.0 avoids dividing by zero
    n = len(delivered)          # number of parcels delivered

    # ---------------------------------------------------------------
    # Metric 2: total km driven, rebuilt trip by trip from the log
    # ---------------------------------------------------------------
    # Distance lookup: (from, to) -> km, converted from the CSV strings
    dist = {(r["location_1"], r["location_2"]): float(r["dist"]) for r in distances}
    # Each parcel's delivery location
    location = {p["parcel_id"]: p["delivery_location_id"] for p in parcels}

    # Group deliveries into trips. A trip is identified by (vehicle_id, trip_id),
    # and events are in time order, so the stops are in the order visited
    trips = {}
    for event in events:
        if event["event_type"] == "delivery":
            key = (event["vehicle_id"], event["trip_id"])
            trips.setdefault(key, []).append(location[event["parcel_id"]])

    # Add up each trip's legs: HUB -> stop 1 -> stop 2 -> ... -> HUB
    total_km = 0.0
    for stops in trips.values():
        route = ["HUB"] + stops + ["HUB"]
        # zip pairs each stop with the next one, e.g. (HUB, L001), (L001, L002), ...
        total_km += sum(dist[(a, b)] for a, b in zip(route, route[1:]))

    # ---------------------------------------------------------------
    # Delivery cost per parcel: what it costs the company to deliver
    # one parcel, using the cost assumptions at the top of this file
    # ---------------------------------------------------------------
    driver_cost_per_minute = DRIVER_COST_PER_HOUR / 60
    driving_minutes = total_km / SPEED_KMH * 60                     # at 60 km/h, 1 km = 1 minute
    energy_cost = total_km * ENERGY_COST_PER_KM                     # electricity for every km driven
    driving_wage = driving_minutes * driver_cost_per_minute         # driver paid while driving
    loading_wage = number_of_trips * LOADING_MINUTES * driver_cost_per_minute  # driver paid while loading each trip
    total_cost = energy_cost + driving_wage + loading_wage
    cost_per_parcel = total_cost / n if n else 0.0                  # 0.0 avoids dividing by zero

    # ---------------------------------------------------------------
    # Results written to metrics.json
    # Each "if ... else 0.0" prevents dividing by zero (NaN is not allowed)
    # ---------------------------------------------------------------
    return {
        # Main metric (lower is better)
        "avg_time_taken": avg_time_taken,
        # Supporting numbers
        "number_of_trips": number_of_trips,
        "total_parcels": total,
        "delivered_count": n,
        "delivery_rate": n / total if total else 0.0,              # share of parcels delivered
        "on_time_count": on_time,
        "late_count": late,
        "early_count": early,
        "on_time_rate": on_time / total if total else 0.0,         # out of ALL parcels, not just delivered
        "avg_lateness": total_lateness / late if late else 0.0,    # minutes, averaged over late parcels only
        "total_km": total_km,
        # Second metric (lower is better)
        "km_per_delivered_parcel": total_km / n if n else 0.0,
        # Cost breakdown (SGD) based on the assumptions at the top of the file
        "energy_cost": energy_cost,
        "driver_cost": driving_wage + loading_wage,
        "total_cost": total_cost,
        "delivery_cost_per_parcel": cost_per_parcel,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """Load one day's inputs and event log, then write the metrics report."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"),
                        help="directory containing dist.csv, config.json and demand/")
    parser.add_argument("--day", required=True, help="day identifier, for example day_001")
    parser.add_argument("--log", type=Path, required=True,
                        help="event log from a simulator run")
    parser.add_argument("--output", type=Path,
                        help="JSON report (default: metrics.json beside the selected log)")
    args = parser.parse_args(argv)
    try:
        parcel_path, distance_path, config_path = day_input_paths(args.data, args.day)
        output = args.output if args.output is not None else args.log.with_name("metrics.json")
        # The input files all live in the data directory, so this also protects them.
        if output.resolve() == args.data.resolve() or args.data.resolve() in output.resolve().parents:
            raise ValueError("report output must be outside the input data directory")
        if output.resolve() == args.log.resolve():
            raise ValueError("report output must not overwrite the log")
        with parcel_path.open(newline="", encoding="utf-8-sig") as stream:
            parcels = list(csv.DictReader(stream))
        with distance_path.open(newline="", encoding="utf-8-sig") as stream:
            distances = list(csv.DictReader(stream))
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        with args.log.open(encoding="utf-8") as stream:
            events = [json.loads(line) for line in stream if line.strip()]
        metrics = calculate_metrics(parcels, distances, config, events)
        report = json.dumps(metrics, indent=2, allow_nan=False) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"Metrics report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())