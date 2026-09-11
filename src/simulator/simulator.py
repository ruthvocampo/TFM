from datetime import timedelta, datetime, timezone
import json
import pandas as pd
import time
from collections import Counter

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

from src.generator.weather_event import WeatherEventGenerator

from src.apis.weather_api import WeatherApi
from src.apis.traffic_api import TrafficApi

from src.kafka.producer import KafkaProducer

from src.onelake_client import OnelakeClient

from src.setup import *




class Simulator:

    SPAIN_FILE="data/reference/spain.csv"
    MADRID_FILE="data/reference/213605-4-callejero-oficial-madrid-csv.csv"

    def __init__(self, fecha_actual):

        # ========================================================
        # FECHA DE SIMULACIÓN
        # ========================================================

        self.fecha_actual = fecha_actual

        # ========================================================
        # ONELAKE
        # ========================================================

        self.client_onelk = OnelakeClient()

        # ========================================================
        # KAFKA
        # ========================================================

        self.kproducer = KafkaProducer()

        self.kproducer.create_topics()

        # ========================================================
        # DATOS BASE
        # ========================================================

        self.drivers = None

        self.orders = None

        self.routes = None

        self.historical_orders = None

        # ========================================================
        # EVENTOS
        # ========================================================

        self.gps_events = []

        self.order_events = []

        self.incidents = []

        self.historical_incidents = []

        # ========================================================
        # WEATHER
        # ========================================================

        self.weather = []

        self.weather_generator = None

        self.weather_event_counter = 0

        self.last_weather_event = None

        # ========================================================
        # TRAFFIC
        # ========================================================

        self.traffic = []

        self.traffic_api = None

        self.traffic_event_counter = 0

        self.last_traffic_event = None

        # ========================================================
        # GENERADORES
        # ========================================================

        self.order_event_generator = None

        self.gps_event_generator = None

    # ============================================================
    # DATOS INICIALES
    # ============================================================

    def generate_initial_data(self):

        # ========================================================
        # ADDRESSES
        # ========================================================
        #
        # IMPORTANTE:
        # Se mantiene la forma de trabajar con tu
        # AddressGenerator.
        #
        # Sustituye SPAIN_FILE y MADRID_FILE únicamente si en tu
        # setup.py tienen otro nombre.
        # ========================================================

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

        # ========================================================
        # DRIVERS
        # ========================================================

        driver_generator = DriverGenerator(
            [],
            addresses_madrid
        )

        self.drivers = (
            driver_generator
            .create_drivers(270)
        )

        # ========================================================
        # ROUTES
        # ========================================================

        route_generator = RouteGenerator(
            self.drivers,
            addresses_madrid,self.fecha_actual
        )

        self.routes = (
            route_generator
            .create_routes()
        )

        # ========================================================
        # HISTORICAL ORDERS
        # ========================================================

        historical_generator = OrderHistoricalGenerator(self.drivers, addresses_madrid, addresses_spain,self.fecha_actual)

        self.historical_orders = (
            historical_generator
            .create_historical(6000)
        )

        # ========================================================
        # HISTORICAL INCIDENTS
        # ========================================================

        historical_incident_generator = (
            IncidentHistoricalGenerator(self.historical_orders )
        )

        self.historical_incidents = (
            historical_incident_generator
            .create_historical_incidents()
        )

        # ========================================================
        # ORDERS
        # ========================================================

        order_generator = OrderGenerator(self.historical_orders,self.fecha_actual)

        self.orders = order_generator.get_orders_for_today()

        # ========================================================
        # ORDER EVENTS
        # ========================================================

        self.order_event_generator = OrderEvents(
            self.orders,
            self.drivers,
            self.routes,
            self.fecha_actual
        )

        # ========================================================
        # GPS EVENTS
        # ========================================================

        self.gps_event_generator = GPSEvents(
            self.orders,
            self.drivers,
            self.routes,
            self.fecha_actual
        )

        # ========================================================
        # WEATHER
        # ========================================================

        self.weather_generator = (
            WeatherEventGenerator(self.fecha_actual)
        )

        self.weather = []

        # ========================================================
        # TRAFFIC
        # ========================================================

        self.traffic_api = TrafficApi(self.fecha_actual)

        self.traffic = []

    # ============================================================
    # AVANZAR TIEMPO
    # ============================================================

    def advance_time(
        self,
        minutes
    ):

        self.fecha_actual += timedelta(
            minutes=minutes
        )

        self.update_event_generators()

    # ============================================================
    # ACTUALIZAR GENERADORES
    # ============================================================

    def update_event_generators(self):

        if self.order_event_generator is not None:

            self.order_event_generator.fecha_actual = (
                self.fecha_actual
            )

        if self.gps_event_generator is not None:

            self.gps_event_generator.fecha_actual = (
                self.fecha_actual
            )

    # ============================================================
    # GENERAR EVENTOS DE SIMULACIÓN
    # ============================================================

    def generate_simulation_events(self):

        order,incident= self.create_order_event()
        

        self.create_gps_events()

        return (
            self.order_events,
            self.gps_events,
            self.incidents
        )

    def update_order_status(self, order_id, new_status):

        for order in self.orders:

            if order.id_order == order_id:

                order.status = new_status
                order.status_modified_date = self.fecha_actual

                print(
                    f"Orden {order_id} actualizada: "
                    f"status={new_status}"
                )

                return order

        print(f"Orden {order_id} no encontrada.")
        return None
    
