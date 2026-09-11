import pandas as pd

from src.generator.incident_generator import IncidentGenerator


class OrderEvents:

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

        self.incident_generator = IncidentGenerator()
        self.incidents = []

    # =========================================================
    # GENERAR UN EVENTO
    # =========================================================

    def generate_event(self):

        for order in self.orders:

            # Una orden finalizada no puede avanzar
            if self.is_final_status(order):
                continue

            next_status = self.choose_available_next_status(order)

            if next_status is None:
                continue

            event = self.generate_event_for_order(
                order,
                next_status
            )

            if event is not None:
                return event

        return None

    # =========================================================
    # COMPROBAR SI UNA ORDEN HA TERMINADO
    # =========================================================
    
    def is_final_status(self, order):

        # -----------------------------------------------------
        # SERVICIO DE RECOGIDA
        # -----------------------------------------------------

        if order.type_service == "RECOGIDA":

            return order.status in [
                "RECOGIDO",
                "CANCELADO"
            ]

        # -----------------------------------------------------
        # SERVICIO DE ENTREGA
        # -----------------------------------------------------

        if order.type_service == "ENTREGA":

            return order.status in [
                "ENTREGADO",
                "RECHAZADO",
                "CANCELADO"
            ]

        return False

    # =========================================================
    # GENERAR UN EVENTO PARA UNA ORDEN CONCRETA
    # =========================================================

    def generate_event_for_order(
        self,
        order,
        next_status
    ):

        previous_status = order.status

        timestamp = self._get_event_timestamp(
            order,
            next_status
        )

        # Por defecto no existe incidencia
        incident = None

        # =====================================================
        # ASIGNACIÓN DE REPARTIDOR
        # =====================================================

        if next_status in [
            "ASIGNADO RECOGIDA",
            "ASIGNADO ENTREGA"
        ]:

            driver_id = self.find_driver_for_order(order)

            if driver_id is None:

                print(
                    f"{order.id_order}: "
                    f"no se ha encontrado un repartidor "
                    f"disponible"
                )

                return None

            # -------------------------------------------------
            # ASIGNACIÓN DE RECOGIDA
            # -------------------------------------------------

            if next_status == "ASIGNADO RECOGIDA":

                order.id_driver_pickup = driver_id

            # -------------------------------------------------
            # ASIGNACIÓN DE ENTREGA
            # -------------------------------------------------

            elif next_status == "ASIGNADO ENTREGA":

                order.id_driver_delivery = driver_id

            # Repartidor actualmente responsable
            order.id_driver = driver_id

        # =====================================================
        # CREAR INCIDENTE
        # =====================================================

        if next_status == "INCIDENTADO":

            # Guardamos el repartidor que tenía la orden
            previous_driver_id = order.id_driver

            incident = self.incident_generator.create_incident(
                order=order,
                incident_date=timestamp
            )

            # El incidente pertenece al repartidor que
            # estaba realizando la entrega
            incident.id_driver = previous_driver_id

            # Guardamos la incidencia en la colección
            self.incidents.append(incident)

        # =====================================================
        # CAMBIO DE ESTADO DE LA ORDEN
        # =====================================================

        order.set_status(
            next_status,
            timestamp
        )

        # =====================================================
        # RESOLUCIÓN DE INCIDENCIA
        # =====================================================

        if (
            previous_status == "INCIDENTADO"
            and
            next_status == "ASIGNADO ENTREGA"
        ):

            order_incidents = [
                incident_item
                for incident_item in self.incidents
                if incident_item.id_order == order.id_order
            ]

            if order_incidents:

                # Última incidencia de esta orden
                incident_to_resolve = order_incidents[-1]

                # Guardamos el repartidor que tenía
                # la incidencia
                previous_driver_id = (
                    incident_to_resolve.id_driver
                )

                # Volvemos a asignar la orden al mismo
                # repartidor
                order.id_driver = previous_driver_id

                order.id_driver_delivery = (
                    previous_driver_id
                )

                # Cerramos la incidencia
                incident_to_resolve.resolve(
                    resolution_date=timestamp,
                    resolution_action=(
                        "REASIGNACIÓN AL MISMO REPARTIDOR"
                    )
                )

        # =====================================================
        # CREAR EVENTO DE ORDEN
        # =====================================================

        self.event_counter += 1

        order_event = {
            "id_event": self.event_counter,
            "id_order": order.id_order,
            "id_driver": order.id_driver,
            "type_service": order.type_service,
            "previous_status": previous_status,
            "status": next_status,
            "timestamp": timestamp
        }

        # Devolvemos el evento de orden y, si existe,
        # el incidente asociado
        return {
            "order_event": order_event,
            "incident": incident
        }

    # =========================================================
    # DETERMINAR SI UNA ORDEN PUEDE AVANZAR
    # =========================================================

    def choose_available_next_status(self, order):

        current_status = order.status
        type_service = order.type_service

        hora = self.fecha_actual.hour

        # =========================================================
        # RECOGIDA
        # =========================================================

        if type_service == "RECOGIDA":

            if current_status == "CREADO":
                return "PENDIENTE DE ASIGNACIÓN RECOGIDA"

            if current_status == "PENDIENTE DE ASIGNACIÓN RECOGIDA":
                if 6 <= hora < 8:
                    return "ASIGNADO RECOGIDA"
                return None

            if current_status == "ASIGNADO RECOGIDA":
                if 6 <= hora < 8:
                    return "EN REPARTO RECOGIDA"
                return None

            if current_status == "EN REPARTO RECOGIDA":
                if 8 <= hora <= 22:
                    return "RECOGIDO"
                return None

            return None

        # =========================================================
        # ENTREGA
        # =========================================================

        if type_service == "ENTREGA":

            if current_status == "CREADO":
                return "PENDIENTE DE ASIGNACIÓN RECOGIDA"

            if current_status == "PENDIENTE DE ASIGNACIÓN RECOGIDA":
                if 6 <= hora < 8:
                    return "ASIGNADO RECOGIDA"
                return None

            if current_status == "ASIGNADO RECOGIDA":
                if 6 <= hora < 8:
                    return "EN REPARTO RECOGIDA"
                return None

            if current_status == "EN REPARTO RECOGIDA":
                if 8 <= hora <= 22:
                    return "RECOGIDO"
                return None

            if current_status == "RECOGIDO":
                return "ENVIADO"

            if current_status == "ENVIADO":
                return "EN TRANSPORTE"

            if current_status == "EN TRANSPORTE":
                if 0 <= hora < 6:
                    return "LLEGADA A NAVE"
                return None

            if current_status == "LLEGADA A NAVE":
                return "PENDIENTE ASIGNACIÓN ENTREGA"

            if current_status == "PENDIENTE ASIGNACIÓN ENTREGA":
                if 6 <= hora < 8:
                    return "ASIGNADO ENTREGA"
                return None

            if current_status == "ASIGNADO ENTREGA":
                if 6 <= hora < 8:
                    return "EN REPARTO ENTREGA"
                return None

            # =====================================================
            # IMPORTANTE:
            #
            # Aquí NO ponemos ENTREGADO.
            #
            # El pedido se encuentra en reparto y será el GPS
            # quien lo marque como ENTREGADO cuando el conductor
            # llegue a las coordenadas exactas del portal.
            # =====================================================

            if current_status == "EN REPARTO ENTREGA":
                return None

            return None

        return None

    # =========================================================
    # BUSCAR REPARTIDOR
    # =========================================================

    def _normalize_address_value(self, value):

        if value is None:
            return ""

        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass

        value = str(value).strip().upper()

        if value.endswith(".0"):
            value = value[:-2]

        return value


    def find_driver_for_order(self, order):

        if order.type_service == "ENTREGA":

            postal_code = (
                order.delivery_postal_code
            )

            street = (
                order.delivery_street
            )

            house_number = (
                order.delivery_house_number
            )

        else:

            postal_code = (
                order.pickup_postal_code
            )

            street = (
                order.pickup_street
            )

            house_number = (
                order.pickup_house_number
            )

        postal_code = self._normalize_address_value(
            postal_code
        )

        street = self._normalize_address_value(
            street
        )

        house_number = self._normalize_address_value(
            house_number
        )

        # ---------------------------------------------------------
        # PRIMERA OPCIÓN:
        # CP + CALLE + PORTAL
        # ---------------------------------------------------------

        exact_routes = [
            route
            for route in self.routes
            if (
                self._normalize_address_value(
                    route.postal_code
                ) == postal_code
                and
                self._normalize_address_value(
                    route.street
                ) == street
                and
                self._normalize_address_value(
                    route.house_number
                ) == house_number
            )
        ]

        # ---------------------------------------------------------
        # FALLBACK:
        # CP + CALLE
        #
        # Solo se utiliza si no encontramos portal.
        # ---------------------------------------------------------

        if not exact_routes:

            exact_routes = [
                route
                for route in self.routes
                if (
                    self._normalize_address_value(
                        route.postal_code
                    ) == postal_code
                    and
                    self._normalize_address_value(
                        route.street
                    ) == street
                    and
                    not self._normalize_address_value(
                        route.house_number
                    )
                )
            ]

        if not exact_routes:
            return None

        # Preferimos la ruta con menor prioridad
        # disponible para ese conductor.
        exact_routes = sorted(
            exact_routes,
            key=lambda route: route.priority
        )

        for route in exact_routes:

            available_drivers = [
                driver
                for driver in self.drivers
                if (
                    driver.id_driver == route.id_driver
                    and driver.available
                )
            ]

            if not available_drivers:
                continue

            driver = available_drivers[0]

            # -----------------------------------------------------
            # MUY IMPORTANTE
            # El pedido queda ligado a ESA ruta exacta.
            # -----------------------------------------------------

            order.id_driver = driver.id_driver
            order.id_route = route.id_route

            if order.type_service == "ENTREGA":

                order.id_driver_delivery = (
                    driver.id_driver
                )

            else:

                order.id_driver_pickup = (
                    driver.id_driver
                )

            return driver.id_driver

        return None

    # =========================================================
    # TIMESTAMP
    # =========================================================

    def _get_event_timestamp(
        self,
        order,
        next_status
    ):

        return self.fecha_actual

    # =========================================================
    # INCIDENCIAS
    # =========================================================

    def get_incidents(self):

        return self.incidents
    def mark_order_delivered_from_gps(
    self,
    order,
    timestamp
    ):

        if order.status != "EN REPARTO ENTREGA":
            return False

        order.set_status(
            "ENTREGADO",
            timestamp
        )

        return True