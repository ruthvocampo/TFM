from datetime import datetime, timedelta
import random
import pandas as pd
from pathlib import Path

from src.config.setup import LANDING_ROOT
from src.objects.orders_historical import OrderHistorical


FINALS_STATUS = [
    "ENTREGADO",
    "RECHAZADO",
    "CANCELADO",
    "INCIDENTADO"
]


class OrderHistoricalGenerator:

    def __init__(self, drivers):
        self.drivers = drivers

    def create_historical(self, num_files, records_per_file):

        historical_path = Path(LANDING_ROOT) / "historical_orders"
        historical_path.mkdir(parents=True, exist_ok=True)


        # 1.Obtenemos las fechas que ya existen

        existing_dates = set()

        for file in historical_path.glob("historical_*.csv"):

            date_str = file.stem.replace("historical_", "")
            existing_dates.add(date_str)

        # 2. Generamos las fechas anteriores a HOY

        today = datetime.now().date()

        available_dates = []

        # Buscamos fechas en los últimos 2 años
        for days_ago in range(1, 730):

            date = today - timedelta(days=days_ago)

            date_str = date.strftime("%Y-%m-%d")

            if date_str not in existing_dates:
                available_dates.append(date)

        # 3. Comprobamos que tenemos suficientes fechas

        if len(available_dates) < num_files:

            raise ValueError(
                f"No hay suficientes fechas disponibles. "
                f"Se solicitan {num_files}, "
                f"pero solo hay {len(available_dates)}."
            )

        # 4. Elegimos las fechas

        selected_dates = random.sample(
            available_dates,
            num_files
        )

        # 5. Creamos un CSV por cada fecha

        for current_date in selected_dates:

            historical_list = []

            for n in range(records_per_file):

                # Hora aleatoria del día
                status_date = datetime.combine(
                    current_date,
                    datetime.min.time()
                ).replace(
                    hour=random.randint(8, 23),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )

                history = OrderHistorical(
                    id_historical=n + 1,
                    id_order=f"ORDH{n + 1:06d}",
                    id_driver=self.drivers.sample(1).iloc[0]["id_driver"],
                    status_order=random.choice(FINALS_STATUS),
                    status_modified_date=status_date
                )

                historical_list.append(history)

            # Convertir a DataFrame
            historical_df = pd.DataFrame([vars(history) for history in historical_list])

            # Nombre del fichero
            file_path = (historical_path / f"historical_{current_date.strftime('%Y-%m-%d')}.csv")

            # Guardar
            historical_df.to_csv(file_path, index=False, encoding="utf-8-sig")

            print(f"Creado: {file_path.name} " f"({records_per_file} registros)")
