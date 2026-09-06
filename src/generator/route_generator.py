import pandas as pd
from sklearn.cluster import KMeans

from src.objects.route import Route


class RouteGenerator:

    DRIVERS_PER_ZONE = 5

    def __init__(self, drivers, addresses, fecha_actual):
        self.drivers = drivers
        self.addresses = addresses
        self.fecha_actual = fecha_actual
        self.routes = []

    def _get_drivers_by_zone(self, postal_code):
        """
        Obtiene los conductores asignados a un código postal.
        """
        postal_code = str(postal_code).strip()

        return [
            driver
            for driver in self.drivers
            if str(driver.zone).strip() == postal_code
        ]

    def _get_streets_by_zone(self, postal_code):
        """
        Obtiene las calles de un código postal junto con
        sus coordenadas en formato decimal.
        """
        postal_code = str(postal_code).strip()

        streets = self.addresses[
            self.addresses["COD_POSTAL"].astype(str).str.strip()
            == postal_code
        ][
            ["VIA_NOMBRE", "LATITUD", "LONGITUD"]
        ].dropna(
            subset=["VIA_NOMBRE", "LATITUD", "LONGITUD"]
        )

        return (
            streets
            .drop_duplicates(subset=["VIA_NOMBRE"])
            .reset_index(drop=True)
        )

    def _assign_streets_by_proximity(
        self,
        streets,
        drivers_zone
    ):
        """
        Agrupa geográficamente las calles y asigna cada grupo
        a un conductor.
        """

        n_drivers = len(drivers_zone)

        if n_drivers == 0 or streets.empty:
            return []

        n_clusters = min(
            n_drivers,
            len(streets)
        )

        coordinates = streets[
            ["LATITUD", "LONGITUD"]
        ].astype(float)

        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10
        )

        streets = streets.copy()

        streets["cluster"] = kmeans.fit_predict(
            coordinates
        )

        drivers = sorted(
            drivers_zone,
            key=lambda driver: driver.id_driver
        )

        cluster_ids = sorted(
            streets["cluster"].unique()
        )

        cluster_to_driver = {
            cluster_id: drivers[index].id_driver
            for index, cluster_id in enumerate(cluster_ids)
        }

        streets["id_driver"] = streets["cluster"].map(
            cluster_to_driver
        )

        return streets

    def create_routes(self):

        self.routes = []

        route_id = 1

        postal_codes = (
            self.addresses["COD_POSTAL"]
            .dropna()
            .astype(str)
            .str.strip()
            .drop_duplicates()
            .tolist()
        )

        for postal_code in postal_codes:

            drivers_zone = self._get_drivers_by_zone(
                postal_code
            )

            if not drivers_zone:
                print(
                    f"CP {postal_code}: "
                    f"sin conductores asignados"
                )
                continue

            streets = self._get_streets_by_zone(
                postal_code
            )

            if streets.empty:
                print(
                    f"CP {postal_code}: "
                    f"sin calles disponibles"
                )
                continue

            assigned_streets = (
                self._assign_streets_by_proximity(
                    streets,
                    drivers_zone
                )
            )

            for _, row in assigned_streets.iterrows():

                route = Route(
                    id_route=route_id,
                    id_driver=row["id_driver"],
                    postal_code=postal_code,
                    street=row["VIA_NOMBRE"]
                )

                self.routes.append(route)

                route_id += 1

        print(
            f"Generados {len(self.routes)} rutas."
        )

        return self.routes