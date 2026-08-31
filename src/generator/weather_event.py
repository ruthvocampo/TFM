from datetime import datetime
from src.apis.weather_api import WeatherApi


MAGNITUDES = {
    "81": "VELOCIDAD_VIENTO",
    "82": "DIRECCION_VIENTO",
    "83": "TEMPERATURA",
    "86": "HUMEDAD_RELATIVA",
    "87": "PRESION_BAROMETRICA",
    "88": "RADIACION_SOLAR",
    "89": "PRECIPITACION"
}


class WeatherEventGenerator:

    def __init__(self):

        self.api = WeatherApi()

        self.event_counter = 0

    def generate_events(self):

        # 1. Obtener datos de la API
        data = self.api.get_info()

        events = []

        # 2. Recorrer los registros
        for record in data:

            magnitude_code = str(record.get("MAGNITUD"))

            magnitude_name = MAGNITUDES.get(
                magnitude_code,
                "DESCONOCIDA"
            )

            # 3. Recorrer las 24 horas
            for hour in range(1, 25):

                hour_key = f"H{hour:02d}"
                validation_key = f"V{hour:02d}"

                value = record.get(hour_key)
                validation = record.get(validation_key)

                # No hay dato
                if value in (None, "", "0"):
                    continue

                # Solo utilizamos datos válidos
                if validation != "V":
                    continue

                try:
                    value = float(value)
                except (ValueError, TypeError):
                    continue

                self.event_counter += 1

                event = {
                    "weather_event_id": self.event_counter,

                    "timestamp": datetime.now(),

                    "station": record.get("ESTACION"),

                    "magnitude_code": magnitude_code,

                    "magnitude": magnitude_name,

                    "date": (
                        f"{record.get('ANO')}-"
                        f"{record.get('MES')}-"
                        f"{record.get('DIA')}"
                    ),

                    "hour": hour,

                    "value": value,

                    "validation": validation
                }

                events.append(event)

        return events
