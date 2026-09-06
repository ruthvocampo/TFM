import random


class GPSEvents:

    def __init__(self, drivers, fecha_actual):
        self.drivers = drivers
        self.fecha_actual = fecha_actual
        self.event_counter = 0

    def id_event_gps(self):

        self.event_counter += 1

        return self.event_counter

    def available_drivers(self):

        return [
            driver
            for driver in self.drivers
            if driver.available
        ]

    def timestamp(self):

        return self.fecha_actual.isoformat()

    def longitud(self):

        return random.uniform(-4.579, -3.053)

    def latitude(self):

        return random.uniform(39.884, 41.164)

    def send_gps(self, driver):

        gps_event_id = self.id_event_gps()

        timestamp = self.timestamp()

        latitude = self.latitude()

        longitud = self.longitud()

        value = {
            "gps_event_id": gps_event_id,
            "id_driver": driver.id_driver,
            "timestamp": timestamp,
            "latitude": latitude,
            "longitud": longitud
        }

        key = gps_event_id

        print(
            "# REPARTIDOR:",
            driver.id_driver
        )

        print(value)

        return key, value

    def generate_available_events(self):

        events = []

        available_drivers = self.available_drivers()

        for driver in available_drivers:

            key, value = self.send_gps(driver)

            events.append(value)

        return events