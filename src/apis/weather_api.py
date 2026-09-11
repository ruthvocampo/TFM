import requests


class WeatherApi:

    def __init__(self):
        self.url = (
            "https://ciudadesabiertas.madrid.es/dynamicAPI/API/query/meteo_tiemporeal.json"
        )

    def get_info(self):
        try:
            all_records = []
            page = 1
            page_size = 100

            while True:

                response = requests.get(
                    self.url,
                    params={
                        "pageSize": page_size,
                        "page": page
                    },
                    timeout=10
                )

                response.raise_for_status()

                data = response.json()

                records = data.get("records", [])

                if not records:
                    break

                all_records.extend(records)

                # Si vienen menos registros que el tamaño de página,
                # ya hemos llegado al final.
                if len(records) < page_size:
                    break

                page += 1

            return all_records

        except requests.RequestException as e:
            raise Exception(
                f"ERROR al conectar con la API Weather: {e}"
            )

        except ValueError:
            raise Exception(
                "ERROR: la respuesta de Weather no tiene formato JSON"
            )