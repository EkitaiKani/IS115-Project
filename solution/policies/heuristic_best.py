"""Greedy, nearest neighbour then two opt"""

from typing import Dict, List

from simulator.models import Parcel, SimulationContext
from solution.policies.helpers import order_stops, is_feasible, route_cost, greedy_route

HUB = "HUB"


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    
    distances = context["travel_distance"]
    route = greedy_route(parcel, context)

    # needs at least 3 stops
    if len(route) < 3:
        return route
    new = order_stops(route, parcel, distances)
    if is_feasible(new, parcel, context) and route_cost(new, parcel, context) <= route_cost(route, parcel, context):
        return new
    return route
