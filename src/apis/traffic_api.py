import requests
import xml.etree.ElementTree as ET
from datetime import datetime


class TrafficApi:

    def __init__(self):
        self.API_URL = "https://informo.madrid.es/informo/tmadrid/pm.xml"

    def get_info(self):

        response = requests.get(
            self.API_URL,
            timeout=(10, 120)
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        fecha_hora = root.findtext("fecha_hora")

        records = []

        for pm in root.findall("pm"):
            record = {
                "fecha_hora": fecha_hora,
                "idelem": pm.findtext("idelem"),
                "descripcion": pm.findtext("descripcion"),
                "accesoAsociado": pm.findtext("accesoAsociado"),
                "intensidad": pm.findtext("intensidad"),
                "ocupacion": pm.findtext("ocupacion"),
                "carga": pm.findtext("carga"),
                "nivelServicio": pm.findtext("nivelServicio"),
                "intensidadSat": pm.findtext("intensidadSat"),
                "error": pm.findtext("error"),
                "subarea": pm.findtext("subarea"),
                "st_x": pm.findtext("st_x"),
                "st_y": pm.findtext("st_y"),
            }

            records.append(record)

        return records