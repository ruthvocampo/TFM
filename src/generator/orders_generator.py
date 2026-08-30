from datetime import datetime, timedelta
import random
import pandas as pd
from pathlib import Path
from src.config.setup import LANDING_ROOT
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

    def __init__(self, drivers, address_madrid, address_spain):
        self.orders = []
        self.drivers = drivers
        self.address_madrid = address_madrid
        self.address_spain = address_spain

    def create_orders(self):

        for n in range(1, 50):

            type_order = random.choice(
                ["ENTREGA", "RECOGIDA"]
            )

            if type_order == "ENTREGA":
                pickup_address = self.address_spain.sample(1).iloc[0]
                delivery_address = self.address_madrid.sample(1).iloc[0]

            else:
                pickup_address = self.address_madrid.sample(1).iloc[0]
                delivery_address = self.address_spain.sample(1).iloc[0]

            order = Order(
                id_order=f"ORD{1500+n:03d}",
                id_driver=None,

                order_date=datetime.now() - timedelta(days=random.randint(0, 30)),

                order_delivery_date=datetime.now() + timedelta(days=random.randint(1, 7)),

                status="PENDIENTE DE ASIGNACIÓN",
                num_products=random.randint(1, 5),
                type_order=type_order,

                # Dirección de recogida
                pickup_street=pickup_address["Street"],
                pickup_house_number=str(pickup_address["HouseNumber"]),
                pickup_floor=(None if pd.isna(pickup_address["Floor"]) else int(pickup_address["Floor"])),
                pickup_letter=(None if pd.isna(pickup_address["Door"]) else str(pickup_address["Door"])),
                pickup_city=pickup_address["Locality"],
                pickup_postal_code=str(pickup_address["PostalCode"]),
                pickup_country=pickup_address["Country"],

                # Dirección de entrega
                delivery_street=delivery_address["Street"],
                delivery_house_number=str(delivery_address["HouseNumber"]),
                delivery_floor=(
                    None
                    if pd.isna(delivery_address["Floor"])
                    else int(delivery_address["Floor"])
                ),
                delivery_letter=(
                    None
                    if pd.isna(delivery_address["Door"])
                    else str(delivery_address["Door"])
                ),
                delivery_city=delivery_address["Locality"],
                delivery_postal_code=str(delivery_address["PostalCode"]),
                delivery_country=delivery_address["Country"]
            )

            self.orders.append(order)


        # Convertimos los objetos Order a DataFrame
        orders_df = pd.DataFrame([vars(order) for order in self.orders])

        # Declaramos la ruta de Orders
        orders_path = Path(LANDING_ROOT) / "orders"
        #Creamos la ruta de Orders si no existe
        orders_path.mkdir(parents=True, exist_ok=True)
        
        # Guardamos en Landing
        orders_df.to_csv(orders_path / "orders.csv",index=False, encoding="utf-8-sig")

        return orders_df