# ============================================================
# GUARDAR DATAFRAME
# ============================================================

    def write_file(self, path, dataframe):
        """
        Write a DataFrame using the format implied by its file extension.
        """

        path = str(path)

        suffix = (
            path
            .rsplit(".", 1)[-1]
            .lower()
        )

        # ---------------------------------------------------------
        # PARQUET
        # ---------------------------------------------------------

        if suffix == "parquet":

            dataframe = dataframe.copy()

            # -----------------------------------------------------
            # LOCATION -> LATITUDE / LONGITUDE
            #
            # Location es un objeto Python y PyArrow no puede
            # serializarlo directamente.
            # -----------------------------------------------------

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

                # Eliminamos el objeto Location porque no puede
                # ser almacenado directamente por PyArrow.
                dataframe = dataframe.drop(
                    columns=["location"]
                )

            dataframe.to_parquet(
                path,
                index=False
            )

        # ---------------------------------------------------------
        # CSV
        # ---------------------------------------------------------

        elif suffix == "csv":

            dataframe.to_csv(
                path,
                index=False
            )

        # ---------------------------------------------------------
        # XLSX
        # ---------------------------------------------------------

        elif suffix == "xlsx":

            dataframe.to_excel(
                path,
                index=False
            )

        # ---------------------------------------------------------
        # JSON
        # ---------------------------------------------------------

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
                f"Unsupported file format: {suffix}"
            )
    # ============================================================
    # GUARDAR DATOS INICIALES
    # ============================================================

    def generate_files(self):

        # ========================================================
        # HISTÓRICO DE ORDERS
        # ========================================================

        historical_records = []

        for order in self.historical_orders:

            record = vars(order).copy()

            historical_records.append(
                record
            )

        historical_df = pd.DataFrame(
            historical_records
        )

        historical_orders_file = (
            f"{GENERATED_HISTORICAL_ORDERS}/"
            "historical_orders.csv"
        )

        self.write_file(
            historical_orders_file,
            historical_df
        )

        # SUBIR A ONELAKE

        self.client_onelk.load_file(
            LANDING_HISTORICAL_ORDERS,
            historical_orders_file
        )

        # ========================================================
        # ORDERS ACTUALES
        # ========================================================

        orders_df = pd.DataFrame(
            [
                vars(order)
                for order in self.orders
            ]
        )

        orders_file = (
            f"{GENERATED_ORDERS}/orders.xlsx"
        )

        self.write_file(
            orders_file,
            orders_df
        )

        # SUBIR A ONELAKE

        self.client_onelk.load_file(
            LANDING_ORDERS,
            orders_file
        )

        # ========================================================
        # DRIVERS
        # ========================================================

        drivers_df = pd.DataFrame(
            [
                vars(driver)
                for driver in self.drivers
            ]
        )

        drivers_file = (
            f"{GENERATED_DRIVERS}/drivers.parquet"
        )

        self.write_file(
            drivers_file,
            drivers_df
        )

        # SUBIR A ONELAKE

        self.client_onelk.load_file(
            LANDING_DRIVERS,
            drivers_file
        )

        # ========================================================
        # ROUTES
        # ========================================================

        routes_df = pd.DataFrame(
            [
                vars(route)
                for route in self.routes
            ]
        )

        routes_file = (
            f"{GENERATED_ROUTES}/routes.json"
        )

        self.write_file(
            routes_file,
            routes_df
        )

        # SUBIR A ONELAKE

        self.client_onelk.load_file(
            LANDING_ROUTES,
            routes_file
        )

        # ========================================================
        # HISTÓRICO DE INCIDENCIAS
        # ========================================================

        historical_incidents_df = pd.DataFrame(
            [
                vars(incident)
                for incident in self.historical_incidents
            ]
        )

        historical_incidents_file = (
            f"{GENERATED_HISTORICAL_INCIDENTS}/"
            "historical_incidents.json"
        )

        self.write_file(
            historical_incidents_file,
            historical_incidents_df
        )

        # SUBIR A ONELAKE

        self.client_onelk.load_file(
            LANDING_HISTORICAL_INCIDENTS,
            historical_incidents_file
        )
        
    # ============================================================
    # ORDER EVENT
    # ============================================================
    def create_order_event(self):

        result = (
            self.order_event_generator
            .generate_event()
        )

        # ========================================================
        # NO HAY EVENTO
        # ========================================================

        if result is None:
            return None, None

        order_event = result["order_event"]
        incident = result["incident"]

        # ========================================================
        # ORDER EVENT
        # ========================================================

        if order_event is not None:

            self.order_events.append(
                order_event
            )

            self.produce_event(
                "order-events",
                order_event,
                "id_event"
            )

        # ========================================================
        # INCIDENT EVENT
        # ========================================================

        if incident is not None:

            self.incidents.append(
                incident
            )

            incident_event = {
                "id_incident": incident.id_incident,
                "id_order": incident.id_order,
                "id_driver": incident.id_driver,
                "incident_date": incident.incident_date,
                "incident_reason": incident.incident_reason,
                "observations": incident.observations,
                "resolved": incident.resolved,
                "resolution_date": incident.resolution_date,
                "resolution_action": incident.resolution_action
            }

            self.produce_event(
                "incident-events",
                incident_event,
                "id_incident"
            )

        # ========================================================
        # SIEMPRE DEVOLVEMOS DOS VALORES
        # ========================================================

        return order_event, incident


    # ============================================================
    # GPS
    # ============================================================
    def create_gps_events(self):

        gps_events = (
            self.gps_event_generator.generate_event()
        )

        print(
            f"[GPS] Eventos generados: "
            f"{len(gps_events) if gps_events else 0}"
        )

        if not gps_events:
            return

        for key, gps_event in gps_events:

            print(
                f"[GPS] Publicando evento: {gps_event}"
            )

            self.produce_event(
                "gps-events",
                gps_event,
                "gps_event_id"
            )


    # ============================================================
    # WEATHER
    # ============================================================

    def generate_weather_event(self):

        self.weather = (
            self.weather_generator
            .generate_events()
        )

        self.weather_event_counter += 1

        weather_event = {

            "weather_event_id":
                self.weather_event_counter,

            "timestamp":
                self.fecha_actual.isoformat(),

            "measurements":
                self.weather
        }

        self.last_weather_event = (
            weather_event
        )

        self.produce_event(
            "weather-events",
            weather_event,
            "weather_event_id"
        )

        return weather_event

    # ============================================================
    # TRAFFIC
    # ============================================================

    def generate_traffic_event(self):

        self.traffic = (
            self.traffic_api
            .get_info()
        )

        self.traffic_event_counter += 1

        traffic_event = {

            "traffic_event_id":
                self.traffic_event_counter,

            "timestamp":
                self.fecha_actual.isoformat(),

            "measurements":
                self.traffic
        }

        self.last_traffic_event = (
            traffic_event
        )

        self.produce_event(
            "traffic-events",
            traffic_event,
            "traffic_event_id"
        )

        return traffic_event

    # ============================================================
    # KAFKA
    # ============================================================

    def produce_event(
        self,
        topic,
        event,
        key_field
    ):

        if event is None:

            return

        # ========================================================
        # INGESTION TIME
        # ========================================================
        print("EVENT:", event)
        print("TYPE:", type(event))
        event["ingestion_time"] = self.fecha_actual.isoformat()
        

        # ========================================================
        # KEY
        # ========================================================

        key_event = str(
            event[key_field]
        )

        # ========================================================
        # JSON
        # ========================================================

        value_event = json.dumps(
            event,
            default=str
        )

        # ========================================================
        # DEBUG SIZE
        # ========================================================

        size_mb = (
            len(
                value_event.encode(
                    "utf-8"
                )
            )
            /
            (1024 * 1024)
        )

        print(
            f"[Kafka] topic={topic} "
            f"key={key_event} "
            f"size={size_mb:.2f} MB"
        )

        # ========================================================
        # PRODUCIR
        # ========================================================

        self.kproducer.produce(
            topic,
            key_event,
            value_event
        )

    
    # ============================================================
    # GUARDAR DATOS REALES
    # ============================================================

    def generate_real_data_files(self):

        fecha = (
            self.fecha_actual
            .strftime("%Y-%m-%d")
        )

        # ========================================================
        # WEATHER
        # ========================================================

        if self.last_weather_event is not None:

            weather_path = (
                DATA_GENERATED
                /
                "weather_events"
                /
                fecha
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

        # ========================================================
        # TRAFFIC
        # ========================================================

        if self.last_traffic_event is not None:

            traffic_path = (
                DATA_GENERATED
                /
                "traffic_events"
                /
                fecha
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

    # ============================================================
    # RUN
    # ============================================================

    def run(self):

        # ========================================================
        # 1. DATOS INICIALES
        # ========================================================

        self.generate_initial_data()

        self.generate_files()

        # ========================================================
        # 2. HORA FINAL
        # ========================================================

        end_time = (
            self.fecha_actual
            .replace(
                hour=22,
                minute=0,
                second=0,
                microsecond=0
            )
        )

        # ========================================================
        # 3. SIMULACIÓN
        # ========================================================

        while self.fecha_actual <= end_time:

            print(
                f"Hora simulada: "
                f"{self.fecha_actual.strftime('%Y-%m-%d %H:%M')}"
            )

            # ----------------------------------------------------
            # PEDIDOS + GPS
            # ----------------------------------------------------

            self.generate_simulation_events()

            # ----------------------------------------------------
            # WEATHER
            # ----------------------------------------------------

            self.generate_weather_event()

            # ----------------------------------------------------
            # TRAFFIC
            # ----------------------------------------------------

            #self.generate_traffic_event()

            # ----------------------------------------------------
            # ESPERAR
            # ----------------------------------------------------

            time.sleep(60)

            # ----------------------------------------------------
            # AVANZAR 60 MINUTOS
            # ----------------------------------------------------

            self.advance_time(60)

    

        print(
            "Simulación finalizada."
        )