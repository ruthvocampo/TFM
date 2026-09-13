import random

from src.objects.location import Location


class GPSEvents:

    WAREHOUSE_LATITUDE = 40.43134
    WAREHOUSE_LONGITUDE = -3.54512

    def __init__(
        self,
        orders,
        drivers,
        routes,
        fecha_actual
    ):

        self.orders = orders
        self.drivers = drivers
        self.routes = routes
        self.fecha_actual = fecha_actual

        self.event_counter = 0

        # Estado de movimiento de cada conductor
        self.driver_state = {}

    # =========================================================
    # EVENT ID
    # =========================================================

    def id_event_gps(self):

        self.event_counter += 1

        return self.event_counter

    # =========================================================
    # TIMESTAMP
    # =========================================================

    def timestamp(self):

        return int(self.fecha_actual.timestamp() * 1000)
    # =========================================================
    # NORMALIZE
    # =========================================================

    @staticmethod
    def normalize(value):

        if value is None:
            return ""

        value = str(value).strip().upper()

        if value.endswith(".0"):
            value = value[:-2]

        return value

    # =========================================================
    # ROUTES DRIVER
    # =========================================================

    def get_routes_for_driver(self, driver_id):

        return sorted(
            [
                route
                for route in self.routes
                if route.id_driver == driver_id
            ],
            key=lambda route: route.priority
        )

    # =========================================================
    # ORDERS ROUTE
    # =========================================================

    def get_orders_for_route(self, route):

        return [
            order
            for order in self.orders
            if getattr(
                order,
                "id_route",
                None
            ) == route.id_route
        ]

    # =========================================================
    # ACTIVE DELIVERY ORDERS
    # =========================================================
    def get_active_orders_for_route(self, route):

        gps_statuses = [
            "EN REPARTO RECOGIDA",
            "RECOGIDO",
            "EN REPARTO ENTREGA",
            "ENTREGADO"
        ]

        return [
            order
            for order in self.get_orders_for_route(route)
            if (
                order.status in gps_statuses
                and getattr(order, "id_driver", None) == route.id_driver
            )
        ]


    # =========================================================
    # DRIVER STATE
    # =========================================================

    def get_driver_state(self, driver):

        driver_id = driver.id_driver

        if driver_id not in self.driver_state:

            routes = self.get_routes_for_driver(
                driver_id
            )

            if not routes:
                return None

            first_route = routes[0]

            self.driver_state[driver_id] = {

                "route_index": 0,

                "progress": 0.0,

                "start_latitude": (
                    self.WAREHOUSE_LATITUDE
                ),

                "start_longitude": (
                    self.WAREHOUSE_LONGITUDE
                ),

                "target_latitude": (
                    float(first_route.latitude)
                ),

                "target_longitude": (
                    float(first_route.longitude)
                ),

                "route_id": first_route.id_route
            }

        return self.driver_state[driver_id]

    # =========================================================
    # CURRENT ROUTE
    # =========================================================

    def get_current_route(self, driver):

        routes = self.get_routes_for_driver(
            driver.id_driver
        )

        if not routes:
            return None

        state = self.get_driver_state(
            driver
        )

        if state is None:
            return None

        route_index = int(
            state["route_index"]
        )

        if route_index >= len(routes):
            return None

        return routes[route_index]

    # =========================================================
    # POSITION
    # =========================================================

    def get_driver_position(self, driver):

        if driver.location is None:

            driver.set_location(
                Location(
                    self.WAREHOUSE_LATITUDE,
                    self.WAREHOUSE_LONGITUDE
                )
            )

        return {
            "latitude": float(
                driver.location.latitude
            ),

            "longitude": float(
                driver.location.longitude
            )
        }

    # =========================================================
    # ADVANCE ROUTE
    # =========================================================

    def advance_route(self, driver):

        state = self.get_driver_state(
            driver
        )

        if state is None:
            return False

        routes = self.get_routes_for_driver(
            driver.id_driver
        )

        current_index = int(
            state["route_index"]
        )

        next_index = current_index + 1

        if next_index >= len(routes):

            state["route_index"] = next_index

            return False

        previous_route = routes[
            current_index
        ]

        next_route = routes[
            next_index
        ]

        state["start_latitude"] = (
            float(previous_route.latitude)
        )

        state["start_longitude"] = (
            float(previous_route.longitude)
        )

        state["target_latitude"] = (
            float(next_route.latitude)
        )

        state["target_longitude"] = (
            float(next_route.longitude)
        )

        state["route_index"] = next_index

        state["route_id"] = (
            next_route.id_route
        )

        state["progress"] = 0.0

        return True

    # =========================================================
    # INTERPOLATION
    # =========================================================

    @staticmethod
    def interpolate(
        start,
        target,
        progress
    ):

        return (
            start
            + (target - start) * progress
        )

    # =========================================================
    # ARRIVE
    # =========================================================
    def arrive_at_route(
        self,
        driver,
        route
    ):

        orders = self.get_active_orders_for_route(route)

        arrived_orders = []

        for order in orders:

            arrived_orders.append(order)

            print(
                f"[GPS] LLEGADA DESTINO -> "
                f"Pedido {order.id_order} | "
                f"{route.street} "
                f"{route.house_number}"
            )

        driver.set_location(
            Location(
                float(route.latitude),
                float(route.longitude)
            )
        )

        self.advance_route(driver)

        return arrived_orders


    # =========================================================
    # SEND GPS
    # =========================================================

    def send_gps(self, driver):

        state = self.get_driver_state(driver)

        if state is None:
            return None

        routes = self.get_routes_for_driver(driver.id_driver)

        if not routes:
            return None

        # ==========================================================
        # BUSCAR TODAS LAS RUTAS QUE TIENEN PEDIDOS ACTIVOS
        # ==========================================================

        active_routes = []

        for route in routes:

            active_orders = self.get_active_orders_for_route(route)

            if active_orders:
                active_routes.append(
                    (route, active_orders)
                )

        if not active_routes:
            return None

        # ==========================================================
        # SELECCIONAR RUTA
        # ==========================================================

        current_route_index = int(state["route_index"])

        selected_route = None
        selected_orders = None
        selected_index = None

        # Primero intentamos continuar desde la ruta actual
        for route, orders in active_routes:

            route_index = next(
                (
                    i
                    for i, r in enumerate(routes)
                    if r.id_route == route.id_route
                ),
                None
            )

            if route_index is None:
                continue

            if route_index >= current_route_index:

                selected_route = route
                selected_orders = orders
                selected_index = route_index
                break

        # Si no encontramos ninguna hacia delante,
        # seleccionamos la primera ruta activa.
        if selected_route is None:

            selected_route, selected_orders = active_routes[0]

            selected_index = next(
                (
                    i
                    for i, r in enumerate(routes)
                    if r.id_route == selected_route.id_route
                ),
                None
            )

        if selected_index is None:
            return None

        # ==========================================================
        # SI HEMOS CAMBIADO DE RUTA, ACTUALIZAMOS EL ESTADO
        # ==========================================================

        if selected_index != int(state["route_index"]):

            previous_route = routes[
                int(state["route_index"])
            ] if int(state["route_index"]) < len(routes) else None

            state["route_index"] = selected_index
            state["route_id"] = selected_route.id_route
            state["progress"] = 0.0

            # La posición actual del driver será el punto de partida
            current_position = self.get_driver_position(driver)

            state["start_latitude"] = current_position["latitude"]
            state["start_longitude"] = current_position["longitude"]

            state["target_latitude"] = float(
                selected_route.latitude
            )

            state["target_longitude"] = float(
                selected_route.longitude
            )

        route = selected_route
        active_orders = selected_orders

        # ==========================================================
        # AVANZAR
        # ==========================================================

        current_progress = float(
            state["progress"]
        )

        increment = random.uniform(
            0.08,
            0.25
        )

        new_progress = min(
            1.0,
            current_progress + increment
        )

        state["progress"] = new_progress

        start_latitude = float(
            state["start_latitude"]
        )

        start_longitude = float(
            state["start_longitude"]
        )

        target_latitude = float(
            state["target_latitude"]
        )

        target_longitude = float(
            state["target_longitude"]
        )

        new_latitude = self.interpolate(
            start_latitude,
            target_latitude,
            new_progress
        )

        new_longitude = self.interpolate(
            start_longitude,
            target_longitude,
            new_progress
        )

        arrived_orders = []

        # ==========================================================
        # LLEGADA
        # ==========================================================

        if new_progress >= 1.0:

            arrived_orders = self.arrive_at_route(
                driver,
                route
            )

            latitude = float(
                route.latitude
            )

            longitude = float(
                route.longitude
            )

        else:

            new_location = Location(
                new_latitude,
                new_longitude
            )

            driver.set_location(
                new_location
            )

            latitude = float(
                new_location.latitude
            )

            longitude = float(
                new_location.longitude
            )

        # ==========================================================
        # EVENTO GPS
        # ==========================================================

        gps_event_id = self.id_event_gps()

        value = {
            "gps_event_id": gps_event_id,
            "id_driver": driver.id_driver,
            "timestamp": self.timestamp(),
            "latitude": latitude,
            "longitude": longitude,
            "id_route": route.id_route,
            "street": route.street,
            "house_number": route.house_number,
            "priority": route.priority
        }

        key = str(
            driver.id_driver
        )

        print(
            f"[GPS] Repartidor {driver.id_driver} | "
            f"Ruta {route.id_route} | "
            f"Progreso {new_progress:.2f} | "
            f"Pedidos activos {len(active_orders)}"
        )

        return (
            key,
            value,
            arrived_orders
        )
        
    def generate_event(self):

        events = []

        for driver in self.drivers:

            event = self.send_gps(driver)

            if event is not None:
                events.append(event)

        print(
            f"[GPS] Eventos generados: {len(events)}"
        )

        return events
