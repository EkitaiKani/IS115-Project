"""Greedy first-fit dispatch in arrival order, skipping parcels that break a hard constraint."""

from typing import Dict, List

from simulator.models import Parcel, SimulationContext
from solution.policies.helpers import nearest_neighbour_parcels, is_feasible, route_cost, greedy_route

HUB = "HUB"


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    
    distances = context["travel_distance"]
    route = greedy_route(parcel, context)

    new = nearest_neighbour_parcels(route, parcel, context)
    if is_feasible(new, parcel, context) and route_cost(new, parcel, context) <= route_cost(route, parcel, context):
        return new
    return route
