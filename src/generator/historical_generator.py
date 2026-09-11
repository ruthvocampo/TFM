from datetime import datetime, timedelta
import random
import numpy as np
import pandas as pd
from faker import Faker
from src.objects.order import Order


ORDERS_TYPE = {
    "BÁSICA": 4,
    "ESTÁNDAR": 2,
    "URGENTE": 1
}


STATUS_COLUMNS = {
    "CREADO": "creado_date",

    "PENDIENTE DE ASIGNACIÓN RECOGIDA":
        "pendiente_de_asignacion_recogida_date",

    "ASIGNADO RECOGIDA":
        "asignado_recogida_date",

    "EN REPARTO RECOGIDA":
        "en_reparto_recogida_date",

    "RECOGIDO":
        "recogido_date",

    "ENVIADO":
        "enviado_date",

    "EN TRANSPORTE":
        "en_transporte_date",

    "LLEGADA A LA NAVE":
        "llegada_a_la_nave_date",

    "PENDIENTE DE ASIGNACIÓN ENTREGA":
        "pendiente_de_asignacion_entrega_date",

    "ASIGNADO ENTREGA":
        "asignado_entrega_date",

    "EN REPARTO ENTREGA":
        "en_reparto_entrega_date",

    "ENTREGADO":
        "entregado_date",

    "RECHAZADO":
        "rechazado_date",

    "INCIDENTADO":
        "incidentado_date",

    "CANCELADO":
        "cancelado_date"
}


