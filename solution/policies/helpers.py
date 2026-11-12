from typing import List

HUB = "HUB"   # ID of the depot in the distance table

# converts time HH:MM into minutes
def to_minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def available_parcels(parcel):
    #Return IDs of parcels that are not yet assigned or delivered.
    # parcel contains EVERY parcel that has arrived, including ones already
    # on a vehicle or delivered, so keep only those still waiting at the hub
    return [pid for pid, p in parcel.items()
            if p["vehicle_assigned"] is None and p["delivery_time"] is None]
 
 
# =====================================================================
# Route measurements: departure time, load, distance, arrival times
# =====================================================================
 
def departure_time(context):
    #Time the vehicle will leave the hub if dispatched now.
    # Vehicles leave 30 minutes after planning (loading and charging)
    return context["current_time"] + context["departure_delay"]
 
 
def route_load(route, parcel):
    #Total size of all parcels in the route.
    # Add up the size of every parcel on the trip (must be <= capacity of 30)
    return sum(parcel[pid]["size"] for pid in route)
 
 
def route_distance(route, parcel, dist):
    #Total km for HUB -> each parcel's location in order -> HUB
    total = 0.0
    current = HUB                                 # every trip starts at the hub
    for pid in route:
        loc = parcel[pid]["delivery_location_id"]
        total += dist[current][loc]               # drive from where we are to the next stop
        current = loc                             # we are now at that stop
    return total + dist[current][HUB]             # finally drive back to the hub
 
 
def arrival_times(route, parcel, context):
    #Return {parcel_id: time the vehicle reaches that parcel's location}
    dist = context["travel_distance"]
    t = departure_time(context)                   # clock starts when the vehicle leaves
    current = HUB
    times = {}
    for pid in route:
        loc = parcel[pid]["delivery_location_id"]
        t += dist[current][loc]                   # 1 km = 1 minute at 60 km/h
        times[pid] = t                            # parcel is delivered when we reach its stop
        current = loc
    return times
 
 
# =====================================================================
# Route checks and scoring
# =====================================================================
 
def is_feasible(route, parcel, context):
    #True if the route meets capacity, range and the 18:00 return cutoff
    # No parcel may appear twice in the same route
    if len(route) != len(set(route)):
        return False
    # Capacity: total size must not exceed the vehicle capacity (30)
    if route_load(route, parcel) > context["capacity"]:
        return False
    # Range: the whole round trip must not exceed 320 km
    km = route_distance(route, parcel, context["travel_distance"])
    if km > context["max_trip_distance_km"]:
        return False
    # Return cutoff: vehicle must be back at the hub by 18:00
    return departure_time(context) + km <= context["return_cutoff"]
 
 
def lateness(pid, arrival, parcel):
    #Minutes after the window end (0 if delivered on time or early).
    # max(0, ...) means early or on-time deliveries count as 0 minutes late
    return max(0.0, arrival - parcel[pid]["delivery_window_end"])
 
 
def route_cost(route, parcel, context):
    # Sum of (delivery time - hub arrival time) for parcels in the route.
 
    # Uses the same formula as avg_time_taken in performance_monitor.py,
    # so policies optimise what the metric measures. Lower is better.
    
    times = arrival_times(route, parcel, context)
    # For each parcel: how long it waited from reaching the hub to being delivered
    return sum(times[pid] - parcel[pid]["arrival_time"] for pid in route)
 
 
# =====================================================================
# Stop ordering: greedy nearest-neighbour + 2-opt local search
# =====================================================================
 
def tour_length(order, dist):
    # Total km for HUB -> each location in order -> HUB.
 
    # Same as route_distance, but takes a list of location IDs
    # instead of parcel IDs.

    stops = [HUB] + order + [HUB]                             # add the hub at both ends
    # zip pairs each stop with the next one: (HUB, L1), (L1, L2), ..., (Lk, HUB)
    return sum(dist[a][b] for a, b in zip(stops, stops[1:]))
 
