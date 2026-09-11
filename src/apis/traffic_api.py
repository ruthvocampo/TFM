import requests
import xml.etree.ElementTree as ET
from datetime import datetime


class TrafficApi:

    def __init__(self, fecha_actual):

        self.API_URL = (
            "https://informo.madrid.es/informo/tmadrid/pm.xml"
        )

        self.fecha_actual = fecha_actual

    def parse_fecha_hora(self, fecha_hora):

        if not fecha_hora:
            return None

        formatos = [
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for formato in formatos:

            try:
                return datetime.strptime(
                    fecha_hora,
                    formato
                )

            except ValueError:
                continue

        return None

    def get_info(self):

        response = requests.get(
            self.API_URL,
            timeout=(10, 120)
        )

        response.raise_for_status()

        root = ET.fromstring(
            response.content
        )

        fecha_hora = root.findtext(
            "fecha_hora"
        )

        timestamp = self.parse_fecha_hora(
            fecha_hora
        )

        if timestamp is None:

            raise Exception(
                f"ERROR: fecha_hora inválida: "
                f"{fecha_hora}"
            )

        # -----------------------------------------------------
        # SOLO ACEPTAR DATOS ANTERIORES A fecha_actual
        # -----------------------------------------------------

        if timestamp >= self.fecha_actual:

            print(
                f"El tráfico disponible ({timestamp}) "
                f"no es anterior a fecha_actual "
                f"({self.fecha_actual})."
            )

            return []

        records = []

        for pm in root.findall("pm"):

            record = {

                "fecha_hora":
                    fecha_hora,

                "idelem":
                    pm.findtext("idelem"),

                "descripcion":
                    pm.findtext("descripcion"),

                "accesoAsociado":
                    pm.findtext("accesoAsociado"),

                "intensidad":
                    pm.findtext("intensidad"),

                "ocupacion":
                    pm.findtext("ocupacion"),

                "carga":
                    pm.findtext("carga"),

                "nivelServicio":
                    pm.findtext("nivelServicio"),

                "intensidadSat":
                    pm.findtext("intensidadSat"),

                "error":
                    pm.findtext("error"),

                "subarea":
                    pm.findtext("subarea"),

                "st_x":
                    pm.findtext("st_x"),

                "st_y":
                    pm.findtext("st_y"),
            }

            records.append(record)

        return records
