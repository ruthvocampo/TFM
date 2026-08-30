from src.generator.address_generator import AddressGenerator
from src.generator.drivers_generator import DriverGenerator
from src.generator.orders_generator import OrderGenerator
from src.generator.history_generator import OrderHistoricalGenerator
from src.config.setup import DATA_ADDRESS
import pyspark

class Simulator:

    def __init__(self, ):
        self.spark = pyspark.sql.SparkSession.builder.appName("Simulator").getOrCreate()

    def generate_initial_data(self):

        # 1. Direcciones
        address_spain = AddressGenerator(DATA_ADDRESS / "spain.csv").get_address_df()
        address_madrid = AddressGenerator(DATA_ADDRESS / "spain-comunidad-de-madrid.csv").get_address_df()

        # 2. Repartidores
        drivers = DriverGenerator(drivers=[]).create_drivers(50)

        # 3. Histórico de pedidos
        
        historical = OrderHistoricalGenerator(drivers)
        
        # Creamos histórico de 10 días de 1000 registros cada uno
        historical.create_historical(10,1000)
        
        # 4. Pedidos
        order_generator = OrderGenerator(drivers=drivers,
                                         address_madrid=address_madrid,
                                         address_spain=address_spain)

        # Crear pedidos
        orders = order_generator.create_orders()

        return orders, drivers  