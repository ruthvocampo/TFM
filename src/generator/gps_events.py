import random
from datetime import datetime, timezone


class GPSEvents:

    def __init__(self, drivers, fecha_actual):
        self.drivers = drivers
        self.fecha_actual = fecha_actual

    def id_event_gps(self):
        return random.randint(1, 300)

    def id_driver(self):
        drivers_list = [driver for driver in self.drivers if driver.available == True]

        if not drivers_list:
            raise ValueError("No hay conductores disponibles")

        return drivers_list[0].id_driver

    def timestamp(self):
        return self.fecha_actual.isoformat()

    def longitud(self):
        return random.uniform(-4.579, -3.053)

    def latitude(self):
        return random.uniform(39.884, 41.164)

    def send_gps(self):

        gps_event_id = self.id_event_gps()
        id_driver = self.id_driver()
        timestamp = self.timestamp()
        latitude = self.latitude()
        longitud = self.longitud()

        value = {
            "gps_event_id": gps_event_id,
            "id_driver": id_driver,
            "timestamp": timestamp,
            "latitude": latitude,
            "longitud": longitud
        }

        key = gps_event_id
        print ("# REPARTIDOR : ", id_driver)
        print (value)
        return key, value