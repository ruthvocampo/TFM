from datetime import datetime, timezone
import random


STATUS_ROUTE_TRANSITIONS = {

    "CREADA": [
        "ASIGNADA",
        "CANCELADA"
    ],

    "ASIGNADA": [
        "EN REPARTO",
        "CANCELADA"
    ],

    "EN REPARTO": [
        "FINALIZADA",
        "INCIDENTADA"
    ],

    "FINALIZADA": [],
    "CANCELADA": [],
    "INCIDENTADA": []
}


class Event_Route:

    def __init__(self, routes):

        self.routes = routes

    def id_route_event(self):

        return random.randint(1, 300)

    def generate_event_route(self):

        # 1. Seleccionar una ruta
        if not self.routes:
            return None

        route_index = random.randrange(len(self.routes))
        route = self.routes[route_index]

        # 2. Obtener posibles transiciones
        possible_statuses = STATUS_ROUTE_TRANSITIONS.get(
            route.status,
            []
        )

        # 3. Si está en estado final, no generamos evento
        if not possible_statuses:
            return None

        # 4. Seleccionar siguiente estado
        next_status = random.choice(
            possible_statuses
        )

        # 5. Crear ID del evento
        id_route_event = self.id_route_event()

        # 6. Timestamp
        timestamp = datetime.now(timezone.utc).isoformat()

        # 7. Crear evento
        value = {
            "route_event_id": id_route_event,
            "id_route": route.id_route,
            "id_driver": route.id_driver,
            "timestamp": timestamp,
            "status": next_status,
            "number_of_orders": route.number_of_orders()
        }

        key = id_route_event

        return key, value
