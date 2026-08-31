from datetime import datetime
import random

from src.config.setup import LANDING_ROOT


STATUS_TRANSITIONS = {
    "PENDIENTE DE ASIGNACIÓN": [
        "ASIGNADO",
        "CANCELADO"
    ],

    "ASIGNADO": [
        "RECOGIDO",
        "CANCELADO"
    ],

    "RECOGIDO": [
        "EN REPARTO"
    ],

    "EN REPARTO": [
        "ENTREGADO",
        "RECHAZADO",
        "INCIDENTADO"
    ],

    "ENTREGADO": [],
    "RECHAZADO": [],
    "CANCELADO": [],
    "INCIDENTADO": []
}


class OrderEvents:

    def __init__(self, orders, routes):
        self.orders = orders
        self.routes = routes

    def id_order_event(self):
        return random.randint(1, 300)

    def find_driver_for_order(self, order): 
        if order["type_order"] == "ENTREGA": 
            postal_code = order["delivery_postal_code"] 
            street = order["delivery_street"] 
        elif order["type_order"] == "RECOGIDA":
            postal_code = order["pickup_postal_code"] 
            street = order["pickup_street"] 
        else: 
            return None 
        print( f"BUSCANDO RUTA: {postal_code} {street}" ) 
        
        matching_route = self.routes[ (self.routes["postal_code"].astype(str) == str(postal_code)) & (self.routes["street"].str.strip().str.upper() == str(street).strip().upper()) ] 
        if matching_route.empty: 
            print("NO EXISTE RUTA") 
            return None 
        
        driver = matching_route.iloc[0]["id_driver"] 
        print( f"RUTA ENCONTRADA → {driver}" ) 
        return driver

    def choose_next_status(self, current_status):

        possible_statuses = STATUS_TRANSITIONS.get(
            current_status,
            []
        )

        if not possible_statuses:
            return None

        if current_status == "PENDIENTE DE ASIGNACIÓN":

            return random.choices(
                possible_statuses,
                weights=[0.90, 0.10],
                k=1
            )[0]

        if current_status == "ASIGNADO":

            return random.choices(
                possible_statuses,
                weights=[0.95, 0.05],
                k=1
            )[0]

        if current_status == "EN REPARTO":

            return random.choices(
                possible_statuses,
                weights=[0.85, 0.10, 0.05],
                k=1
            )[0]

        return random.choice(possible_statuses)

    def generate_event(self):

        # -----------------------------------------
        # 1. Buscar pedidos que todavía pueden avanzar
        # -----------------------------------------

        active_orders = self.orders[
            ~self.orders["status"].isin([
                "ENTREGADO",
                "RECHAZADO",
                "CANCELADO",
                "INCIDENTADO"
            ])
        ]

        if active_orders.empty:
            return None

        # -----------------------------------------
        # 2. Seleccionar un pedido activo
        # -----------------------------------------

        order = active_orders.sample(n=1).iloc[0]

        # -----------------------------------------
        # 3. Estado actual
        # -----------------------------------------

        current_status = order["status"]

        # -----------------------------------------
        # 4. Obtener siguiente estado
        # -----------------------------------------

        next_status = self.choose_next_status(
            current_status
        )

        if next_status is None:
            return None

        # -----------------------------------------
        # 5. Repartidor actual
        # -----------------------------------------

        id_driver = order["id_driver"]

        # -----------------------------------------
        # 6. Si pasa a ASIGNADO
        # buscar repartidor mediante Route
        # -----------------------------------------

        if next_status == "ASIGNADO":

            id_driver = self.find_driver_for_order(order)

            if id_driver is None:
                return None

        # -----------------------------------------
        # 7. Crear evento
        # -----------------------------------------

        event_id = self.id_order_event()

        value = {
            "order_event_id": event_id,
            "id_order": order["id_order"],
            "id_driver": id_driver,
            "timestamp": datetime.now(),
            "status": next_status
        }

        # -----------------------------------------
        # 8. Actualizar pedido
        # -----------------------------------------

        mask = (
            self.orders["id_order"]
            == order["id_order"]
        )

        self.orders.loc[
            mask,
            "status"
        ] = next_status

        self.orders.loc[
            mask,
            "id_driver"
        ] = id_driver

        print(
            f"{order['id_order']}: "
            f"{current_status} → {next_status}"
        )

        return event_id, value