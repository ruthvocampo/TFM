from datetime import (
    timedelta,
    datetime
)

import json
import time
import pandas as pd

from src.generator.address_generator import (
    AddressGenerator
)

from src.generator.drivers_generator import (
    DriverGenerator
)

from src.generator.orders_generator import (
    OrderGenerator
)

from src.generator.historical_generator import (
    OrderHistoricalGenerator
)

from src.generator.order_event import (
    OrderEvents
)

from src.generator.route_generator import (
    RouteGenerator
)

from src.generator.gps_events import (
    GPSEvents
)

from src.generator.incident_historical_generator import (
    IncidentHistoricalGenerator
)

from src.generator.weather_event import (
    WeatherEventGenerator
)

from src.apis.traffic_api import (
    TrafficApi
)

from src.kafka.producer import (
    KafkaProducer
)

from src.onelake_client import (
    OnelakeClient
)

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

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        fecha_actual
    ):

        self.fecha_actual = (
            fecha_actual
        )

        self.client_onelk = (
            OnelakeClient()
        )

        self.kproducer = (
            KafkaProducer()
        )

        self.kproducer.create_topics()

        self.drivers = []
        self.orders = []
        self.routes = []
        self.historical_orders = []

        self.gps_events = []
        self.order_events = []
        self.incidents = []

        self.historical_incidents = []

        self.weather = []
        self.weather_generator = None

        self.weather_event_counter = 0

        self.last_weather_event = None

        self.traffic = []
        self.traffic_api = None

        self.traffic_event_counter = 0

        self.last_traffic_event = None

        self.order_event_generator = None
        self.gps_event_generator = None

    # =========================================================
    # STATE EXISTS
    # =========================================================

    def state_exists(self):

        return self.STATE_FILE.exists()

    # =========================================================
    # INITIAL DATA
    # =========================================================

    def generate_initial_data(self):

        print(
            "Generando datos iniciales..."
        )

        address_generator = AddressGenerator(
            self.SPAIN_FILE,
            self.MADRID_FILE
        )

        addresses_spain = (
            address_generator
            .get_address_spain_df()
        )

        addresses_madrid = (
            address_generator
            .get_address_madrid_df()
        )

        # -----------------------------------------------------
        # DRIVERS
        # -----------------------------------------------------

        driver_generator = DriverGenerator(
            [],
            addresses_madrid
        )

        self.drivers = (
            driver_generator
            .create_drivers(270)
        )

        # -----------------------------------------------------
        # ROUTES
        # -----------------------------------------------------

        route_generator = RouteGenerator(
            self.drivers,
            addresses_madrid,
            self.fecha_actual
        )

        self.routes = (
            route_generator
            .create_routes()
        )

        # -----------------------------------------------------
        # HISTORICAL ORDERS
        # -----------------------------------------------------

        historical_generator = (
            OrderHistoricalGenerator(
                self.drivers,
                addresses_madrid,
                addresses_spain,
                self.fecha_actual
            )
        )

        self.historical_orders = (
            historical_generator
            .create_historical(6000)
        )

        # -----------------------------------------------------
        # HISTORICAL INCIDENTS
        # -----------------------------------------------------

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
        # ORDERS TODAY
        # -----------------------------------------------------

        order_generator = OrderGenerator(
            self.historical_orders,
            self.fecha_actual
        )

        self.orders = (
            order_generator
            .get_orders_for_today()
        )

        # -----------------------------------------------------
        # ORDER EVENTS
        # -----------------------------------------------------

        self.order_event_generator = (
            OrderEvents(
                self.orders,
                self.drivers,
                self.routes,
                self.fecha_actual
            )
        )

        # -----------------------------------------------------
        # GPS
        # -----------------------------------------------------

        self.gps_event_generator = (
            GPSEvents(
                self.orders,
                self.drivers,
                self.routes,
                self.fecha_actual
            )
        )

        # -----------------------------------------------------
        # WEATHER
        # -----------------------------------------------------

        self.weather_generator = (
            WeatherEventGenerator(
                self.fecha_actual
            )
        )

        self.weather = []

        # -----------------------------------------------------
        # TRAFFIC
        # -----------------------------------------------------

        self.traffic_api = TrafficApi(
            self.fecha_actual
        )

        self.traffic = []

        # -----------------------------------------------------
        # COUNTERS
        # -----------------------------------------------------

        self._initialize_counters()

    # =========================================================
    # COUNTERS
    # =========================================================

    def _initialize_counters(self):

        # Order event
        self.order_event_generator.event_counter = 0

        # GPS
        self.gps_event_generator.event_counter = 0

        # Weather
        self.weather_event_counter = 0

        self.weather_generator.event_counter = 0

        # Traffic
        self.traffic_event_counter = 0

        # Incidents
        max_incident = self._get_max_incident_number(
            self.historical_incidents
        )

        self.order_event_generator.incident_generator.incident_counter = (
            max_incident
        )

    # =========================================================
    # MAX INCIDENT
    # =========================================================

    @staticmethod
    def _get_max_incident_number(
        incidents
    ):

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
    # ADVANCE TIME
    # =========================================================

    def advance_time(
        self,
        minutes
    ):

        self.fecha_actual += (
            timedelta(
                minutes=minutes
            )
        )

        self.update_event_generators()

    # =========================================================
    # UPDATE GENERATORS
    # =========================================================

    def update_event_generators(self):

        if self.order_event_generator is not None:

            self.order_event_generator.fecha_actual = (
                self.fecha_actual
            )

        if self.gps_event_generator is not None:

            self.gps_event_generator.fecha_actual = (
                self.fecha_actual
            )

        if self.weather_generator is not None:

            self.weather_generator.fecha_actual = (
                self.fecha_actual
            )

        if self.traffic_api is not None:

            self.traffic_api.fecha_actual = (
                self.fecha_actual
            )

    # =========================================================
    # SIMULATION EVENTS
    # =========================================================

    def generate_simulation_events(self):

        order, incident = (
            self.create_order_event()
        )

        self.create_gps_events()

        return (
            self.order_events,
            self.gps_events,
            self.incidents
        )

    # =========================================================
    # UPDATE ORDER
    # =========================================================

    def update_order_status(
        self,
        order_id,
        new_status
    ):

        for order in self.orders:

            if order.id_order == order_id:

                order.set_status(
                    new_status,
                    self.fecha_actual
                )

                print(
                    f"Orden {order_id} "
                    f"actualizada: "
                    f"status={new_status}"
                )

                return order

        print(
            f"Orden {order_id} "
            f"no encontrada."
        )

        return None

    # =========================================================
    # ORDER EVENT
    # =========================================================

    def create_order_event(self):

        result = (
            self.order_event_generator
            .generate_event()
        )

        if result is None:

            return None, None

        order_event = (
            result["order_event"]
        )

        incident = (
            result["incident"]
        )

        if order_event is not None:

            self.order_events.append(
                order_event
            )

            self.produce_event(
                "order-events",
                order_event,
                "id_event"
            )

        if incident is not None:

            self.incidents.append(
                incident
            )

            incident_event = {

                "id_incident":
                    incident.id_incident,

                "id_order":
                    incident.id_order,

                "id_driver":
                    incident.id_driver,

                "incident_date":
                    incident.incident_date,

                "incident_reason":
                    incident.incident_reason,

                "observations":
                    incident.observations,

                "resolved":
                    incident.resolved,

                "resolution_date":
                    incident.resolution_date,

                "resolution_action":
                    incident.resolution_action
            }

            self.produce_event(
                "incident-events",
                incident_event,
                "id_incident"
            )

        return (
            order_event,
            incident
        )

    # =========================================================
    # GPS
    # =========================================================

    def create_gps_events(self):

        gps_events = (
            self.gps_event_generator
            .generate_event()
        )

        print(
            f"[GPS] Eventos generados: "
            f"{len(gps_events) if gps_events else 0}"
        )

        if not gps_events:

            return

        for key, gps_event in gps_events:

            self.gps_events.append(
                gps_event
            )

            self.produce_event(
                "gps-events",
                gps_event,
                "gps_event_id"
            )

    # =========================================================
    # WEATHER
    # =========================================================

    def generate_weather_event(self):

        events = (
            self.weather_generator
            .generate_events()
        )

        self.weather = events

        if not events:

            return []

        for event in events:

            self.weather_event_counter += 1

            # El generator tiene su propio ID.
            # Lo dejamos como identificador del evento.
            self.last_weather_event = event

            self.produce_event(
                "weather-events",
                event,
                "weather_event_id"
            )

        return events

    # =========================================================
    # TRAFFIC
    # =========================================================

    def generate_traffic_event(self):
        measurements = self.traffic_api.get_info()

        self.traffic = measurements

        for event in measurements:

            self.traffic_event_counter += 1

            self.last_traffic_event = event

            self.produce_event(
                "traffic-events",
                event,
                "idelem"
            )

        return measurements
    # =========================================================
    # PRODUCE
    # =========================================================

    def produce_event(
        self,
        topic,
        event,
        key_field
    ):

        if event is None:

            return

        key_event = str(
            event[key_field]
        )

        print(
            f"[Kafka] "
            f"topic={topic} "
            f"key={key_event}"
        )

        # IMPORTANTE:
        # NO json.dumps().
        #
        # AvroSerializer recibe el dict.

        self.kproducer.produce(
            topic,
            key_event,
            event
        )

    # =========================================================
    # SERIALIZATION HELPERS
    # =========================================================

    @staticmethod
    def _datetime_to_json(
        value
    ):

        if value is None:

            return None

        if isinstance(
            value,
            datetime
        ):

            return value.isoformat()

        return str(value)

    @staticmethod
    def _datetime_from_json(
        value
    ):

        if value is None:

            return None

        return datetime.fromisoformat(
            value
        )

    @staticmethod
    def _clean_value(
        value
    ):

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

            pickup_street=data["pickup_street"],

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
            data["id_driver_pickup"]
        )

        order.id_driver_delivery = (
            data["id_driver_delivery"]
        )

        order.id_route = (
            data["id_route"]
        )

        order.status_history = {

            status:
                self._datetime_from_json(
                    date
                )

            for status, date
            in data["status_history"].items()
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

        if data["location"] is not None:

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
                float(route.latitude),

            "longitude":
                float(route.longitude),

            "priority":
                int(route.priority)
        }

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
                bool(incident.resolved),

            "resolution_date":
                self._datetime_to_json(
                    incident.resolution_date
                ),

            "resolution_action":
                incident.resolution_action
        }

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

        return {
            str(driver_id): {

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

            for driver_id, state
            in self.gps_event_generator
                .driver_state.items()
        }

    # =========================================================
    # SAVE STATE
    # =========================================================

    def save_state(self):

        self.STATE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        state = {

            "version": 1,

            "fecha_actual":
                self._datetime_to_json(
                    self.fecha_actual
                ),

            "counters": {

                "order_event":
                    self.order_event_generator.event_counter,

                "gps_event":
                    self.gps_event_generator.event_counter,

                "weather_event":
                    self.weather_event_counter,

                "weather_generator_event":
                    self.weather_generator.event_counter,

                "traffic_event":
                    self.traffic_event_counter,

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
            f"[STATE] Estado guardado: "
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
        # FECHA
        # -----------------------------------------------------

        self.fecha_actual = (
            self._datetime_from_json(
                state["fecha_actual"]
            )
        )

        # -----------------------------------------------------
        # DRIVERS
        # -----------------------------------------------------

        self.drivers = [

            self.deserialize_driver(
                data
            )

            for data
            in state["drivers"]
        ]

        # -----------------------------------------------------
        # ROUTES
        # -----------------------------------------------------

        self.routes = [

            self.deserialize_route(
                data
            )

            for data
            in state["routes"]
        ]

        # -----------------------------------------------------
        # HISTORICAL ORDERS
        # -----------------------------------------------------

        self.historical_orders = [

            self.deserialize_order(
                data
            )

            for data
            in state[
                "historical_orders"
            ]
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
            in state[
                "historical_incidents"
            ]
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

        self.order_event_generator = (
            OrderEvents(
                self.orders,
                self.drivers,
                self.routes,
                self.fecha_actual
            )
        )

        self.gps_event_generator = (
            GPSEvents(
                self.orders,
                self.drivers,
                self.routes,
                self.fecha_actual
            )
        )

        self.weather_generator = (
            WeatherEventGenerator(
                self.fecha_actual
            )
        )

        self.traffic_api = TrafficApi(
            self.fecha_actual
        )

        # -----------------------------------------------------
        # RESTORE COUNTERS
        # -----------------------------------------------------

        counters = state[
            "counters"
        ]

        self.order_event_generator.event_counter = (
            counters["order_event"]
        )

        self.gps_event_generator.event_counter = (
            counters["gps_event"]
        )

        self.weather_event_counter = (
            counters["weather_event"]
        )

        self.weather_generator.event_counter = (
            counters[
                "weather_generator_event"
            ]
        )

        self.traffic_event_counter = (
            counters["traffic_event"]
        )

        self.order_event_generator \
            .incident_generator \
            .incident_counter = (
                counters["incident"]
            )

        # -----------------------------------------------------
        # RESTORE INCIDENTS INTO GENERATOR
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
        # RESTORE GPS STATE
        # -----------------------------------------------------

        self.gps_event_generator.driver_state = (
            state.get(
                "gps_driver_state",
                {}
            )
        )

        # -----------------------------------------------------
        # UPDATE REFERENCES
        # -----------------------------------------------------

        self.update_event_generators()

        print(
            "[STATE] Estado cargado correctamente."
        )

        print(
            f"[STATE] Fecha simulada: "
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
                "[STATE] No había estado que eliminar."
            )

    # =========================================================
    # WRITE FILE
    # =========================================================

    def write_file(
        self,
        path,
        dataframe
    ):

        path = str(path)

        suffix = (
            path.rsplit(
                ".",
                1
            )[-1]
            .lower()
        )

        if suffix == "parquet":

            dataframe = dataframe.copy()

            if "location" in dataframe.columns:

                dataframe["latitude"] = (
                    dataframe["location"]
                    .apply(
                        lambda location:
                        float(
                            location.latitude
                        )
                        if location is not None
                        else None
                    )
                )

                dataframe["longitude"] = (
                    dataframe["location"]
                    .apply(
                        lambda location:
                        float(
                            location.longitude
                        )
                        if location is not None
                        else None
                    )
                )

                dataframe = dataframe.drop(
                    columns=["location"]
                )

            dataframe.to_parquet(
                path,
                index=False
            )

        elif suffix == "csv":

            dataframe.to_csv(
                path,
                index=False
            )

        elif suffix == "xlsx":

            dataframe.to_excel(
                path,
                index=False
            )

        elif suffix == "json":

            dataframe.to_json(
                path,
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
    # GENERATE OUTPUT FILES
    # =========================================================

    def generate_files(self):

        # -----------------------------------------------------
        # HISTORICAL ORDERS
        # -----------------------------------------------------

        historical_records = [
            vars(order).copy()
            for order
            in self.historical_orders
        ]

        historical_df = pd.DataFrame(
            historical_records
        )

        historical_orders_file = (
            f"{GENERATED_HISTORICAL_ORDERS}"
            "/historical_orders.csv"
        )

        self.write_file(
            historical_orders_file,
            historical_df
        )

        self.client_onelk.load_file(
            LANDING_HISTORICAL_ORDERS,
            historical_orders_file
        )

        # -----------------------------------------------------
        # CURRENT ORDERS
        # -----------------------------------------------------

        orders_df = pd.DataFrame(
            [
                vars(order)
                for order
                in self.orders
            ]
        )

        orders_file = (
            f"{GENERATED_ORDERS}"
            "/orders.xlsx"
        )

        self.write_file(
            orders_file,
            orders_df
        )

        self.client_onelk.load_file(
            LANDING_ORDERS,
            orders_file
        )

        # -----------------------------------------------------
        # DRIVERS
        # -----------------------------------------------------

        drivers_df = pd.DataFrame(
            [
                vars(driver)
                for driver
                in self.drivers
            ]
        )

        drivers_file = (
            f"{GENERATED_DRIVERS}"
            "/drivers.parquet"
        )

        self.write_file(
            drivers_file,
            drivers_df
        )

        self.client_onelk.load_file(
            LANDING_DRIVERS,
            drivers_file
        )

        # -----------------------------------------------------
        # ROUTES
        # -----------------------------------------------------

        routes_df = pd.DataFrame(
            [
                vars(route)
                for route
                in self.routes
            ]
        )

        routes_file = (
            f"{GENERATED_ROUTES}"
            "/routes.json"
        )

        self.write_file(
            routes_file,
            routes_df
        )

        self.client_onelk.load_file(
            LANDING_ROUTES,
            routes_file
        )

        # -----------------------------------------------------
        # HISTORICAL INCIDENTS
        # -----------------------------------------------------

        historical_incidents_df = (
            pd.DataFrame(
                [
                    vars(incident)
                    for incident
                    in self.historical_incidents
                ]
            )
        )

        historical_incidents_file = (
            f"{GENERATED_HISTORICAL_INCIDENTS}"
            "/historical_incidents.json"
        )

        self.write_file(
            historical_incidents_file,
            historical_incidents_df
        )

        self.client_onelk.load_file(
            LANDING_HISTORICAL_INCIDENTS,
            historical_incidents_file
        )

    # =========================================================
    # REAL DATA FILES
    # =========================================================

    def generate_real_data_files(self):

        fecha = (
            self.fecha_actual.strftime(
                "%Y-%m-%d"
            )
        )

        if self.last_weather_event is not None:

            weather_path = (
                DATA_GENERATED
                / "weather_events"
                / fecha
            )

            weather_path.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(
                weather_path / "weather.json",
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    self.last_weather_event,
                    file,
                    ensure_ascii=False,
                    indent=4,
                    default=str
                )

        if self.last_traffic_event is not None:

            traffic_path = (
                DATA_GENERATED
                / "traffic_events"
                / fecha
            )

            traffic_path.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(
                traffic_path / "traffic.json",
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    self.last_traffic_event,
                    file,
                    ensure_ascii=False,
                    indent=4,
                    default=str
                )

        return (
            self.last_weather_event,
            self.last_traffic_event
        )

    # =========================================================
    # RUN
    # =========================================================
    def run(self, steps=1, realtime=False):

        if self.state_exists():

            self.load_state()

        else:

            print("[STATE] No existe checkpoint.")

            self.generate_initial_data()
            self.generate_files()
            self.save_state()

        for step in range(steps):

            print()
            print("=" * 70)
            print(f"STEP {step + 1}/{steps}")
            print(
                f"Hora simulada: "
                f"{self.fecha_actual.strftime('%Y-%m-%d %H:%M')}"
            )
            print("=" * 70)

            # Eventos de la hora actual
            self.create_order_event()
            self.create_gps_events()
            self.generate_weather_event()
            self.generate_traffic_event()

            # Archivos
            self.generate_files()
            self.generate_real_data_files()

            # Avanzar reloj
            self.advance_time(60)

            # Guardar checkpoint ya avanzado
            self.save_state()

            if realtime:
                time.sleep(60)

        self.kproducer.flush()

        print()
        print("Simulación finalizada.")
        print(f"Estado actual: {self.fecha_actual}")