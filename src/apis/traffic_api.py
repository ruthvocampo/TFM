import requests


class TrafficApi:

    def __init__(self):
        self.url = "https://datos.madrid.es/api/3/action/datastore_search"

    def get_info(self):
        params = {
            "resource_id": "202087-0-trafico-intensidad",
            "limit": 100
        }

        try:
            req = requests.get(
                self.url,
                params=params,
                timeout=10
            )

            req.raise_for_status()

            data = req.json()

            return data["result"]["records"]

        except requests.RequestException as e:
            raise Exception(f"ERROR al conectar con la API: {e}")

        except ValueError:
            raise Exception("ERROR: La respuesta no tiene formato JSON")