import random

from src.objects.location import Location


class GPSEvents:

    GPS_STATUSES = [
        "EN REPARTO RECOGIDA",
        "EN REPARTO ENTREGA",
    ]

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

        # -----------------------------------------------------
        # ESTADO PERSISTENTE DEL GPS
        #
        # No se reinicia cada hora.
        # -----------------------------------------------------

        self.driver_state = {}

    # ---------------------------------------------------------
    # EVENT ID
    # ---------------------------------------------------------

    def id_event_gps(self):

        self.event_counter += 1

        return self.event_counter

    # ---------------------------------------------------------
    # TIMESTAMP
    # ---------------------------------------------------------

    def timestamp(self):

        return self.fecha_actual.isoformat()

    # ---------------------------------------------------------
    # NORMALIZACIÓN
    # ---------------------------------------------------------

    @staticmethod
    def normalize(value):

        if value is None:
            return ""

        value = str(value).strip().upper()

        if value.endswith(".0"):
            value = value[:-2]

        return value

    # ---------------------------------------------------------
    # RUTAS DEL CONDUCTOR
    # ---------------------------------------------------------

    def get_routes_for_driver(self, driver_id):

        return sorted(
            [
                route
                for route in self.routes
                if route.id_driver == driver_id
            ],
            key=lambda route: route.priority
        )

    # ---------------------------------------------------------
    # PEDIDOS DE UNA RUTA
    # ---------------------------------------------------------

    def get_orders_for_route(self, route):

        return [
            order
            for order in self.orders
            if (
                getattr(order, "id_route", None)
                == route.id_route
            )
        ]

    # ---------------------------------------------------------
    # PEDIDOS DE ENTREGA ACTIVOS
    # ---------------------------------------------------------

    def get_active_delivery_orders_for_route(
        self,
        route
    ):

        return [
            order
            for order in self.get_orders_for_route(route)
            if (
                order.type_service == "ENTREGA"
                and
                order.status == "EN REPARTO ENTREGA"
            )
        ]

    # ---------------------------------------------------------
    # OBTENER / CREAR ESTADO DEL CONDUCTOR
    # ---------------------------------------------------------

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

                # Ruta que está haciendo
                "route_index": 0,

                # Progreso de 0.0 a 1.0
                "progress": 0.0,

                # Inicio del trayecto
                # Inicialmente: almacén
                "start_latitude": (
                    self.WAREHOUSE_LATITUDE
                ),

                "start_longitude": (
                    self.WAREHOUSE_LONGITUDE
                ),

                # Destino actual
                "target_latitude": (
                    float(first_route.latitude)
                ),

                "target_longitude": (
                    float(first_route.longitude)
                ),

                "route_id": first_route.id_route
            }

        return self.driver_state[driver_id]

    # ---------------------------------------------------------
    # RUTA ACTUAL
    # ---------------------------------------------------------

    def get_current_route(self, driver):

        routes = self.get_routes_for_driver(
            driver.id_driver
        )

        if not routes:
            return None

        state = self.get_driver_state(driver)

        if state is None:
            return None

        route_index = state["route_index"]

        if route_index >= len(routes):
            return None

        return routes[route_index]

    # ---------------------------------------------------------
    # POSICIÓN DEL DRIVER
    # ---------------------------------------------------------

    def get_driver_position(self, driver):

        # Si todavía no tiene GPS,
        # empieza en el almacén.
        if driver.gps is None:

            driver.set_location(
                Location(
                    self.WAREHOUSE_LATITUDE,
                    self.WAREHOUSE_LONGITUDE
                )
            )

        return {
            "latitude": float(
                driver.gps.latitude
            ),
            "longitude": float(
                driver.gps.longitude
            )
        }

    # ---------------------------------------------------------
    # AVANZAR RUTA
    # ---------------------------------------------------------

    def advance_route(self, driver):

        state = self.get_driver_state(driver)

        if state is None:
            return False

        routes = self.get_routes_for_driver(
            driver.id_driver
        )

        current_index = state["route_index"]

        next_index = current_index + 1

        if next_index >= len(routes):

            # Ya no quedan rutas
            state["route_index"] = next_index

            return False

        previous_route = routes[
            current_index
        ]

        next_route = routes[
            next_index
        ]

        # -----------------------------------------------------
        # EL SIGUIENTE TRAYECTO COMIENZA EXACTAMENTE
        # DONDE TERMINÓ EL ANTERIOR.
        # -----------------------------------------------------

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

        state["route_id"] = next_route.id_route

        # Reiniciamos únicamente el progreso
        # de la nueva ruta.
        state["progress"] = 0.0

        return True

    # ---------------------------------------------------------
    # INTERPOLACIÓN
    # ---------------------------------------------------------

    @staticmethod
    def interpolate(
        start,
        target,
        progress
    ):

        return (
            start
            +
            (target - start)
            * progress
        )

    # ---------------------------------------------------------
    # LLEGADA A DESTINO
    # ---------------------------------------------------------

    def arrive_at_route(
        self,
        driver,
        route
    ):

        orders = (
            self.get_active_delivery_orders_for_route(
                route
            )
        )

        # -----------------------------------------------------
        # ENTREGAR LOS PEDIDOS DEL MISMO PORTAL
        # -----------------------------------------------------

        for order in orders:

            order.set_status(
                "ENTREGADO",
                self.fecha_actual
            )

            print(
                f"ENTREGADO -> "
                f"Pedido {order.id_order} | "
                f"{route.street} "
                f"{route.house_number} | "
                f"GPS=({route.latitude}, "
                f"{route.longitude})"
            )

        # -----------------------------------------------------
        # GPS EXACTAMENTE EN LAS COORDENADAS DEL PORTAL
        # -----------------------------------------------------

        driver.set_location(
            Location(
                float(route.latitude),
                float(route.longitude)
            )
        )

        # -----------------------------------------------------
        # PASAR A SIGUIENTE RUTA
        # -----------------------------------------------------

        self.advance_route(driver)

    # ---------------------------------------------------------
    # ENVIAR GPS
    # ---------------------------------------------------------

    def send_gps(self, driver):

        route = self.get_current_route(driver)

        if route is None:
            return None

        # -----------------------------------------------------
        # IMPORTANTE:
        #
        # Solo movemos el GPS si el conductor tiene un pedido
        # EN REPARTO ENTREGA en esta ruta.
        # -----------------------------------------------------

        active_orders = (
            self.get_active_delivery_orders_for_route(
                route
            )
        )

        if not active_orders:

            return None

        state = self.get_driver_state(driver)

        if state is None:
            return None

        current_progress = float(
            state["progress"]
        )

        # -----------------------------------------------------
        # AVANCE ALEATORIO HACIA DELANTE
        #
        # Nunca restamos progreso.
        # Nunca retrocedemos.
        # -----------------------------------------------------

        increment = random.uniform(
            0.08,
            0.25
        )

        new_progress = (
            current_progress
            +
            increment
        )

        # -----------------------------------------------------
        # 0.97 significa:
        #
        # mientras no llegue al 100%, seguimos generando
        # posiciones intermedias.
        #
        # Cuando superaría ese valor, vamos exactamente
        # al destino.
        # -----------------------------------------------------

        if new_progress >= 1.0:

            new_progress = 1.0

        state["progress"] = new_progress

        # -----------------------------------------------------
        # CALCULAR NUEVA POSICIÓN
        # -----------------------------------------------------

        start_latitude = (
            state["start_latitude"]
        )

        start_longitude = (
            state["start_longitude"]
        )

        target_latitude = (
            state["target_latitude"]
        )

        target_longitude = (
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

        # -----------------------------------------------------
        # LLEGADA
        # -----------------------------------------------------

        if new_progress >= 1.0:

            # Ponemos exactamente las coordenadas
            # del portal.
            self.arrive_at_route(
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

        # -----------------------------------------------------
        # EVENTO GPS
        # -----------------------------------------------------

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

        key = str(driver.id_driver)

        print(
            "# GPS REPARTIDOR:",
            driver.id_driver
        )

        print(value)

        return key, value

    # ---------------------------------------------------------
    # GENERAR GPS
    # ---------------------------------------------------------

    def generate_event(self):

        events = []

        # -----------------------------------------------------
        # NO RANDOM CHOICE.
        #
        # Cada conductor que tenga una entrega activa
        # puede generar su posición GPS en esta ronda.
        # -----------------------------------------------------

        for driver in self.drivers:

            event = self.send_gps(driver)

            if event is not None:
                events.append(event)

        return events