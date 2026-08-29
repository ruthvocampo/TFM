from pyspark.sql import Row
from datetime import datetime, timedelta
import random
import pandas as pd
from src.config.setup import LANDING_ROOT
from src.objects.driver import Driver


class DriverGenerator:
    def __init__(self, spark, drivers):
        self.spark = spark
        self.drivers = drivers

    def create_drivers(self):
        for n in range(1,15):
            driver = Driver(
                id_driver = f"DRV{n:03d}",
                name = f"Driver {n:03d}",
                license_number = f"LIC-{n:04d}",
                vehicle_type = random.choice(["car", "van", "truck"]),
                available = random.choice([True, False]),
                zone = random.randint(28001,28054),
            )
            self.drivers.append(driver)
            
    
        drivers_df = self.spark.createDataFrame(self.drivers)
        drivers_df.coalesce(1).write.mode("overwrite").parquet(f"{LANDING_ROOT}/drivers")
        return drivers_df