import random
import pandas as pd
from pathlib import Path

from src.config.setup import LANDING_ROOT
from src.objects.route import Route


class RouteManager:

    def __init__(self, drivers, orders, max_orders_per_route=10):
        self.drivers = drivers
        self.orders = orders
        self.max_orders_per_route = max_orders_per_route
        self.routes = []

    def generate_route_id(self):
        existing_ids = {route.id_route for route in self.routes}

        while True:
            route_id = random.randint(1, 300)

            if route_id not in existing_ids:
                return route_id

    def get_available_driver(self):

        available_drivers = self.drivers[
            self.drivers["available"] == True
        ]

        if available_drivers.empty:
            return None

        return available_drivers.sample(n=1).iloc[0]

    def create_route(self, order):

        driver = self.get_available_driver()

        if driver is None:
            return None

        route = Route(
            id_route=self.generate_route_id(),
            id_driver=driver["id_driver"]
        )

        route.add_order(order)

        self.routes.append(route)

        # El conductor deja de estar disponible
        self.drivers.loc[
            self.drivers["id_driver"] == driver["id_driver"],
            "available"
        ] = False

        return route

    def find_route(self):

        for route in self.routes:

            if route.status == "FINALIZADA":
                continue

            if route.number_of_orders() < self.max_orders_per_route:
                return route

        return None

    def assign_order(self, order):

        route = self.find_route()

        if route is not None:
            route.add_order(order)
            return route

        return self.create_route(order)

    def create_routes(self):

        for _, order in self.orders.iterrows():

            self.assign_order(order)

        self.save_routes()

        return self.routes

    def save_routes(self):

        route_records = []

        for route in self.routes:

            for order in route.orders:

                route_records.append({
                    "id_route": route.id_route,
                    "id_driver": route.id_driver,
                    "id_order": order["id_order"]
                })

        routes_df = pd.DataFrame(route_records)

        routes_path = Path(LANDING_ROOT) / "routes"
        routes_path.mkdir(parents=True, exist_ok=True)

        routes_df.to_json(
            routes_path / "routes.json",
            orient="records",
            lines=True,
            force_ascii=False
        )

    def finish_route(self, route):

        route.finish()

        self.drivers.loc[
            self.drivers["id_driver"] == route.id_driver,
            "available"
        ] = True

    def get_routes(self):
        return self.routes

    def get_active_routes(self):

        return [route for route in self.routes if route.status != "FINALIZADA"]