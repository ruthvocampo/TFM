from datetime import datetime
import random

from src.generator.incident_generator import IncidentGenerator


FINAL_STATUSES = [
    "RECOGIDO",
    "ENTREGADO",
    "RECHAZADO",
    "CANCELADO"
]


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
    # GENERAR TODOS LOS EVENTOS POSIBLES EN ESTE MOMENTO
    # =========================================================

    def generate_available_events(self):

        events = []

        # =====================================================
        # Recorremos las órdenes existentes
        # =====================================================

        for order in self.orders:

            # Una orden finalizada no puede avanzar más
            if order.status in FINAL_STATUSES:
                continue

            next_status = self.choose_available_next_status(order)

            if next_status is None:
                continue

            event = self.generate_event_for_order(
                order,
                next_status
            )

            if event is not None:
                events.append(event)

        return events

    # =========================================================
    # GENERAR UN EVENTO PARA UNA ORDEN CONCRETA
    # =========================================================

    def generate_event_for_order(self, order, next_status):

        previous_status = order.status

        timestamp = self._get_event_timestamp(
            order,
            next_status
        )

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

            # Guardamos el repartidor correspondiente
            if next_status == "ASIGNADO RECOGIDA":
                order.id_driver_pickup = driver_id

            elif next_status == "ASIGNADO ENTREGA":
                order.id_driver_delivery = driver_id

            order.id_driver = driver_id

        # =====================================================
        # INCIDENTE
        # =====================================================

        if next_status == "INCIDENTADO":

            previous_driver_id = order.id_driver

            incident = self.incident_generator.create_incident(
                order=order,
                incident_date=timestamp
            )

            incident.id_driver = previous_driver_id

            self.incidents.append(incident)

        # =====================================================
        # CAMBIO DE ESTADO
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
                incident
                for incident in self.incidents
                if incident.id_order == order.id_order
            ]

            if order_incidents:

                incident = order_incidents[-1]

                previous_driver_id = incident.id_driver

                # Volvemos al mismo repartidor
                order.id_driver = previous_driver_id

                order.id_driver_delivery = (
                    previous_driver_id
                )

                incident.resolve(
                    resolution_date=timestamp,
                    resolution_action="REASIGNACIÓN AL MISMO REPARTIDOR"
                )

        # =====================================================
        # CREAR EVENTO
        # =====================================================

        self.event_counter += 1

        event = {
            "id_event": self.event_counter,
            "id_order": order.id_order,
            "id_driver": order.id_driver,
            "type_service": order.type_service,
            "previous_status": previous_status,
            "status": next_status,
            "timestamp": timestamp
        }

        return event

    # =========================================================
    # DETERMINAR SI UNA ORDEN PUEDE AVANZAR
    # =========================================================

    def choose_available_next_status(self, order):

        current_status = order.status
        type_service = order.type_service

        hora = self.fecha_actual.hour

        # =====================================================
        # RECOGIDA
        # =====================================================

        if type_service == "RECOGIDA":

            if current_status == "CREADO":

                return "PENDIENTE DE ASIGNACIÓN RECOGIDA"

            if current_status == "PENDIENTE DE ASIGNACIÓN RECOGIDA":

                # Solo asignamos durante la ventana 06:00-07:59
                if 6 <= hora < 8:

                    return "ASIGNADO RECOGIDA"

                return None

            if current_status == "ASIGNADO RECOGIDA":

                if 6 <= hora < 8:

                    return "EN REPARTO RECOGIDA"

                return None

            if current_status == "EN REPARTO RECOGIDA":

                # RECOGIDO nunca antes de las 08:00
                if 8 <= hora <= 22:

                    return "RECOGIDO"

                return None

            return None

        # =====================================================
        # ENTREGA
        # =====================================================

        if type_service == "ENTREGA":

            # -------------------------------------------------
            # FASE DE RECOGIDA
            # -------------------------------------------------

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

            # -------------------------------------------------
            # LLEGADA A LA NAVE
            # -------------------------------------------------

            if current_status == "EN TRANSPORTE":

                # La llegada a nave solo puede producirse
                # durante la madrugada
                if 0 <= hora < 6:

                    return "LLEGADA A LA NAVE"

                return None

            if current_status == "LLEGADA A LA NAVE":

                return "PENDIENTE DE ASIGNACIÓN ENTREGA"

            # -------------------------------------------------
            # FASE DE ENTREGA
            # -------------------------------------------------

            if current_status == "PENDIENTE DE ASIGNACIÓN ENTREGA":

                if 6 <= hora < 8:

                    return random.choice([
                        "ASIGNADO ENTREGA",
                        "CANCELADO"
                    ])

                return None

            if current_status == "ASIGNADO ENTREGA":

                if 6 <= hora < 8:

                    return "EN REPARTO ENTREGA"

                return None

            if current_status == "EN REPARTO ENTREGA":

                # Los resultados de reparto solo se producen
                # durante la jornada.
                if 8 <= hora <= 22:

                    return random.choice([
                        "ENTREGADO",
                        "RECHAZADO",
                        "INCIDENTADO"
                    ])

                return None

            # -------------------------------------------------
            # INCIDENTE
            # -------------------------------------------------

            if current_status == "INCIDENTADO":

                # La resolución vuelve a asignación
                if 6 <= hora <= 22:

                    return "ASIGNADO ENTREGA"

                return None

            return None

        return None

    # =========================================================
    # BUSCAR REPARTIDOR
    # =========================================================

    def find_driver_for_order(self, order):

        if order.type_service == "ENTREGA":

            # En una entrega usamos el destino cuando
            # buscamos al repartidor que realizará la entrega.
            postal_code = order.delivery_postal_code
            street = order.delivery_street

        else:

            postal_code = order.pickup_postal_code
            street = order.pickup_street

        postal_code = str(
            postal_code
        ).strip()

        street = str(
            street
        ).strip().upper()

        matching_routes = [
            route
            for route in self.routes
            if (
                str(route.postal_code).strip()
                == postal_code
                and
                str(route.street).strip().upper()
                == street
            )
        ]

        if not matching_routes:

            print(
                f"{order.id_order}: "
                f"no existe ruta para "
                f"{postal_code} - {street}"
            )

            return None

        route = matching_routes[0]

        driver_id = route.id_driver

        matching_drivers = [
            driver
            for driver in self.drivers
            if (
                str(driver.id_driver).strip()
                == str(driver_id).strip()
            )
        ]

        if not matching_drivers:

            print(
                f"{order.id_order}: "
                f"no existe el conductor {driver_id}"
            )

            return None

        driver = matching_drivers[0]

        if not driver.available:

            print(
                f"{order.id_order}: "
                f"el conductor {driver_id} "
                f"no está disponible"
            )

            return None

        return driver.id_driver

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