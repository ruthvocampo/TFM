import pandas as pd
import random
from config.setup import LANDING_ROOT
from src.objects import Route

class RouteGenerator:
    def __init__(self, spark, drivers, orders):
        self.spark = spark
        self.routes = []
        self.drivers = drivers
        self.orders = orders

    def create_routes(self):
        for n in range(1, 20):
            driver = random.choice(self.drivers)
            num_orders = random.randint(1, 20)
            orders_for_route = random.sample(self.orders, num_orders)
            route = Route(
                id_route=f"ROUTE{n:03d}",
                driver=driver,
                orders=orders_for_route
            )
            self.routes.append(route)

        routes_df = self.spark.createDataFrame(self.routes)
        routes_df.coalesce(1).write.mode("overwrite").parquet(f"{LANDING_ROOT}/routes")
