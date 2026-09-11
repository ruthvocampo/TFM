import pandas as pd
import random
import re


MADRID_ZONAS = {
    "01": {
        "nombre": "Centro",
        "barrios": {
            "1": "Palacio",
            "2": "Embajadores",
            "3": "Cortes",
            "4": "Justicia",
            "5": "Universidad",
            "6": "Sol",
        },
    },
    "02": {
        "nombre": "Arganzuela",
        "barrios": {
            "1": "Imperial",
            "2": "Acacias",
            "3": "Chopera",
            "4": "Legazpi",
            "5": "Delicias",
            "6": "Palos de la Frontera",
            "7": "Atocha",
        },
    },
    "03": {
        "nombre": "Retiro",
        "barrios": {
            "1": "Pacífico",
            "2": "Adelfas",
            "3": "Estrella",
            "4": "Ibiza",
            "5": "Los Jerónimos",
            "6": "Niño Jesús",
        },
    },
    "04": {
        "nombre": "Salamanca",
        "barrios": {
            "1": "Recoletos",
            "2": "Goya",
            "3": "Fuente del Berro",
            "4": "Guindalera",
            "5": "Lista",
            "6": "Castellana",
        },
    },
    "05": {
        "nombre": "Chamartín",
        "barrios": {
            "1": "El Viso",
            "2": "Prosperidad",
            "3": "Ciudad Jardín",
            "4": "Hispanoamérica",
            "5": "Nueva España",
            "6": "Castilla",
        },
    },
    "06": {
        "nombre": "Tetuán",
        "barrios": {
            "1": "Bellas Vistas",
            "2": "Cuatro Caminos",
            "3": "Castillejos",
            "4": "Almenara",
            "5": "Valdeacederas",
            "6": "Berruguete",
        },
    },
    "07": {
        "nombre": "Chamberí",
        "barrios": {
            "1": "Gaztambide",
            "2": "Arapiles",
            "3": "Trafalgar",
            "4": "Almagro",
            "5": "Ríos Rosas",
            "6": "Vallehermoso",
        },
    },
    "08": {
        "nombre": "Fuencarral-El Pardo",
        "barrios": {
            "1": "El Pardo",
            "2": "Fuentelarreina",
            "3": "Peñagrande",
            "4": "Pilar",
            "5": "La Paz",
            "6": "Valverde",
            "7": "Mirasierra",
            "8": "El Goloso",
        },
    },
    "09": {
        "nombre": "Moncloa-Aravaca",
        "barrios": {
            "1": "Casa de Campo",
            "2": "Argüelles",
            "3": "Ciudad Universitaria",
            "4": "Valdezarza",
            "5": "Aravaca",
        },
    },
    "10": {
        "nombre": "Latina",
        "barrios": {
            "1": "Los Cármenes",
            "2": "LETRA del Ángel",
            "3": "Lucero",
            "4": "Aluche",
            "5": "Campamento",
            "6": "Cuatro Vientos",
            "7": "Las Águilas",
        },
    },
    "11": {
        "nombre": "Carabanchel",
        "barrios": {
            "1": "Comillas",
            "2": "Opañel",
            "3": "San Isidro",
            "4": "Vista Alegre",
            "5": "LETRA Bonita",
            "6": "Buenavista",
            "7": "Abrantes",
        },
    },
    "12": {
        "nombre": "Usera",
        "barrios": {
            "1": "Orcasitas",
            "2": "Orcasur",
            "3": "San Fermín",
            "4": "Almendrales",
            "5": "Moscardó",
            "6": "Zofío",
            "7": "Pradolongo",
        },
    },
    "13": {
        "nombre": "Puente de Vallecas",
        "barrios": {
            "1": "Entrevías",
            "2": "San Diego",
            "3": "Palomeras Bajas",
            "4": "Palomeras Sureste",
            "5": "Portazgo",
            "6": "Numancia",
        },
    },
    "14": {
        "nombre": "Moratalaz",
        "barrios": {
            "1": "Pavones",
            "2": "Horcajo",
            "3": "Marroquina",
            "4": "Media Legua",
            "5": "Fontarrón",
            "6": "Vinateros",
        },
    },
    "15": {
        "nombre": "Ciudad Lineal",
        "barrios": {
            "1": "Ventas",
            "2": "Pueblo Nuevo",
            "3": "Quintana",
            "4": "Concepción",
            "5": "San Pascual",
            "6": "San Juan Bautista",
            "7": "Colina",
            "8": "Atalaya",
        },
    },
    "16": {
        "nombre": "Hortaleza",
        "barrios": {
            "1": "Palomas",
            "2": "Piovera",
            "3": "Canillas",
            "4": "Pinar del Rey",
            "5": "Apóstol Santiago",
            "6": "Valdefuentes",
        },
    },
    "17": {
        "nombre": "Villaverde",
        "barrios": {
            "1": "Casco Histórico de Villaverde",
            "2": "San Cristóbal",
            "3": "Butarque",
            "4": "Los Rosales",
            "5": "Los Ángeles",
        },
    },
    "18": {
        "nombre": "Villa de Vallecas",
        "barrios": {
            "1": "Casco Histórico de Vallecas",
            "2": "Santa Eugenia",
            "3": "Ensanche de Vallecas",
        },
    },
    "19": {
        "nombre": "Vicálvaro",
        "barrios": {
            "1": "Casco Histórico de Vicálvaro",
            "2": "Ambroz",
            "3": "Valdebernardo",
            "4": "Valderrivas",
            "5": "El Cañaveral",
        },
    },
    "20": {
        "nombre": "San Blas-Canillejas",
        "barrios": {
            "1": "Simancas",
            "2": "Hellín",
            "3": "Amposta",
            "4": "Arcos",
            "5": "Rosas",
            "6": "Rejas",
            "7": "Canillejas",
            "8": "Salvador",
        },
    },
    "21": {
        "nombre": "Barajas",
        "barrios": {
            "1": "Alameda de Osuna",
            "2": "Aeropuerto",
            "3": "Casco Histórico de Barajas",
            "4": "Timón",
            "5": "Corralejos",
        },
    },
}


