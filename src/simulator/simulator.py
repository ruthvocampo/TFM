from src.generator.address_generator import AddressGenerator
from src.generator.drivers_generator import DriverGenerator
from src.generator.orders_generator import OrderGenerator
from src.generator.history_generator import OrderHistoricalGenerator
from src.generator.order_event import OrderEvents
from src.generator.route_generator import RouteGenerator
from src.generator.gps_events import GPSEvents
from src.config.setup import DATA_ADDRESS

import pyspark

class Simulator:

    def __init__(self, ):
        #self.spark = pyspark.sql.SparkSession.builder.appName("Simulator").getOrCreate()
        self.drivers=None
        self.orders=None
        self.routes=None
 

    def generate_initial_data(self):

        # 1. Direcciones
        address_spain = AddressGenerator(DATA_ADDRESS / "spain.csv").get_address_df()
        address_madrid = AddressGenerator(DATA_ADDRESS / "spain-comunidad-de-madrid.csv").get_address_df()
        print(address_madrid.head(5))
        # 2. Repartidores
        self.drivers = DriverGenerator([], address_madrid).create_drivers(50)

        # 3. Rutas
        self.routes = RouteGenerator(self.drivers, address_madrid).create_routes()
        
        # 4. Histórico de pedidos
        
        historical = OrderHistoricalGenerator(self.drivers)
        
        # Creamos histórico de 10 días de 1000 registros cada uno
        historical.create_historical(10,1000)
        
        # 5. Pedidos
        order_generator = OrderGenerator(drivers=self.drivers,
                                         address_madrid=address_madrid,
                                         address_spain=address_spain)

        # Crear pedidos
        self.orders = order_generator.create_orders()
        
        
        return self.orders, self.drivers, self.routes
    
    
    def create_order_events(self, num_events):

        event_generator = OrderEvents(self.orders,self.routes)

        events = []

        for _ in range(num_events):

            event = event_generator.generate_event()

            if event is not None:
                events.append(event)

        return events
    
    
    def create_gps_events(self, num_events):
    
            event_generator = GPSEvents(self.drivers)
    
            events = []
    
            for _ in range(num_events):
    
                event = event_generator.send_gps()
    
                if event is not None:
                    events.append(event)
    
            return events
            
            

        
        
    
        
        
        