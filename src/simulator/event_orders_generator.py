from pyspark.sql import Row
from datetime import datetime, timedelta
import random
import pandas as pd
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
        order = random.choice(self.orders)
        next_status = random.choice(STATUS_TRANSITIONS[order.status_order])
        event = Row(
            id_order=order.id_order,
            id_driver=order.id_driver,
            timestamp=datetime.now(),
            previous_status=order.status_order,
            new_status=next_status
        )
        
        event_orders_df = self.spark.createDataFrame([event])
        event_orders_df.coalesce(1).write.mode("append").parquet(f"{LANDING_ROOT}/event_orders")
        
    