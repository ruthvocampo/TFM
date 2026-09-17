from datetime import datetime, timedelta


class OrderGenerator:

    def __init__(
        self,
        historical_orders,
        fecha_actual
    ):

        self.historical_orders = historical_orders
        self.orders = []
        self.fecha_actual = fecha_actual

    # ============================================================
    # PEDIDOS DEL DÍA
    # ============================================================

    def get_orders_for_today(self):

        today = self.fecha_actual.date()

        final_statuses = [
            "RECOGIDO",
            "ENTREGADO",
            "RECHAZADO",
            "CANCELADO"
        ]

        candidates = []

        # --------------------------------------------------------
        # BUSCAR CANDIDATOS
        # --------------------------------------------------------

        for order in self.historical_orders:

            if order.order_created_date is None:
                continue

            if order.order_created_date.date() > today:
                continue

            if order.status in final_statuses:
                continue

            if order.order_expected_date is None:
                continue

            expected_date = (
                order.order_expected_date.date()
            )

            if expected_date > (
                today + timedelta(days=1)
            ):
                continue

            candidates.append(order)

        # --------------------------------------------------------
        # ORDENAR POR FECHA ESPERADA
        # --------------------------------------------------------

        candidates.sort(
            key=lambda order: order.order_expected_date
        )

        self.orders = []

        # --------------------------------------------------------
        # PREPARAR PEDIDOS PARA EL DÍA
        # --------------------------------------------------------

        for order in candidates:

            # Limpiar asignación anterior.
            order.id_driver = None
            order.id_driver_pickup = None
            order.id_driver_delivery = None
            order.id_route = None

            # ----------------------------------------------------
            # RECOGIDA
            # ----------------------------------------------------

            if order.type_service == "RECOGIDA":

                order.status = (
                    "PENDIENTE DE ASIGNACIÓN RECOGIDA"
                )

            # ----------------------------------------------------
            # ENTREGA
            # ----------------------------------------------------

            elif order.type_service == "ENTREGA":

                order.status = (
                    "PENDIENTE DE ASIGNACIÓN ENTREGA"
                )

            else:
                continue

            order.status_modified_date = (
                self.fecha_actual
            )

            if (
                not hasattr(order, "status_history")
                or order.status_history is None
            ):
                order.status_history = {}

            order.status_history[
                order.status
            ] = self.fecha_actual

            self.orders.append(order)

        print(
            f"Generados {len(self.orders)} "
            f"pedidos para hoy."
        )

        return self.orders