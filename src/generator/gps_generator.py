from pyspark.sql import Row
from datetime import datetime, timedelta
import random
import pandas as pd
from config.setup import LANDING_ROOT

class GPSGenerator:
    def __init__(self, spark, LANDING_ROOT,drivers):
        self.spark = spark
        self.LANDING_ROOT = LANDING_ROOT
        self.gps = []
        self.drivers = drivers

    def create_gps(self):
        
        for n in range(1, 15):
            localization = Row(
                id_device = f"PDA{n:03d}",
                id_driver = random.choice(self.drivers).id_driver,
                timestamp = datetime.now(),
                latitude = random.uniform(-90, 90),
                longitude = random.uniform(-180, 180)
            )
            self.gps.append(localization)

        gps_df = self.spark.createDataFrame(self.gps)
        gps_df.coalesce(1).write.mode("overwrite").parquet(f"{LANDING_ROOT}/gps")