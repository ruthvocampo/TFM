from datetime import datetime, timedelta
import random
import pandas as pd
from src.config.setup import LANDING_ROOT, DATA_ADDRESS
from src.objects.order import Order




STATUS_ORDERS = [
    "PENDIENTE DE ASIGNACIÓN",
    "ASIGNADO",
    "RECOGIDO",
    "EN REPARTO",
    "ENTREGADO",
    "RECHAZADO",
    "CANCELADO",
    "INCIDENTADO"
]

class OrderGenerator:
    def __init__(self, spark, drivers,address_madrid,address_spain):
        self.spark = spark
        self.orders = []
        self.drivers = drivers
        self.address_madrid = address_madrid
        self.address_spain = address_spain


    def create_orders(self):
       
        for n in range(1, 50):
            type_order = random.choice(["ENTREGA", "RECOGIDA"])
            if type_order == "ENTREGA":
                    pickup_address= self.address_spain.get_random_address()
                    delivery_address= self.address_madrid.get_random_address()
            else:
                    pickup_address= self.address_madrid.get_random_address()
                    delivery_address= self.address_spain.get_random_address()
            
            order = Order(
                id_order = f"ORD{n:03d}",
                id_driver = None,
                order_date = datetime.now() - timedelta(days=random.randint(0, 30)),
                order_delivery_date = datetime.now() + timedelta(days=random.randint(1, 7)),
                status = "PENDIENTE DE ASIGNACIÓN",
                num_products = random.randint(1, 5),
                type_order = type_order,
                pickup_address = pickup_address,
                delivery_address = delivery_address,
            )
            
            self.orders.append(order)
        
        orders_df = self.spark.createDataFrame(self.orders)
        orders_df.coalesce(1).write.mode("overwrite").parquet(f"{LANDING_ROOT}/orders")
        