import requests
import xml.etree.ElementTree as ET


class TrafficApi:

    def __init__(self, fecha_actual):
        self.API_URL = (
            "https://informo.madrid.es/informo/tmadrid/pm.xml"
        )
        self.fecha_actual = fecha_actual

    def update_time(self, fecha_actual):
        self.fecha_actual = fecha_actual

    def get_info(self):

        response = requests.get(
            self.API_URL,
            timeout=(10, 120)
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)

        fecha_hora_api = root.findtext("fecha_hora")

        records = []
        


        for pm in root.findall("pm"):

            record = {
            "fecha_hora": self.fecha_actual,

            "idelem": pm.findtext("idelem"),
            "descripcion": pm.findtext("descripcion"),

            "accesoAsociado": pm.findtext("accesoAsociado"),

            "intensidad": int(pm.findtext("intensidad")),
            "ocupacion": int(pm.findtext("ocupacion")),
            "carga": int(pm.findtext("carga")),
            "nivelServicio": int(pm.findtext("nivelServicio")),
            "intensidadSat": (
                None
                if pm.findtext("intensidadSat") is None
                else int(pm.findtext("intensidadSat"))
            ),

            "error": pm.findtext("error"),

            "subarea": pm.findtext("subarea"),

            "st_x": self._to_float(pm.findtext("st_x")),
            "st_y": self._to_float(pm.findtext("st_y")),
        }

            records.append(record)

        return records

    @staticmethod
    def _to_float(value):
        print(value)
        if value is None:
            return None

        try:
            return float(value.replace(",", "."))
        except (ValueError, TypeError):
            return None