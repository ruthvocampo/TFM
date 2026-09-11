import random
from faker import Faker

from src.objects.driver import Driver
from src.objects.location import Location

class DriverGenerator:

    MAX_DRIVERS_PER_ZONE = 5
    AVAILABLE_PERCENTAGE = 0.90
    # Localización por defecto del wharehouse
    DEFAULT_LOCATION = Location(40.43134,-3.54512)
                    

    def __init__(self, drivers, address):
        self.drivers = drivers
        self.address = address
        self.fake = Faker("es_ES")


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

        # Contar cuántos conductores tiene actualmente cada CP
        drivers_by_zone = {
            postal_code: 0
            for postal_code in postal_codes
        }

        for driver in self.drivers:

            zone = str(driver.zone).strip()

            if zone in drivers_by_zone:
                drivers_by_zone[zone] += 1

        # ID inicial
        next_driver_number = len(self.drivers) + 1

        drivers_created = 0

        # ---------------------------------------------------------
        # 1. REPARTIR LOS CONDUCTORES POR RONDAS
        # ---------------------------------------------------------
        #
        # Ronda 1 → 1 conductor por CP
        # Ronda 2 → 2 conductores por CP
        # ...
        # Ronda 5 → máximo 5 conductores por CP
        #
        # De esta forma ningún CP se llena antes de cubrir los demás.
        # ---------------------------------------------------------

        for ronda in range(self.MAX_DRIVERS_PER_ZONE):

            for postal_code in postal_codes:

                # Si ya hemos creado todos los conductores solicitados
                if drivers_created >= num_drivers:
                    break

                # Conductores actuales en este CP
                current_drivers = drivers_by_zone[postal_code]

                # Esta ronda representa tener:
                # ronda + 1 conductores en el CP
                if current_drivers > ronda:
                    continue
                
                
                # Crear conductor
                driver = Driver(
                    id_driver=f"DRV{next_driver_number:03d}",
                    username=f"Driver_{next_driver_number:03d}",
                    name = self.fake.name(),
                    license_number=f"LIC-{next_driver_number:04d}",
                    vehicle_type=random.choice(
                        ["car", "van", "truck"]
                    ),
                    available=True,
                    zone=postal_code,
                    location = self.DEFAULT_LOCATION)
                self.drivers.append(driver)

                drivers_by_zone[postal_code] += 1

                drivers_created += 1
                next_driver_number += 1

            # Si ya tenemos todos los conductores, terminamos
            if drivers_created >= num_drivers:
                break

        # ---------------------------------------------------------
        # 2. ASIGNAR DISPONIBILIDAD
        # ---------------------------------------------------------
        #
        # Por ejemplo:
        # 90 % → True
        # 10 % → False
        #
        # Se calcula sobre los conductores REALMENTE creados.
        # ---------------------------------------------------------

        num_available = round(
            drivers_created * self.AVAILABLE_PERCENTAGE
        )

        num_unavailable = (
            drivers_created - num_available
        )

        availability = (
            [True] * num_available
            + [False] * num_unavailable
        )

        random.shuffle(availability)

        # Asignamos la disponibilidad solamente
        # a los conductores creados en esta ejecución
        first_new_driver = len(self.drivers) - drivers_created

        for i in range(drivers_created):

            self.drivers[first_new_driver + i].available = availability[i]

        # ---------------------------------------------------------
        # 3. AVISO SI NO SE PUDIERON CREAR TODOS
        # ---------------------------------------------------------

        if drivers_created < num_drivers:

            print(
                f"Se solicitaron {num_drivers} conductores, "
                f"pero solo se pudieron crear "
                f"{drivers_created}."
            )

        return self.drivers