class OrderHistoricalGenerator:

    def __init__(self,drivers, address_madrid, address_spain,fecha_actual):
        self.drivers = drivers
        self.address_madrid = address_madrid
        self.address_spain = address_spain
        self.fecha_actual = fecha_actual
        self.fake = Faker("es_ES")
        self.historical_orders = []

    def create_historical(self, n_orders, min_pending_today=600):

        # =========================================================
        # COMPROBACIONES
        # =========================================================

        if n_orders <= 0:
            return []

        # No podemos reservar más pedidos de los que vamos a generar
        min_pending_today = min(
            min_pending_today,
            n_orders
        )

        # =========================================================
        # GENERACIÓN
        # =========================================================

        for pos in range(n_orders):

            # -----------------------------------------------------
            # Elegimos qué pedidos deben pertenecer a HOY
            # -----------------------------------------------------

            is_pending_today = pos < min_pending_today

            if is_pending_today:

                operation_date = self.fecha_actual.date()

            else:

                operation_date = (
                    self.fecha_actual.date()
                    - timedelta(days=random.randint(1, 10))
                )

            # -----------------------------------------------------
            # TIPO DE SERVICIO
            # -----------------------------------------------------

            type_service = random.choice([
                "ENTREGA",
                "RECOGIDA"
            ])

            # -----------------------------------------------------
            # DIRECCIONES
            # -----------------------------------------------------

            if type_service == "ENTREGA":

                pickup_address = (
                    self.address_spain
                    .sample(1)
                    .iloc[0]
                )

                delivery_address = (
                    self.address_madrid
                    .sample(1)
                    .iloc[0]
                )

            else:

                pickup_address = (
                    self.address_madrid
                    .sample(1)
                    .iloc[0]
                )

                delivery_address = (
                    self.address_spain
                    .sample(1)
                    .iloc[0]
                )

            # -----------------------------------------------------
            # TIPO DE PEDIDO / SLA
            # -----------------------------------------------------

            type_order = random.choice(
                list(ORDERS_TYPE.keys())
            )

            # -----------------------------------------------------
            # SECUENCIA DE ESTADOS
            # -----------------------------------------------------

            status_sequence = self._generate_status_sequence(
                type_service,
                operation_date
            )

            # -----------------------------------------------------
            # FECHAS DE ESTADOS
            # -----------------------------------------------------

            status_dates = self._generate_status_dates(
                status_sequence,
                type_service,
                operation_date
            )

            current_status = status_sequence[-1]

            # -----------------------------------------------------
            # CONDUCTORES
            # -----------------------------------------------------

            id_driver = None
            id_driver_pickup = None
            id_driver_delivery = None

            if "ASIGNADO RECOGIDA" in status_sequence:

                driver = random.choice(self.drivers)

                id_driver_pickup = driver.id_driver

            if "ASIGNADO ENTREGA" in status_sequence:

                driver = random.choice(self.drivers)

                id_driver_delivery = driver.id_driver

            if type_service == "RECOGIDA":

                id_driver = id_driver_pickup

            else:

                id_driver = id_driver_delivery

            # -----------------------------------------------------
            # FECHAS PRINCIPALES
            # -----------------------------------------------------

            order_created_date = status_dates["CREADO"]

            order_expected_date = (
                order_created_date
                + timedelta(
                    days=ORDERS_TYPE[type_order]
                )
            )

            status_modified_date = (
                status_dates[current_status]
            )

            # -----------------------------------------------------
            # CREAR ORDER
            # -----------------------------------------------------

            order = Order(
                id_order=f"ORDH{pos + 1:05d}",

                id_driver=id_driver,

                order_created_date=order_created_date,
                order_expected_date=order_expected_date,

                status=current_status,
                status_modified_date=status_modified_date,

                num_products=random.randint(1, 5),

                type_order=type_order,
                type_service=type_service,
                sender = self.fake.name(),
                pickup_street=pickup_address["VIA_NOMBRE"],
                pickup_house_number=pickup_address["NUMERO"],
                pickup_floor= np.where(pickup_address['TIPO_NDP']=='PORTAL',pickup_address['PLANTA'],pd.NA),
                pickup_letter= np.where(pickup_address['TIPO_NDP']=='PORTAL',pickup_address['LETRA'],pd.NA),
                pickup_city=pickup_address["PROVINCIA"],
                pickup_postal_code=str(pickup_address["COD_POSTAL"]).strip(),
                pickup_country=pickup_address["PAIS"],
                destinatary = self.fake.name(),
                delivery_street=delivery_address["VIA_NOMBRE"],
                delivery_house_number=delivery_address["NUMERO"],
                delivery_floor= np.where(delivery_address['TIPO_NDP']=='PORTAL',delivery_address['PLANTA'],pd.NA),
                delivery_letter= np.where(delivery_address['TIPO_NDP']=='PORTAL',delivery_address['LETRA'],pd.NA),
                delivery_city=delivery_address["PROVINCIA"],
                delivery_postal_code=str(
                    delivery_address["COD_POSTAL"]
                ).strip(),
                delivery_country=delivery_address["PAIS"]
            )

            # -----------------------------------------------------
            # CONDUCTORES DE LAS FASES
            # -----------------------------------------------------

            order.id_driver_pickup = id_driver_pickup
            order.id_driver_delivery = id_driver_delivery

            # -----------------------------------------------------
            # HISTÓRICO DE ESTADOS
            # -----------------------------------------------------

            order.status_history = status_dates.copy()

            # -----------------------------------------------------
            # GUARDAR PEDIDO
            # -----------------------------------------------------

            self.historical_orders.append(order)

        # =========================================================
        # COMPROBACIÓN FINAL
        # =========================================================

        pending_today = [
            order
            for order in self.historical_orders
            if (
                order.status in [
                    "PENDIENTE DE ASIGNACIÓN RECOGIDA",
                    "PENDIENTE DE ASIGNACIÓN ENTREGA"
                ]
                and
                order.status_modified_date.date()
                == self.fecha_actual.date()
            )
        ]

        print(
            f"Generados {len(self.historical_orders)} "
            f"pedidos históricos."
        )

        print(
            f"Pedidos pendientes para hoy: "
            f"{len(pending_today)}"
        )

        return self.historical_orders

    # =====================================================
    # DÍA OPERATIVO
    # =====================================================

    def _generate_operation_date(self):

        if random.random() < 0.15:
            return self.fecha_actual.date()

        return (
            self.fecha_actual.date()
            - timedelta(days=random.randint(1, 10))
        )

    # =====================================================
    # SECUENCIA DE ESTADOS
    # =====================================================

    def _generate_status_sequence(
        self,
        type_service,
        operation_date
    ):

        is_today = (
            operation_date == self.fecha_actual.date()
        )

        # ================================================
        # RECOGIDA
        # ================================================

        if type_service == "RECOGIDA":

            sequence = [
                "CREADO",
                "PENDIENTE DE ASIGNACIÓN RECOGIDA"
            ]

            # Si es hoy, el histórico termina aquí.
            if is_today:
                return sequence

            # Cancelación antes de asignación
            if random.random() < 0.05:
                sequence.append("CANCELADO")
                return sequence

            sequence.append("ASIGNADO RECOGIDA")

            # Cancelación después de asignación
            if random.random() < 0.02:
                sequence.append("CANCELADO")
                return sequence

            sequence.extend([
                "EN REPARTO RECOGIDA",
                "RECOGIDO"
            ])

            return sequence

        # ================================================
        # ENTREGA
        # ================================================

        sequence = [
            "CREADO",
            "PENDIENTE DE ASIGNACIÓN RECOGIDA",
            "ASIGNADO RECOGIDA",
            "EN REPARTO RECOGIDA",
            "RECOGIDO",
            "ENVIADO",
            "EN TRANSPORTE",
            "LLEGADA A LA NAVE",
            "PENDIENTE DE ASIGNACIÓN ENTREGA"
        ]

        # Si es hoy, nos detenemos aquí.
        if is_today:
            return sequence

        # Cancelación antes de asignación de entrega
        if random.random() < 0.05:
            sequence.append("CANCELADO")
            return sequence

        sequence.append("ASIGNADO ENTREGA")

        # Cancelación después de asignación
        if random.random() < 0.02:
            sequence.append("CANCELADO")
            return sequence

        sequence.append("EN REPARTO ENTREGA")

        # Incidencia
        if random.random() < 0.08:

            sequence.append("INCIDENTADO")

            # La incidencia se resuelve
            if random.random() < 0.70:

                sequence.extend([
                    "ASIGNADO ENTREGA",
                    "EN REPARTO ENTREGA",
                    random.choice([
                        "ENTREGADO",
                        "RECHAZADO"
                    ])
                ])

            return sequence

        sequence.append(
            random.choice([
                "ENTREGADO",
                "RECHAZADO"
            ])
        )

        return sequence

    # =====================================================
    # FECHAS
    # =====================================================

    def _generate_status_dates(self, status_sequence, type_service, operation_date):
        dates = {}

        today = self.fecha_actual.date()
        is_today = operation_date == today

        # =========================================================
        # RECOGIDA
        #
        # CREADO
        # PENDIENTE DE ASIGNACIÓN RECOGIDA
        # ASIGNADO RECOGIDA
        # EN REPARTO RECOGIDA
        # RECOGIDO
        # =========================================================

        if type_service == "RECOGIDA":

            # -----------------------------------------------------
            # CREADO
            # -----------------------------------------------------

            created_date = self._random_datetime(
                operation_date,
                5,
                7
            )

            dates["CREADO"] = created_date

            # -----------------------------------------------------
            # PENDIENTE DE ASIGNACIÓN RECOGIDA
            # 06:00 - 07:59
            # -----------------------------------------------------

            pending_date = self._random_datetime(
                operation_date,
                6,
                7
            )

            # Tiene que ser posterior a creado
            if pending_date <= created_date:

                pending_date = (
                    created_date
                    + timedelta(
                        minutes=random.randint(10, 45)
                    )
                )

            dates[
                "PENDIENTE DE ASIGNACIÓN RECOGIDA"
            ] = pending_date

            # -----------------------------------------------------
            # SI ES HOY
            #
            # El histórico se detiene aquí.
            # OrderEvents continuará el pedido durante la
            # simulación.
            # -----------------------------------------------------

            if is_today:

                return dates

            # -----------------------------------------------------
            # CANCELADO
            # -----------------------------------------------------

            if status_sequence[-1] == "CANCELADO":

                cancel_date = (
                    pending_date
                    + timedelta(
                        minutes=random.randint(5, 120)
                    )
                )

                dates["CANCELADO"] = cancel_date

                return dates

            # -----------------------------------------------------
            # ASIGNADO RECOGIDA
            # 06:00 - 07:59
            # -----------------------------------------------------

            assigned_date = self._random_datetime(
                operation_date,
                6,
                7
            )

            if assigned_date <= pending_date:

                assigned_date = (
                    pending_date
                    + timedelta(
                        minutes=random.randint(10, 45)
                    )
                )

            dates["ASIGNADO RECOGIDA"] = assigned_date

            # -----------------------------------------------------
            # EN REPARTO RECOGIDA
            # -----------------------------------------------------

            in_delivery_date = (
                assigned_date
                + timedelta(
                    minutes=random.randint(15, 60)
                )
            )

            dates[
                "EN REPARTO RECOGIDA"
            ] = in_delivery_date

            # -----------------------------------------------------
            # RECOGIDO
            # 08:00 - 22:00
            # -----------------------------------------------------

            picked_up_date = (
                in_delivery_date
                + timedelta(
                    minutes=random.randint(30, 180)
                )
            )

            min_final = self._start_of_day(
                operation_date,
                8
            )

            max_final = self._start_of_day(
                operation_date,
                22
            )

            if picked_up_date < min_final:
                picked_up_date = min_final

            if picked_up_date > max_final:
                picked_up_date = max_final

            dates["RECOGIDO"] = picked_up_date

            return dates

        # =========================================================
        # ENTREGA
        #
        # CREADO
        # PENDIENTE DE ASIGNACIÓN RECOGIDA
        # ASIGNADO RECOGIDA
        # EN REPARTO RECOGIDA
        # RECOGIDO
        # ENVIADO
        # EN TRANSPORTE
        # LLEGADA A LA NAVE
        # PENDIENTE DE ASIGNACIÓN ENTREGA
        # ASIGNADO ENTREGA
        # EN REPARTO ENTREGA
        # INCIDENTADO / FINAL
        # =========================================================

        # ---------------------------------------------------------
        # 1. LLEGADA A LA NAVE
        #
        # La usamos como punto de referencia porque sabemos que
        # debe ocurrir durante la madrugada.
        # ---------------------------------------------------------

        warehouse_date = self._random_datetime(
            operation_date,
            0,
            5
        )

        # ---------------------------------------------------------
        # 2. EN TRANSPORTE
        #
        # Siempre antes de llegar a la nave.
        # ---------------------------------------------------------

        transport_date = (
            warehouse_date
            - timedelta(
                hours=random.randint(2, 6)
            )
        )

        # ---------------------------------------------------------
        # 3. ENVIADO
        # ---------------------------------------------------------

        sent_date = (
            transport_date
            - timedelta(
                minutes=random.randint(15, 60)
            )
        )

        # ---------------------------------------------------------
        # 4. RECOGIDO
        #
        # Tiene que ser después de las 08:00.
        #
        # Si vamos hacia atrás desde ENVIADO y caemos antes de
        # las 08:00, utilizamos el día anterior.
        # ---------------------------------------------------------

        picked_up_date = (
            sent_date
            - timedelta(
                minutes=random.randint(10, 30)
            )
        )

        min_pickup_date = self._start_of_day(
            picked_up_date.date(),
            8
        )

        if picked_up_date < min_pickup_date:

            # Si el recogido cae de madrugada, lo movemos al día
            # anterior por la tarde.
            previous_day = (
                operation_date
                - timedelta(days=1)
            )

            picked_up_date = self._random_datetime(
                previous_day,
                8,
                22
            )

            # Volvemos a calcular los estados posteriores
            sent_date = (
                picked_up_date
                + timedelta(
                    minutes=random.randint(10, 30)
                )
            )

            transport_date = (
                sent_date
                + timedelta(
                    hours=random.randint(2, 6)
                )
            )

            warehouse_date = (
                transport_date
                + timedelta(
                    hours=random.randint(1, 3)
                )
            )

            # Garantizamos que llegue de madrugada
            warehouse_date = datetime.combine(
                operation_date,
                datetime.min.time()
            ).replace(
                hour=random.randint(0, 5),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                microsecond=0
            )

            # Recalculamos transporte y enviado hacia atrás desde
            # la llegada para mantener toda la secuencia coherente.
            transport_date = (
                warehouse_date
                - timedelta(
                    hours=random.randint(2, 6)
                )
            )

            sent_date = (
                transport_date
                - timedelta(
                    minutes=random.randint(15, 60)
                )
            )

            picked_up_date = (
                sent_date
                - timedelta(
                    minutes=random.randint(10, 30)
                )
            )

        # ---------------------------------------------------------
        # 5. EN REPARTO RECOGIDA
        # ---------------------------------------------------------

        in_pickup_date = (
            picked_up_date
            - timedelta(
                minutes=random.randint(30, 180)
            )
        )

        # Tiene que ser posterior a las 06:00
        # si pertenece a la misma jornada.
        if in_pickup_date < self._start_of_day(
            picked_up_date.date(),
            6
        ):

            in_pickup_date = (
                picked_up_date
                - timedelta(
                    minutes=60
                )
            )

        # ---------------------------------------------------------
        # 6. ASIGNADO RECOGIDA
        # ---------------------------------------------------------

        assigned_pickup_date = (
            in_pickup_date
            - timedelta(
                minutes=random.randint(15, 60)
            )
        )

        # ---------------------------------------------------------
        # 7. PENDIENTE DE ASIGNACIÓN RECOGIDA
        # ---------------------------------------------------------

        pending_pickup_date = (
            assigned_pickup_date
            - timedelta(
                minutes=random.randint(10, 45)
            )
        )

        # ---------------------------------------------------------
        # 8. CREADO
        #
        # La creación puede ocurrir varios días antes.
        # ---------------------------------------------------------

        created_date = self._random_datetime(
            (
                pending_pickup_date.date()
                - timedelta(
                    days=random.randint(1, 5)
                )
            ),
            8,
            20
        )

        # =========================================================
        # GUARDAMOS LA PRIMERA PARTE
        # =========================================================

        dates["CREADO"] = created_date

        dates[
            "PENDIENTE DE ASIGNACIÓN RECOGIDA"
        ] = pending_pickup_date

        dates[
            "ASIGNADO RECOGIDA"
        ] = assigned_pickup_date

        dates[
            "EN REPARTO RECOGIDA"
        ] = in_pickup_date

        dates["RECOGIDO"] = picked_up_date

        dates["ENVIADO"] = sent_date

        dates["EN TRANSPORTE"] = transport_date

        dates["LLEGADA A LA NAVE"] = warehouse_date

        # ---------------------------------------------------------
        # PENDIENTE DE ASIGNACIÓN ENTREGA
        # ---------------------------------------------------------

        pending_delivery_date = (
            warehouse_date
            + timedelta(
                minutes=random.randint(5, 30)
            )
        )

        dates[
            "PENDIENTE DE ASIGNACIÓN ENTREGA"
        ] = pending_delivery_date

        # =========================================================
        # SI ES HOY
        #
        # El pedido llega a la nave y queda pendiente de entrega.
        # OrderEvents continuará desde aquí.
        # =========================================================

        if is_today:

            return dates

        # =========================================================
        # CANCELADO
        # =========================================================

        if status_sequence[-1] == "CANCELADO":

            cancel_date = (
                pending_delivery_date
                + timedelta(
                    minutes=random.randint(5, 120)
                )
            )

            dates["CANCELADO"] = cancel_date

            return dates

        # =========================================================
        # ASIGNADO ENTREGA
        # 06:00 - 07:59
        # =========================================================

        assigned_delivery_date = self._random_datetime(
            operation_date,
            6,
            7
        )

        if assigned_delivery_date <= pending_delivery_date:

            assigned_delivery_date = (
                pending_delivery_date
                + timedelta(
                    minutes=random.randint(10, 45)
                )
            )

        dates[
            "ASIGNADO ENTREGA"
        ] = assigned_delivery_date

        # =========================================================
        # EN REPARTO ENTREGA
        # =========================================================

        in_delivery_date = (
            assigned_delivery_date
            + timedelta(
                minutes=random.randint(15, 90)
            )
        )

        dates[
            "EN REPARTO ENTREGA"
        ] = in_delivery_date

        # =========================================================
        # INCIDENTADO
        # =========================================================

        if "INCIDENTADO" in status_sequence:

            incident_date = (
                in_delivery_date
                + timedelta(
                    minutes=random.randint(30, 180)
                )
            )

            # La incidencia nunca antes de las 08:00
            min_incident_date = self._start_of_day(
                operation_date,
                8
            )

            if incident_date < min_incident_date:
                incident_date = min_incident_date

            dates["INCIDENTADO"] = incident_date

            # -----------------------------------------------
            # INCIDENCIA RESUELTA
            # -----------------------------------------------

            later_statuses = status_sequence[
                status_sequence.index("INCIDENTADO") + 1:
            ]

            if "ASIGNADO ENTREGA" in later_statuses:

                reassigned_date = (
                    incident_date
                    + timedelta(
                        minutes=random.randint(15, 90)
                    )
                )

                dates[
                    "ASIGNADO ENTREGA"
                ] = reassigned_date

                resumed_delivery_date = (
                    reassigned_date
                    + timedelta(
                        minutes=random.randint(15, 60)
                    )
                )

                dates[
                    "EN REPARTO ENTREGA"
                ] = resumed_delivery_date

                final_status = status_sequence[-1]

                final_date = (
                    resumed_delivery_date
                    + timedelta(
                        minutes=random.randint(30, 180)
                    )
                )

                final_date = self._limit_final_date(
                    final_date,
                    operation_date
                )

                dates[final_status] = final_date

            return dates

        # =========================================================
        # ESTADO FINAL
        # =========================================================

        final_status = status_sequence[-1]

        final_date = (
            in_delivery_date
            + timedelta(
                minutes=random.randint(30, 180)
            )
        )

        final_date = self._limit_final_date(
            final_date,
            operation_date
        )

        dates[final_status] = final_date

        return dates
    # =====================================================
    # DATAFRAME
    # =====================================================

    def create_historical_dataframe(self):

        records = []

        for order in self.historical_orders:

            record = {
                "id_order": order.id_order,
                "id_driver": order.id_driver,
                "id_driver_pickup": getattr(
                    order,
                    "id_driver_pickup",
                    None
                ),
                "id_driver_delivery": getattr(
                    order,
                    "id_driver_delivery",
                    None
                ),
                "order_created_date": (
                    order.order_created_date
                ),
                "order_expected_date": (
                    order.order_expected_date
                ),
                "status": order.status,
                "status_modified_date": (
                    order.status_modified_date
                ),
                "num_products": order.num_products,
                "type_order": order.type_order,
                "type_service": order.type_service,

                "pickup_street": order.pickup_street,
                "pickup_house_number": order.pickup_house_number,
                "pickup_floor": order.pickup_floor,
                "pickup_letter": order.pickup_letter,
                "pickup_city": order.pickup_city,
                "pickup_postal_code": (
                    order.pickup_postal_code
                ),
                "pickup_country": order.pickup_country,

                "delivery_street": order.delivery_street,
                "delivery_house_number": (
                    order.delivery_house_number
                ),
                "delivery_floor": order.delivery_floor,
                "delivery_letter": order.delivery_letter,
                "delivery_city": order.delivery_city,
                "delivery_postal_code": (
                    order.delivery_postal_code
                ),
                "delivery_country": order.delivery_country
            }

            for status, column_name in STATUS_COLUMNS.items():

                record[column_name] = (
                    order.status_history.get(status)
                )

            records.append(record)

        return pd.DataFrame(records)

    # =====================================================
    # UTILIDADES
    # =====================================================

    def _random_datetime(
        self,
        operation_date,
        start_hour,
        end_hour
    ):

        return datetime.combine(
            operation_date,
            datetime.min.time()
        ).replace(
            hour=random.randint(
                start_hour,
                end_hour
            ),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
            microsecond=0
        )

    def _start_of_day(
        self,
        operation_date,
        hour
    ):

        return datetime.combine(
            operation_date,
            datetime.min.time()
        ).replace(
            hour=hour,
            minute=0,
            second=0,
            microsecond=0
        )

    def _limit_final_date(
        self,
        date,
        operation_date
    ):

        min_date = self._start_of_day(
            operation_date,
            8
        )

        max_date = self._start_of_day(
            operation_date,
            22
        )

        if date < min_date:
            return min_date

        if date > max_date:
            return max_date

        return date