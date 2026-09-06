from pathlib import Path


# ============================================================
# ROOT DEL PROYECTO
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ============================================================
# DATA
# ============================================================

DATA_ROOT = PROJECT_ROOT / "data"

DATA_ADDRESS = DATA_ROOT / "reference"

HISTORICAL_ROOT = DATA_ROOT / "historical"

SIMULATED_ROOT = DATA_ROOT / "simulated"


# ============================================================
# LAKEHOUSE
# ============================================================

LAKEHOUSE_ROOT = PROJECT_ROOT / "lakehouse"


# ============================================================
# LANDING
# ============================================================

LANDING_ROOT = LAKEHOUSE_ROOT / "landing"

LANDING_ORDERS = LANDING_ROOT / "orders"

LANDING_DRIVERS = LANDING_ROOT / "drivers"

LANDING_ROUTES = LANDING_ROOT / "routes"

LANDING_ORDER_EVENTS = LANDING_ROOT / "order_events"

LANDING_GPS = LANDING_ROOT / "gps"

LANDING_WEATHER = LANDING_ROOT / "weather"

LANDING_TRAFFIC = LANDING_ROOT / "traffic"


# ============================================================
# BRONZE
# ============================================================

BRONZE_ROOT = LAKEHOUSE_ROOT / "bronze"

BRONZE_ORDERS = BRONZE_ROOT / "orders"

BRONZE_DRIVERS = BRONZE_ROOT / "drivers"

BRONZE_ROUTES = BRONZE_ROOT / "routes"

BRONZE_ORDER_EVENTS = BRONZE_ROOT / "order_events"

BRONZE_GPS = BRONZE_ROOT / "gps"

BRONZE_WEATHER = BRONZE_ROOT / "weather"

BRONZE_TRAFFIC = BRONZE_ROOT / "traffic"


# ============================================================
# SILVER
# ============================================================

SILVER_ROOT = LAKEHOUSE_ROOT / "silver"

SILVER_ORDERS = SILVER_ROOT / "orders"

SILVER_DRIVERS = SILVER_ROOT / "drivers"

SILVER_ROUTES = SILVER_ROOT / "routes"

SILVER_ORDER_EVENTS = SILVER_ROOT / "order_events"

SILVER_GPS = SILVER_ROOT / "gps"

SILVER_WEATHER = SILVER_ROOT / "weather"

SILVER_TRAFFIC = SILVER_ROOT / "traffic"


# ============================================================
# GOLD
# ============================================================

GOLD_ROOT = LAKEHOUSE_ROOT / "gold"

GOLD_SLA_RISK = GOLD_ROOT / "sla_risk"

GOLD_DRIVER_PERFORMANCE = GOLD_ROOT / "driver_performance"

GOLD_ZONE_PERFORMANCE = GOLD_ROOT / "zone_performance"

GOLD_RECOMMENDATIONS = GOLD_ROOT / "recommendations"
