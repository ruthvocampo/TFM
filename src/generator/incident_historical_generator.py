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
        "La dirección indicada no coincide con la ubicación encontrada.",
        "La dirección proporcionada no permite localizar el domicilio."
    ],
    "CÓDIGO POSTAL INCORRECTO": [
        "El código postal no coincide con la dirección.",
        "El código postal indicado pertenece a otra zona."
    ],
    "FALTA NÚMERO DE PISO": [
        "No se ha indicado el número de piso.",
        "El domicilio requiere información adicional sobre el piso."
    ],
    "NO ES POSIBLE CONTACTAR CON EL DESTINATARIO": [
        "No se consigue contactar con el destinatario.",
        "No responde a las llamadas de contacto."
    ],
    "DESTINATARIO AUSENTE": [
        "El destinatario no se encuentra en el domicilio.",
        "No hay nadie disponible para recibir el pedido."
    ],
    "ACCESO AL DOMICILIO NO POSIBLE": [
        "No es posible acceder al edificio.",
        "El acceso al domicilio se encuentra bloqueado."
    ],
    "PAQUETE DAÑADO": [
        "Se detecta daño visible en el paquete.",
        "El paquete presenta daños durante el transporte."
    ],
    "PAQUETE NO LOCALIZADO": [
        "El paquete no ha podido ser localizado.",
        "No se encuentra el paquete en el vehículo."
    ],
    "OTRO": [
        "Incidencia no contemplada en las categorías anteriores."
    ]
}


class IncidentHistoricalGenerator:

    def __init__(self, historical_orders):

        self.historical_orders = historical_orders
        self.historical_incidents = []
        self.incident_counter = 0

    def create_historical_incidents(self):

        for order in self.historical_orders:

            status_history = order.status_history

            # Si el pedido nunca tuvo una incidencia,
            # no generamos ningún registro.
            if "INCIDENTADO" not in status_history:
                continue

            self.incident_counter += 1

            incident_date = status_history["INCIDENTADO"]

            # Repartidor que tenía la orden cuando ocurrió
            # la incidencia.
            id_driver = order.id_driver

            # -------------------------------------------------
            # Comprobar si la incidencia fue resuelta
            # -------------------------------------------------

            resolution_date = None
            resolution_action = None
            resolved = False

            # Si después de INCIDENTADO vuelve a ASIGNADO ENTREGA,
            # consideramos que la incidencia se resolvió.
            if "ASIGNADO ENTREGA" in status_history:

                reassignment_date = status_history[
                    "ASIGNADO ENTREGA"
                ]

                # Solo debe contar como resolución si la
                # reasignación ocurrió después de la incidencia.
                if reassignment_date > incident_date:

                    resolved = True

                    resolution_date = reassignment_date

                    resolution_action = (
                        "REASIGNACIÓN AL MISMO REPARTIDOR"
                    )

            # -------------------------------------------------
            # Crear incidencia
            # -------------------------------------------------

            incident_reason = self._generate_reason()

            observations = self._generate_observations(
                incident_reason
            )

            incident = Incident(
                id_incident=f"INC{self.incident_counter:05d}",
                id_order=order.id_order,
                id_driver=id_driver,
                incident_date=incident_date,
                incident_reason=incident_reason,
                observations=observations,
                resolved=resolved,
                resolution_date=resolution_date,
                resolution_action=resolution_action,
            )

            self.historical_incidents.append(
                incident
            )

        print(
            f"Generadas "
            f"{len(self.historical_incidents)} "
            f"incidencias históricas."
        )

        return self.historical_incidents

    def _generate_reason(self):

        return random.choice(
            INCIDENT_REASONS
        )

    def _generate_observations(self, reason):

        return random.choice(
            OBSERVATIONS[reason]
        )