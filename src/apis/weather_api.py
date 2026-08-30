import requests


class WeatherApi:

    def get_info(self):
        url = "https://datos.madrid.es/dataset/300754-0-meteorologia-tiempo-real-acumula/resource/300754-1-meteorologia-tiempo-real-acumula-api/download/300754-1-meteorologia-tiempo-real-acumula-api.api"

        try:
            req = requests.get(url, timeout=10)
            req.raise_for_status()

            return req.json()

        except requests.RequestException as e:
            raise Exception(f"ERROR al conectar con la API: {e}")