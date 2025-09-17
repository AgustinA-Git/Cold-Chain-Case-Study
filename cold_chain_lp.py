"""Cold chain logistics LP simulation.

This module builds and solves a linear programming (LP) model that captures
common trade-offs in temperature-controlled logistics.  The scenario included
in ``main`` shows how to route palletized vaccine shipments from multiple
distribution centers to health care facilities while balancing transportation
costs, limited cooling resources, and penalties for unmet demand.

The model is intentionally verbose and well documented so it can serve as a
template for experimentation.  Adjust the scenario parameters or reuse the
``build_cold_chain_problem`` helper to explore other cold chain planning
questions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, MutableMapping, Tuple

import pulp


@dataclass(frozen=True)
class DistributionCenter:
    """Represents a refrigerated distribution center that holds inventory."""

    supply: float


@dataclass(frozen=True)
class Destination:
    """Represents a delivery point that requires temperature-sensitive goods."""

    demand: float
    cooling_required_per_pallet: float
    shortage_penalty: float


@dataclass(frozen=True)
class Route:
    """Represents a lane between a distribution center and a destination."""

    shipping_cost: float
    ambient_heat_load: float
    capacity: float | None = None


@dataclass(frozen=True)
class PackagingOption:
    """Cooling option that can be added to a shipment."""

    cost: float
    cooling_capacity: float
    co2_per_unit: float = 0.0


@dataclass(frozen=True)
class ColdChainScenario:
    """Container object for all inputs required by the LP model."""

    distribution_centers: Mapping[str, DistributionCenter]
    destinations: Mapping[str, Destination]
    routes: Mapping[Tuple[str, str], Route]
    packaging_options: Mapping[str, PackagingOption]
    packaging_inventory: Mapping[str, float]
    co2_budget: float | None = None


def _iter_routes_for_origin(routes: Iterable[Tuple[str, str]], origin: str) -> Iterable[Tuple[str, str]]:
    return (key for key in routes if key[0] == origin)


def _iter_routes_for_destination(routes: Iterable[Tuple[str, str]], destination: str) -> Iterable[Tuple[str, str]]:
    return (key for key in routes if key[1] == destination)


def build_cold_chain_problem(
    scenario: ColdChainScenario,
) -> Tuple[
    pulp.LpProblem,
    MutableMapping[Tuple[str, str], pulp.LpVariable],
    Dict[str, MutableMapping[Tuple[str, str], pulp.LpVariable]],
    MutableMapping[str, pulp.LpVariable],
]:
    """Create an LP model for the provided cold chain scenario.

    Returns the PuLP problem and the decision variable dictionaries so that the
    caller can inspect the solution after calling ``solve``.
    """

    problem = pulp.LpProblem("ColdChainLogisticsOptimization", pulp.LpMinimize)

    # Decision variables ----------------------------------------------------
    shipments = pulp.LpVariable.dicts(
        "Ship", scenario.routes.keys(), lowBound=0.0, cat="Continuous"
    )
    shortages = pulp.LpVariable.dicts(
        "Shortage", scenario.destinations.keys(), lowBound=0.0, cat="Continuous"
    )
    packaging_vars: Dict[str, MutableMapping[Tuple[str, str], pulp.LpVariable]] = {
        name: pulp.LpVariable.dicts(
            f"Use_{name}", scenario.routes.keys(), lowBound=0.0, cat="Continuous"
        )
        for name in scenario.packaging_options
    }

    # Objective -------------------------------------------------------------
    transport_cost = pulp.lpSum(
        shipments[route] * scenario.routes[route].shipping_cost
        for route in scenario.routes
    )

    cooling_cost = pulp.lpSum(
        packaging_vars[name][route] * scenario.packaging_options[name].cost
        for name in scenario.packaging_options
        for route in scenario.routes
    )

    shortage_cost = pulp.lpSum(
        shortages[dest] * scenario.destinations[dest].shortage_penalty
        for dest in scenario.destinations
    )

    problem += transport_cost + cooling_cost + shortage_cost

    # Constraints -----------------------------------------------------------
    # Demand satisfaction at each destination.
    for destination, destination_data in scenario.destinations.items():
        incoming_routes = list(
            _iter_routes_for_destination(scenario.routes.keys(), destination)
        )
        if not incoming_routes:
            raise ValueError(
                f"No inbound routes defined for destination '{destination}'."
            )

        problem += (
            pulp.lpSum(shipments[route] for route in incoming_routes)
            + shortages[destination]
            == destination_data.demand,
            f"DemandBalance_{destination}",
        )

    # Supply limits at each distribution center.
    for origin, origin_data in scenario.distribution_centers.items():
        outbound_routes = list(
            _iter_routes_for_origin(scenario.routes.keys(), origin)
        )
        if not outbound_routes:
            raise ValueError(
                f"No outbound routes defined for distribution center '{origin}'."
            )

        problem += (
            pulp.lpSum(shipments[route] for route in outbound_routes)
            <= origin_data.supply,
            f"SupplyLimit_{origin}",
        )

    # Cooling balance on every route.
    for route_key, route in scenario.routes.items():
        destination = scenario.destinations[route_key[1]]
        total_heat_load_per_pallet = (
            destination.cooling_required_per_pallet + route.ambient_heat_load
        )

        problem += (
            pulp.lpSum(
                scenario.packaging_options[name].cooling_capacity
                * packaging_vars[name][route_key]
                for name in scenario.packaging_options
            )
            >= total_heat_load_per_pallet * shipments[route_key],
            f"CoolingBalance_{route_key[0]}_{route_key[1]}",
        )

        if route.capacity is not None:
            problem += (
                shipments[route_key] <= route.capacity,
                f"RouteCapacity_{route_key[0]}_{route_key[1]}",
            )

    # Packaging resource availability.
    for name, available in scenario.packaging_inventory.items():
        problem += (
            pulp.lpSum(packaging_vars[name][route] for route in scenario.routes)
            <= available,
            f"PackagingInventory_{name}",
        )

    # Aggregate CO2 budget for dry ice usage (if provided).
    if scenario.co2_budget is not None:
        problem += (
            pulp.lpSum(
                scenario.packaging_options[name].co2_per_unit
                * packaging_vars[name][route]
                for name in scenario.packaging_options
                for route in scenario.routes
            )
            <= scenario.co2_budget,
            "CO2Budget",
        )

    return problem, shipments, packaging_vars, shortages


def solve_cold_chain_problem(
    scenario: ColdChainScenario,
) -> Dict[str, object]:
    """Solve the cold chain optimization model and report the results."""

    problem, shipments, packaging_vars, shortages = build_cold_chain_problem(
        scenario
    )

    solver = pulp.PULP_CBC_CMD(msg=False)
    problem.solve(solver)

    status = pulp.LpStatus[problem.status]

    shipments_solution = {
        route: value
        for route, value in ((route, shipments[route].value()) for route in shipments)
        if value is not None and value > 1e-6
    }

    packaging_solution: Dict[str, Dict[Tuple[str, str], float]] = {}
    for name, variables in packaging_vars.items():
        values = {
            route: var.value()
            for route, var in variables.items()
            if var.value() is not None and var.value() > 1e-6
        }
        if values:
            packaging_solution[name] = values

    shortages_solution = {
        destination: value
        for destination, value in (
            (destination, shortages[destination].value())
            for destination in shortages
        )
        if value is not None and value > 1e-6
    }

    transport_cost = sum(
        scenario.routes[route].shipping_cost * shipments[route].value()
        for route in scenario.routes
        if shipments[route].value() is not None
    )

    cooling_cost = 0.0
    for name, option in scenario.packaging_options.items():
        cooling_cost += sum(
            option.cost * packaging_vars[name][route].value()
            for route in scenario.routes
            if packaging_vars[name][route].value() is not None
        )

    shortage_cost = sum(
        scenario.destinations[destination].shortage_penalty
        * shortages[destination].value()
        for destination in scenario.destinations
        if shortages[destination].value() is not None
    )

    co2_usage = sum(
        scenario.packaging_options[name].co2_per_unit * variables[route].value()
        for name, variables in packaging_vars.items()
        for route in scenario.routes
        if variables[route].value() is not None
    )

    return {
        "status": status,
        "objective_value": pulp.value(problem.objective),
        "shipments": shipments_solution,
        "packaging": packaging_solution,
        "shortages": shortages_solution,
        "cost_breakdown": {
            "transportation": transport_cost,
            "cooling": cooling_cost,
            "shortage": shortage_cost,
        },
        "co2_usage": co2_usage,
    }


def _format_route(route: Tuple[str, str]) -> str:
    return f"{route[0]} -> {route[1]}"


def main() -> None:
    """Run a demonstration scenario and print the optimization results."""

    scenario = ColdChainScenario(
        distribution_centers={
            "Chicago_DC": DistributionCenter(supply=130),
            "Atlanta_DC": DistributionCenter(supply=140),
        },
        destinations={
            "Denver_Hospital": Destination(
                demand=75, cooling_required_per_pallet=3.5, shortage_penalty=950
            ),
            "Phoenix_Clinic": Destination(
                demand=60, cooling_required_per_pallet=4.0, shortage_penalty=1100
            ),
            "Miami_Pharmacy": Destination(
                demand=90, cooling_required_per_pallet=4.8, shortage_penalty=1300
            ),
        },
        routes={
            ("Chicago_DC", "Denver_Hospital"): Route(
                shipping_cost=210, ambient_heat_load=0.9, capacity=70
            ),
            ("Chicago_DC", "Phoenix_Clinic"): Route(
                shipping_cost=260, ambient_heat_load=1.4, capacity=65
            ),
            ("Chicago_DC", "Miami_Pharmacy"): Route(
                shipping_cost=300, ambient_heat_load=1.7, capacity=70
            ),
            ("Atlanta_DC", "Denver_Hospital"): Route(
                shipping_cost=230, ambient_heat_load=1.2, capacity=55
            ),
            ("Atlanta_DC", "Phoenix_Clinic"): Route(
                shipping_cost=250, ambient_heat_load=1.6, capacity=70
            ),
            ("Atlanta_DC", "Miami_Pharmacy"): Route(
                shipping_cost=220, ambient_heat_load=1.1, capacity=85
            ),
        },
        packaging_options={
            "gel_pack": PackagingOption(cost=6.5, cooling_capacity=2.0),
            "dry_ice": PackagingOption(
                cost=9.0, cooling_capacity=4.5, co2_per_unit=1.8
            ),
        },
        packaging_inventory={"gel_pack": 210, "dry_ice": 150},
        co2_budget=220.0,
    )

    solution = solve_cold_chain_problem(scenario)

    print("=== Cold Chain Optimization Results ===")
    print(f"Status: {solution['status']}")
    print(f"Optimal cost: ${solution['objective_value']:.2f}")

    print("\nShipments (pallets):")
    shipments = solution["shipments"]
    if shipments:
        for route, value in sorted(shipments.items()):
            print(f"  {_format_route(route)}: {value:.2f}")
    else:
        print("  No shipments recommended.")

    print("\nCooling resources applied (units):")
    packaging = solution["packaging"]
    if packaging:
        for name, allocation in packaging.items():
            print(f"  {name}:")
            for route, value in sorted(allocation.items()):
                print(f"    {_format_route(route)}: {value:.2f}")
    else:
        print("  No cooling resources required.")

    print("\nUnmet demand (pallets):")
    shortages = solution["shortages"]
    if shortages:
        for destination, value in shortages.items():
            print(f"  {destination}: {value:.2f}")
    else:
        print("  All demand satisfied.")

    print("\nCost breakdown (USD):")
    for name, value in solution["cost_breakdown"].items():
        print(f"  {name.capitalize()}: ${value:.2f}")

    if scenario.co2_budget is not None:
        print(
            f"\nCO2 budget used: {solution['co2_usage']:.2f} / {scenario.co2_budget:.2f} kg"
        )


if __name__ == "__main__":
    main()

