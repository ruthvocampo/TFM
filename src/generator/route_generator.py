import pandas as pd
from sklearn.cluster import KMeans

from src.objects.route import Route


class RouteGenerator:

    WAREHOUSE_LATITUDE = 40.43134
    WAREHOUSE_LONGITUDE = -3.54512

    # Posibles nombres de la columna de portal.
    # Si tu fichero utiliza otro nombre, se puede añadir aquí.
    PORTAL_COLUMNS = [
        "PORTAL",
        "NUMERO",
        "NUM_PORTAL",
        "NUMERO_PORTAL",
        "NUMERO_VIA",
        "PORTAL_NUMERO",
        "Nº",
        "Nº PORTAL",
        "NUM",
    ]

    def __init__(self, drivers, addresses, fecha_actual):
        self.drivers = drivers
        self.addresses = addresses
        self.fecha_actual = fecha_actual
        self.routes = []

    # ---------------------------------------------------------
    # NORMALIZACIÓN
    # ---------------------------------------------------------

    @staticmethod
    def _normalize(value):

        if pd.isna(value):
            return ""

        value = str(value).strip().upper()

        # Evita casos como 9.0 cuando viene de pandas
        if value.endswith(".0"):
            value = value[:-2]

        return value

    # ---------------------------------------------------------
    # DETECTAR COLUMNA PORTAL
    # ---------------------------------------------------------

    def _find_portal_column(self):

        for column in self.PORTAL_COLUMNS:
            if column in self.addresses.columns:
                return column

        return None

    # ---------------------------------------------------------
    # CONDUCTORES POR ZONA
    # ---------------------------------------------------------

    def _get_drivers_by_zone(self, postal_code):

        postal_code = self._normalize(postal_code)

        return [
            driver
            for driver in self.drivers
            if self._normalize(driver.zone) == postal_code
        ]

    # ---------------------------------------------------------
    # PORTALES DE UNA ZONA
    # ---------------------------------------------------------

    def _get_streets_by_zone(self, postal_code):

        postal_code = self._normalize(postal_code)

        df = self.addresses.copy()

        df["_POSTAL"] = (
            df["COD_POSTAL"]
            .apply(self._normalize)
        )

        df = df[
            df["_POSTAL"] == postal_code
        ]

        portal_column = self._find_portal_column()

        required_columns = [
            "VIA_NOMBRE",
            "LATITUD",
            "LONGITUD"
        ]

        for column in required_columns:

            if column not in df.columns:
                raise ValueError(
                    f"Falta la columna '{column}' "
                    f"en el fichero de direcciones."
                )

        if portal_column is not None:

            columns = [
                "VIA_NOMBRE",
                portal_column,
                "LATITUD",
                "LONGITUD"
            ]

        else:

            print(
                "ADVERTENCIA: no se ha encontrado "
                "columna de portal."
            )

            columns = [
                "VIA_NOMBRE",
                "LATITUD",
                "LONGITUD"
            ]

        streets = df[columns].copy()

        # Coordenadas numéricas
        streets["LATITUD"] = pd.to_numeric(
            streets["LATITUD"],
            errors="coerce"
        )

        streets["LONGITUD"] = pd.to_numeric(
            streets["LONGITUD"],
            errors="coerce"
        )

        streets = streets.dropna(
            subset=[
                "VIA_NOMBRE",
                "LATITUD",
                "LONGITUD"
            ]
        )

        # IMPORTANTE:
        # NO hacemos drop_duplicates por calle.
        #
        # Cada portal conserva su propia fila y sus
        # propias coordenadas.
        if portal_column is not None:

            streets["_STREET"] = (
                streets["VIA_NOMBRE"]
                .apply(self._normalize)
            )

            streets["_PORTAL"] = (
                streets[portal_column]
                .apply(self._normalize)
            )

            streets = streets.drop_duplicates(
                subset=[
                    "_STREET",
                    "_PORTAL",
                    "LATITUD",
                    "LONGITUD"
                ]
            )

        else:

            streets = streets.drop_duplicates(
                subset=[
                    "VIA_NOMBRE",
                    "LATITUD",
                    "LONGITUD"
                ]
            )

        return streets.reset_index(drop=True)

    # ---------------------------------------------------------
    # ASIGNACIÓN DE PORTALES A CONDUCTORES
    # ---------------------------------------------------------

    def _assign_streets_by_proximity(
        self,
        streets,
        drivers_zone
    ):

        if len(drivers_zone) == 0 or streets.empty:
            return []

        streets = streets.copy()

        streets["LATITUD"] = streets["LATITUD"].astype(float)
        streets["LONGITUD"] = streets["LONGITUD"].astype(float)

        num_drivers = len(drivers_zone)
        num_streets = len(streets)

        n_clusters = min(
            num_drivers,
            num_streets
        )

        coordinates = streets[
            ["LATITUD", "LONGITUD"]
        ]

        if n_clusters == 1:

            streets["cluster"] = 0

        else:

            kmeans = KMeans(
                n_clusters=n_clusters,
                random_state=42,
                n_init=20
            )

            streets["cluster"] = (
                kmeans.fit_predict(coordinates)
            )

        drivers = sorted(
            drivers_zone,
            key=lambda driver: driver.id_driver
        )

        assignments = []

        if n_clusters == 1:

            cluster_driver = drivers[0]

            for _, row in streets.iterrows():

                portal = None

                if "_PORTAL" in row:
                    portal = row["_PORTAL"]

                assignments.append({
                    "id_driver": cluster_driver.id_driver,
                    "street": row["VIA_NOMBRE"],
                    "house_number": portal,
                    "latitude": float(row["LATITUD"]),
                    "longitude": float(row["LONGITUD"])
                })

            return assignments

        # Ordenamos clusters por centro geográfico
        centers = kmeans.cluster_centers_

        ordered_clusters = sorted(
            range(n_clusters),
            key=lambda cluster_id: (
                centers[cluster_id][0],
                centers[cluster_id][1]
            )
        )

        for index, cluster_id in enumerate(
            ordered_clusters
        ):

            driver = drivers[index]

            cluster_streets = streets[
                streets["cluster"] == cluster_id
            ]

            for _, row in cluster_streets.iterrows():

                portal = None

                if "_PORTAL" in row:
                    portal = row["_PORTAL"]

                assignments.append({
                    "id_driver": driver.id_driver,
                    "street": row["VIA_NOMBRE"],
                    "house_number": portal,
                    "latitude": float(row["LATITUD"]),
                    "longitude": float(row["LONGITUD"])
                })

        return assignments

    # ---------------------------------------------------------
    # DISTANCIA
    # ---------------------------------------------------------

    @staticmethod
    def _distance(
        latitude_1,
        longitude_1,
        latitude_2,
        longitude_2
    ):

        # Para ordenar rutas localmente, esta distancia
        # euclídea sobre lat/lon es suficiente.

        return (
            (latitude_2 - latitude_1) ** 2
            +
            (longitude_2 - longitude_1) ** 2
        ) ** 0.5

    # ---------------------------------------------------------
    # ORDENAR RUTAS DE UN CONDUCTOR
    # ---------------------------------------------------------

    def _order_driver_routes(
        self,
        assignments
    ):

        remaining = list(assignments)
        ordered = []

        current_latitude = (
            self.WAREHOUSE_LATITUDE
        )

        current_longitude = (
            self.WAREHOUSE_LONGITUDE
        )

        priority = 1

        while remaining:

            next_assignment = min(
                remaining,
                key=lambda assignment:
                    self._distance(
                        current_latitude,
                        current_longitude,
                        assignment["latitude"],
                        assignment["longitude"]
                    )
            )

            next_assignment["priority"] = priority

            ordered.append(next_assignment)

            current_latitude = (
                next_assignment["latitude"]
            )

            current_longitude = (
                next_assignment["longitude"]
            )

            remaining.remove(next_assignment)

            priority += 1

        return ordered

    # ---------------------------------------------------------
    # CREAR RUTAS
    # ---------------------------------------------------------

    def create_routes(self):

        self.routes = []

        route_id = 1

        postal_codes = (
            self.addresses["COD_POSTAL"]
            .dropna()
            .apply(self._normalize)
            .drop_duplicates()
            .tolist()
        )

        all_assignments = []

        # Primero asignamos los portales a conductores
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
                    f"sin portales disponibles"
                )

                continue

            assignments = (
                self._assign_streets_by_proximity(
                    streets,
                    drivers_zone
                )
            )

            for assignment in assignments:

                assignment["postal_code"] = postal_code

                all_assignments.append(
                    assignment
                )

        # -----------------------------------------------------
        # AHORA ORDENAMOS GLOBALMENTE POR CONDUCTOR
        # -----------------------------------------------------

        assignments_by_driver = {}

        for assignment in all_assignments:

            driver_id = assignment["id_driver"]

            assignments_by_driver.setdefault(
                driver_id,
                []
            ).append(assignment)

        # -----------------------------------------------------
        # CREAR ROUTES
        # -----------------------------------------------------

        for driver_id, driver_assignments in (
            assignments_by_driver.items()
        ):

            ordered_assignments = (
                self._order_driver_routes(
                    driver_assignments
                )
            )

            for assignment in ordered_assignments:

                route = Route(
                    id_route=route_id,
                    id_driver=driver_id,
                    postal_code=assignment[
                        "postal_code"
                    ],
                    street=assignment[
                        "street"
                    ],
                    house_number=assignment[
                        "house_number"
                    ],
                    latitude=assignment[
                        "latitude"
                    ],
                    longitude=assignment[
                        "longitude"
                    ],
                    priority=assignment[
                        "priority"
                    ]
                )

                self.routes.append(route)

                route_id += 1

        print(
            f"Generados {len(self.routes)} "
            f"rutas/portales."
        )

        # Información útil para comprobar el resultado
        for route in self.routes:

            print(
                f"Driver={route.id_driver} | "
                f"Priority={route.priority} | "
                f"{route.street} "
                f"{route.house_number} | "
                f"({route.latitude}, "
                f"{route.longitude})"
            )

        return self.routes