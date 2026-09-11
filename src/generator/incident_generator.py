import random

from src.objects.incident import Incident


INCIDENT_REASONS = [
    "DIRECCIÓN INCORRECTA",
    "CÓDIGO POSTAL INCORRECTO",
    "FALTA NÚMERO DE PISO",
    "NO ES POSIBLE CONTACTAR CON EL DESTINATARIO",
    "DESTINATARIO AUSENTE",
    "ACCESO AL DOMICILIO NO POSIBLE",
    "PAQUETE DAÑADO",
    "PAQUETE NO LOCALIZADO",
    "OTRO"
]


OBSERVATIONS = {

    "DIRECCIÓN INCORRECTA": [
        "La dirección indicada no permite localizar el domicilio."
    ],

    "CÓDIGO POSTAL INCORRECTO": [
        "El código postal indicado no coincide con la dirección."
    ],

    "FALTA NÚMERO DE PISO": [
        "No se ha indicado el número de piso."
    ],

    "NO ES POSIBLE CONTACTAR CON EL DESTINATARIO": [
        "No es posible contactar con el destinatario."
    ],

    "DESTINATARIO AUSENTE": [
        "El destinatario no se encuentra en el domicilio."
    ],

    "ACCESO AL DOMICILIO NO POSIBLE": [
        "No es posible acceder al edificio."
    ],

    "PAQUETE DAÑADO": [
        "El paquete presenta daños visibles."
    ],

    "PAQUETE NO LOCALIZADO": [
        "El paquete no ha podido ser localizado."
    ],

    "OTRO": [
        "Incidencia no contemplada en las categorías anteriores."
    ]
}


class IncidentGenerator:

    def __init__(self):

        self.incidents = []

        self.incident_counter = 0

    def create_incident(
        self,
        order,
        incident_date
    ):

        self.incident_counter += 1

        reason = random.choice(
            INCIDENT_REASONS
        )

        observations = random.choice(
            OBSERVATIONS[reason]
        )

        incident = Incident(

            id_incident=(
                f"INC{self.incident_counter:05d}"
            ),

            id_order=order.id_order,

            id_driver=order.id_driver,

            incident_date=incident_date,

            incident_reason=reason,

            observations=observations,

            resolved=False,

            resolution_date=None,

            resolution_action=None
        )

        self.incidents.append(
            incident
        )

        return incident

    def get_incidents(self):

        return self.incidents