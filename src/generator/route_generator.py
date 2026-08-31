import random
import pandas as pd
from pathlib import Path
from src.objects.route import Route

from src.config.setup import LANDING_ROOT

class RouteGenerator:

    def __init__(self, drivers, addresses):
        self.drivers = drivers
        self.addresses = addresses
        self.routes = []
        
        
    def create_routes(self):
        # Códigos postales disponibles
        postal_codes = (
            self.addresses["PostalCode"]
            .dropna()
            .unique()
            .tolist()
        )

        # Mezclamos los códigos postales
        random.shuffle(postal_codes)

        # Repartimos los códigos postales entre los drivers
        for i, postal_code in enumerate(postal_codes):

            driver = self.drivers.iloc[
                i % len(self.drivers)
            ]

            driver_id = driver["id_driver"]

            streets = (
                self.addresses[
                    self.addresses["PostalCode"] == postal_code
                ]["Street"]
                .dropna()
                .unique()
                .tolist()
            )

            for street in streets:

                self.routes.append(Route(
                    id_route= i + 1,
                    id_driver= driver_id,
                    postal_code= postal_code,
                    street= street
                ))
        
        
        # Convertimos los objetos Order a DataFrame
        routes_df = pd.DataFrame([vars(route) for route in self.routes])
        
        routes_path = Path(LANDING_ROOT) / "routes"
        routes_path.mkdir(parents=True, exist_ok=True)

        routes_df.to_json(routes_path / "routes.json",orient="records",lines=True,force_ascii=False)

        return routes_df