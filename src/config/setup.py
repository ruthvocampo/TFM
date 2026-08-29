from pathlib import Path

from pyspark.sql import SparkSession



STORAGE = spark.conf.get("adls.account.name")



# Raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[2]


# Data
DATA_ROOT = PROJECT_ROOT / "data"

HISTORICAL_ROOT = DATA_ROOT / "historical"
SIMULATED_ROOT = DATA_ROOT / "simulated"


# Lakehouse
LAKEHOUSE_ROOT = PROJECT_ROOT / "lakehouse"

LANDING_ROOT = LAKEHOUSE_ROOT / "landing"
BRONZE_ROOT = LAKEHOUSE_ROOT / "bronze"
SILVER_ROOT = LAKEHOUSE_ROOT / "silver"
GOLD_ROOT = LAKEHOUSE_ROOT / "gold"

# Landing
LANDING_ORDERS = LANDING_ROOT / "orders"
LANDING_DRIVERS = LANDING_ROOT / "drivers"
LANDING_GPS = LANDING_ROOT / "gps"
LANDING_WEATHER = LANDING_ROOT / "weather"
LANDING_TRAFFIC = LANDING_ROOT / "traffic"

# Bronze
BRONZE_ORDERS = BRONZE_ROOT / "orders"
BRONZE_DRIVERS = BRONZE_ROOT / "drivers"
BRONZE_GPS = BRONZE_ROOT / "gps"
BRONZE_WEATHER = BRONZE_ROOT / "weather"
BRONZE_TRAFFIC = BRONZE_ROOT / "traffic"


# Silver
SILVER_ORDERS = SILVER_ROOT / "orders"
SILVER_DRIVERS = SILVER_ROOT / "drivers"
SILVER_GPS = SILVER_ROOT / "gps"
SILVER_WEATHER = SILVER_ROOT / "weather"
SILVER_TRAFFIC = SILVER_ROOT / "traffic"


# Gold
GOLD_SLA_RISK = GOLD_ROOT / "sla_risk"
GOLD_DRIVER_PERFORMANCE = GOLD_ROOT / "driver_performance"
GOLD_ZONE_PERFORMANCE = GOLD_ROOT / "zone_performance"
GOLD_RECOMMENDATIONS = GOLD_ROOT / "recommendations"