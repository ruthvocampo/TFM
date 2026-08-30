import random
import pandas as pd
from pathlib import Path
from src.config.setup import LANDING_ROOT
from src.objects.driver import Driver



class DriverGenerator:

    def __init__(self,drivers):
        self.drivers = drivers

    def create_drivers(self,num_drivers):

        for n in range(1, num_drivers):

            driver = Driver(
                id_driver=f"DRV{n:03d}",
                name=f"Driver {n:03d}",
                license_number=f"LIC-{n:04d}",
                vehicle_type=random.choice(
                    ["car", "van", "truck"]
                ),
                available=random.choice(
                    [True, False]
                ),
                zone=random.randint(28001, 28054),
            )

            self.drivers.append(driver)

        # Convertimos los objetos Driver a DataFrame
        drivers_df = pd.DataFrame([vars(driver) for driver in self.drivers])

        # Creamos la carpeta de Landing
        drivers_path = Path(LANDING_ROOT) / "drivers"
        drivers_path.mkdir(parents=True, exist_ok=True)

        # Guardamos los datos
        drivers_df.to_json( drivers_path / "drivers.json",orient="records",lines=True,force_ascii=False)

        return drivers_df