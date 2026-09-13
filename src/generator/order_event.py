import random
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

    def id_event(self):

        self.event_counter += 1

        return self.event_counter
    
    # =========================================================
    # GENERAR EVENTO
    # =========================================================
    def generate_event(self, max_orders_per_driver=8):

        results = []

        # ==========================================================
        # 1. PRIMERO: PEDIDOS QUE NECESITAN ASIGNACIÓN
        # ==========================================================

        for order in self.orders:

            if self.is_final_status(order):
                continue

            next_status = self.choose_available_next_status(order)

            if next_status is None:
                continue

            # Si necesita asignar conductor, intentamos asignarlo
            if next_status in [
                "ASIGNADO RECOGIDA",
                "ASIGNADO ENTREGA"
            ]:

                driver_id = self.find_driver_for_order(order)

                if driver_id is None:
                    continue

            result = self.generate_event_for_order(
                order,
                next_status
            )

            if result is None:
                continue

            results.append(result)

        # ==========================================================
        # 2. AGRUPAR LOS PEDIDOS POR DRIVER
        # ==========================================================

        orders_by_driver = {}

        for order in self.orders:

            if self.is_final_status(order):
                continue

            driver_id = getattr(order, "id_driver", None)

            if driver_id is None:
                continue

            if driver_id not in orders_by_driver:
                orders_by_driver[driver_id] = []

            orders_by_driver[driver_id].append(order)

        # ==========================================================
        # 3. CADA DRIVER AVANZA HASTA 8 PEDIDOS
        # ==========================================================

        for driver_id, driver_orders in orders_by_driver.items():

            processed = 0

            for order in driver_orders:

                if processed >= max_orders_per_driver:
                    break

                if self.is_final_status(order):
                    continue

                next_status = self.choose_available_next_status(order)

                if next_status is None:
                    continue

                result = self.generate_event_for_order(
                    order,
                    next_status
                )

                if result is None:
                    continue

                results.append(result)

                processed += 1

        return results
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

    def resolve_last_incident(self, order):

        for incident in reversed(self.incidents):

            if incident.id_order == order.id_order:

                incident.resolved = True
                incident.resolution_date = self.fecha_actual
                incident.resolution_action = "Pedido reasignado"

                return incident

        return None
    
    
    def generate_delivery_completed_event(self, order):

        if order.status != "EN REPARTO ENTREGA":
            return None

        previous_status = order.status

        order.set_status(
            "ENTREGADO",
            self.fecha_actual
        )

        event = {
            "id_event": self.id_event(),
            "id_order": order.id_order,
            "id_driver": order.id_driver,
            "event_date": self.fecha_actual,
            "previous_status": previous_status,
            "type_service": order.type_service,
            "status": "ENTREGADO",
            "timestamp": int(self.fecha_actual.timestamp() * 1000)
        }

        return {
            "order_event": event,
            "incident": None
        }
    
    
    # =========================================================
    # CREAR EVENTO
    # =========================================================
    def generate_event_for_order(self, order, next_status):

        previous_status = order.status

        # =========================================================
        # ASIGNACIÓN DE RECOGIDA
        # =========================================================

        if next_status == "ASIGNADO RECOGIDA":

            driver_id = self.find_driver_for_order(order)

            if driver_id is None:
                return None

            order.id_driver = driver_id

        # =========================================================
        # ASIGNACIÓN DE ENTREGA
        # =========================================================

        elif next_status == "ASIGNADO ENTREGA":

            driver_id = self.find_driver_for_order(order)

            if driver_id is None:
                return None

            order.id_driver = driver_id

        # =========================================================
        # INCIDENCIA
        # =========================================================

        incident = None

        if next_status == "INCIDENTADO":

            incident = self.incident_generator.create_incident(
                order,self.fecha_actual
            )

            if incident is None:
                return None

        # =========================================================
        # CAMBIO DE ESTADO
        # =========================================================

        order.status = next_status

        # =========================================================
        # RESOLUCIÓN DE INCIDENCIA
        # =========================================================

        if (
            previous_status == "INCIDENTADO"
            and next_status == "ASIGNADO ENTREGA"
        ):
            self.resolve_last_incident(order)

        # =========================================================
        # EVENTO DE PEDIDO
        # =========================================================

        event = {
            "id_event": self.id_event(),
            "id_order": order.id_order,
            "id_driver": order.id_driver,
            "type_service": str(order.type_service),
            "timestamp": int(self.fecha_actual.timestamp() * 1000),
            "previous_status": previous_status,
            "type_service": str(order.type_service),
            "status": order.status
        }

        return {
            "order_event": event,
            "incident": incident
        }

    # =========================================================
    # ESTADOS SIGUIENTES
    # =========================================================
    def choose_available_next_status(self, order):

        current_status = order.status
        current_hour = self.fecha_actual.hour
        current_minute = self.fecha_actual.minute

        # ==========================================================
        # HORA ACTUAL EN FORMATO DECIMAL
        # Ejemplo:
        # 07:00 -> 7.0
        # 07:30 -> 7.5
        # 08:00 -> 8.0
        # ==========================================================

        current_time = current_hour + (current_minute / 60)

        # ==========================================================
        # RECOGIDA
        # ==========================================================

        if order.type_service == "RECOGIDA":

            if current_status == "CREADO":
                return "PENDIENTE DE ASIGNACIÓN RECOGIDA"

            if current_status == "PENDIENTE DE ASIGNACIÓN RECOGIDA":

                # De 06:00 a 07:30 se asignan las recogidas
                if 6 <= current_time < 7.5:
                    return "ASIGNADO RECOGIDA"

                return None

            if current_status == "ASIGNADO RECOGIDA":

                # Desde las 07:30 empieza el reparto/recogida
                if current_time >= 7.5:
                    return "EN REPARTO RECOGIDA"

                return None

            if current_status == "EN REPARTO RECOGIDA":

                # El pedido puede ser recogido durante la jornada
                if 8 <= current_hour <= 22:
                    return "RECOGIDO"

                return None

            if current_status == "RECOGIDO":
                return None

        # ==========================================================
        # ENTREGA
        # ==========================================================

        if order.type_service == "ENTREGA":

            if current_status == "CREADO":
                return "PENDIENTE DE ASIGNACIÓN RECOGIDA"

            if current_status == "PENDIENTE DE ASIGNACIÓN RECOGIDA":

                # La recogida se asigna durante la ventana 06:00-07:30
                if 6 <= current_time < 7.5:
                    return "ASIGNADO RECOGIDA"

                return None

            if current_status == "ASIGNADO RECOGIDA":

                if current_time >= 7.5:
                    return "EN REPARTO RECOGIDA"

                return None

            if current_status == "EN REPARTO RECOGIDA":

                return "RECOGIDO"

            if current_status == "RECOGIDO":

                return "ENVIADO"

            if current_status == "ENVIADO":

                return "EN TRANSPORTE"

            if current_status == "EN TRANSPORTE":

                # Llegada a nave durante la noche/madrugada
                if 0 <= current_hour < 6:
                    return "LLEGADA A LA NAVE"

                return None

            if current_status == "LLEGADA A LA NAVE":

                return "PENDIENTE DE ASIGNACIÓN ENTREGA"

            if current_status == "PENDIENTE DE ASIGNACIÓN ENTREGA":

                # De 06:00 a 07:30 se asignan las entregas
                if 6 <= current_time < 7.5:
                    return "ASIGNADO ENTREGA"

                return None

            if current_status == "ASIGNADO ENTREGA":

                # Desde las 07:30 comienza el reparto
                if current_time >= 7.5:
                    return "EN REPARTO ENTREGA"

                return None

            if current_status == "EN REPARTO ENTREGA":

                # 10% de probabilidad de incidente
                if random.random() < 0.10:
                    return "INCIDENTADO"

                return None

            if current_status == "INCIDENTADO":

                # Una vez resuelto, vuelve a asignado
                if current_time >= 7.5:
                    return "ASIGNADO ENTREGA"

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