def greedy_route(parcel, context):
    distances = context["travel_distance"]
    departure = context["current_time"] + context["departure_delay"]
    max_distance = context["max_trip_distance_km"]
    waiting = sorted(
        available_parcels(parcel),
        key=lambda parcel_id: (parcel[parcel_id]["arrival_time"], parcel_id),
    )
    route: List[str] = []
    load = 0.0
    # km from the hub to the route's last stop, not counting the return leg.
    travelled = 0.0
    location = HUB
    for parcel_id in waiting:
        record = parcel[parcel_id]
        if load + record["size"] > context["capacity"]:
            continue
        destination = record["delivery_location_id"]
        trip_distance = travelled + distances[location][destination]
        round_trip = trip_distance + distances[destination][HUB]
        # At 60 km/h, km also equals travel time in minutes.
        if round_trip > max_distance or departure + round_trip > context["return_cutoff"]:
            continue
        route.append(parcel_id)
        load += record["size"]
        travelled = trip_distance
        location = destination
    return route

 
def nearest_neighbour(locations, dist):
    # Greedy: start at the HUB and always go to the closest unvisited location.

    # locations: list of distinct location IDs, e.g. ["L003", "L017", "L021"]
    # Returns the same locations in visiting order.

    current = "HUB"
    unvisited = list(locations)
    order = []

    while unvisited:
        nxt = min(unvisited, key=lambda loc: dist[current][loc])
        order.append(nxt)
        unvisited.remove(nxt)
        current = nxt

    return order

def nearest_neighbour_parcels(route, parcel, context):
    """Reorder a route's parcels: always go to the parcel whose stop is closest."""
    dist = context["travel_distance"]
    current = HUB
    unvisited = list(route)
    order = []
    while unvisited:
        nxt = min(unvisited,
                  key=lambda pid: dist[current][parcel[pid]["delivery_location_id"]])
        order.append(nxt)
        unvisited.remove(nxt)
        current = parcel[nxt]["delivery_location_id"]
    return order

def two_opt(order, dist):
    # Local search: reverse sections of the route while that makes it shorter.

    # order: list of location IDs from nearest_neighbour.
    # Returns an order whose tour_length is the same or shorter.
    order = list(order)
    improved = True

    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                candidate = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                if tour_length(candidate, dist) < tour_length(order, dist):
                    order = candidate
                    improved = True
                    break
            if improved:
                break

    return order

def two_opt_parcels(route, parcel, context):
    """2-opt on parcel IDs, scored by route_cost (sum of delivery times)."""
    best = list(route)
    best_cost = route_cost(best, parcel, context)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                if not is_feasible(candidate, parcel, context):
                    continue
                cost = route_cost(candidate, parcel, context)
                if cost < best_cost:          # strict, so ties cannot loop forever
                    best, best_cost = candidate, cost
                    improved = True
    return best
 
def order_stops(route, parcel, dist):
    # Reorder a trip's parcels to shorten the drive. Same parcels, new order.
 
    # route: list of parcel IDs for one trip (any order)
    # dist:  context["travel_distance"]
    # Parcels for the same location are kept together, so each location is visited once.

    # Step 1: group parcels by location (dict of lists),
    # e.g. {"L003": ["P001", "P007"], "L017": ["P002"]}
    by_location = {}
    for pid in route:
        loc = parcel[pid]["delivery_location_id"]
        by_location.setdefault(loc, []).append(pid)   # create the list the first time, then add to it
 
    # Step 2: order the distinct locations - greedy first, then improve with 2-opt
    order = nearest_neighbour(list(by_location), dist)
    order = two_opt(order, dist)
 
    # Step 3: expand back to parcel IDs in the new location order,
    # e.g. ["L017", "L003"] -> ["P002", "P001", "P007"]
    return [pid for loc in order for pid in by_location[loc]]
 