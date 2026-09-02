from datetime import datetime
from src.apis.weather_api import WeatherApi


# MAGNITUDES METEOROLÓGICAS

MAGNITUDES = {
    "81": "VELOCIDAD_VIENTO",
    "82": "DIRECCION_VIENTO",
    "83": "TEMPERATURA",
    "86": "HUMEDAD_RELATIVA",
    "87": "PRESION_BAROMETRICA",
    "88": "RADIACION_SOLAR",
    "89": "PRECIPITACION"
}


# ESTACIONES METEOROLÓGICAS
# 

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

    def __init__(self):

        self.api = WeatherApi()

        self.event_counter = 0


    # BUSCAR ÚLTIMA HORA DISPONIBLE
    def get_latest_hour(self, data):

        latest_hour = None

        for record in data:

            for hour in range(23, 0, -1):

                hour_key = f"H{hour:02d}"
                validation_key = f"V{hour:02d}"

                value = record.get(hour_key)
                validation = record.get(validation_key)

                # El dato existe y está validado
                if (
                    value not in (None, "", "0")
                    and validation == "V"
                ):

                    if latest_hour is None or hour > latest_hour:
                        latest_hour = hour

                    break

        return latest_hour



    # GENERAR EVENTOS
    def generate_events(self):

        # 1. Obtener datos de la API

        data = self.api.get_info()

        if not data:
            return []


        
        # 2. Obtener última hora disponible

        latest_hour = self.get_latest_hour(data)

        if latest_hour is None:
            return []


        print(
            f"Última hora disponible: "
            f"{latest_hour:02d}:00"
        )


        # 3. Recorrer los registros

        events = []

        for record in data:

            magnitude_code = str(
                record.get("MAGNITUD")
            )

            magnitude_name = MAGNITUDES.get(
                magnitude_code,
                "DESCONOCIDA"
            )


            
            # 4. Obtener valor de la última hora

            hour_key = f"H{latest_hour:02d}"
            validation_key = f"V{latest_hour:02d}"

            value = record.get(hour_key)
            validation = record.get(validation_key)


            # 5. Comprobar que existe y es válido
            

            if value in (None, "", "0"):
                continue

            if validation != "V":
                continue


            # 6. Convertir valor
            try:

                value = float(value)

            except (ValueError, TypeError):

                continue


        
            # 7. Timestamp
            timestamp = self.create_timestamp(
                record,
                latest_hour
            )

            if timestamp is None:
                continue


            # 8. Información de la estación
            station_code = str(
                record.get("ESTACION")
            )

            station_name = STATIONS.get(
                station_code,
                "DESCONOCIDA"
            )


            # 9. Crear evento
            self.event_counter += 1

            event = {

                "weather_event_id":
                    self.event_counter,

                # LOCALIZACIÓN
                "province":
                    "Madrid",

                "municipality":
                    "Madrid",

                "station":
                    station_code,

                "station_name":
                    station_name,

                # FECHA Y HORA

                "year": record.get('ANO'),
            
                "month":record.get('MES'),
                
                "day" : record.get('DIA'),

                "hour":
                    latest_hour,

                # MAGNITUD
                "magnitude_code":
                    magnitude_code,

                "magnitude":
                    magnitude_name,

                # VALOR
                "value":
                    value,

                "validation":
                    validation
            }
            print(event)
            events.append(event)


        # 10. Mostrar resultado
        print(f"Eventos generados: {len(events)}")


        return events
