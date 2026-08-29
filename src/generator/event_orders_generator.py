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


class Event_Order:

    def __init__(self, spark, orders, drivers):
        self.spark = spark
        self.orders = orders
        self.drivers = drivers

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
        event = Row(
            id_order=order.id_order,
            id_driver=id_driver,
            timestamp=datetime.now(),
            previous_status=order.status_order,
            new_status=next_status
        )

        # 8. Guardar el evento
        event_orders_df = self.spark.createDataFrame([event])

        event_orders_df.coalesce(1).write.mode("append").parquet(f"{LANDING_ROOT}/event_orders")

        # 9. Actualizar el pedido
        updated_order = Row(id_order=order.id_order,id_driver=id_driver,timestamp=order.timestamp,status_order=next_status,num_products=order.num_products)
        
        self.orders[order_index] = updated_order
        