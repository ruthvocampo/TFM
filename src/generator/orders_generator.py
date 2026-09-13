from datetime import datetime,timedelta

class OrderGenerator:

    def __init__(self, historical_orders, fecha_actual):
        self.historical_orders = historical_orders
        self.orders = []
        self.fecha_actual = fecha_actual

    def get_orders_for_today(self):
        """
        Obtiene los pedidos que pueden ser planificados para el día actual.

        Prioridad:
        1. Pedidos atrasados.
        2. Pedidos cuya fecha esperada es hoy.
        3. Pedidos del día siguiente que ya hayan sido creados,
        para permitir adelantar trabajo.

        Nunca se incluyen pedidos creados después del día actual.
        """

        today = self.fecha_actual.date()

        final_statuses = [
            "RECOGIDO",
            "ENTREGADO",
            "RECHAZADO",
            "CANCELADO"
        ]

        candidates = []

        for order in self.historical_orders:

            # El pedido debe existir ya
            if order.order_created_date is None:
                continue

            if order.order_created_date.date() > today:
                continue

            # No planificar pedidos ya finalizados
            if order.status in final_statuses:
                continue

            if order.order_expected_date is None:
                continue

            expected_date = order.order_expected_date.date()

            # Solo:
            # - atrasados
            # - de hoy
            # - de mañana (para adelantar)
            if expected_date > today + timedelta(days=1):
                continue

            candidates.append(order)

        # Orden de prioridad:
        # primero los más atrasados y después los de hoy/mañana.
        candidates.sort(
            key=lambda order: order.order_expected_date
        )

        self.orders = []

        for order in candidates:

            # Reiniciar información generada por la simulación
            order.id_driver = None
            order.id_driver_pickup = None
            order.id_driver_delivery = None
            order.id_route = None

            # Estado inicial de la simulación
            if order.type_service == "RECOGIDA":

                order.status = "PENDIENTE DE ASIGNACIÓN RECOGIDA"

            elif order.type_service == "ENTREGA":

                order.status = "PENDIENTE DE ASIGNACIÓN ENTREGA"

            else:
                continue

            order.status_modified_date = self.fecha_actual
            order.status_history[order.status] = self.fecha_actual

            self.orders.append(order)

        print(f"Generados {len(self.orders)} pedidos para hoy.")

        return self.orders