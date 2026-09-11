import pandas as pd

from src.generator.incident_generator import (
    IncidentGenerator
)


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

        self.incident_generator = (
            IncidentGenerator()
        )

        self.incidents = []

    # =========================================================
    # GENERAR EVENTO
    # =========================================================

    def generate_event(self):

        for order in self.orders:

            if self.is_final_status(order):
                continue

            next_status = (
                self.choose_available_next_status(
                    order
                )
            )

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
    # ESTADOS FINALES
    # =========================================================

    def is_final_status(self, order):

        if order.type_service == "RECOGIDA":

            return order.status in [
                "RECOGIDO",
                "CANCELADO"
            ]

        if order.type_service == "ENTREGA":

            return order.status in [
                "ENTREGADO",
                "RECHAZADO",
                "CANCELADO"
            ]

        return False

    # =========================================================
    # CREAR EVENTO
    # =========================================================

    def generate_event_for_order(
        self,
        order,
        next_status
    ):

        previous_status = order.status

        timestamp = (
            self._get_event_timestamp(
                order,
                next_status
            )
        )

        incident = None

        # -----------------------------------------------------
        # ASIGNACIÓN
        # -----------------------------------------------------

        if next_status in [
            "ASIGNADO RECOGIDA",
            "ASIGNADO ENTREGA"
        ]:

            driver_id = (
                self.find_driver_for_order(
                    order
                )
            )

            if driver_id is None:

                print(
                    f"{order.id_order}: "
                    f"no se ha encontrado "
                    f"un repartidor disponible"
                )

                return None

            if next_status == "ASIGNADO RECOGIDA":

                order.id_driver_pickup = (
                    driver_id
                )

            elif next_status == "ASIGNADO ENTREGA":

                order.id_driver_delivery = (
                    driver_id
                )

            order.id_driver = driver_id

        # -----------------------------------------------------
        # INCIDENTE
        # -----------------------------------------------------

        if next_status == "INCIDENTADO":

            previous_driver_id = (
                order.id_driver
            )

            incident = (
                self.incident_generator
                .create_incident(
                    order=order,
                    incident_date=timestamp
                )
            )

            incident.id_driver = (
                previous_driver_id
            )

            self.incidents.append(
                incident
            )

        # -----------------------------------------------------
        # ACTUALIZAR PEDIDO
        # -----------------------------------------------------

        order.set_status(
            next_status,
            timestamp
        )

        # -----------------------------------------------------
        # RESOLVER INCIDENTE
        # -----------------------------------------------------

        if (
            previous_status == "INCIDENTADO"
            and
            next_status == "ASIGNADO ENTREGA"
        ):

            order_incidents = [
                incident_item
                for incident_item in self.incidents
                if incident_item.id_order
                == order.id_order
            ]

            if order_incidents:

                incident_to_resolve = (
                    order_incidents[-1]
                )

                previous_driver_id = (
                    incident_to_resolve.id_driver
                )

                order.id_driver = (
                    previous_driver_id
                )

                order.id_driver_delivery = (
                    previous_driver_id
                )

                incident_to_resolve.resolve(
                    resolution_date=timestamp,
                    resolution_action=(
                        "REASIGNACIÓN AL MISMO REPARTIDOR"
                    )
                )

        # -----------------------------------------------------
        # ID EVENTO
        # -----------------------------------------------------

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

        return {
            "order_event": order_event,
            "incident": incident
        }

    # =========================================================
    # ESTADOS SIGUIENTES
    # =========================================================

    def choose_available_next_status(
        self,
        order
    ):

        current_status = order.status

        type_service = order.type_service

        hora = self.fecha_actual.hour

        # =====================================================
        # RECOGIDA
        # =====================================================

        if type_service == "RECOGIDA":

            if current_status == "CREADO":

                return (
                    "PENDIENTE DE ASIGNACIÓN RECOGIDA"
                )

            if (
                current_status
                == "PENDIENTE DE ASIGNACIÓN RECOGIDA"
            ):

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

        # =====================================================
        # ENTREGA
        # =====================================================

        if type_service == "ENTREGA":

            if current_status == "CREADO":

                return (
                    "PENDIENTE DE ASIGNACIÓN RECOGIDA"
                )

            if (
                current_status
                == "PENDIENTE DE ASIGNACIÓN RECOGIDA"
            ):

                return "ASIGNADO RECOGIDA"

            if current_status == "ASIGNADO RECOGIDA":

                return "EN REPARTO RECOGIDA"

            if current_status == "EN REPARTO RECOGIDA":

                return "RECOGIDO"

            if current_status == "RECOGIDO":

                return "ENVIADO"

            if current_status == "ENVIADO":

                return "EN TRANSPORTE"

            if current_status == "EN TRANSPORTE":

                if 0 <= hora < 6:

                    return "LLEGADA A LA NAVE"

                return None

            if current_status == "LLEGADA A LA NAVE":

                return (
                    "PENDIENTE DE ASIGNACIÓN ENTREGA"
                )

            if (
                current_status
                == "PENDIENTE DE ASIGNACIÓN ENTREGA"
            ):

                if 6 <= hora < 8:

                    return "ASIGNADO ENTREGA"

                return None

            if current_status == "ASIGNADO ENTREGA":

                if 6 <= hora < 8:

                    return "EN REPARTO ENTREGA"

                return None

            if current_status == "EN REPARTO ENTREGA":

                # GPS será el responsable de entregar.
                return None

            if current_status == "INCIDENTADO":

                if 6 <= hora <= 22:

                    return "ASIGNADO ENTREGA"

                return None

            return None

        return None

    # =========================================================
    # NORMALIZACIÓN
    # =========================================================

    def _normalize_address_value(
        self,
        value
    ):

        if value is None:
            return ""

        try:

            if pd.isna(value):
                return ""

        except Exception:

            pass

        value = str(
            value
        ).strip().upper()

        if value.endswith(".0"):

            value = value[:-2]

        return value

    # =========================================================
    # BUSCAR DRIVER
    # =========================================================

    def find_driver_for_order(
        self,
        order
    ):

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

        postal_code = (
            self._normalize_address_value(
                postal_code
            )
        )

        street = (
            self._normalize_address_value(
                street
            )
        )

        house_number = (
            self._normalize_address_value(
                house_number
            )
        )

        exact_routes = [

            route
            for route in self.routes

            if (
                self._normalize_address_value(
                    route.postal_code
                )
                == postal_code

                and

                self._normalize_address_value(
                    route.street
                )
                == street

                and

                self._normalize_address_value(
                    route.house_number
                )
                == house_number
            )
        ]

        if not exact_routes:

            exact_routes = [

                route
                for route in self.routes

                if (
                    self._normalize_address_value(
                        route.postal_code
                    )
                    == postal_code

                    and

                    self._normalize_address_value(
                        route.street
                    )
                    == street

                    and

                    not self._normalize_address_value(
                        route.house_number
                    )
                )
            ]

        if not exact_routes:

            return None

        exact_routes = sorted(
            exact_routes,
            key=lambda route: route.priority
        )

        for route in exact_routes:

            available_drivers = [

                driver
                for driver in self.drivers

                if (
                    driver.id_driver
                    == route.id_driver
                    and driver.available
                )
            ]

            if not available_drivers:

                continue

            driver = available_drivers[0]

            order.id_driver = (
                driver.id_driver
            )

            order.id_route = (
                route.id_route
            )

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
    # INCIDENTS
    # =========================================================

    def get_incidents(self):

        return self.incidents

    # =========================================================
    # GPS ENTREGA
    # =========================================================

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