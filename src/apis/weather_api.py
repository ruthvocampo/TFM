import requests


class WeatherApi:

    def __init__(self):
        self.url = ("https://ciudadesabiertas.madrid.es/dynamicAPI/API/query/meteo_tiemporeal.json")
        
    def get_info(self):
        try:
            response = requests.get(
                self.url,
                params={
                    "pageSize": 100,
                    "page": 1
                },
                timeout=10
            )

            response.raise_for_status()

            data = response.json()

            # La API devuelve un diccionario.
            # Los datos meteorológicos están dentro de "records".
            return data["records"]

        except requests.RequestException as e:
            raise Exception(
                f"ERROR al conectar con la API Weather: {e}"
            )

        except ValueError:
            raise Exception(
                "ERROR: la respuesta de Weather no tiene formato JSON"
            )

        except KeyError:
            raise Exception(
                "ERROR: la respuesta de Weather no contiene 'records'"
            )