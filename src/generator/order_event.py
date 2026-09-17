import random
import pandas as pd

from src.generator.incident_generator import (
    IncidentGenerator
)
class OrderEvents:

    def __init__(self, orders, drivers, routes, fecha_actual):
        self.orders = orders
        self.drivers = drivers
        self.routes = routes
        self.fecha_actual = fecha_actual

        self.event_counter = 0
        self.incident_generator = IncidentGenerator()
        self.incidents = []

        # Evita que un pedido avance más de una vez
        # durante el mismo tick de simulación.
        self.processed_order_ids = set()

        # Cada pedido solo puede recibir una decisión
        # de incidencia una vez.
        self._incident_decided_orders = set()
        
    # ============================================================
    # EVENT ID
    # ============================================================

    def id_event(self):
        self.event_counter += 1
        return self.event_counter

    # ============================================================
    # GENERAR EVENTOS
    # ============================================================

    def generate_event(self):

        events = []

        # Se limpia en cada tick.
        self.processed_order_ids = set()

        # --------------------------------------------------------
        # Procesar TODOS los pedidos
        # --------------------------------------------------------

        for order in self.orders:

            if order.id_order in self.processed_order_ids:
                continue

            next_status = self.choose_available_next_status(order)

            if next_status is None:
                continue

            # ----------------------------------------------------
            # ASIGNACIÓN
            # ----------------------------------------------------

            if next_status in [
                "ASIGNADO RECOGIDA",
                "ASIGNADO ENTREGA"
            ]:

                driver_id, route_id = (
                    self.find_driver_and_route_for_order(order)
                )

                # Si no hay driver con una ruta válida,
                # el pedido permanece en su estado actual.
                if driver_id is None or route_id is None:
                    continue

                # Driver asignado al pedido.
                order.id_driver = driver_id

                # Ruta concreta asignada al pedido.
                order.id_route = route_id

                # Driver específico según el tipo de operación.
                if next_status == "ASIGNADO RECOGIDA":
                    order.id_driver_pickup = driver_id

                elif next_status == "ASIGNADO ENTREGA":
                    order.id_driver_delivery = driver_id

            # ----------------------------------------------------
            # CREAR EVENTO
            # ----------------------------------------------------

            event = self.generate_event_for_order(
                order,
                next_status
            )

            if event is not None:
                events.append(event)
                self.processed_order_ids.add(
                    order.id_order
                )

        return events

    # ============================================================
    # BUSCAR DRIVER + RUTA
    # ============================================================

    def find_driver_and_route_for_order(self, order):
        candidates = []

        for route in self.routes:
            driver_id = getattr(route, "id_driver", None)
            route_id = getattr(route, "id_route", None)

            if driver_id is not None and route_id is not None:
                candidates.append((driver_id, route_id))

        if not candidates:
            return None, None

        return random.choice(candidates)

    # ============================================================
    # GENERAR EVENTO PARA PEDIDO
    # ============================================================

    def generate_event_for_order(
        self,
        order,
        next_status
    ):

        previous_status = order.status

        # --------------------------------------------------------
        # INCIDENCIA
        # --------------------------------------------------------

        if next_status == "INCIDENTADO":

            event = {
                "id_event": self.id_event(),
                "id_order": order.id_order,
                "id_driver": order.id_driver,
                "type_service": str(order.type_service),
                "timestamp": int(
                    self.fecha_actual.timestamp() * 1000
                ),
                "previous_status": previous_status,
                "type_service": str(order.type_service),
                "status": "INCIDENTADO"
            }

            order.status = "INCIDENTADO"
            order.status_modified_date = self.fecha_actual

            if (
                not hasattr(order, "status_history")
                or order.status_history is None
            ):
                order.status_history = {}

            if "INCIDENTADO" not in order.status_history:
                order.status_history[
                    "INCIDENTADO"
                ] = self.fecha_actual

            return event

        # --------------------------------------------------------
        # TRANSICIÓN NORMAL
        # --------------------------------------------------------

        order.status = next_status
        order.status_modified_date = self.fecha_actual

        if (
            not hasattr(order, "status_history")
            or order.status_history is None
        ):
            order.status_history = {}

        if next_status not in order.status_history:
            order.status_history[
                next_status
            ] = self.fecha_actual

        event = {
            "id_event": self.id_event(),
            "id_order": order.id_order,
            "id_driver": order.id_driver,
            "type_service": str(order.type_service),
            "timestamp": int(
                self.fecha_actual.timestamp() * 1000
            ),
            "previous_status": previous_status,
            "type_service": str(order.type_service),
            "status": order.status
        }

        return event

    # ============================================================
    # SIGUIENTE ESTADO
    # ============================================================

    def choose_available_next_status(self, order):

        current_status = order.status

        current_time = (
            self.fecha_actual.hour
            + self.fecha_actual.minute / 60
            + self.fecha_actual.second / 3600
        )

        # ========================================================
        # RECOGIDA
        # ========================================================

        if order.type_service == "RECOGIDA":

            if current_status == (
                "PENDIENTE DE ASIGNACIÓN RECOGIDA"
            ):

                # Ventana de asignación: 06:00 - 08:00
                if 6 <= current_time < 8:

                    if random.random() < 0.10:
                        return "CANCELADO"

                    return "ASIGNADO RECOGIDA"

                return None

            if current_status == "ASIGNADO RECOGIDA":

                # A partir de las 08:00 empieza la ruta.
                if current_time >= 8:
                    return "EN REPARTO RECOGIDA"

                return None

            if current_status == "EN REPARTO RECOGIDA":

                if random.random() < 0.95:
                    return "RECOGIDO"

                return "INCIDENTADO"

            return None

        # ========================================================
        # ENTREGA
        # ========================================================

        if order.type_service == "ENTREGA":

            # ----------------------------------------------------
            # RECOGIDA INICIAL
            # ----------------------------------------------------

            if current_status == (
                "PENDIENTE DE ASIGNACIÓN RECOGIDA"
            ):

                if 6 <= current_time < 8:

                    if random.random() < 0.10:
                        return "CANCELADO"

                    return "ASIGNADO RECOGIDA"

                return None

            if current_status == "ASIGNADO RECOGIDA":

                if current_time >= 8:
                    return "EN REPARTO RECOGIDA"

                return None

            if current_status == "EN REPARTO RECOGIDA":

                return "RECOGIDO"

            # ----------------------------------------------------
            # TRANSPORTE
            # ----------------------------------------------------

            if current_status == "RECOGIDO":
                return "ENVIADO"

            if current_status == "ENVIADO":
                return "EN TRANSPORTE"

            if current_status == "EN TRANSPORTE":
                return "LLEGADA A LA NAVE"

            # ----------------------------------------------------
            # ASIGNACIÓN DE ENTREGA
            # ----------------------------------------------------

            if current_status == (
                "LLEGADA A LA NAVE"
            ):
                return "PENDIENTE DE ASIGNACIÓN ENTREGA"

            if current_status == (
                "PENDIENTE DE ASIGNACIÓN ENTREGA"
            ):

                # Ventana de asignación: 06:00 - 08:00
                if 6 <= current_time < 8:

                    if random.random() < 0.10:
                        return "CANCELADO"

                    return "ASIGNADO ENTREGA"

                return None

            if current_status == "ASIGNADO ENTREGA":

                # Salida a reparto desde las 08:00.
                if current_time >= 8:
                    return "EN REPARTO ENTREGA"

                return None

            # ----------------------------------------------------
            # ENTREGA FINAL
            # ----------------------------------------------------

            if current_status == "EN REPARTO ENTREGA":

                # Solo se decide una vez si el pedido
                # tiene una incidencia.
                if order.id_order not in (
                    self._incident_decided_orders
                ):

                    self._incident_decided_orders.add(
                        order.id_order
                    )

                    # 10% de incidencia.
                    if random.random() < 0.10:
                        return "INCIDENTADO"

                # Sin incidencia.
                if random.random() < 0.85:
                    return "ENTREGADO"

                return "RECHAZADO"

            # ----------------------------------------------------
            # RESOLUCIÓN DE INCIDENCIA
            # ----------------------------------------------------

            if current_status == "INCIDENTADO":
                return "ASIGNADO ENTREGA"

            return None

        return None

    # ============================================================
    # EVENTO ENTREGA COMPLETADA
    # ============================================================
    def generate_delivery_completed_event(self, order):

        previous_status = order.status

        if order.type_service == "RECOGIDA":
            final_status = "RECOGIDO"
        else:
            final_status = "ENTREGADO"

        order.status = final_status
        order.status_modified_date = self.fecha_actual

        if (
            not hasattr(order, "status_history")
            or order.status_history is None
        ):
            order.status_history = {}

        if final_status not in order.status_history:
            order.status_history[final_status] = (
                self.fecha_actual
            )

        event = {
            "id_event": self.id_event(),
            "id_order": order.id_order,
            "id_driver": order.id_driver,
            "type_service": str(order.type_service),
            "timestamp": int(
                self.fecha_actual.timestamp() * 1000
            ),
            "previous_status": previous_status,
            "status": final_status
        }

        return event

    # ============================================================
    # RESOLVER INCIDENCIA
    # ============================================================

    def resolve_last_incident(self, order):

        if order is None:
            return None

        if order.status != "INCIDENTADO":
            return None

        previous_status = order.status

        order.status = "ASIGNADO ENTREGA"
        order.status_modified_date = self.fecha_actual

        if (
            not hasattr(order, "status_history")
            or order.status_history is None
        ):
            order.status_history = {}

        if "ASIGNADO ENTREGA" not in order.status_history:
            order.status_history[
                "ASIGNADO ENTREGA"
            ] = self.fecha_actual

        event = {
            "id_event": self.id_event(),
            "id_order": order.id_order,
            "id_driver": order.id_driver,
            "type_service": order.type_service,
            "timestamp": int(
                self.fecha_actual.timestamp() * 1000
            ),
            "previous_status": previous_status,
            "status": "ASIGNADO ENTREGA"
        }

        return event