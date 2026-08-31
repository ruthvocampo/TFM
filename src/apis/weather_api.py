import requests


class WeatherApi:

    def __init__(self):
        self.url = "https://ciudadesabiertas.madrid.es/dynamicAPI/API/query/meteo_tiemporeal.json"

    def get_info(self):

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

        print("TIPO DE DATA:", type(data))

        if isinstance(data, dict):
            print("CAMPOS:")
            for key, value in data.items():
                print(
                    key,
                    "->",
                    type(value),
                    "->",
                    value
                )

        elif isinstance(data, list):
            print("NÚMERO DE ELEMENTOS:", len(data))

            if data:
                print("TIPO DEL PRIMER ELEMENTO:", type(data[0]))

                for key, value in data[0].items():
                    print(
                        key,
                        "->",
                        type(value),
                        "->",
                        value
                    )

        return data