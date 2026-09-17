from datetime import datetime, timedelta
from pathlib import Path
import json
import time
import random

import pandas as pd

from src.generator.address_generator import AddressGenerator
from src.generator.drivers_generator import DriverGenerator
from src.generator.orders_generator import OrderGenerator
from src.generator.historical_generator import OrderHistoricalGenerator
from src.generator.order_event import OrderEvents
from src.generator.route_generator import RouteGenerator
from src.generator.gps_events import GPSEvents
from src.generator.incident_historical_generator import (
    IncidentHistoricalGenerator
)

from src.kafka.producer import KafkaProducer

from src.onelake_client import OnelakeClient

from src.objects.order import Order
from src.objects.driver import Driver
from src.objects.route import Route
from src.objects.incident import Incident
from src.objects.location import Location

from src.setup import *


class Simulator:

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


    # INIT


    def __init__(
        self,
        fecha_actual: datetime
    ):

        self.fecha_actual = fecha_actual

        self.client_onelk = (OnelakeClient())

        self.kproducer = (KafkaProducer())

        self.kproducer.create_topics()

        self.drivers = []
        self.orders = []
        self.routes = []

        self.historical_orders = []

        self.incidents = []
        self.historical_incidents = []

        self.gps_events = []
        self.order_events = []

        self.order_event_generator = None
        self.gps_event_generator = None

        self.current_simulation_date = (self.fecha_actual.date())

        self.last_batch_date = None

        self.running = False

        # Objetivo del día.
        self.daily_orders_target = (270 * random.randint(120, 200))


    # STATE


    def state_exists(self) -> bool:
        return self.STATE_FILE.exists()


    # INITIAL DATA
    def generate_initial_data(self):
        self._load_addresses()

        # DIRECCIONES


        # Mantén aquí exactamente tu código original
        # de carga de addresses_madrid y addresses_spain.


        # DRIVERS


        self.drivers = DriverGenerator(
            [],
            self.addresses_madrid
        ).create_drivers(270)



        # RUTAS


        self.routes = RouteGenerator(
            self.drivers,
            self.addresses_madrid,
            self.fecha_actual
        ).create_routes()


        # HISTÓRICO


        self.historical_generator = (
            OrderHistoricalGenerator(self.drivers,
                self.addresses_madrid,
                self.addresses_spain,
                self.fecha_actual)
        )

        #elf.historical_orders = self.historical_generator.create_historical(6000,today_orders=200)
        self.historical_orders = self.historical_generator.create_historical(100,today_orders=20)
        from collections import Counter

        print(
            "\n[DEBUG] HISTORICAL:",
            len(self.historical_orders)
        )

        print(
            "[DEBUG] ESTADOS HISTORICAL:"
        )

        print(
            Counter(
                order.status
                for order in self.historical_orders
            )
        )

        # PEDIDOS DEL DÍA


        self.order_generator = OrderGenerator(
            self.historical_orders,
            self.fecha_actual
        )

        self.orders = (
            self.order_generator.get_orders_for_today()
        )


        # EVENTOS



        self._create_event_generators()
        
        
    def _load_addresses(self):
        """
        Carga las direcciones de Madrid y España desde data/reference.
        """

        base_dir = Path(__file__).resolve().parents[2]

        spain_file = base_dir / self.SPAIN_FILE
        madrid_file = base_dir / self.MADRID_FILE

        if not spain_file.exists():
            raise FileNotFoundError(
                f"No se encuentra el fichero de España: {spain_file}"
            )

        if not madrid_file.exists():
            raise FileNotFoundError(
                f"No se encuentra el fichero de Madrid: {madrid_file}"
            )

        print(f"[DATA] Cargando direcciones España: {spain_file}")
        print(f"[DATA] Cargando direcciones Madrid: {madrid_file}")

        self.addresses_spain = pd.read_csv(
            spain_file,
            sep=None,
            engine="python"
        )

        self.addresses_madrid = pd.read_csv(
            madrid_file,
            sep=";",
            encoding=('latin-1')
        )

        self.addresses_madrid.columns = (
            self.addresses_madrid.columns
            .astype(str)
            .str.strip()
            .str.replace("\ufeff", "", regex=False)
        )

        self.addresses_madrid["COD_POSTAL"] = (
            pd.to_numeric(
                self.addresses_madrid["COD_POSTAL"],
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
            .astype(str)
            .str.zfill(5)
        )

        self.addresses_madrid["NUMERO"] = (
            self.addresses_madrid["NUMERO"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        self.addresses_madrid["VIA_NOMBRE_ACENTOS"] = (
            self.addresses_madrid["VIA_NOMBRE_ACENTOS"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    
        
    def _is_final_order(self, order):

        if order.type_service == "RECOGIDA":

            return order.status in {
                "RECOGIDO",
                "RECHAZADO",
                "CANCELADO"
            }

        if order.type_service == "ENTREGA":

            return order.status in {
                "ENTREGADO",
                "RECHAZADO",
                "CANCELADO"
            }

        return False    
    
    # OBTENER PEDIDOS DEL DÍA
    def _get_orders_for_current_day(self,daily_target=None):

        today = self.fecha_actual.date()

        active_statuses = {
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

            "INCIDENTADO"
        }

        candidates = []

        for order in self.historical_orders:

            if order.order_created_date is None:
                continue

            if order.order_created_date.date() > today:
                continue

            if self._is_final_order(order):
                continue

            if order.status not in active_statuses:
                continue

            candidates.append(order)

        # Los más antiguos / urgentes primero
        candidates.sort(
            key=lambda order: (
                order.order_expected_date
                if order.order_expected_date is not None
                else datetime.max
            )
        )

        if daily_target is None:
            daily_target = 270 * random.randint(120, 200)

        selected = candidates[:daily_target]

        print(
            f"[INIT] Pedidos históricos activos: "
            f"{len(candidates)}"
        )

        print(
            f"[INIT] Pedidos seleccionados para hoy: "
            f"{len(selected)}"
        )

        return selected


    # CREATE GENERATORS


    def _create_event_generators(self):

        self.order_event_generator = (OrderEvents(self.orders,
                self.drivers,
                self.routes,
                self.fecha_actual))

        self.gps_event_generator = (GPSEvents(self.orders,
                self.drivers,
                self.routes,
                self.fecha_actual))


    # COUNTERS


    def _initialize_counters(self):

        self.order_event_generator.event_counter = 0

        self.gps_event_generator.event_counter = 0

        max_incident = (self._get_max_incident_number(self.historical_incidents))

        self.order_event_generator \
            .incident_generator \
            .incident_counter = max_incident

        self.order_event_generator.incidents = (self.incidents)

        self.order_event_generator \
            .incident_generator \
            .incidents = (self.incidents)


    # MAX INCIDENT


    @staticmethod
    def _get_max_incident_number(
        incidents
    ) -> int:

        maximum = 0

        for incident in incidents:

            value = str(incident.id_incident)

            if not value.startswith("INC"):
                continue

            try:

                number = int(value[3:])

                maximum = max(maximum,
                    number)

            except ValueError:
                continue

        return maximum


    # TIME


    def advance_time(
        self,
        minutes: int
    ):

        if minutes <= 0:
            raise ValueError("minutes debe ser > 0")

        previous_date = (self.fecha_actual.date())

        self.fecha_actual += (timedelta(minutes=minutes))

        new_date = (self.fecha_actual.date())

        self.update_event_generators()

        if new_date != previous_date:

            self.handle_day_change(new_date)


    # UPDATE GENERATORS


    def update_event_generators(self):

        if self.order_event_generator is not None:

            self.order_event_generator.fecha_actual = (self.fecha_actual)

        if self.gps_event_generator is not None:

            self.gps_event_generator.fecha_actual = (self.fecha_actual)


    # DAY CHANGE


    def handle_day_change(
        self,
        new_date
    ):

        print()
        print("=" * 70)

        print(f"[DAY] CAMBIO DE DÍA: "
            f"{self.current_simulation_date} "
            f"-> {new_date}")

        print("=" * 70)

        self.current_simulation_date = new_date

        self.start_new_day()


    # SIMULATION STEP


    def simulation_step(self):
        print()
        print(f"[SIM] {self.fecha_actual:%Y-%m-%d %H:%M:%S}")

        print("[DEBUG] Antes de create_order_event()", flush=True)

        self.create_order_event()

        print("[DEBUG] Después de create_order_event()", flush=True)

        arrived_orders = self.create_gps_events()

        print("[DEBUG] Después de create_gps_events()", flush=True)

        self.process_arrived_orders(arrived_orders)

        print("[DEBUG] Después de process_arrived_orders()", flush=True)

        self.sync_orders_with_historical()

        print("[DEBUG] Después de sync_orders_with_historical()", flush=True)

    # ORDER EVENT

    def create_order_event(self):

        results = self.order_event_generator.generate_event()

        if not results:
            return

        order_events = []

        for order_event in results:

            if order_event is None:
                continue

            print(
                f"[DEBUG ORDER] "
                f"id_event={order_event.get('id_event')} | "
                f"id_order={order_event.get('id_order')} | "
                f"id_driver={order_event.get('id_driver')} | "
                f"type_service={order_event.get('type_service')} | "
                f"{order_event.get('previous_status')} "
                f"-> {order_event.get('status')}",
                flush=True
            )

            # Comprobación importante antes de Avro
            if order_event.get("id_driver") is None:

                print(
                    f"[ERROR ORDER] "
                    f"Pedido {order_event.get('id_order')} "
                    f"sin id_driver",
                    flush=True
                )

                continue

            self.order_events.append(order_event)
            order_events.append(order_event)

            self.produce_event(
                "order-events",
                order_event,
                "id_event"
            )

        print(
            f"[ORDER] Eventos generados: "
            f"{len(order_events)}",
            flush=True
        )


    # GPS


    def create_gps_events(self):

        if self.gps_event_generator is None:
            return []

        gps_events = (self.gps_event_generator.generate_event())

        if not gps_events:
            return []

        print(f"[GPS] "
            f"{len(gps_events)} eventos")

        arrived_orders = []

        for item in gps_events:

            key, gps_event, orders_arrived = item

            if gps_event is not None:

                self.gps_events.append(gps_event)

                self.produce_event("gps-events",
                    gps_event,
                    "gps_event_id")

            if orders_arrived:

                arrived_orders.extend(orders_arrived)

        return arrived_orders


    # DELIVERY COMPLETED


    def process_arrived_orders(self, arrived_orders):

        if not arrived_orders:
            return

        for order in arrived_orders:

            result = (
                self.order_event_generator
                .generate_delivery_completed_event(order)
            )

            if result is None:
                continue

            order_event = result

            print(
                f"[ORDER EVENT GPS] "
                f"{order_event.get('id_order')} | "
                f"{order_event.get('previous_status')} -> "
                f"{order_event.get('status')}",
                flush=True
            )

            self.order_events.append(order_event)

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


    # KAFKA


    def produce_event(
        self,
        topic,
        event,
        key_field
    ):

        if event is None:
            return

        if key_field not in event:

            raise KeyError(f"Campo '{key_field}' "
                f"no existe en evento para "
                f"topic '{topic}'")

        key_event = str(event[key_field])

        print(f"[Kafka] "
            f"topic={topic} "
            f"key={key_event}")

        self.kproducer.produce(topic,
            key_event,
            event)


    # UPDATE ORDER STATUS


    def update_order_status(
        self,
        order_id,
        new_status
    ):

        for order in self.orders:

            if order.id_order != order_id:
                continue

            order.set_status(new_status,
                self.fecha_actual)

            print(f"[ORDER] "
                f"{order_id} -> "
                f"{new_status}")

            return order

        print(f"[ORDER] "
            f"{order_id} no encontrada.")

        return None


    # SERIALIZATION HELPERS


    @staticmethod
    def _datetime_to_json(value):

        if value is None:
            return None

        if isinstance(value,
            datetime):

            return int(value.timestamp() * 1000)

        return value

    @staticmethod
    def _datetime_from_json(value):

        if value is None:
            return None

        if isinstance(value,
            (int, float)):

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

        if isinstance(value,
            (str, int, float, bool)):

            return value

        return str(value)


    # ORDER SERIALIZATION


    def serialize_order(
        self,
        order
    ):

        return {

            "id_order":
                self._clean_value(order.id_order),

            "id_driver":
                self._clean_value(order.id_driver),

            "id_driver_pickup":
                self._clean_value(order.id_driver_pickup),

            "id_driver_delivery":
                self._clean_value(order.id_driver_delivery),

            "id_route":
                self._clean_value(order.id_route),

            "order_created_date":
                self._datetime_to_json(order.order_created_date),

            "order_expected_date":
                self._datetime_to_json(order.order_expected_date),

            "status":
                self._clean_value(order.status),

            "status_modified_date":
                self._datetime_to_json(order.status_modified_date),

            "num_products":
                int(order.num_products),

            "type_order":
                self._clean_value(order.type_order),

            "type_service":
                self._clean_value(order.type_service),

            "sender":
                self._clean_value(order.sender),

            "pickup_street":
                self._clean_value(order.pickup_street),

            "pickup_house_number":
                self._clean_value(order.pickup_house_number),

            "pickup_floor":
                self._clean_value(order.pickup_floor),

            "pickup_letter":
                self._clean_value(order.pickup_letter),

            "pickup_city":
                self._clean_value(order.pickup_city),

            "pickup_postal_code":
                self._clean_value(order.pickup_postal_code),

            "pickup_country":
                self._clean_value(order.pickup_country),

            "destinatary":
                self._clean_value(order.destinatary),

            "delivery_street":
                self._clean_value(order.delivery_street),

            "delivery_house_number":
                self._clean_value(order.delivery_house_number),

            "delivery_floor":
                self._clean_value(order.delivery_floor),

            "delivery_letter":
                self._clean_value(order.delivery_letter),

            "delivery_city":
                self._clean_value(order.delivery_city),

            "delivery_postal_code":
                self._clean_value(order.delivery_postal_code),

            "delivery_country":
                self._clean_value(order.delivery_country),

            "status_history": {

                status:
                    self._datetime_to_json(date
                    )

                for status, date
                in order.status_history.items()
            }
        }


    # ORDER DESERIALIZATION


    def deserialize_order(
        self,
        data
    ):

        order = Order(

            id_order=data["id_order"],

            id_driver=data["id_driver"],

            order_created_date=(self._datetime_from_json(data["order_created_date"])),

            order_expected_date=(self._datetime_from_json(data["order_expected_date"])),

            status=data["status"],

            status_modified_date=(self._datetime_from_json(data["status_modified_date"])),

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
            ])

        order.id_driver_pickup = (data.get("id_driver_pickup"))

        order.id_driver_delivery = (data.get("id_driver_delivery"))

        order.id_route = (data.get("id_route"))

        order.status_history = {

            status:
                self._datetime_from_json(date)

            for status, date
            in data.get("status_history",
                {}).items()
        }

        return order


    # DRIVER SERIALIZATION


    def serialize_driver(
        self,
        driver
    ):

        location = None

        if driver.location is not None:

            location = {

                "latitude":
                    float(driver.location.latitude
                    ),

                "longitude":
                    float(driver.location.longitude
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
                self._clean_value(driver.zone),

            "location":
                location
        }


    # DRIVER DESERIALIZATION


    def deserialize_driver(
        self,
        data
    ):

        location = None

        if data.get("location") is not None:

            location = Location(

                float(data["location"]["latitude"]),

                float(data["location"]["longitude"]))

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

            location=location)


    # ROUTE


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
                self._clean_value(route.postal_code),

            "street":
                self._clean_value(route.street),

            "house_number":
                self._clean_value(route.house_number),

            "latitude":
                float(route.latitude),

            "longitude":
                float(route.longitude),

            "priority":
                int(route.priority)
        }


    # ROUTE DESERIALIZATION


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

            latitude=float(data["latitude"]),

            longitude=float(data["longitude"]),

            priority=int(data["priority"]))


    # INCIDENT


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
                self._datetime_to_json(incident.incident_date),

            "incident_reason":
                incident.incident_reason,

            "observations":
                incident.observations,

            "resolved":
                bool(incident.resolved),

            "resolution_date":
                self._datetime_to_json(incident.resolution_date),

            "resolution_action":
                incident.resolution_action
        }


    # INCIDENT DESERIALIZATION


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

            incident_date=(self._datetime_from_json(data["incident_date"])),

            incident_reason=data[
                "incident_reason"
            ],

            observations=data[
                "observations"
            ],

            resolved=data[
                "resolved"
            ],

            resolution_date=(self._datetime_from_json(data["resolution_date"])),

            resolution_action=data[
                "resolution_action"
            ])


    # GPS STATE


    def serialize_gps_state(self):

        if self.gps_event_generator is None:
            return {}

        result = {}

        for driver_id, state in (self.gps_event_generator
            .driver_state
            .items()):

            result[str(driver_id)] = {

                "route_index":
                    int(state["route_index"]
                    ),

                "progress":
                    float(state["progress"]
                    ),

                "start_latitude":
                    float(state["start_latitude"]
                    ),

                "start_longitude":
                    float(state["start_longitude"]
                    ),

                "target_latitude":
                    float(state["target_latitude"]
                    ),

                "target_longitude":
                    float(state["target_longitude"]
                    ),

                "route_id":
                    state["route_id"]
            }

        return result


    # SAVE STATE


    def save_state(self):

        self.STATE_FILE.parent.mkdir(parents=True,
            exist_ok=True)

        state = {

            "version": 2,

            "fecha_actual":
                self._datetime_to_json(self.fecha_actual),

            "current_simulation_date":
                self.current_simulation_date.isoformat(),

            "last_batch_date": (self.last_batch_date.isoformat()
                if self.last_batch_date
                else None),

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
                self.serialize_incident(incident)
                for incident in self.incidents
            ],

            "historical_incidents": [
                self.serialize_incident(incident)
                for incident
                in self.historical_incidents
            ],

            "gps_driver_state":
                self.serialize_gps_state()
        }

        temporary_file = (self.STATE_FILE.with_suffix(".tmp"))

        with open(temporary_file,
            "w",
            encoding="utf-8") as file:

            json.dump(state,
                file,
                ensure_ascii=False,
                indent=2)

        temporary_file.replace(self.STATE_FILE)

        print(f"[STATE] Guardado: "
            f"{self.STATE_FILE}")


    # LOAD STATE


    def load_state(self):

        print(f"[STATE] Cargando: "
            f"{self.STATE_FILE}")

        with open(self.STATE_FILE,
            "r",
            encoding="utf-8") as file:

            state = json.load(file)

        self.fecha_actual = (self._datetime_from_json(state["fecha_actual"]))

        self.current_simulation_date = (datetime.fromisoformat(state.get("current_simulation_date",
                    self.fecha_actual.date()
                    .isoformat())).date())

        last_batch_date = state.get("last_batch_date")

        if last_batch_date:

            self.last_batch_date = (datetime.fromisoformat(last_batch_date).date())

        else:

            self.last_batch_date = None

        self.drivers = [
            self.deserialize_driver(data)
            for data in state["drivers"]
        ]

        self.routes = [
            self.deserialize_route(data)
            for data in state["routes"]
        ]

        self.historical_orders = [
            self.deserialize_order(data)
            for data
            in state["historical_orders"]
        ]

        self.orders = [
            self.deserialize_order(data)
            for data
            in state["orders"]
        ]

        self.historical_incidents = [
            self.deserialize_incident(data)
            for data
            in state["historical_incidents"]
        ]

        self.incidents = [
            self.deserialize_incident(data)
            for data
            in state["incidents"]
        ]

        self._create_event_generators()
        self._initialize_counters()
        
        counters = state["counters"]

        self.order_event_generator.event_counter = (counters["order_event"])

        self.gps_event_generator.event_counter = (counters["gps_event"])

        self.order_event_generator \
            .incident_generator \
            .incident_counter = (counters["incident"])

        self.order_event_generator.incidents = (self.incidents)

        self.order_event_generator \
            .incident_generator \
            .incidents = (self.incidents)

        gps_state = state.get("gps_driver_state",
            {})

        self.gps_event_generator.driver_state = (gps_state)

        self.update_event_generators()

        print("[STATE] Estado cargado correctamente.")

        print(f"[STATE] Fecha: "
            f"{self.fecha_actual}")

        print(f"[STATE] Pedidos: "
            f"{len(self.orders)}")

        print(f"[STATE] Conductores: "
            f"{len(self.drivers)}")

        print(f"[STATE] Incidencias: "
            f"{len(self.incidents)}")


    # RESET


    def reset_state(self):

        if self.STATE_FILE.exists():

            self.STATE_FILE.unlink()

            print("[STATE] Estado eliminado.")

        else:

            print("[STATE] No había estado.")


    # START NEW DAY
    def start_new_day(self):
        today = self.fecha_actual.date()

        active_orders = [
            order
            for order in self.orders
            if not self._is_final_order(order)
        ]

        self.daily_orders_target = (
            270 * random.randint(120, 200)
        )

        active_ids = {
            str(order.id_order)
            for order in active_orders
        }

        candidates = []

        for order in self.historical_orders:

            if str(order.id_order) in active_ids:
                continue

            if order.order_created_date is None:
                continue

            if order.order_created_date.date() > today:
                continue

            if self._is_final_order(order):
                continue

            candidates.append(order)

        candidates.sort(
            key=lambda order: (
                order.order_expected_date
                if order.order_expected_date
                else datetime.max
            )
        )

        remaining = max(
            0,
            self.daily_orders_target - len(active_orders)
        )

        for order in candidates[:remaining]:

            active_orders.append(order)
            active_ids.add(str(order.id_order))

        self.orders = active_orders

        self._create_event_generators()

        self.order_event_generator.incidents = self.incidents
        self.order_event_generator.incident_generator.incidents = (
            self.incidents
        )

        self._restore_runtime_counters_after_generator_reset()
        self.update_event_generators()

        print(
            f"[DAY] Pedidos activos: {len(self.orders)}"
        )


    # RESTORE COUNTERS


    def _restore_runtime_counters_after_generator_reset(
        self
    ):

        max_incident = (self._get_max_incident_number(self.incidents))

        historical_max_incident = (self._get_max_incident_number(self.historical_incidents))

        self.order_event_generator \
            .incident_generator \
            .incident_counter = max(max_incident,
                historical_max_incident)


    # SYNC ORDERS


    def sync_orders_with_historical(self):

        historical_by_id = {

            str(order.id_order): order

            for order
            in self.historical_orders
        }

        for order in self.orders:

            historical_order = (historical_by_id.get(str(order.id_order)))

            if historical_order is None:
                continue

            historical_order.id_driver = (order.id_driver)

            historical_order.id_driver_pickup = (order.id_driver_pickup)

            historical_order.id_driver_delivery = (order.id_driver_delivery)

            historical_order.id_route = (order.id_route)

            historical_order.status = (order.status)

            historical_order.status_modified_date = (order.status_modified_date)

            historical_order.status_history = dict(order.status_history)


    # WRITE FILE


    def write_file(
        self,
        path,
        dataframe
    ):

        path = Path(path)

        path.parent.mkdir(parents=True,
            exist_ok=True)

        suffix = path.suffix.lower()

        if suffix == ".parquet":

            dataframe = dataframe.copy()

            if "location" in dataframe.columns:

                dataframe["latitude"] = (dataframe["location"]
                    .apply(lambda location:
                        float(location.latitude)
                        if location is not None
                        else None
                    ))

                dataframe["longitude"] = (dataframe["location"]
                    .apply(lambda location:
                        float(location.longitude)
                        if location is not None
                        else None
                    ))

                dataframe = dataframe.drop(columns=["location"])

            dataframe.to_parquet(str(path),
                index=False)

        elif suffix == ".csv":

            dataframe.to_csv(str(path),
                index=False)

        elif suffix == ".xlsx":

            dataframe.to_excel(str(path),
                index=False)

        elif suffix == ".json":

            dataframe.to_json(str(path),
                orient="records",
                force_ascii=False,
                indent=4,
                date_format="iso")

        else:

            raise ValueError(f"Unsupported file format: "
                f"{suffix}")


    # BATCH FILES


    def generate_files(self):

        str_fecha = (self.fecha_actual.strftime("%Y-%m-%d"))

        print()
        print("=" * 70)

        print(f"[BATCH] ARCHIVOS {str_fecha}")

        print("=" * 70)

        historical_records = []

        for order in self.historical_orders:

            record = vars(order).copy()

            record["status_history"] = ", ".join(

                f"{status}: "
                f"{date.strftime('%d/%m/%Y %H:%M:%S')}"

                for status, date
                in order.status_history.items()

                if date is not None)

            historical_records.append(record)

        historical_df = pd.DataFrame(historical_records)

        historical_orders_file = (f"{GENERATED_HISTORICAL_ORDERS}"
            f"/{str_fecha}"
            "/historical_orders.csv")

        self.write_file(historical_orders_file,
            historical_df)

        self.client_onelk.load_file(f"{LANDING_HISTORICAL_ORDERS}"
            f"/{str_fecha}",
            historical_orders_file)

        orders_df = pd.DataFrame([
                vars(order)
                for order in self.orders
            ])

        orders_file = (f"{GENERATED_ORDERS}"
            f"/{str_fecha}"
            "/orders.xlsx")

        self.write_file(orders_file,
            orders_df)

        self.client_onelk.load_file(f"{LANDING_ORDERS}"
            f"/{str_fecha}",
            orders_file)

        drivers_df = pd.DataFrame([
                vars(driver)
                for driver in self.drivers
            ])

        drivers_file = (f"{GENERATED_DRIVERS}"
            f"/{str_fecha}"
            "/drivers.parquet")

        self.write_file(drivers_file,
            drivers_df)

        self.client_onelk.load_file(f"{LANDING_DRIVERS}"
            f"/{str_fecha}",
            drivers_file)

        routes_df = pd.DataFrame([
                vars(route)
                for route in self.routes
            ])

        routes_file = (f"{GENERATED_ROUTES}"
            f"/{str_fecha}"
            "/routes.json")

        self.write_file(routes_file,
            routes_df)

        self.client_onelk.load_file(f"{LANDING_ROUTES}"
            f"/{str_fecha}",
            routes_file)

        historical_incidents_df = pd.DataFrame([
                vars(incident)
                for incident
                in self.historical_incidents
            ])

        historical_incidents_file = (f"{GENERATED_HISTORICAL_INCIDENTS}"
            f"/{str_fecha}"
            "/historical_incidents.json")

        self.write_file(historical_incidents_file,
            historical_incidents_df)

        self.client_onelk.load_file(f"{LANDING_HISTORICAL_INCIDENTS}"
            f"/{str_fecha}",
            historical_incidents_file)

        self.last_batch_date = (self.fecha_actual.date())

        print(f"[BATCH] Archivos de "
            f"{str_fecha} generados.")


    # RUN DAY

    def run_day(
        self,
        simulated_minutes_per_second: float = 10,
        start_time: datetime = None,
        end_time: datetime = None,
        reset: bool = False,
        step_minutes: int = 2,
        checkpoint_every_steps: int = 10,
        generate_batch: bool = True,
        fast_minutes_per_second: float = 600
    ):

        if step_minutes <= 0:
            raise ValueError("step_minutes debe ser > 0")

        if simulated_minutes_per_second <= 0:
            raise ValueError(
                "simulated_minutes_per_second debe ser > 0"
            )

        if fast_minutes_per_second <= 0:
            raise ValueError(
                "fast_minutes_per_second debe ser > 0"
            )

        if checkpoint_every_steps <= 0:
            raise ValueError(
                "checkpoint_every_steps debe ser > 0"
            )

        if reset:
            self.reset_state()

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

        if start_time is not None:

            if reset:

                self.fecha_actual = start_time

                self.current_simulation_date = (
                    start_time.date()
                )

                self.update_event_generators()

            elif start_time > self.fecha_actual:

                print(
                    f"[SIM] Avanzando hasta "
                    f"{start_time}"
                )

                self.fecha_actual = start_time

                self.current_simulation_date = (
                    start_time.date()
                )

                self.update_event_generators()

        if end_time is None:

            end_time = (
                self.fecha_actual
                .replace(
                    hour=21,
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
            f"[SIM] Velocidad normal: "
            f"{simulated_minutes_per_second} "
            f"min simulados / segundo"
        )

        print(
            f"[SIM] Velocidad rápida 06:00-08:00: "
            f"{fast_minutes_per_second} "
            f"min simulados / segundo"
        )

        print(
            f"[SIM] Tick: "
            f"{step_minutes} minuto(s)"
        )

        print("=" * 70)

        self.running = True

        step = 0

        # Para no ejecutar dos veces el cambio de las 08:00
        reparto_forzado = False

        try:

            while (
                self.running
                and self.fecha_actual <= end_time
            ):

                step += 1

                hora_actual = self.fecha_actual.time()

                # ==================================================
                # BATCH DE LAS 06:00
                # ==================================================

                if (
                    self.fecha_actual.hour == 6
                    and self.fecha_actual.minute == 0
                    and self.last_batch_date
                    != self.fecha_actual.date()
                ):

                    print(
                        "[BATCH] "
                        "06:00 - generando archivos"
                    )

                    self.generate_files()

                # ==================================================
                # VELOCIDAD DINÁMICA
                #
                # 06:00 - 07:59 -> rápida
                # 08:00 en adelante -> normal
                # ==================================================

                if self.fecha_actual.hour < 8:

                    velocidad_actual = (
                        fast_minutes_per_second
                    )

                    modo_velocidad = "RÁPIDA"

                else:

                    velocidad_actual = (
                        simulated_minutes_per_second
                    )

                    modo_velocidad = "NORMAL"

                real_seconds_per_step = (
                    step_minutes
                    / velocidad_actual
                )

                print(
                    f"[SIM] {self.fecha_actual} | "
                    f"modo={modo_velocidad} | "
                    f"velocidad={velocidad_actual} min/s"
                )


                print()

                # ==================================================
                # SIMULACIÓN DEL TICK
                # ==================================================

                inicio_tick = time.perf_counter()

                self.simulation_step()

                fin_tick = time.perf_counter()

                tiempo_tick = (
                    fin_tick - inicio_tick
                )

                print(
                    f"[PERF] simulation_step="
                    f"{tiempo_tick:.4f}s"
                )

                # ==================================================
                # CHECKPOINT
                # ==================================================

                if (
                    step
                    % checkpoint_every_steps
                    == 0
                ):

                    self.save_state()

                # ==================================================
                # AVANZAR TIEMPO
                # ==================================================

                next_time = (
                    self.fecha_actual
                    + timedelta(minutes=step_minutes)
                )

                if next_time > end_time:

                    self.fecha_actual = end_time

                else:

                    self.fecha_actual = next_time

                self.update_event_generators()

                # ==================================================
                # ESPERA REAL
                # ==================================================

                time.sleep(real_seconds_per_step)

        except KeyboardInterrupt:

            print()
            print("[SIM] Interrumpida por usuario.")

        finally:

            self.running = False

            self.sync_orders_with_historical()

            self.save_state()

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
    # STOP


    def stop(self):

        print("[SIM] Solicitud de parada...")

        self.running = False

        self.save_state()

        self.kproducer.flush()


    # LEGACY RUN


    def run(
        self,
        steps=1,
        realtime=False
    ):

        if self.state_exists():

            self.load_state()

        else:

            self.generate_initial_data()

            self.generate_files()

            self.save_state()

        print(f"FECHA ACTUAL: "
            f"{self.fecha_actual:%Y-%m-%d %H:%M}")

        for step in range(steps):

            print()
            print("=" * 70)

            print(f"STEP {step + 1}/{steps}")

            print(f"Hora simulada: "
                f"{self.fecha_actual:%Y-%m-%d %H:%M}")

            print("=" * 70)

            self.simulation_step()

            self.advance_time(60)

            self.save_state()

        self.kproducer.flush()

        print()
        print("Simulación finalizada.")

        print(f"Estado actual: "
            f"{self.fecha_actual}")