from src.generator.address_generator import AddressGenerator
from src.generator.drivers_generator import DriverGenerator
from src.generator.orders_generator import OrderGenerator
from src.generator.historical_generator import OrderHistoricalGenerator
from src.generator.order_event import OrderEvents
from src.generator.route_generator import RouteGenerator
from src.generator.gps_events import GPSEvents

from src.generator.weather_event import WeatherEventGenerator
from src.apis.weather_api import WeatherApi
from src.apis.traffic_api import TrafficApi

import json


from src.config.setup import DATA_ADDRESS
from src.config.setup import LANDING_ROOT
import pandas as pd

class Simulator:

    def __init__(self, fecha_actual):
        #self.spark = pyspark.sql.SparkSession.builder.appName("Simulator").getOrCreate()
        self.drivers=None
        self.orders=None
        self.routes=None
        self.historical_orders=None
        self.gps_events=None
        self.order_events=None
        self.traffic=None
        self.weather=None
        self.fecha_actual = fecha_actual
   
    def generate_initial_data(self):

        # 1. Direcciones
        address_spain = AddressGenerator(DATA_ADDRESS / "spain.csv").get_address_df()
        address_madrid = AddressGenerator(DATA_ADDRESS / "spain-comunidad-de-madrid.csv").get_address_df()
       
        # 2. Repartidores
        Drivers_generator = DriverGenerator([], address_madrid)
        self.drivers = Drivers_generator.create_drivers(270)  # 5 drivers por cada uno de los 54 distritos de Madrid

        # 3. Rutas
        route_generator = RouteGenerator(drivers=self.drivers, addresses=address_madrid,fecha_actual=self.fecha_actual)
        self.routes = route_generator.create_routes()  # Crea rutas para cada repartidor en función de su zona y las calles asignadas
        
        # 3. Histórico de pedidos
        
        historical_generator = OrderHistoricalGenerator(drivers=self.drivers,
                                         address_madrid=address_madrid,
                                         address_spain=address_spain,fecha_actual=self.fecha_actual
                                         )
        
        # Creamos histórico de 10 días de 1000 registros cada uno
        self.historical_orders = historical_generator.create_historical(10000)
        
        # 4. Pedidos para repartir hoy
        order_generator = OrderGenerator(historical_orders= self.historical_orders,fecha_actual=self.fecha_actual)

        # Crear pedidos
        self.orders = order_generator.get_orders_for_today()
        
        # GPS
        self.gps_events = GPSEvents(self.drivers, self.fecha_actual)
        
        #eventos pedidos
        self.order_events = OrderEvents(self.orders,self.drivers,self.routes,self.fecha_actual)
        
        
        weather_generator = WeatherEventGenerator()
        self.weather =   weather_generator.generate_events()

        traffic_api = TrafficApi()
        self.traffic = traffic_api.get_info()

        
        return self.historical_orders, self.orders, self.drivers, self.routes
    
    
    def create_order_events(self, num_events):

        event_generator = OrderEvents(self.orders,self.drivers,self.routes,self.fecha_actual)

        events = []

        for _ in range(num_events):

            event = event_generator.generate_event()

            if event is not None:
                events.append(event)

        return events
    
    
    def create_gps_events(self, num_events):
    
            event_generator = GPSEvents(self.drivers, self.fecha_actual)
    
            events = []
    
            for _ in range(num_events):
    
                event = event_generator.send_gps()
    
                if event is not None:
                    events.append(event)
    
            return events
            
            
    def generate_files(self, historical_orders, orders, drivers, routes):
        historical_path = LANDING_ROOT / "historical_orders"
        orders_path = LANDING_ROOT / "orders"
        drivers_path = LANDING_ROOT / "drivers"
        routes_path = LANDING_ROOT / "routes"

        historical_path.mkdir(parents=True, exist_ok=True)
        orders_path.mkdir(parents=True, exist_ok=True)
        drivers_path.mkdir(parents=True, exist_ok=True)
        routes_path.mkdir(parents=True, exist_ok=True)

        historical_df = pd.DataFrame([vars(order) for order in historical_orders])
        historical_df.to_csv(historical_path / "historical_orders.csv", index=False, encoding="utf-8-sig")

        orders_df = pd.DataFrame([vars(order) for order in orders])
        orders_df.to_excel( orders_path / "orders.xlsx",index=False )

        drivers_df = pd.DataFrame([vars(driver) for driver in drivers])
        drivers_df.to_parquet( drivers_path / "drivers.parquet",index=False)

        routes_df = pd.DataFrame([vars(route) for route in routes])
        routes_df.to_json(routes_path/ "routes.json", orient="records", force_ascii=False)
                
                
    def generate_simulation_events(self, num_order_events, num_gps_events):
        fecha = self.fecha_actual.strftime("%Y-%m-%d")

        self.gps_events = self.create_gps_events(num_gps_events)
        self.order_events = self.create_order_events(num_order_events)
        gps_events_path = LANDING_ROOT / "gps_events" / fecha
        order_events_path = LANDING_ROOT / "order_events" / fecha


        gps_events_path.mkdir(parents=True, exist_ok=True)
        order_events_path.mkdir(parents=True, exist_ok=True)

        #self.gps_events.to_json(gps_events_path / "gps_events.json", orient="records",encoding="utf-8" )

        #self.order_events.to_json(order_events_path / "order_events.json", orient="records", encoding="utf-8")
        

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
                default=str
            )

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
                default=str
            )
            return self.order_events, self.gps_events

    def generate_real_data_files(self):
        fecha = self.fecha_actual.strftime("%Y-%m-%d")

        weather_path = LANDING_ROOT / "weather_events" / fecha
        traffic_path = LANDING_ROOT / "traffic_events" / fecha

        weather_path.mkdir(parents=True, exist_ok=True)
        traffic_path.mkdir(parents=True, exist_ok=True)

        with open( weather_path / "weather.json", "w", encoding="utf-8" ) as file:
            json.dump( self.weather, file, ensure_ascii=False, indent=4, default=str )

        with open( traffic_path / "traffic.json", "w", encoding="utf-8" ) as file:
            json.dump( self.traffic, file, ensure_ascii=False, indent=4, default=str )

        return self.weather, self.traffic
        
            
            
        
            
            
            