class AddressGenerator:

    def __init__(self, spain_file, madrid_file):

        self.spain_df = pd.read_csv(
            spain_file,
            dtype={
                "Latitude": "string",
                "Longitude": "string",
                "PostalCode": "string",
                "HouseNumber": "string",
            },
        ).rename(
            columns={
                "Street": "VIA_NOMBRE",
                "HouseNumber": "NUMERO",
                "PostalCode": "COD_POSTAL",
                "Province": "PROVINCIA",
                "Country": "PAIS",
                "Latitude": "LATITUD",
                "Longitude": "LONGITUD",
            }
        )

        self.madrid_df = pd.read_csv(
            madrid_file,
            sep=";",
            encoding="latin-1",
            dtype=str,
        )


    def get_address_spain_df(self):

        df = self.spain_df.copy()

        df["TIPO_NDP"] = [
            random.choice(
                [
                    "PARCELA",
                    "PORTAL",
                    "GARAJE",
                    "JARDÍN/PARQUE",
                    "FRENTE FACHADA",
                ]
            )
            for _ in range(len(df))
        ]

        df["PLANTA"] = None
        df["LETRA"] = None

        mask = df["TIPO_NDP"] == "PORTAL"

        df.loc[mask, "PLANTA"] = [
            random.randint(1, 12)
            for _ in range(mask.sum())
        ]

        df.loc[mask, "LETRA"] = [
            random.choice(["A", "B", "C", "D", "E", "F"])
            for _ in range(mask.sum())
        ]

        return df

    def get_address_madrid_df(self):

        df = self.madrid_df.copy()

        # ----------------------------------------------
        # Limpieza de códigos
        # ----------------------------------------------

        df["DISTRITO"] = (
            df["DISTRITO"]
            .str.strip()
            .replace("", pd.NA)
        )

        df["BARRIO"] = (
            df["BARRIO"]
            .str.strip()
            .replace("", pd.NA)
        )

        df = df.dropna(
            subset=["DISTRITO", "BARRIO"]
        ).copy()

        # ----------------------------------------------
        # Normalizar códigos
        # ----------------------------------------------

        df["DISTRITO"] = (
            df["DISTRITO"]
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(2)
        )

        df["BARRIO"] = (
            df["BARRIO"]
            .str.replace(r"\.0$", "", regex=True)
        )

        # ----------------------------------------------
        # Nombres de distrito y barrio
        # ----------------------------------------------

        df["DISTRITO_NOMBRE"] = [
            MADRID_ZONAS.get(
                distrito,
                {}
            ).get("nombre")
            for distrito in df["DISTRITO"]
        ]

        df["BARRIO_NOMBRE"] = [
            MADRID_ZONAS.get(
                distrito,
                {}
            ).get("barrios", {}).get(
                barrio
            )
            for distrito, barrio in zip(
                df["DISTRITO"],
                df["BARRIO"],
            )
        ]

        # ----------------------------------------------
        # Datos administrativos
        # ----------------------------------------------

        df["REGION"] = "Comunidad de Madrid"
        df["PROVINCIA"] = "Madrid"
        df["LOCALIDAD"] = "Madrid"
        df["PAIS"] = "España"

        # ----------------------------------------------
        # Tipo de dirección
        # ----------------------------------------------

        df["TIPO_NDP"] = [
            random.choice(
                [
                    "PARCELA",
                    "PORTAL",
                    "GARAJE",
                    "JARDÍN/PARQUE",
                    "FRENTE FACHADA",
                ]
            )
            for _ in range(len(df))
        ]

        # ----------------------------------------------
        # Planta y LETRA
        # ----------------------------------------------

        df["PLANTA"] = None
        df["LETRA"] = None

        mask = df["TIPO_NDP"] == "PORTAL"

        df.loc[mask, "PLANTA"] = [
            random.randint(1, 12)
            for _ in range(mask.sum())
        ]

        df.loc[mask, "LETRA"] = [
            random.choice(
                ["A", "B", "C", "D", "E", "F"]
            )
            for _ in range(mask.sum())
        ]

        # ----------------------------------------------
        # Coordenadas DMS -> decimal
        # ----------------------------------------------

        df["LATITUD"] = [
            self.coordenada_dms_a_decimal(valor)
            for valor in df["LATITUD"]
        ]

        df["LONGITUD"] = [
            self.coordenada_dms_a_decimal(valor)
            for valor in df["LONGITUD"]
        ]

        # ----------------------------------------------
        # El DataFrame ya contiene coordenadas decimales
        # ----------------------------------------------

        df["latitude"] = df["LATITUD"]
        df["longitude"] = df["LONGITUD"]

        # ----------------------------------------------
        # Convertir coordenadas explícitamente
        # ----------------------------------------------

        df["LATITUD"] = pd.Series(
            df["LATITUD"],
            index=df.index,
            dtype="float64",
        )

        df["LONGITUD"] = pd.Series(
            df["LONGITUD"],
            index=df.index,
            dtype="float64",
        )

        df["latitude"] = df["LATITUD"]
        df["longitude"] = df["LONGITUD"]

       

   

        return df.reset_index(drop=True)

    @staticmethod
    def coordenada_dms_a_decimal(valor):

        if pd.isna(valor):
            return None

        valor = str(valor).strip().upper()

        # Ejemplos:
        # 40°26'15.32'' N
        # 3°36'5.49'' W

        patron = (
            r"^\s*"
            r"(\d+)\s*°\s*"
            r"(\d+)\s*['’]\s*"
            r"([\d.,]+)\s*['\"]{1,2}\s*"
            r"([NSEOW])"
            r"\s*$"
        )

        match = re.match(
            patron,
            valor,
        )

        if not match:
            raise ValueError(
                f"Formato de coordenada no reconocido: {valor}"
            )

        grados = float(
            match.group(1)
        )

        minutos = float(
            match.group(2)
        )

        segundos = float(
            match.group(3).replace(",", ".")
        )

        direccion = match.group(4)

        decimal = (
            grados
            + minutos / 60
            + segundos / 3600
        )

        if direccion in ("S", "W", "O"):
            decimal = -decimal

        return decimal

