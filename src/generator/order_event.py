from pyspark.sql import Row
from datetime import datetime
import random

from config.setup import LANDING_ROOT


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

    def __init__(self, orders, drivers):
        self.orders = orders
        self.drivers = drivers

    def id_order_event(self):
        return random.randint(1, 300)
    
    def generate_event_order(self):

        # 1. Seleccionar un pedido
        order_index = random.randrange(len(self.orders))
        order = self.orders[order_index]

        # 2. Obtener las siguientes posibles transiciones
        possible_statuses = STATUS_TRANSITIONS[order.status_order]

        # 3. Si el pedido está en estado final, no hacemos nada
        if not possible_statuses:
            return

        # 4. Seleccionar el siguiente estado
        next_status = random.choice(possible_statuses)

        # 5. Por defecto, mantener el repartidor actual
        id_driver = order.id_driver

        # 6. Si se asigna el pedido, buscar un repartidor disponible
        if next_status == "ASIGNADO":

            available_drivers = [
                driver for driver in self.drivers
                if driver.available
            ]

            # Si no hay repartidores disponibles
            if not available_drivers:
                return

            driver = random.choice(available_drivers)
            id_driver = driver.id_driver

        # 7. Crear el evento
        id_event_order = self.id_order_event()
        id_order = order.id_order
        id_driver = id_driver
        timestamp= datetime.now()
        status = next_status
        
        value = {
            "order_event_id": id_event_order,
            "id_order": id_order,
            "id_driver": id_driver,
            "timestamp": timestamp,
            "status": status
        }

        key = id_event_order
        
        return key, value
        