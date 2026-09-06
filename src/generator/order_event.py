from datetime import datetime
import random


FINAL_STATUSES = {
    "ENTREGADO",
    "RECHAZADO",
    "CANCELADO",
    "INCIDENTADO",
    "RECOGIDO",
}


class OrderEvents:

    def __init__(self, orders, drivers, routes, fecha_actual):
        self.orders = orders
        self.drivers = drivers
        self.routes = routes
        self.fecha_actual = fecha_actual

        # Contador para evitar IDs de evento duplicados
        self.event_counter = 0

    # ==========================================================
    # ID EVENTO
    # ==========================================================

    def id_order_event(self):
        self.event_counter += 1
        return self.event_counter

    # ==========================================================
    # BUSCAR REPARTIDOR
    # ==========================================================

    def find_driver_for_order(self, order):
        """
        Busca en routes el repartidor que tiene asignada
        la calle del pedido.

        ENTREGA:
            utiliza la dirección de entrega.

        RECOGIDA:
            utiliza la dirección de recogida.
        """

        if order.type_service == "ENTREGA":

            postal_code = str(
                order.delivery_postal_code
            ).strip()

            street = str(
                order.delivery_street
            ).strip().upper()

        elif order.type_service == "RECOGIDA":

            postal_code = str(
                order.pickup_postal_code
            ).strip()

            street = str(
                order.pickup_street
            ).strip().upper()

        else:
            print(
                f"{order.id_order}: "
                f"tipo de servicio desconocido."
            )
            return None

        matching_routes = [ route for route in self.routes 
                           if (str(route.postal_code).strip()== postal_code and str(route.street).strip().upper()== street)]

        if not matching_routes:

            print(
                f"{order.id_order}: "
                f"no existe ruta para "
                f"{postal_code} - {street}"
            )

            return None

        # La ruta ya determina qué repartidor cubre esa calle
        driver_id = matching_routes[0].id_driver

        # Comprobamos que el conductor siga existiendo
        # y esté operativo.
        matching_driver = [driver for driver in self.drivers if driver.id_driver == driver_id]

        if not matching_driver:

            print(
                f"{order.id_order}: "
                f"el repartidor {driver_id} "
                f"no existe."
            )

            return None

        driver = matching_driver[0]

        if not bool(driver.available):

            print(
                f"{order.id_order}: "
                f"el repartidor {driver_id} "
                f"no está disponible."
            )

            return None

        print(
            f"{order.id_order}: "
            f"ruta encontrada → {driver_id}"
        )

        return driver_id

    # ==========================================================
    # SIGUIENTE ESTADO
    # ==========================================================

    def choose_next_status(self, order):
        """
        Decide el siguiente estado dependiendo del pedido
        y de su tipo de servicio.
        """

        current_status = order.status

        # ------------------------------------------------------
        # PENDIENTE DE ASIGNACIÓN
        # ------------------------------------------------------

        if current_status == "PENDIENTE DE ASIGNACIÓN":

            return random.choices(
                [
                    "ASIGNADO",
                    "CANCELADO"
                ],
                weights=[
                    0.95,
                    0.05
                ],
                k=1
            )[0]

        # ------------------------------------------------------
        # ASIGNADO
        # ------------------------------------------------------

        if current_status == "ASIGNADO":

            # Tanto las recogidas como las entregas
            # pasan primero por EN REPARTO.
            return random.choices(
                [
                    "EN REPARTO",
                    "CANCELADO"
                ],
                weights=[
                    0.95,
                    0.05
                ],
                k=1
            )[0]

        # ------------------------------------------------------
        # EN REPARTO
        # ------------------------------------------------------

        if current_status == "EN REPARTO":

            # Para una RECOGIDA, el servicio termina
            # cuando se recoge el paquete.
            if order.type_service == "RECOGIDA":

                return "RECOGIDO"

            # Para una ENTREGA, puede:
            # - entregarse
            # - rechazarse
            # - sufrir una incidencia

            return random.choices(
                [
                    "ENTREGADO",
                    "RECHAZADO",
                    "INCIDENTADO"
                ],
                weights=[
                    0.85,
                    0.10,
                    0.05
                ],
                k=1
            )[0]

        return None

    # ==========================================================
    # GENERAR EVENTO
    # ==========================================================

    def generate_event(self):
        """
        Selecciona un pedido activo, calcula su siguiente estado,
        asigna repartidor cuando corresponde y actualiza el Order.
        """

        # ------------------------------------------------------
        # 1. Buscar pedidos activos
        # ------------------------------------------------------

        active_orders = [
            order
            for order in self.orders
            if order.status not in FINAL_STATUSES
        ]

        if not active_orders:
            return None

        # ------------------------------------------------------
        # 2. Seleccionar pedido
        # ------------------------------------------------------

        order = random.choice(active_orders)

        current_status = order.status

        # ------------------------------------------------------
        # 3. Obtener siguiente estado
        # ------------------------------------------------------

        next_status = self.choose_next_status(order)

        if next_status is None:
            return None

        # ------------------------------------------------------
        # 4. Repartidor actual
        # ------------------------------------------------------

        id_driver = order.id_driver

        # ------------------------------------------------------
        # 5. Si pasa a ASIGNADO
        # buscar repartidor mediante Route
        # ------------------------------------------------------

        if next_status == "ASIGNADO":

            id_driver = self.find_driver_for_order(order)

            # No se puede asignar si no hay repartidor válido.
            if id_driver is None:
                return None

        # ------------------------------------------------------
        # 6. Crear evento
        # ------------------------------------------------------

        event_id = self.id_order_event()

        timestamp = self.fecha_actual

        event = {
            "order_event_id": event_id,
            "id_order": order.id_order,
            "id_driver": id_driver,
            "timestamp": timestamp,
            "status": next_status
        }

        # ------------------------------------------------------
        # 7. Actualizar Order
        # ------------------------------------------------------

        order.id_driver = id_driver

        order.set_status(
            next_status,
            timestamp
        )

        # ------------------------------------------------------
        # 8. Mostrar información
        # ------------------------------------------------------

        print(
            f"{order.id_order}: "
            f"{current_status} → {next_status}"
        )

        if id_driver is not None:
            print(
                f"   Repartidor: {id_driver}"
            )

        return event_id, event