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


STATIONS = {
    "4": "Plaza España",
    "8": "Escuelas Aguirre",
    "16": "Arturo Soria",
    "18": "Farolillo",
    "24": "Casa de Campo",
    "35": "Plaza del Carmen",
    "36": "Moratalaz",
    "38": "Cuatro Caminos",
    "39": "Barrio del Pilar",
    "54": "Ensanche de Vallecas",
    "56": "Plaza Elíptica",
    "58": "El Pardo",
    "59": "Juan Carlos I",
    "102": "J.M.D. Moratalaz",
    "103": "J.M.D. Villaverde",
    "104": "E.D.A.R. La China",
    "106": "Centro Mpal. de Acústica",
    "107": "J.M.D. Hortaleza",
    "108": "Peñagrande",
    "109": "J.M.D. Chamberí",
    "110": "J.M.D. Centro",
    "111": "J.M.D. Chamartín",
    "112": "J.M.D. Vallecas 1",
    "113": "J.M.D. Vallecas 2",
    "114": "Matadero 01",
    "115": "Matadero 02"
}


class WeatherEventGenerator:

    def __init__(self,  fecha_actual):
        self.fecha_actual =  fecha_actual
        self.api = WeatherApi()
        self.event_counter = 0

    # ---------------------------------------------------------
    # CREAR DATETIME DE UN REGISTRO
    # ---------------------------------------------------------

    def create_timestamp(self, record, hour):

        try:

            year = int(record.get("ANO"))
            month = int(record.get("MES"))
            day = int(record.get("DIA"))

            return datetime(
                year,
                month,
                day,
                hour,
                0,
                0
            )

        except (TypeError, ValueError):

            return None

    # ---------------------------------------------------------
    # BUSCAR LA ÚLTIMA HORA ANTERIOR A fecha_actual
    # ---------------------------------------------------------

    def get_latest_datetime(self, data):

        latest_datetime = None

        for record in data:

            for hour in range(24):

                hour_key = f"H{hour:02d}"
                validation_key = f"V{hour:02d}"

                value = record.get(hour_key)
                validation = record.get(validation_key)

                # El dato no existe
                if value in (None, "", "0"):
                    continue

                # El dato no está validado
                if validation != "V":
                    continue

                timestamp = self.create_timestamp(
                    record,
                    hour
                )

                if timestamp is None:
                    continue

                # IMPORTANTE:
                # Solo aceptamos datos ANTERIORES
                # a fecha_actual.
                if timestamp >= self.fecha_actual:
                    continue

                if (
                    latest_datetime is None
                    or timestamp > latest_datetime
                ):
                    latest_datetime = timestamp

        return latest_datetime

    # ---------------------------------------------------------
    # OBTENER SNAPSHOT DE LA ÚLTIMA HORA DISPONIBLE
    # ---------------------------------------------------------

    def get_snapshot(self):

        data = self.api.get_info()

        if not data:
            return []

        latest_datetime = self.get_latest_datetime(
            data)

        if latest_datetime is None:

            print(
                "No hay datos meteorológicos "
                "anteriores a la fecha actual."
            )

            return []

        print(
            f"Fecha actual: "
            f"{self.fecha_actual.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print(
            f"Última hora meteorológica disponible: "
            f"{latest_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        latest_hour = latest_datetime.hour

        # -----------------------------------------------------
        # AGRUPAR POR ESTACIÓN
        # -----------------------------------------------------

        stations = {}

        for record in data:

            timestamp = self.create_timestamp(
                record,
                latest_hour
            )

            # Solo queremos registros de la hora encontrada
            if timestamp != latest_datetime:
                continue

            station_code = str(
                record.get("ESTACION")
            )

            if not station_code:
                continue

            station_name = STATIONS.get(
                station_code,
                "DESCONOCIDA"
            )

            magnitude_code = str(
                record.get("MAGNITUD")
            )

            magnitude_name = MAGNITUDES.get(
                magnitude_code,
                "DESCONOCIDA"
            )

            hour_key = f"H{latest_hour:02d}"
            validation_key = f"V{latest_hour:02d}"

            value = record.get(hour_key)
            validation = record.get(validation_key)

            if value in (None, "", "0"):
                continue

            if validation != "V":
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            # Crear estación
            if station_code not in stations:

                stations[station_code] = {

                    "station": station_code,

                    "station_name": station_name,

                    "province": "Madrid",

                    "municipality": "Madrid",

                    "year": record.get("ANO"),

                    "month": record.get("MES"),

                    "day": record.get("DIA"),

                    "hour": latest_hour,

                    "timestamp":
                        latest_datetime.isoformat(),

                    "measurements": {}
                }

            # Añadir magnitud
            stations[station_code]["measurements"][
                magnitude_name
            ] = {

                "magnitude_code":
                    magnitude_code,

                "value":
                    value,

                "validation":
                    validation
            }

        return list(stations.values())

    # ---------------------------------------------------------
    # GENERAR EVENTOS INDIVIDUALES
    # ---------------------------------------------------------

    def generate_events(self):

        snapshot = self.get_snapshot()

        events = []

        for station in snapshot:

            self.event_counter += 1
            timestamp = station["timestamp"]

            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )
                
            measurements = {}

            for magnitude_name, data in station["measurements"].items():

                measurements[str(magnitude_name)] = {
                    "magnitude_code": str(data["magnitude_code"]),
                    "value": (
                        float(data["value"])
                        if data.get("value") is not None
                        else None
                    ),
                    "validation": (
                        str(data["validation"])
                        if data.get("validation") is not None
                        else None
                    )
                }
                            
            event = {
                "weather_event_id": int(self.event_counter),
                "province": str(station["province"]),
                "municipality": str(station["municipality"]),
                "station": str(station["station"]),
                "station_name": str(station["station_name"]),
                "year": int(station["year"]),
                "month": int(station["month"]),
                "day": int(station["day"]),
                "hour": int(station["hour"]),
                "timestamp": timestamp,
                "measurements": measurements
            }

            events.append(event)

        print(
            f"Eventos Weather generados: "
            f"{len(events)}"
        )

        return events
