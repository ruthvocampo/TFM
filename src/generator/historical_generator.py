from datetime import datetime, timedelta
import random

from src.objects.order import Order


ORDERS_TYPE = {
    "BÁSICA": 4,
    "ESTÁNDAR": 2,
    "URGENTE": 1
}

FINAL_STATUSES = [
    "RECOGIDO",
    "ENTREGADO",
    "RECHAZADO",
    "CANCELADO",
    "INCIDENTADO"
]


class OrderHistoricalGenerator:

    def __init__(
        self,
        drivers,
        address_madrid,
        address_spain,
        fecha_actual
    ):
        self.drivers = drivers
        self.address_madrid = address_madrid
        self.address_spain = address_spain
        self.fecha_actual = fecha_actual

        self.historical_orders = []

    def create_historical(self, n_orders):

        for pos in range(n_orders):

            type_service = random.choice(
                ["ENTREGA", "RECOGIDA"]
            )

            if type_service == "ENTREGA":
                pickup_address = self.address_spain.sample(1).iloc[0]
                delivery_address = self.address_madrid.sample(1).iloc[0]

            else:
                pickup_address = self.address_madrid.sample(1).iloc[0]
                delivery_address = self.address_spain.sample(1).iloc[0]

            type_order = random.choice(
                list(ORDERS_TYPE.keys())
            )

            status_sequence = self._generate_status_sequence(
                type_service
            )

            status_dates = self._generate_status_dates(
                status_sequence
            )

            current_status = status_sequence[-1]

            # Si el pedido sigue pendiente, todavía no tiene conductor.
            if current_status == "PENDIENTE DE ASIGNACIÓN":
                id_driver = None
            elif "ASIGNADO" in status_sequence:
                id_driver = random.choice(
                    self.drivers
                ).id_driver
            else:
                id_driver = None

            order_created_date = status_dates["EN RECOGIDA"]

            order_expected_date = (
                order_created_date
                + timedelta(days=ORDERS_TYPE[type_order])
            )

            order = Order(
                id_order=f"ORDH{pos + 1:05d}",
                id_driver=id_driver,
                order_created_date=order_created_date,
                order_expected_date=order_expected_date,
                status=current_status,
                status_modified_date=status_dates[current_status],
                num_products=random.randint(1, 5),
                type_order=type_order,
                type_service=type_service,

                pickup_street=pickup_address["Street"],
                pickup_house_number=pickup_address["HouseNumber"],
                pickup_floor=None,
                pickup_letter=None,
                pickup_city=pickup_address["Locality"],
                pickup_postal_code=str(
                    pickup_address["PostalCode"]
                ).strip(),
                pickup_country=pickup_address["Country"],

                delivery_street=delivery_address["Street"],
                delivery_house_number=delivery_address["HouseNumber"],
                delivery_floor=None,
                delivery_letter=None,
                delivery_city=delivery_address["Locality"],
                delivery_postal_code=str(
                    delivery_address["PostalCode"]
                ).strip(),
                delivery_country=delivery_address["Country"]
            )

            # Guardamos TODO el recorrido del pedido
            order.status_history = status_dates.copy()

            self.historical_orders.append(order)

        print(
            f"Generados {len(self.historical_orders)} "
            f"pedidos históricos."
        )

        return self.historical_orders

    def _generate_status_sequence(self, type_service):

        sequence = [
            "EN RECOGIDA",
            "EN TRANSPORTE",
            "LLEGADA A LA NAVE",
            "PENDIENTE DE ASIGNACIÓN"
        ]

        # Algunas órdenes continúan su recorrido
        continue_order = random.random() < 0.85

        if not continue_order:
            return sequence

        sequence.extend([
            "ASIGNADO",
            "EN REPARTO"
        ])

        if type_service == "RECOGIDA":
            sequence.append("RECOGIDO")
        else:
            sequence.append(
                random.choice([
                    "ENTREGADO",
                    "RECHAZADO",
                    "INCIDENTADO"
                ])
            )

        return sequence

    def _generate_status_dates(self, status_sequence):

        dates = {}

        # ---------------------------------------------------------
        # 1. Elegimos el día operativo en el que llega a la nave
        # ---------------------------------------------------------
        #
        # Para que existan pedidos pendientes HOY, algunas órdenes
        # tendrán como día operativo la fecha de la simulación.
        #
        # El resto se reparte en días anteriores.
        #
        if random.random() < 0.15:
            operation_date = self.fecha_actual.date()
        else:
            days_ago = random.randint(1, 10)
            operation_date = (
                self.fecha_actual.date()
                - timedelta(days=days_ago)
            )

        # ---------------------------------------------------------
        # 2. EN RECOGIDA
        # ---------------------------------------------------------

        created_date = datetime.combine(
            operation_date - timedelta(days=random.randint(1, 5)),
            datetime.min.time()
        ).replace(
            hour=random.randint(8, 20),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )

        dates["EN RECOGIDA"] = created_date

        # ---------------------------------------------------------
        # 3. EN TRANSPORTE
        # ---------------------------------------------------------

        transport_date = created_date + timedelta(
            hours=random.randint(2, 12)
        )

        dates["EN TRANSPORTE"] = transport_date

        # ---------------------------------------------------------
        # 4. LLEGADA A LA NAVE
        #    Siempre durante la madrugada
        # ---------------------------------------------------------

        warehouse_arrival = datetime.combine(
            operation_date,
            datetime.min.time()
        ).replace(
            hour=random.randint(0, 5),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )

        dates["LLEGADA A LA NAVE"] = warehouse_arrival

        # ---------------------------------------------------------
        # 5. PENDIENTE DE ASIGNACIÓN
        #
        # IMPORTANTE:
        # siempre es el MISMO día que LLEGADA A LA NAVE.
        # ---------------------------------------------------------

        pending_date = warehouse_arrival + timedelta(
            minutes=random.randint(5, 30)
        )

        dates["PENDIENTE DE ASIGNACIÓN"] = pending_date

        # Si la orden termina aquí, ya está correctamente preparada
        # para que OrderGenerator la encuentre HOY.
        if len(status_sequence) == 4:
            return dates

        # ---------------------------------------------------------
        # 6. ASIGNADO
        #    06:00 - 07:59
        # ---------------------------------------------------------

        assigned_date = datetime.combine(
            operation_date,
            datetime.min.time()
        ).replace(
            hour=random.randint(6, 7),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )

        # Nos aseguramos de que sea posterior a pendiente
        if assigned_date <= pending_date:
            assigned_date = pending_date + timedelta(
                minutes=random.randint(30, 90)
            )

        dates["ASIGNADO"] = assigned_date

        # ---------------------------------------------------------
        # 7. EN REPARTO
        # ---------------------------------------------------------

        delivery_start = assigned_date + timedelta(
            minutes=random.randint(15, 90)
        )

        dates["EN REPARTO"] = delivery_start

        # ---------------------------------------------------------
        # 8. ESTADO FINAL
        #    08:00 - 22:00
        # ---------------------------------------------------------

        final_hour = random.randint(8, 21)
        final_minute = random.randint(0, 59)

        final_date = datetime.combine(
            operation_date,
            datetime.min.time()
        ).replace(
            hour=final_hour,
            minute=final_minute,
            second=random.randint(0, 59)
        )

        # Debe ser posterior a EN REPARTO
        if final_date <= delivery_start:
            final_date = delivery_start + timedelta(
                minutes=random.randint(30, 180)
            )

            # Nunca pasar de las 22:00
            max_final_date = datetime.combine(
                operation_date,
                datetime.min.time()
            ).replace(
                hour=22,
                minute=0,
                second=0
            )

            if final_date > max_final_date:
                final_date = max_final_date

        # El último estado de la secuencia es el estado final
        final_status = status_sequence[-1]

        dates[final_status] = final_date

        return dates