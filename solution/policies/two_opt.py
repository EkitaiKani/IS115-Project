"""Greedy selection, then 2-opt on the parcel order to reduce waiting time."""

from typing import Dict, List

from simulator.models import Parcel, SimulationContext
from solution.policies.helpers import two_opt_parcels, is_feasible, route_cost, greedy_route

HUB = "HUB"


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:

    route = greedy_route(parcel, context)

    # needs at least 3 stops
    if len(route) < 3:
        return route
    new = two_opt_parcels(route, parcel, context)
    if is_feasible(new, parcel, context) and route_cost(new, parcel, context) <= route_cost(route, parcel, context):
        return new
    return route