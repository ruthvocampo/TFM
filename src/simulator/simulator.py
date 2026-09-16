from datetime import datetime, timedelta
from pathlib import Path
import json
import time

import pandas as pd

from src.generator.address_generator import AddressGenerator
from src.generator.drivers_generator import DriverGenerator
from src.generator.orders_generator import OrderGenerator
from src.generator.historical_generator import OrderHistoricalGenerator
from src.generator.order_event import OrderEvents
from src.generator.route_generator import RouteGenerator
from src.generator.gps_events import GPSEvents
from src.generator.incident_historical_generator import (IncidentHistoricalGenerator)


from src.kafka.producer import KafkaProducer

from src.onelake_client import OnelakeClient

from src.objects.order import Order
from src.objects.driver import Driver
from src.objects.route import Route
from src.objects.incident import Incident
from src.objects.location import Location

from src.setup import *


class Simulator:
    """
    Simulador de operaciones de última milla.

    El simulador trabaja con un reloj virtual.

    Ejemplo:

        simulator.run_day(
            simulated_minutes_per_second=10
        )

    significa:

        1 segundo real = 10 minutos simulados.

    Un día completo:

        24 * 60 / 10 = 144 segundos
    """

    # =========================================================
    # CONFIGURATION
    # =========================================================

    SPAIN_FILE = (
        "data/reference/spain.csv"
    )

    MADRID_FILE = (
        "data/reference/"
        "213605-4-callejero-oficial-madrid-csv.csv"
    )

    STATE_FILE = (
        DATA_GENERATED
        / "simulation"
        / "state.json"
    )

    FINAL_ORDER_STATUSES = {
        "RECOGIDO",
        "ENTREGADO",
        "RECHAZADO",
        "CANCELADO"
    }

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        fecha_actual: datetime
    ):
        self.fecha_actual = fecha_actual

        # -----------------------------------------------------
        # CLIENTS
        # -----------------------------------------------------

        self.client_onelk = OnelakeClient()

        self.kproducer = KafkaProducer()

        self.kproducer.create_topics()

        # -----------------------------------------------------
        # DOMAIN STATE
        # -----------------------------------------------------

        self.drivers = []
        self.orders = []
        self.routes = []

        self.historical_orders = []

        self.incidents = []
        self.historical_incidents = []

        # -----------------------------------------------------
        # EVENT STATE
        # -----------------------------------------------------

        self.gps_events = []
        self.order_events = []


        # -----------------------------------------------------
        # GENERATORS
        # -----------------------------------------------------

        self.order_event_generator = None
        self.gps_event_generator = None

        # -----------------------------------------------------
        # RUNTIME STATE
        # -----------------------------------------------------

        self.current_simulation_date = (
            self.fecha_actual.date()
        )

        self.last_batch_date = None

        self.running = False

    # =========================================================
    # STATE
    # =========================================================

    def state_exists(self) -> bool:
        return self.STATE_FILE.exists()

    # =========================================================
    # INITIAL DATA
    # =========================================================

    def generate_initial_data(self):
        """
        Genera todos los datos necesarios para comenzar
        una simulación.
        """

        print()
        print("=" * 70)
        print("[INIT] GENERANDO DATOS INICIALES")
        print("=" * 70)

        address_generator = AddressGenerator(
            self.SPAIN_FILE,
            self.MADRID_FILE
        )

        addresses_spain = (
            address_generator.get_address_spain_df()
        )

        addresses_madrid = (
            address_generator.get_address_madrid_df()
        )

        # -----------------------------------------------------
        # DRIVERS
        # -----------------------------------------------------

        print("[INIT] Generando conductores...")

        driver_generator = DriverGenerator(
            [],
            addresses_madrid
        )

        self.drivers = driver_generator.create_drivers(
            270
        )

        # -----------------------------------------------------
        # ROUTES
        # -----------------------------------------------------

        print("[INIT] Generando rutas...")

        route_generator = RouteGenerator(
            self.drivers,
            addresses_madrid,
            self.fecha_actual
        )

        self.routes = route_generator.create_routes()

        # -----------------------------------------------------
        # HISTORICAL ORDERS
        # -----------------------------------------------------

        print("[INIT] Generando histórico de pedidos...")

        historical_generator = OrderHistoricalGenerator(
            self.drivers,
            addresses_madrid,
            addresses_spain,
            self.fecha_actual
        )

        self.historical_orders = (
            historical_generator.create_historical(
                6000
            )
        )

        # -----------------------------------------------------
        # HISTORICAL INCIDENTS
        # -----------------------------------------------------

        print("[INIT] Generando histórico de incidencias...")

        historical_incident_generator = (
            IncidentHistoricalGenerator(
                self.historical_orders
            )
        )

        self.historical_incidents = (
            historical_incident_generator
            .create_historical_incidents()
        )

        # -----------------------------------------------------
        # TODAY ORDERS
        # -----------------------------------------------------

        print("[INIT] Generando pedidos del día...")

        order_generator = OrderGenerator(
            self.historical_orders,
            self.fecha_actual
        )

        self.orders = (
            order_generator.get_orders_for_today()
        )

        # -----------------------------------------------------
        # EVENT GENERATORS
        # -----------------------------------------------------

        self._create_event_generators()

        # -----------------------------------------------------
        # COUNTERS
        # -----------------------------------------------------

        self._initialize_counters()

        self.current_simulation_date = (
            self.fecha_actual.date()
        )

        print()
        print(
            f"[INIT] Conductores: {len(self.drivers)}"
        )

        print(
            f"[INIT] Rutas: {len(self.routes)}"
        )

        print(
            f"[INIT] Pedidos: {len(self.orders)}"
        )

        print(
            f"[INIT] Histórico pedidos: "
            f"{len(self.historical_orders)}"
        )

        print(
            f"[INIT] Incidencias históricas: "
            f"{len(self.historical_incidents)}"
        )

        print("=" * 70)

    # =========================================================
    # CREATE GENERATORS
    # =========================================================

    def _create_event_generators(self):
        """
        Crea/recrea todos los generators utilizando
        el estado actual del simulador.
        """

        self.order_event_generator = OrderEvents(
            self.orders,
            self.drivers,
            self.routes,
            self.fecha_actual
        )

        self.gps_event_generator = GPSEvents(
            self.orders,
            self.drivers,
            self.routes,
            self.fecha_actual
        )


    # =========================================================
    # COUNTERS
    # =========================================================

    def _initialize_counters(self):
        """
        Inicializa contadores.
        """

        self.order_event_generator.event_counter = 0

        self.gps_event_generator.event_counter = 0

        max_incident = (
            self._get_max_incident_number(
                self.historical_incidents
            )
        )

        self.order_event_generator \
            .incident_generator \
            .incident_counter = max_incident

    # =========================================================
    # MAX INCIDENT
    # =========================================================

    @staticmethod
    def _get_max_incident_number(
        incidents
    ) -> int:

        maximum = 0

        for incident in incidents:

            value = str(
                incident.id_incident
            )

            if not value.startswith("INC"):
                continue

            try:

                number = int(
                    value[3:]
                )

                maximum = max(
                    maximum,
                    number
                )

            except ValueError:
                continue

        return maximum

    # =========================================================
    # TIME
    # =========================================================

    def advance_time(
        self,
        minutes: int
    ):
        """
        Avanza el reloj virtual.
        """

        if minutes <= 0:
            raise ValueError(
                "minutes debe ser > 0"
            )

        previous_date = (
            self.fecha_actual.date()
        )

        self.fecha_actual += timedelta(
            minutes=minutes
        )

        new_date = (
            self.fecha_actual.date()
        )

        self.update_event_generators()

        if new_date != previous_date:

            self.handle_day_change(
                new_date
            )

    # =========================================================
    # UPDATE GENERATORS
    # =========================================================

    def update_event_generators(self):
        """
        Actualiza la fecha utilizada por todos los
        generadores.
        """

        if self.order_event_generator is not None:

            self.order_event_generator.fecha_actual = (
                self.fecha_actual
            )

        if self.gps_event_generator is not None:

            self.gps_event_generator.fecha_actual = (
                self.fecha_actual
            )


    # =========================================================
    # DAY CHANGE
    # =========================================================

    def handle_day_change(
        self,
        new_date
    ):
        """
        Gestiona el cambio de día.
        """

        print()
        print("=" * 70)
        print(
            f"[DAY] CAMBIO DE DÍA: "
            f"{self.current_simulation_date} "
            f"-> {new_date}"
        )
        print("=" * 70)

        self.current_simulation_date = new_date

        self.start_new_day()

    # =========================================================
    # SIMULATION STEP
    # =========================================================

    def simulation_step(self):
        """
        Ejecuta todas las operaciones correspondientes
        al instante actual de simulación.
        """

        print()
        print(
            f"[SIM] "
            f"{self.fecha_actual:%Y-%m-%d %H:%M:%S}"
        )

        # -----------------------------------------------------
        # ORDER EVENTS
        # -----------------------------------------------------

        self.create_order_event()

        # -----------------------------------------------------
        # GPS
        # -----------------------------------------------------

        arrived_orders = (
            self.create_gps_events()
        )

        # -----------------------------------------------------
        # ARRIVALS / DELIVERY
        # -----------------------------------------------------

        self.process_arrived_orders(
            arrived_orders
        )


        # -----------------------------------------------------
        # SYNC
        # -----------------------------------------------------

        self.sync_orders_with_historical()

    # =========================================================
    # ORDER EVENT
    # =========================================================

    def create_order_event(self):

        if self.order_event_generator is None:
            return [], []

        results = (
            self.order_event_generator.generate_event(
                max_orders_per_driver=8
            )
        )

        if not results:
            return [], []

        order_events = []
        incidents = []

        for result in results:

            if result is None:
                continue

            order_event = result.get(
                "order_event"
            )

            incident = result.get(
                "incident"
            )

            # -------------------------------------------------
            # ORDER EVENT
            # -------------------------------------------------

            if order_event is not None:

                self.order_events.append(
                    order_event
                )

                order_events.append(
                    order_event
                )

                self.produce_event(
                    "order-events",
                    order_event,
                    "id_event"
                )

            # -------------------------------------------------
            # INCIDENT
            # -------------------------------------------------

            if incident is not None:

                self.incidents.append(
                    incident
                )

                incidents.append(
                    incident
                )

                incident_event = (
                    self.serialize_incident(
                        incident
                    )
                )

                self.produce_event(
                    "incident-events",
                    incident_event,
                    "id_incident"
                )

        if order_events:

            print(
                f"[ORDER] "
                f"{len(order_events)} eventos"
            )

        if incidents:

            print(
                f"[INCIDENT] "
                f"{len(incidents)} incidencias"
            )

        return order_events, incidents

    # =========================================================
    # GPS
    # =========================================================

    def create_gps_events(self):

        if self.gps_event_generator is None:
            return []

        gps_events = (
            self.gps_event_generator.generate_event()
        )

        if not gps_events:

            return []

        print(
            f"[GPS] "
            f"{len(gps_events)} eventos"
        )

        arrived_orders = []

        for item in gps_events:

            key, gps_event, orders_arrived = item

            if gps_event is not None:

                self.gps_events.append(
                    gps_event
                )

                self.produce_event(
                    "gps-events",
                    gps_event,
                    "gps_event_id"
                )

            if orders_arrived:

                arrived_orders.extend(
                    orders_arrived
                )

        return arrived_orders

    # =========================================================
    # DELIVERY COMPLETED
    # =========================================================

    def process_arrived_orders(
        self,
        arrived_orders
    ):

        if not arrived_orders:
            return

        for order in arrived_orders:

            result = (
                self.order_event_generator
                .generate_delivery_completed_event(
                    order
                )
            )

            if result is None:
                continue

            order_event = result.get(
                "order_event"
            )

            if order_event is None:
                continue

            self.order_events.append(
                order_event
            )

            self.produce_event(
                "order-events",
                order_event,
                "id_event"
            )

            print(
                f"[DELIVERY] "
                f"Pedido {order.id_order} "
                f"entregado"
            )

    


    # =========================================================
    # KAFKA
    # =========================================================

    def produce_event(
        self,
        topic,
        event,
        key_field
    ):
        """
        Publica un evento en Kafka.

        El producer recibe directamente el dict porque
        el AvroSerializer se encarga de serializarlo.
        """

        if event is None:
            return

        if key_field not in event:
            raise KeyError(
                f"Campo '{key_field}' "
                f"no existe en evento para "
                f"topic '{topic}'"
            )

        key_event = str(
            event[key_field]
        )

        print(
            f"[Kafka] "
            f"topic={topic} "
            f"key={key_event}"
        )

        self.kproducer.produce(
            topic,
            key_event,
            event
        )

    # =========================================================
    # UPDATE ORDER STATUS
    # =========================================================

    def update_order_status(
        self,
        order_id,
        new_status
    ):

        for order in self.orders:

            if order.id_order != order_id:
                continue

            order.set_status(
                new_status,
                self.fecha_actual
            )

            print(
                f"[ORDER] "
                f"{order_id} -> "
                f"{new_status}"
            )

            return order

        print(
            f"[ORDER] "
            f"{order_id} no encontrada."
        )

        return None

    # =========================================================
    # SERIALIZATION HELPERS
    # =========================================================

    @staticmethod
    def _datetime_to_json(value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return int(value.timestamp() * 1000)

        return value

    @staticmethod
    def _datetime_from_json(value):
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000)

        return datetime.fromisoformat(value)

    @staticmethod
    def _clean_value(value):

        if value is None:
            return None

        try:

            if pd.isna(value):
                return None

        except Exception:
            pass

        if isinstance(
            value,
            (str, int, float, bool)
        ):
            return value

        return str(value)

    # =========================================================
    # ORDER SERIALIZATION
    # =========================================================

    def serialize_order(
        self,
        order
    ):

        return {

            "id_order":
                self._clean_value(
                    order.id_order
                ),

            "id_driver":
                self._clean_value(
                    order.id_driver
                ),

            "id_driver_pickup":
                self._clean_value(
                    order.id_driver_pickup
                ),

            "id_driver_delivery":
                self._clean_value(
                    order.id_driver_delivery
                ),

            "id_route":
                self._clean_value(
                    order.id_route
                ),

            "order_created_date":
                self._datetime_to_json(
                    order.order_created_date
                ),

            "order_expected_date":
                self._datetime_to_json(
                    order.order_expected_date
                ),

            "status":
                self._clean_value(
                    order.status
                ),

            "status_modified_date":
                self._datetime_to_json(
                    order.status_modified_date
                ),

            "num_products":
                int(order.num_products),

            "type_order":
                self._clean_value(
                    order.type_order
                ),

            "type_service":
                self._clean_value(
                    order.type_service
                ),

            "sender":
                self._clean_value(
                    order.sender
                ),

            "pickup_street":
                self._clean_value(
                    order.pickup_street
                ),

            "pickup_house_number":
                self._clean_value(
                    order.pickup_house_number
                ),

            "pickup_floor":
                self._clean_value(
                    order.pickup_floor
                ),

            "pickup_letter":
                self._clean_value(
                    order.pickup_letter
                ),

            "pickup_city":
                self._clean_value(
                    order.pickup_city
                ),

            "pickup_postal_code":
                self._clean_value(
                    order.pickup_postal_code
                ),

            "pickup_country":
                self._clean_value(
                    order.pickup_country
                ),

            "destinatary":
                self._clean_value(
                    order.destinatary
                ),

            "delivery_street":
                self._clean_value(
                    order.delivery_street
                ),

            "delivery_house_number":
                self._clean_value(
                    order.delivery_house_number
                ),

            "delivery_floor":
                self._clean_value(
                    order.delivery_floor
                ),

            "delivery_letter":
                self._clean_value(
                    order.delivery_letter
                ),

            "delivery_city":
                self._clean_value(
                    order.delivery_city
                ),

            "delivery_postal_code":
                self._clean_value(
                    order.delivery_postal_code
                ),

            "delivery_country":
                self._clean_value(
                    order.delivery_country
                ),

            "status_history": {

                status:
                    self._datetime_to_json(
                        date
                    )

                for status, date
                in order.status_history.items()
            }
        }

    # =========================================================
    # ORDER DESERIALIZATION
    # =========================================================

    def deserialize_order(
        self,
        data
    ):

        order = Order(

            id_order=data["id_order"],

            id_driver=data["id_driver"],

            order_created_date=(
                self._datetime_from_json(
                    data["order_created_date"]
                )
            ),

            order_expected_date=(
                self._datetime_from_json(
                    data["order_expected_date"]
                )
            ),

            status=data["status"],

            status_modified_date=(
                self._datetime_from_json(
                    data["status_modified_date"]
                )
            ),

            num_products=data["num_products"],

            type_order=data["type_order"],

            type_service=data["type_service"],

            sender=data["sender"],

            pickup_street=data[
                "pickup_street"
            ],

            pickup_house_number=data[
                "pickup_house_number"
            ],

            pickup_floor=data[
                "pickup_floor"
            ],

            pickup_letter=data[
                "pickup_letter"
            ],

            pickup_city=data[
                "pickup_city"
            ],

            pickup_postal_code=data[
                "pickup_postal_code"
            ],

            pickup_country=data[
                "pickup_country"
            ],

            destinatary=data[
                "destinatary"
            ],

            delivery_street=data[
                "delivery_street"
            ],

            delivery_house_number=data[
                "delivery_house_number"
            ],

            delivery_floor=data[
                "delivery_floor"
            ],

            delivery_letter=data[
                "delivery_letter"
            ],

            delivery_city=data[
                "delivery_city"
            ],

            delivery_postal_code=data[
                "delivery_postal_code"
            ],

            delivery_country=data[
                "delivery_country"
            ]
        )

        order.id_driver_pickup = (
            data.get(
                "id_driver_pickup"
            )
        )

        order.id_driver_delivery = (
            data.get(
                "id_driver_delivery"
            )
        )

        order.id_route = (
            data.get(
                "id_route"
            )
        )

        order.status_history = {

            status:
                self._datetime_from_json(
                    date
                )

            for status, date
            in data.get(
                "status_history",
                {}
            ).items()
        }

        return order

    # =========================================================
    # DRIVER SERIALIZATION
    # =========================================================

    def serialize_driver(
        self,
        driver
    ):

        location = None

        if driver.location is not None:

            location = {

                "latitude":
                    float(
                        driver.location.latitude
                    ),

                "longitude":
                    float(
                        driver.location.longitude
                    )
            }

        return {

            "id_driver":
                driver.id_driver,

            "username":
                driver.username,

            "name":
                driver.name,

            "license_number":
                driver.license_number,

            "vehicle_type":
                driver.vehicle_type,

            "available":
                bool(driver.available),

            "zone":
                self._clean_value(
                    driver.zone
                ),

            "location":
                location
        }

    # =========================================================
    # DRIVER DESERIALIZATION
    # =========================================================

    def deserialize_driver(
        self,
        data
    ):

        location = None

        if data.get("location") is not None:

            location = Location(

                float(
                    data["location"]["latitude"]
                ),

                float(
                    data["location"]["longitude"]
                )
            )

        return Driver(

            id_driver=data["id_driver"],

            username=data["username"],

            name=data["name"],

            license_number=data[
                "license_number"
            ],

            vehicle_type=data[
                "vehicle_type"
            ],

            available=data[
                "available"
            ],

            zone=data[
                "zone"
            ],

            location=location
        )

    # =========================================================
    # ROUTE
    # =========================================================

    def serialize_route(
        self,
        route
    ):

        return {

            "id_route":
                route.id_route,

            "id_driver":
                route.id_driver,

            "postal_code":
                self._clean_value(
                    route.postal_code
                ),

            "street":
                self._clean_value(
                    route.street
                ),

            "house_number":
                self._clean_value(
                    route.house_number
                ),

            "latitude":
                float(
                    route.latitude
                ),

            "longitude":
                float(
                    route.longitude
                ),

            "priority":
                int(
                    route.priority
                )
        }

    # =========================================================
    # ROUTE DESERIALIZATION
    # =========================================================

    def deserialize_route(
        self,
        data
    ):

        return Route(

            id_route=data[
                "id_route"
            ],

            id_driver=data[
                "id_driver"
            ],

            postal_code=data[
                "postal_code"
            ],

            street=data[
                "street"
            ],

            house_number=data[
                "house_number"
            ],

            latitude=float(
                data["latitude"]
            ),

            longitude=float(
                data["longitude"]
            ),

            priority=int(
                data["priority"]
            )
        )

    # =========================================================
    # INCIDENT
    # =========================================================

    def serialize_incident(
        self,
        incident
    ):

        return {

            "id_incident":
                incident.id_incident,

            "id_order":
                incident.id_order,

            "id_driver":
                incident.id_driver,

            "incident_date":
                self._datetime_to_json(
                    incident.incident_date
                ),

            "incident_reason":
                incident.incident_reason,

            "observations":
                incident.observations,

            "resolved":
                bool(
                    incident.resolved
                ),

            "resolution_date":
                self._datetime_to_json(
                    incident.resolution_date
                ),

            "resolution_action":
                incident.resolution_action
        }

    # =========================================================
    # INCIDENT DESERIALIZATION
    # =========================================================

    def deserialize_incident(
        self,
        data
    ):

        return Incident(

            id_incident=data[
                "id_incident"
            ],

            id_order=data[
                "id_order"
            ],

            id_driver=data[
                "id_driver"
            ],

            incident_date=(
                self._datetime_from_json(
                    data["incident_date"]
                )
            ),

            incident_reason=data[
                "incident_reason"
            ],

            observations=data[
                "observations"
            ],

            resolved=data[
                "resolved"
            ],

            resolution_date=(
                self._datetime_from_json(
                    data["resolution_date"]
                )
            ),

            resolution_action=data[
                "resolution_action"
            ]
        )

    # =========================================================
    # GPS STATE
    # =========================================================

    def serialize_gps_state(self):

        if self.gps_event_generator is None:
            return {}

        result = {}

        for driver_id, state in (
            self.gps_event_generator
            .driver_state
            .items()
        ):

            result[str(driver_id)] = {

                "route_index":
                    int(
                        state["route_index"]
                    ),

                "progress":
                    float(
                        state["progress"]
                    ),

                "start_latitude":
                    float(
                        state["start_latitude"]
                    ),

                "start_longitude":
                    float(
                        state["start_longitude"]
                    ),

                "target_latitude":
                    float(
                        state["target_latitude"]
                    ),

                "target_longitude":
                    float(
                        state["target_longitude"]
                    ),

                "route_id":
                    state["route_id"]
            }

        return result

    # =========================================================
    # SAVE STATE
    # =========================================================

    def save_state(self):

        self.STATE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        state = {

            "version": 2,

            "fecha_actual":
                self._datetime_to_json(
                    self.fecha_actual
                ),

            "current_simulation_date":
                self.current_simulation_date.isoformat(),

            "last_batch_date":
                (
                    self.last_batch_date.isoformat()
                    if self.last_batch_date
                    else None
                ),

            "counters": {

                "order_event":
                    self.order_event_generator
                    .event_counter,

                "gps_event":
                    self.gps_event_generator
                    .event_counter,
                "incident":
                    self.order_event_generator
                    .incident_generator
                    .incident_counter
            },

            "orders": [
                self.serialize_order(order)
                for order in self.orders
            ],

            "historical_orders": [
                self.serialize_order(order)
                for order in self.historical_orders
            ],

            "drivers": [
                self.serialize_driver(driver)
                for driver in self.drivers
            ],

            "routes": [
                self.serialize_route(route)
                for route in self.routes
            ],

            "incidents": [
                self.serialize_incident(
                    incident
                )
                for incident in self.incidents
            ],

            "historical_incidents": [
                self.serialize_incident(
                    incident
                )
                for incident
                in self.historical_incidents
            ],

            "gps_driver_state":
                self.serialize_gps_state()
        }

        temporary_file = (
            self.STATE_FILE.with_suffix(
                ".tmp"
            )
        )

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                state,
                file,
                ensure_ascii=False,
                indent=2
            )

        temporary_file.replace(
            self.STATE_FILE
        )

        print(
            f"[STATE] Guardado: "
            f"{self.STATE_FILE}"
        )

    # =========================================================
    # LOAD STATE
    # =========================================================

    def load_state(self):

        print(
            f"[STATE] Cargando: "
            f"{self.STATE_FILE}"
        )

        with open(
            self.STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            state = json.load(file)

        # -----------------------------------------------------
        # DATE
        # -----------------------------------------------------

        self.fecha_actual = (
            self._datetime_from_json(
                state["fecha_actual"]
            )
        )

        self.current_simulation_date = (
            datetime.fromisoformat(
                state.get(
                    "current_simulation_date",
                    self.fecha_actual.date()
                    .isoformat()
                )
            ).date()
        )

        last_batch_date = state.get(
            "last_batch_date"
        )

        if last_batch_date:

            self.last_batch_date = (
                datetime.fromisoformat(
                    last_batch_date
                ).date()
            )

        else:

            self.last_batch_date = None

        # -----------------------------------------------------
        # DRIVERS
        # -----------------------------------------------------

        self.drivers = [

            self.deserialize_driver(
                data
            )

            for data in state["drivers"]
        ]

        # -----------------------------------------------------
        # ROUTES
        # -----------------------------------------------------

        self.routes = [

            self.deserialize_route(
                data
            )

            for data in state["routes"]
        ]

        # -----------------------------------------------------
        # HISTORICAL ORDERS
        # -----------------------------------------------------

        self.historical_orders = [

            self.deserialize_order(
                data
            )

            for data
            in state["historical_orders"]
        ]

        # -----------------------------------------------------
        # CURRENT ORDERS
        # -----------------------------------------------------

        self.orders = [

            self.deserialize_order(
                data
            )

            for data
            in state["orders"]
        ]

        # -----------------------------------------------------
        # HISTORICAL INCIDENTS
        # -----------------------------------------------------

        self.historical_incidents = [

            self.deserialize_incident(
                data
            )

            for data
            in state["historical_incidents"]
        ]

        # -----------------------------------------------------
        # CURRENT INCIDENTS
        # -----------------------------------------------------

        self.incidents = [

            self.deserialize_incident(
                data
            )

            for data
            in state["incidents"]
        ]

        # -----------------------------------------------------
        # GENERATORS
        # -----------------------------------------------------

        self._create_event_generators()

        # -----------------------------------------------------
        # COUNTERS
        # -----------------------------------------------------

        counters = state["counters"]

        self.order_event_generator.event_counter = (
            counters["order_event"]
        )

        self.gps_event_generator.event_counter = (
            counters["gps_event"]
        )


        self.order_event_generator \
            .incident_generator \
            .incident_counter = (
                counters["incident"]
            )

        # -----------------------------------------------------
        # INCIDENT REFERENCES
        # -----------------------------------------------------

        self.order_event_generator.incidents = (
            self.incidents
        )

        self.order_event_generator \
            .incident_generator \
            .incidents = (
                self.incidents
            )

        # -----------------------------------------------------
        # GPS STATE
        # -----------------------------------------------------

        gps_state = state.get(
            "gps_driver_state",
            {}
        )

        self.gps_event_generator.driver_state = (
            gps_state
        )

        # -----------------------------------------------------
        # REFERENCES
        # -----------------------------------------------------

        self.update_event_generators()

        print(
            "[STATE] Estado cargado correctamente."
        )

        print(
            f"[STATE] Fecha: "
            f"{self.fecha_actual}"
        )

        print(
            f"[STATE] Pedidos: "
            f"{len(self.orders)}"
        )

        print(
            f"[STATE] Conductores: "
            f"{len(self.drivers)}"
        )

        print(
            f"[STATE] Incidencias: "
            f"{len(self.incidents)}"
        )

    # =========================================================
    # RESET
    # =========================================================

    def reset_state(self):

        if self.STATE_FILE.exists():

            self.STATE_FILE.unlink()

            print(
                "[STATE] Estado eliminado."
            )

        else:

            print(
                "[STATE] No había estado."
            )

    # =========================================================
    # START NEW DAY
    # =========================================================

    def start_new_day(self):

        today = self.fecha_actual.date()

        tomorrow = (
            today + timedelta(days=1)
        )

        print()
        print("=" * 70)
        print(
            f"[DAY] PREPARANDO: {today}"
        )
        print("=" * 70)

        # -----------------------------------------------------
        # ACTIVE ORDERS
        # -----------------------------------------------------

        active_orders = {

            str(order.id_order): order

            for order in self.orders

            if order.status
            not in self.FINAL_ORDER_STATUSES
        }

        # -----------------------------------------------------
        # HISTORICAL CANDIDATES
        # -----------------------------------------------------

        candidates = []

        for order in self.historical_orders:

            if order.order_created_date is None:
                continue

            if order.order_expected_date is None:
                continue

            if (
                order.order_created_date.date()
                > today
            ):
                continue

            if (
                order.status
                in self.FINAL_ORDER_STATUSES
            ):
                continue

            expected_date = (
                order.order_expected_date.date()
            )

            if expected_date > tomorrow:
                continue

            candidates.append(order)

        candidates.sort(
            key=lambda order:
            order.order_expected_date
        )

        # -----------------------------------------------------
        # CURRENT ORDERS
        # -----------------------------------------------------

        new_orders = []
        added_ids = set()

        # Existing active orders
        for order in self.orders:

            if (
                order.status
                in self.FINAL_ORDER_STATUSES
            ):
                continue

            order_id = str(
                order.id_order
            )

            new_orders.append(order)

            added_ids.add(
                order_id
            )

        # New candidates
        for order in candidates:

            order_id = str(
                order.id_order
            )

            if order_id in added_ids:
                continue

            if order.type_service == "RECOGIDA":

                order.status = (
                    "PENDIENTE DE ASIGNACIÓN RECOGIDA"
                )

            elif order.type_service == "ENTREGA":

                order.status = (
                    "PENDIENTE DE ASIGNACIÓN ENTREGA"
                )

            else:

                continue

            order.id_driver = None
            order.id_driver_pickup = None
            order.id_driver_delivery = None
            order.id_route = None

            order.status_modified_date = (
                self.fecha_actual
            )

            order.status_history[
                order.status
            ] = self.fecha_actual

            new_orders.append(order)

            added_ids.add(
                order_id
            )

        self.orders = new_orders

        print(
            f"[DAY] Pedidos activos: "
            f"{len(self.orders)}"
        )

        # -----------------------------------------------------
        # RECREATE GENERATORS
        # -----------------------------------------------------

        self._create_event_generators()

        # -----------------------------------------------------
        # RESTORE INCIDENT REFERENCES
        # -----------------------------------------------------

        self.order_event_generator.incidents = (
            self.incidents
        )

        self.order_event_generator \
            .incident_generator \
            .incidents = (
                self.incidents
            )

        # -----------------------------------------------------
        # PRESERVE COUNTERS
        # -----------------------------------------------------

        self._restore_runtime_counters_after_generator_reset()

        self.update_event_generators()

        print(
            "[DAY] Generadores actualizados."
        )

    # =========================================================
    # RESTORE COUNTERS AFTER RECREATING GENERATORS
    # =========================================================

    def _restore_runtime_counters_after_generator_reset(self):

        max_incident = (
            self._get_max_incident_number(
                self.incidents
            )
        )

        historical_max_incident = (
            self._get_max_incident_number(
                self.historical_incidents
            )
        )

        self.order_event_generator \
            .incident_generator \
            .incident_counter = max(
                max_incident,
                historical_max_incident
            )

    # =========================================================
    # SYNC ORDERS
    # =========================================================

    def sync_orders_with_historical(self):

        historical_by_id = {

            str(order.id_order): order

            for order
            in self.historical_orders
        }

        for order in self.orders:

            historical_order = (
                historical_by_id.get(
                    str(order.id_order)
                )
            )

            if historical_order is None:
                continue

            historical_order.id_driver = (
                order.id_driver
            )

            historical_order.id_driver_pickup = (
                order.id_driver_pickup
            )

            historical_order.id_driver_delivery = (
                order.id_driver_delivery
            )

            historical_order.id_route = (
                order.id_route
            )

            historical_order.status = (
                order.status
            )

            historical_order.status_modified_date = (
                order.status_modified_date
            )

            historical_order.status_history = dict(
                order.status_history
            )

    # =========================================================
    # WRITE FILE
    # =========================================================

    def write_file(
        self,
        path,
        dataframe
    ):

        path = Path(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        suffix = path.suffix.lower()

        if suffix == ".parquet":

            dataframe = dataframe.copy()

            if "location" in dataframe.columns:

                dataframe["latitude"] = (
                    dataframe["location"]
                    .apply(
                        lambda location:
                        float(location.latitude)
                        if location is not None
                        else None
                    )
                )

                dataframe["longitude"] = (
                    dataframe["location"]
                    .apply(
                        lambda location:
                        float(location.longitude)
                        if location is not None
                        else None
                    )
                )

                dataframe = dataframe.drop(
                    columns=["location"]
                )

            dataframe.to_parquet(
                str(path),
                index=False
            )

        elif suffix == ".csv":

            dataframe.to_csv(
                str(path),
                index=False
            )

        elif suffix == ".xlsx":

            dataframe.to_excel(
                str(path),
                index=False
            )

        elif suffix == ".json":

            dataframe.to_json(
                str(path),
                orient="records",
                force_ascii=False,
                indent=4,
                date_format="iso"
            )

        else:

            raise ValueError(
                f"Unsupported file format: "
                f"{suffix}"
            )

    # =========================================================
    # BATCH FILES
    # =========================================================

    def generate_files(self):

        str_fecha = (
            self.fecha_actual.strftime(
                "%Y-%m-%d"
            )
        )

        print()
        print("=" * 70)
        print(
            f"[BATCH] ARCHIVOS {str_fecha}"
        )
        print("=" * 70)

        # -----------------------------------------------------
        # HISTORICAL ORDERS
        # -----------------------------------------------------

        historical_records = []

        for order in self.historical_orders:

            record = vars(order).copy()

            record["status_history"] = ", ".join(

                f"{status}: "
                f"{date.strftime('%d/%m/%Y %H:%M:%S')}"

                for status, date
                in order.status_history.items()

                if date is not None
            )

            historical_records.append(
                record
            )

        historical_df = pd.DataFrame(
            historical_records
        )

        historical_orders_file = (
            f"{GENERATED_HISTORICAL_ORDERS}"
            f"/{str_fecha}"
            "/historical_orders.csv"
        )

        self.write_file(
            historical_orders_file,
            historical_df
        )

        self.client_onelk.load_file(
            f"{LANDING_HISTORICAL_ORDERS}"
            f"/{str_fecha}",
            historical_orders_file
        )

        # -----------------------------------------------------
        # ORDERS
        # -----------------------------------------------------

        orders_df = pd.DataFrame(
            [
                vars(order)
                for order in self.orders
            ]
        )

        orders_file = (
            f"{GENERATED_ORDERS}"
            f"/{str_fecha}"
            "/orders.xlsx"
        )

        self.write_file(
            orders_file,
            orders_df
        )

        self.client_onelk.load_file(
            f"{LANDING_ORDERS}"
            f"/{str_fecha}",
            orders_file
        )

        # -----------------------------------------------------
        # DRIVERS
        # -----------------------------------------------------

        drivers_df = pd.DataFrame(
            [
                vars(driver)
                for driver in self.drivers
            ]
        )

        drivers_file = (
            f"{GENERATED_DRIVERS}"
            f"/{str_fecha}"
            "/drivers.parquet"
        )

        self.write_file(
            drivers_file,
            drivers_df
        )

        self.client_onelk.load_file(
            f"{LANDING_DRIVERS}"
            f"/{str_fecha}",
            drivers_file
        )

        # -----------------------------------------------------
        # ROUTES
        # -----------------------------------------------------

        routes_df = pd.DataFrame(
            [
                vars(route)
                for route in self.routes
            ]
        )

        routes_file = (
            f"{GENERATED_ROUTES}"
            f"/{str_fecha}"
            "/routes.json"
        )

        self.write_file(
            routes_file,
            routes_df
        )

        self.client_onelk.load_file(
            f"{LANDING_ROUTES}"
            f"/{str_fecha}",
            routes_file
        )

        # -----------------------------------------------------
        # HISTORICAL INCIDENTS
        # -----------------------------------------------------

        historical_incidents_df = pd.DataFrame(
            [
                vars(incident)
                for incident
                in self.historical_incidents
            ]
        )

        historical_incidents_file = (
            f"{GENERATED_HISTORICAL_INCIDENTS}"
            f"/{str_fecha}"
            "/historical_incidents.json"
        )

        self.write_file(
            historical_incidents_file,
            historical_incidents_df
        )

        self.client_onelk.load_file(
            f"{LANDING_HISTORICAL_INCIDENTS}"
            f"/{str_fecha}",
            historical_incidents_file
        )

        self.last_batch_date = (
            self.fecha_actual.date()
        )

        print(
            f"[BATCH] Archivos de "
            f"{str_fecha} generados."
        )

    

    # =========================================================
    # RUN DAY
    # =========================================================

    def run_day(
        self,
        simulated_minutes_per_second: float = 10,
        start_time: datetime = None,
        end_time: datetime = None,
        reset: bool = False,
        step_minutes: int = 2,
        checkpoint_every_steps: int = 10,
        generate_batch: bool = True
    ):
        """
        Ejecuta una simulación temporal de un día.

        Parámetros
        ----------
        simulated_minutes_per_second:
            Cuántos minutos simulados pasan por cada
            segundo real.

        start_time:
            Hora de inicio de la simulación.

        end_time:
            Hora de finalización.

        reset:
            Si True, elimina el checkpoint antes de iniciar.

        step_minutes:
            Tamaño de cada tick simulado.

        checkpoint_every_steps:
            Cada cuántos ticks se guarda el estado.

        generate_batch:
            Si True, genera los archivos iniciales del día.
        """

        if step_minutes <= 0:

            raise ValueError(
                "step_minutes debe ser > 0"
            )

        if simulated_minutes_per_second <= 0:

            raise ValueError(
                "simulated_minutes_per_second "
                "debe ser > 0"
            )

        if checkpoint_every_steps <= 0:

            raise ValueError(
                "checkpoint_every_steps "
                "debe ser > 0"
            )

        # -----------------------------------------------------
        # RESET
        # -----------------------------------------------------

        if reset:

            self.reset_state()

        # -----------------------------------------------------
        # LOAD / INIT
        # -----------------------------------------------------

        if self.state_exists():

            self.load_state()

        else:

            if start_time is not None:

                self.fecha_actual = start_time

            self.current_simulation_date = (
                self.fecha_actual.date()
            )

            self.generate_initial_data()

            if generate_batch:

                self.generate_files()

            self.save_state()

        # -----------------------------------------------------
        # APPLY START TIME
        # -----------------------------------------------------

        if start_time is not None:

            if reset:

                self.fecha_actual = start_time

                self.current_simulation_date = (
                    start_time.date()
                )

                self.update_event_generators()

            elif (
                start_time
                > self.fecha_actual
            ):

                print(
                    f"[SIM] Avanzando hasta "
                    f"{start_time}"
                )

                self.fecha_actual = start_time

                self.current_simulation_date = (
                    start_time.date()
                )

                self.update_event_generators()

        # -----------------------------------------------------
        # DEFAULT END
        # -----------------------------------------------------

        if end_time is None:

            end_time = (
                self.fecha_actual
                .replace(
                    hour=23,
                    minute=59,
                    second=0,
                    microsecond=0
                )
            )

        if end_time <= self.fecha_actual:

            raise ValueError(
                "end_time debe ser posterior "
                "a fecha_actual"
            )

        # -----------------------------------------------------
        # HEADER
        # -----------------------------------------------------

        print()
        print("=" * 70)
        print("[SIM] INICIO DE SIMULACIÓN")
        print("=" * 70)

        print(
            f"[SIM] Desde: "
            f"{self.fecha_actual}"
        )

        print(
            f"[SIM] Hasta: "
            f"{end_time}"
        )

        print(
            f"[SIM] Velocidad: "
            f"{simulated_minutes_per_second} "
            f"min simulados / segundo"
        )

        print(
            f"[SIM] Tick: "
            f"{step_minutes} minuto(s)"
        )

        print("=" * 70)

        # -----------------------------------------------------
        # REAL TIME CALCULATION
        # -----------------------------------------------------

        real_seconds_per_step = (
            step_minutes
            / simulated_minutes_per_second
        )

        self.running = True

        step = 0

        try:

            while (
                self.running
                and self.fecha_actual <= end_time
            ):

                step += 1

                # ---------------------------------------------
                # 06:00 BATCH
                # ---------------------------------------------

                if (
                    self.fecha_actual.hour == 6
                    and self.fecha_actual.minute
                    == 0
                    and self.last_batch_date
                    != self.fecha_actual.date()
                ):

                    print(
                        "[BATCH] "
                        "06:00 - generando archivos"
                    )

                    self.generate_files()

                # ---------------------------------------------
                # SIMULATION
                # ---------------------------------------------

                self.simulation_step()

                # ---------------------------------------------
                # CHECKPOINT
                # ---------------------------------------------

                if (
                    step
                    % checkpoint_every_steps
                    == 0
                ):

                    self.save_state()

                # ---------------------------------------------
                # ADVANCE CLOCK
                # ---------------------------------------------

                next_time = (
                    self.fecha_actual
                    + timedelta(
                        minutes=step_minutes
                    )
                )

                if next_time > end_time:

                    self.fecha_actual = end_time

                else:

                    self.fecha_actual = next_time

                self.update_event_generators()

                # ---------------------------------------------
                # REAL TIME WAIT
                # ---------------------------------------------

                time.sleep(
                    real_seconds_per_step
                )

        except KeyboardInterrupt:

            print()
            print(
                "[SIM] Interrumpida por usuario."
            )

        finally:

            self.running = False

            # ---------------------------------------------
            # FINAL SYNC
            # ---------------------------------------------

            self.sync_orders_with_historical()

            # ---------------------------------------------
            # FINAL CHECKPOINT
            # ---------------------------------------------

            self.save_state()

            # ---------------------------------------------
            # KAFKA FLUSH
            # ---------------------------------------------

            self.kproducer.flush()

        print()
        print("=" * 70)
        print("[SIM] SIMULACIÓN FINALIZADA")
        print("=" * 70)

        print(
            f"[SIM] Fecha final: "
            f"{self.fecha_actual}"
        )

        print(
            f"[SIM] Steps: "
            f"{step}"
        )

        print(
            f"[SIM] Eventos ORDER: "
            f"{len(self.order_events)}"
        )

        print(
            f"[SIM] Eventos GPS: "
            f"{len(self.gps_events)}"
        )

        print(
            f"[SIM] Incidencias: "
            f"{len(self.incidents)}"
        )

        print("=" * 70)

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        print(
            "[SIM] Solicitud de parada..."
        )

        self.running = False

        self.save_state()

        self.kproducer.flush()

    # =========================================================
    # LEGACY RUN
    # =========================================================

    def run(
        self,
        steps=1,
        realtime=False
    ):
        """
        Método compatible con la versión anterior.

        Mantiene el comportamiento de ejecutar varios pasos,
        pero cada paso representa 1 hora simulada.

        Para nuevas pruebas se recomienda usar run_day().
        """

        if self.state_exists():

            self.load_state()

        else:

            self.generate_initial_data()

            self.generate_files()

            self.save_state()

        print(
            f"FECHA ACTUAL: "
            f"{self.fecha_actual:%Y-%m-%d %H:%M}"
        )

        for step in range(steps):

            print()
            print("=" * 70)

            print(
                f"STEP {step + 1}/{steps}"
            )

            print(
                f"Hora simulada: "
                f"{self.fecha_actual:%Y-%m-%d %H:%M}"
            )

            print("=" * 70)

            self.simulation_step()

            self.advance_time(60)

            self.save_state()

            #if realtime:

                #time.sleep(60)

        self.kproducer.flush()

        print()
        print(
            "Simulación finalizada."
        )

        print(
            f"Estado actual: "
            f"{self.fecha_actual}"
        )
