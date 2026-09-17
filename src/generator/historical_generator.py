from datetime import datetime, timedelta
import random
import numpy as np
import pandas as pd
from faker import Faker
from src.objects.order import Order


class OrderHistoricalGenerator:

    ORDERS_TYPE = {
        "BÁSICA": 4,
        "ESTÁNDAR": 2,
        "URGENTE": 1
    }

    STATUS_COLUMNS = [
        "CREADO",
        "PENDIENTE DE ASIGNACIÓN RECOGIDA",
        "ASIGNADO RECOGIDA",
        "EN REPARTO RECOGIDA",
        "RECOGIDO",
        "ENVIADO",
        "EN TRANSPORTE",
        "LLEGADA A LA NAVE",
        "PENDIENTE DE ASIGNACIÓN ENTREGA",
        "ASIGNADO ENTREGA",
        "EN REPARTO ENTREGA",
        "ENTREGADO",
        "RECHAZADO",
        "CANCELADO",
        "INCIDENTADO"
    ]

    def __init__(
        self,
        drivers,
        addresses_madrid,
        addresses_spain,
        fecha_actual
    ):

        self.drivers = drivers
        self.addresses_madrid = addresses_madrid
        self.addresses_spain = addresses_spain
        self.fecha_actual = fecha_actual

        self.fake = Faker("es_ES")

        self.historical_orders = []

    # ============================================================
    # CREAR HISTÓRICO
    # ============================================================

    def create_historical(self, n_orders, today_orders):

        self.historical_orders = []

        # --------------------------------------------------------
        # VALIDAR VOLUMEN
        # --------------------------------------------------------

        if n_orders < 0:
            raise ValueError(
                "n_orders no puede ser negativo."
            )

        if today_orders < 0:
            raise ValueError(
                "today_orders no puede ser negativo."
            )

        if today_orders > n_orders:
            today_orders = n_orders

        print(
            f"[HISTORICAL] Pedidos totales: {n_orders}"
        )

        print(
            f"[HISTORICAL] Pedidos creados hoy: {today_orders}"
        )

        print(
            f"[HISTORICAL] Pedidos históricos: "
            f"{n_orders - today_orders}"
        )

        # --------------------------------------------------------
        # CREAR PEDIDOS
        # --------------------------------------------------------

        for i in range(n_orders):

            # ----------------------------------------------------
            # FECHA DE CREACIÓN
            # ----------------------------------------------------

            if i < today_orders:

                # Pedido creado HOY
                created_date = self._random_datetime(
                    self.fecha_actual.date()
                )

            else:

                # Pedido histórico de días anteriores
                days_ago = random.randint(1, 10)

                created_date = self._random_datetime(
                    (
                        self.fecha_actual
                        - timedelta(days=days_ago)
                    ).date()
                )

            # ----------------------------------------------------
            # NUNCA PERMITIR FECHA FUTURA
            # ----------------------------------------------------

            if created_date > self.fecha_actual:

                created_date = (
                    self.fecha_actual
                    - timedelta(
                        minutes=random.randint(1, 60)
                    )
                )

            # ----------------------------------------------------
            # TIPO DE SERVICIO
            #
            # 90% ENTREGA
            # 10% RECOGIDA
            # ----------------------------------------------------

            if random.random() < 0.90:

                type_service = "ENTREGA"

            else:

                type_service = "RECOGIDA"

            # ----------------------------------------------------
            # TIPO DE PEDIDO / SLA
            # ----------------------------------------------------

            type_order = random.choice(
                list(self.ORDERS_TYPE.keys())
            )

            sla_days = self.ORDERS_TYPE[type_order]

            expected_date = (
                created_date
                + timedelta(days=sla_days)
            )

            # ----------------------------------------------------
            # DIRECCIONES
            # ----------------------------------------------------

            if type_service == "ENTREGA":

                # Recogida en España
                pickup = self._random_address(
                    self.addresses_spain
                )

                # Entrega en Madrid
                delivery = self._random_address(
                    self.addresses_madrid
                )

            else:

                # Recogida en Madrid
                pickup = self._random_address(
                    self.addresses_madrid
                )

                # Destino en España
                delivery = self._random_address(
                    self.addresses_spain
                )

            # ----------------------------------------------------
            # DATOS DEL PEDIDO
            # ----------------------------------------------------

            id_order = f"ORDER-{i + 1:08d}"

            sender = self.fake.company()

            destinatary = self.fake.name()

            num_products = random.randint(1, 5)

            # ----------------------------------------------------
            # HISTORIAL DE ESTADOS
            # ----------------------------------------------------
            #
            # PEDIDOS CREADOS HOY:
            #
            #   CREADO
            #       ↓
            #   PENDIENTE DE ASIGNACIÓN RECOGIDA
            #
            # Esto es igual tanto para RECOGIDA como para ENTREGA.
            #
            # Una ENTREGA no puede saltarse la recogida.
            #
            # PEDIDOS HISTÓRICOS:
            #
            # Se genera la evolución completa posible hasta
            # self.fecha_actual.
            # ----------------------------------------------------

            if created_date.date() == self.fecha_actual.date():

                status_history = {
                    "CREADO": created_date
                }

                # ------------------------------------------------
                # TODOS LOS PEDIDOS NUEVOS EMPIEZAN POR RECOGIDA
                # ------------------------------------------------

                current_status = (
                    "PENDIENTE DE ASIGNACIÓN RECOGIDA"
                )

                # Generamos el momento real en el que pasa
                # al estado pendiente de recogida.
                status_modified_date = self._next_date(
                    created_date
                )

                # Nunca puede quedar después de la fecha actual.
                if status_modified_date > self.fecha_actual:

                    status_modified_date = (
                        self.fecha_actual
                    )

                status_history[current_status] = (
                    status_modified_date
                )

            else:

                # ------------------------------------------------
                # PEDIDO HISTÓRICO
                # ------------------------------------------------

                status_history = (
                    self._generate_historical_history(
                        type_service,
                        created_date,
                        expected_date
                    )
                )

                (
                    current_status,
                    status_modified_date
                ) = self._get_last_historical_status(
                    status_history,
                    created_date
                )

            # ----------------------------------------------------
            # CREAR OBJETO ORDER
            # ----------------------------------------------------

            order = Order(
                id_order,
                None,
                created_date,
                expected_date,
                current_status,
                status_modified_date,
                num_products,
                type_order,
                type_service,
                sender,

                # -------------------------
                # PICKUP
                # -------------------------

                pickup["street"],
                pickup["house_number"],
                pickup.get("floor", ""),
                pickup.get("letter", ""),
                pickup["city"],
                pickup["postal_code"],
                pickup.get("country", "España"),

                # -------------------------
                # DESTINATARIO
                # -------------------------

                destinatary,

                # -------------------------
                # DELIVERY
                # -------------------------

                delivery["street"],
                delivery["house_number"],
                delivery.get("floor", ""),
                delivery.get("letter", ""),
                delivery["city"],
                delivery["postal_code"],
                delivery.get("country", "España")
            )

            # ----------------------------------------------------
            # HISTORIAL
            # ----------------------------------------------------

            order.status_history = status_history

            # ----------------------------------------------------
            # SIN DRIVER NI RUTA AL CREAR EL HISTÓRICO
            # ----------------------------------------------------

            order.id_driver = None
            order.id_driver_pickup = None
            order.id_driver_delivery = None
            order.id_route = None

            # ----------------------------------------------------
            # GUARDAR PEDIDO
            # ----------------------------------------------------

            self.historical_orders.append(order)

        # --------------------------------------------------------
        # RESULTADO
        # --------------------------------------------------------

        print(
            f"Generados {len(self.historical_orders)} "
            f"pedidos históricos."
        )

        print(
            f"Pedidos creados hoy: {today_orders}"
        )

        print(
            f"Pedidos históricos anteriores: "
            f"{len(self.historical_orders) - today_orders}"
        )

        return self.historical_orders

    # ============================================================
    # HISTORIAL DE ESTADOS
    # ============================================================

    def _generate_historical_history(
        self,
        type_service,
        created_date,
        expected_date
    ):

        history = {}

        # --------------------------------------------------------
        # CREADO
        # --------------------------------------------------------

        history["CREADO"] = created_date

        current_date = created_date

        # --------------------------------------------------------
        # RECOGIDA
        # --------------------------------------------------------

        pickup_statuses = [
            "PENDIENTE DE ASIGNACIÓN RECOGIDA",
            "ASIGNADO RECOGIDA",
            "EN REPARTO RECOGIDA",
            "RECOGIDO"
        ]

        for status in pickup_statuses:

            current_date = self._next_date(
                current_date
            )

            # Si el siguiente estado ocurre después
            # de la fecha actual, el pedido se queda
            # en el estado anterior.
            if current_date > self.fecha_actual:
                break

            history[status] = current_date

        # --------------------------------------------------------
        # SI ES RECOGIDA, TERMINAMOS
        # --------------------------------------------------------

        if type_service == "RECOGIDA":

            # Solo tiene sentido cancelar después de haber
            # llegado a un estado operativo de recogida.
            if "RECOGIDO" in history:

                if random.random() < 0.05:

                    cancel_date = self._next_date(
                        history["RECOGIDO"]
                    )

                    if cancel_date <= self.fecha_actual:

                        history["CANCELADO"] = (
                            cancel_date
                        )

            return history

        # --------------------------------------------------------
        # ENTREGA
        # --------------------------------------------------------
        #
        # IMPORTANTE:
        #
        # Una ENTREGA primero tiene que pasar por:
        #
        # CREADO
        # ↓
        # PENDIENTE DE ASIGNACIÓN RECOGIDA
        # ↓
        # ASIGNADO RECOGIDA
        # ↓
        # EN REPARTO RECOGIDA
        # ↓
        # RECOGIDO
        #
        # Solo después puede entrar en:
        #
        # ENVIADO
        # ↓
        # EN TRANSPORTE
        # ↓
        # LLEGADA A LA NAVE
        # ↓
        # PENDIENTE DE ASIGNACIÓN ENTREGA
        # ...

        # --------------------------------------------------------
        # SI TODAVÍA NO HA SIDO RECOGIDO
        # --------------------------------------------------------

        if "RECOGIDO" not in history:

            return history

        # --------------------------------------------------------
        # FASE DE TRANSPORTE / ENTREGA
        # --------------------------------------------------------

        delivery_statuses = [
            "ENVIADO",
            "EN TRANSPORTE",
            "LLEGADA A LA NAVE",
            "PENDIENTE DE ASIGNACIÓN ENTREGA",
            "ASIGNADO ENTREGA",
            "EN REPARTO ENTREGA"
        ]

        for status in delivery_statuses:

            current_date = self._next_date(
                current_date
            )

            if current_date > self.fecha_actual:

                break

            history[status] = current_date

        # --------------------------------------------------------
        # RESULTADO FINAL
        # --------------------------------------------------------

        if "EN REPARTO ENTREGA" in history:

            # 90% de probabilidad de tener resultado final
            if random.random() < 0.90:

                # 90% de esos casos son entregados
                if random.random() < 0.90:

                    final_status = "ENTREGADO"

                else:

                    final_status = "RECHAZADO"

                final_date = self._next_date(
                    history["EN REPARTO ENTREGA"]
                )

                if final_date <= self.fecha_actual:

                    history[final_status] = (
                        final_date
                    )

        return history

    # ============================================================
    # SIGUIENTE FECHA
    # ============================================================

    def _next_date(self, previous_date):

        if random.random() < 0.90:

            hours = random.uniform(
                0.5,
                8
            )

        else:

            hours = random.uniform(
                8,
                30
            )

        next_date = (
            previous_date
            + timedelta(hours=hours)
        )

        # Seguridad
        if next_date <= previous_date:

            next_date = (
                previous_date
                + timedelta(minutes=1)
            )

        return next_date

    # ============================================================
    # ÚLTIMO ESTADO
    # ============================================================

    def _get_last_historical_status(
        self,
        history,
        created_date
    ):

        valid_history = {
            status: date
            for status, date in history.items()
            if date <= self.fecha_actual
        }

        if not valid_history:

            return (
                "CREADO",
                created_date
            )

        last_status = max(
            valid_history,
            key=valid_history.get
        )

        return (
            last_status,
            valid_history[last_status]
        )

    # ============================================================
    # DIRECCIÓN ALEATORIA
    # ============================================================

    def _random_address(self, addresses):

        # --------------------------------------------------------
        # DATAFRAME VACÍO
        # --------------------------------------------------------

        if addresses is None:

            return self._fallback_address()

        if isinstance(addresses, pd.DataFrame):

            if addresses.empty:

                return self._fallback_address()

            # Seleccionar una fila aleatoria
            index = random.randrange(
                len(addresses)
            )

            address = addresses.iloc[index]

            return self._normalize_address(
                address
            )

        # --------------------------------------------------------
        # LISTA / TUPLA
        # --------------------------------------------------------

        if isinstance(addresses, (list, tuple)):

            if len(addresses) == 0:

                return self._fallback_address()

            address = random.choice(
                addresses
            )

            return self._normalize_address(
                address
            )

        # --------------------------------------------------------
        # DICCIONARIO
        # --------------------------------------------------------

        if isinstance(addresses, dict):

            return self._normalize_address(
                addresses
            )

        # --------------------------------------------------------
        # CUALQUIER OTRO CASO
        # --------------------------------------------------------

        return self._fallback_address()

    # ============================================================
    # DIRECCIÓN FALLBACK
    # ============================================================

    def _fallback_address(self):

        return {
            "street": self.fake.street_name(),

            "house_number": str(
                random.randint(1, 200)
            ),

            "floor": "",

            "letter": "",

            "city": self.fake.city(),

            "postal_code": "28001",

            "country": "España"
        }

    # ============================================================
    # NORMALIZAR DIRECCIÓN
    # ============================================================

    def _normalize_address(self, address):

        # --------------------------------------------------------
        # PANDAS SERIES
        # --------------------------------------------------------

        if isinstance(address, pd.Series):

            columns = set(
                address.index
            )

            # ----------------------------------------------------
            # MADRID
            # ----------------------------------------------------

            if (
                "VIA_NOMBRE" in columns
                and "COD_POSTAL" in columns
            ):

                street = address.get(
                    "VIA_NOMBRE",
                    ""
                )

                house_number = address.get(
                    "NUMERO",
                    ""
                )

                qualifier = address.get(
                    "CALIFICADOR",
                    ""
                )

                if pd.isna(street):

                    street = ""

                if pd.isna(house_number):

                    house_number = ""

                if pd.isna(qualifier):

                    qualifier = ""

                # Si existe calificador, lo añadimos
                # como parte del portal cuando corresponda.
                house_number = str(
                    house_number
                ).strip()

                qualifier = str(
                    qualifier
                ).strip()

                return {
                    "street": str(
                        street
                    ).strip(),

                    "house_number": house_number,

                    "floor": "",

                    "letter": qualifier,

                    "city": "Madrid",

                    "postal_code": (
                        self._normalize_postal_code(
                            address.get(
                                "COD_POSTAL",
                                ""
                            )
                        )
                    ),

                    "country": "España"
                }

            # ----------------------------------------------------
            # ESPAÑA
            # ----------------------------------------------------

            if (
                "Street" in columns
                or "\ufeffStreet" in columns
            ):

                street_column = (
                    "Street"
                    if "Street" in columns
                    else "\ufeffStreet"
                )

                return {
                    "street": str(
                        address.get(
                            street_column,
                            ""
                        )
                    ).strip(),

                    "house_number": str(
                        address.get(
                            "HouseNumber",
                            ""
                        )
                    ).strip(),

                    "floor": "",

                    "letter": "",

                    "city": str(
                        address.get(
                            "Locality",
                            ""
                        )
                    ).strip(),

                    "postal_code": (
                        self._normalize_postal_code(
                            address.get(
                                "PostalCode",
                                ""
                            )
                        )
                    ),

                    "country": str(
                        address.get(
                            "Country",
                            "España"
                        )
                    ).strip()
                }

        # --------------------------------------------------------
        # DICCIONARIO
        # --------------------------------------------------------

        if isinstance(address, dict):

            return {
                "street": address.get(
                    "street",
                    address.get(
                        "direccion",
                        ""
                    )
                ),

                "house_number": str(
                    address.get(
                        "house_number",
                        address.get(
                            "numero",
                            ""
                        )
                    )
                ),

                "floor": address.get(
                    "floor",
                    address.get(
                        "planta",
                        ""
                    )
                ),

                "letter": address.get(
                    "letter",
                    address.get(
                        "puerta",
                        ""
                    )
                ),

                "city": address.get(
                    "city",
                    address.get(
                        "ciudad",
                        ""
                    )
                ),

                "postal_code": (
                    self._normalize_postal_code(
                        address.get(
                            "postal_code",
                            address.get(
                                "codigo_postal",
                                ""
                            )
                        )
                    )
                ),

                "country": address.get(
                    "country",
                    "España"
                )
            }

        # --------------------------------------------------------
        # OTRO FORMATO
        # --------------------------------------------------------

        return self._fallback_address()

    # ============================================================
    # NORMALIZAR CÓDIGO POSTAL
    # ============================================================

    @staticmethod
    def _normalize_postal_code(value):

        if value is None:

            return ""

        if pd.isna(value):

            return ""

        value = str(
            value
        ).strip()

        if not value:

            return ""

        # Evitar 28022.0
        if value.endswith(".0"):

            value = value[:-2]

        try:

            return str(
                int(float(value))
            ).zfill(5)

        except (
            ValueError,
            TypeError
        ):

            return value.zfill(5)

    # ============================================================
    # FECHA ALEATORIA
    # ============================================================

    def _random_datetime(self, date):

        hour = random.randint(
            0,
            23
        )

        minute = random.randint(
            0,
            59
        )

        second = random.randint(
            0,
            59
        )

        return datetime(
            date.year,
            date.month,
            date.day,
            hour,
            minute,
            second
        )

    # ============================================================
    # DATAFRAME
    # ============================================================

    def create_historical_dataframe(self):

        rows = []

        for order in self.historical_orders:

            row = {
                "id_order": order.id_order,

                "id_driver": order.id_driver,

                "id_route": order.id_route,

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

                "num_products": (
                    order.num_products
                ),

                "type_order": (
                    order.type_order
                ),

                "type_service": (
                    order.type_service
                )
            }

            for status in self.STATUS_COLUMNS:

                row[status] = (
                    order.status_history.get(
                        status
                    )
                )

            rows.append(row)

        return pd.DataFrame(rows)

    # ============================================================
    # FORMATEAR HISTORIAL
    # ============================================================

    def format_status_history(self, order):

        result = {}

        for status in self.STATUS_COLUMNS:

            result[status] = (
                order.status_history.get(
                    status
                )
            )

        return result