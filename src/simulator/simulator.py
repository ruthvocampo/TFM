from datetime import timedelta
import json
import pandas as pd
import time

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

from src.config.setup import DATA_ADDRESS
from src.config.setup import *
from src.simulator.azure_storage import write_file

class Simulator:

    def __init__(self, fecha_actual):

        
        # DATOS
        

        self.drivers = None
        self.orders = None
        self.routes = None
        self.historical_orders = None

        
        # EVENTOS
        

        self.gps_events = []
        self.order_events = []
        self.incidents = []

        
        # HISTÓRICO DE INCIDENCIAS
        

        self.historical_incidents = []

        
        # DATOS REALES
        

        self.traffic = None
        self.weather = None

        
        # HORA DE SIMULACIÓN
        

        self.fecha_actual = fecha_actual

        
        # GENERADORES DE EVENTOS
        # Se crean una sola vez para mantener su estado
        

        self.order_event_generator = None
        self.gps_event_generator = None

    
    # GENERAR DATOS INICIALES

    def generate_initial_data(self):

        
        # 1. DIRECCIONES
        
        spain_path = DATA_ADDRESS / "spain.csv"
        madrid_path = DATA_ADDRESS / "213605-4-callejero-oficial-madrid-csv.csv"
        
        addresses = AddressGenerator(spain_path,madrid_path)
                
        address_spain = addresses.get_address_spain_df()
    
        address_madrid = addresses.get_address_madrid_df()

        
        # 2. REPARTIDORES
        

        driver_generator = DriverGenerator(
            [],
            address_madrid
        )

        self.drivers = driver_generator.create_drivers(270)

        
        # 3. RUTAS
        

        route_generator = RouteGenerator(
            drivers=self.drivers,
            addresses=address_madrid,
            fecha_actual=self.fecha_actual
        )

        self.routes = route_generator.create_routes()

        
        # 4. HISTÓRICO DE PEDIDOS
        

        historical_generator = OrderHistoricalGenerator(
            drivers=self.drivers,
            address_madrid=address_madrid,
            address_spain=address_spain,
            fecha_actual=self.fecha_actual
        )

        self.historical_orders = (
            historical_generator.create_historical(
                10000,
                min_pending_today=100
            )
        )

        
        # 5. HISTÓRICO DE INCIDENCIAS
        

        incident_historical_generator = (
            IncidentHistoricalGenerator(
                historical_orders=self.historical_orders
            )
        )

        self.historical_incidents = (
            incident_historical_generator
            .create_historical_incidents()
        )

        print(
            f"Generadas "
            f"{len(self.historical_incidents)} "
            f"incidencias históricas."
        )

        
        # 6. PEDIDOS PARA LA SIMULACIÓN
        

        order_generator = OrderGenerator(
            historical_orders=self.historical_orders,
            fecha_actual=self.fecha_actual
        )

        self.orders = (
            order_generator.get_orders_for_today()
        )

        
        # 7. GENERADOR DE ORDER EVENTS
        

        self.order_event_generator = OrderEvents(
            self.orders,
            self.drivers,
            self.routes,
            self.fecha_actual
        )

        
        # 8. GENERADOR DE GPS EVENTS
        

        self.gps_event_generator = GPSEvents(
            self.drivers,
            self.fecha_actual
        )

        
        # 9. WEATHER
        

        weather_generator = WeatherEventGenerator()

        self.weather = (
            weather_generator.generate_events()
        )

        
        # 10. TRAFFIC
        

        traffic_api = TrafficApi()

        self.traffic = traffic_api.get_info()

        return (
            self.historical_orders,
            self.orders,
            self.drivers,
            self.routes
        )

    # GENERAR ORDER EVENTS
    def create_order_events(self):

        if self.order_event_generator is None:

            self.order_event_generator = OrderEvents(
                self.orders,
                self.drivers,
                self.routes,
                self.fecha_actual
            )

        events = (
            self.order_event_generator
            .generate_available_events()
        )

        self.order_events.extend(events)

        # Recuperar incidencias
        self.incidents = (
            self.order_event_generator
            .get_incidents()
        )

        return events


    # GENERAR GPS EVENTS

    def create_gps_events(self):

        if self.gps_event_generator is None:

            self.gps_event_generator = GPSEvents(
                self.drivers,
                self.fecha_actual
            )

        events = (
            self.gps_event_generator
            .generate_available_events()
        )

        self.gps_events.extend(events)

        return events


    # GENERAR Y GUARDAR EVENTOS DE SIMULACIÓN


    def generate_simulation_events(self):

        fecha = self.fecha_actual.strftime("%Y-%m-%d")
        
        hora= f"{self.fecha_actual.hour:02d}"
        print(hora)

        
        # GENERAR
        

        self.order_events = self.create_order_events()

        self.gps_events = self.create_gps_events()

        
        # RUTAS
        

        gps_events_path = (LANDING_ROOT/ "gps_events")

        order_events_path = (LANDING_ROOT/ "order_events")

        incident_events_path = (LANDING_ROOT/ "incidents_events")

        
        # DIRECTORIOS
        

        gps_events_path.mkdir(
            parents=True,
            exist_ok=True
        )

        order_events_path.mkdir(
            parents=True,
            exist_ok=True
        )

        incident_events_path.mkdir(
            parents=True,
            exist_ok=True
        )

        
        # GPS EVENTS
        

        with open(
            gps_events_path / "gps_events.json",
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.gps_events,
                file,
                ensure_ascii=False,
                indent=4,
                default=lambda obj: obj.isoformat()
            )

        
        # ORDER EVENTS
        

        with open(
            order_events_path / "order_events.json",
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.order_events,
                file,
                ensure_ascii=False,
                indent=4,
                default=lambda obj: obj.isoformat()
            )

        
        # INCIDENTS
        

        with open(
            incident_events_path / "incident_events.json",
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                [
                    vars(incident)
                    for incident in self.incidents
                ],
                file,
                ensure_ascii=False,
                indent=4,
                default=lambda obj: obj.isoformat()
            )

        return (
            self.order_events,
            self.gps_events,
            self.incidents
        )


    # GUARDAR DATOS INICIALES


    def generate_files(self):
        
        # HISTÓRICO DE ORDERS
        #
        # Aquí NO aplanamos status_history.
        # Se conserva para Silver.
        

        historical_records = []

        for order in self.historical_orders:

            record = vars(order).copy()

            historical_records.append(record)

        historical_df = pd.DataFrame(
            historical_records
        )

        write_file(LANDING_HISTORICAL_ORDERS /"historical_orders.csv",historical_df)

        
        # ORDERS ACTUALES
        orders_df = pd.DataFrame(
            [
                vars(order)
                for order in self.orders
            ]
        )

        write_file( LANDING_ORDERS /"orders.xlsx",orders_df)

        
        # DRIVERS
        drivers_df = pd.DataFrame(
            [
                vars(driver)
                for driver in self.drivers
            ]
        )

        write_file(LANDING_DRIVERS / "drivers.parquet",drivers_df)

        
        # ROUTES
        

        routes_df = pd.DataFrame(
            [
                vars(route)
                for route in self.routes
            ]
        )

        write_file(LANDING_ROUTES /"routes.json",routes_df)


        
        # HISTÓRICO DE INCIDENCIAS
        historical_incidents_df = pd.DataFrame([
                vars(incident)
                for incident
                in self.historical_incidents
            ])

        write_file(LANDING_HISTORICAL_INCIDENTS/"historical_incidents.json",historical_incidents_df)


    # DATOS REALES
    def generate_real_data_files(self):

        fecha = self.fecha_actual.strftime("%Y-%m-%d")

        weather_path = (
            LANDING_ROOT
            / "weather_events"
            / fecha
        )

        traffic_path = (
            LANDING_ROOT
            / "traffic_events"
            / fecha
        )

        weather_path.mkdir(
            parents=True,
            exist_ok=True
        )

        traffic_path.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
                weather_path / "weather.json",
                "w",
                encoding="utf-8"
            ) as file:

            json.dump(
                self.weather,
                file,
                ensure_ascii=False,
                indent=4,
                default=lambda obj: obj.isoformat()
            )

        with open(
            traffic_path / "traffic.json",
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.traffic,
                file,
                ensure_ascii=False,
                indent=4,
                default=lambda obj: obj.isoformat()
            )
        return (
            self.weather,
            self.traffic
        )


    # AVANZAR TIEMPO DE SIMULACIÓN


    def advance_time(self, minutes):

        self.fecha_actual += timedelta(
            minutes=minutes
        )

        # Actualizar la hora que utilizan los generadores
        if self.order_event_generator is not None:

            self.order_event_generator.fecha_actual = (
                self.fecha_actual
            )

        if self.gps_event_generator is not None:

            self.gps_event_generator.fecha_actual = (
                self.fecha_actual
            )
            
    def run(self):

        # =========================================
        # DATOS INICIALES
        # =========================================

        self.generate_initial_data()

        self.generate_files()

        # =========================================
        # SIMULACIÓN
        # =========================================

        end_time = self.fecha_actual.replace(
            hour=22,
            minute=0,
            second=0,
            microsecond=0
        )

        while self.fecha_actual <= end_time:

            print(
                f"Hora simulada: "
                f"{self.fecha_actual.strftime('%Y-%m-%d %H:%M')}"
            )

            self.generate_simulation_events()
            time.sleep(60)
            
            self.advance_time(60)

        # =========================================
        # DATOS REALES
        # =========================================

        self.generate_real_data_files()

        print("Simulación finalizada.")