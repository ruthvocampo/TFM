from datetime import datetime

class OrderGenerator:

    def __init__(self, historical_orders, fecha_actual):
        self.historical_orders = historical_orders
        self.orders = []
        self.fecha_actual = fecha_actual

    def get_orders_for_today(self):
        """
        Obtiene los pedidos que llegaron a la nave durante
        la madrugada y siguen pendientes de asignación.
        """

        today = datetime.now().date()

        self.orders = [order
            for order in self.historical_orders
            if (
                order.status in ["PENDIENTE DE ASIGNACIÓN ENTREGA", "PENDIENTE DE ASIGNACIÓN RECOGIDA"]
                and order.status_modified_date.date() == today
            )
        ]

        print(f"Generados {len(self.orders)} pedidos para hoy.")

        return self.orders