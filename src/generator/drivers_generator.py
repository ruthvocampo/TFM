import random
import pandas as pd

from src.objects.driver import Driver


class DriverGenerator:

    MAX_DRIVERS_PER_ZONE = 5

    def __init__(self, drivers, address):
        self.drivers = drivers
        self.address = address

    def _get_postal_codes(self):
        return (
            self.address["COD_POSTAL"]
            .dropna()
            .astype(str)
            .str.strip()
            .drop_duplicates()
            .tolist()
        )

    def create_drivers(self, num_drivers):
        postal_codes = self._get_postal_codes()

        # Contar cuántos conductores tiene actualmente cada código postal.
        drivers_by_zone = {
            postal_code: 0
            for postal_code in postal_codes
        }

        for driver in self.drivers:
            zone = str(driver.zone).strip()

            if zone in drivers_by_zone:
                drivers_by_zone[zone] += 1

        # ID inicial:continúa después del último driver existente

        next_driver_number = len(self.drivers) + 1

        drivers_created = 0

        # Recorremos los CP en orden

        for postal_code in postal_codes:

            current_drivers = drivers_by_zone[postal_code]

            available_slots = (self.MAX_DRIVERS_PER_ZONE - current_drivers)

            if available_slots <= 0:
                continue

            drivers_to_create = min(available_slots,num_drivers - drivers_created)

            for _ in range(drivers_to_create):

                driver = Driver(
                    id_driver=f"DRV{next_driver_number:03d}",
                    name=f"Driver {next_driver_number:03d}",
                    license_number=f"LIC-{next_driver_number:04d}",
                    vehicle_type=random.choice(["car", "van", "truck"]),
                    available=random.choice([True, False]),
                    zone=postal_code
                )

                self.drivers.append(driver)

                drivers_created += 1
                next_driver_number += 1

            if drivers_created == num_drivers:
                break

        
        # Avisar si no se pudieron crear todos
        if drivers_created < num_drivers:
            print(f"Se solicitaron {num_drivers} conductores, "
                f"pero solo se pudieron crear "
                f"{drivers_created}.")

        return self.drivers