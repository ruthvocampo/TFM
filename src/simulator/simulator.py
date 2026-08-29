from src.generator.address_generator import AddressGenerator
from src.generator.drivers_generator import DriverGenerator
from src.generator.orders_generator import OrderGenerator
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
        drivers = DriversGenerator(self.spark, drivers=[])

        # 3. Pedidos
        order_generator = OrderGenerator(self.spark,drivers=drivers,
                address_madrid=address_madrid,address_spain=address_spain)

        # 4. Crear pedidos
        orders = order_generator.create_orders()

        return orders, drivers