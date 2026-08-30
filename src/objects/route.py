from datetime import datetime


class Route:

    def __init__(self, id_route, id_driver):

        self.id_route = id_route
        self.id_driver = id_driver

        self.orders = []

        self.status = "CREADA"

        self.created_at = datetime.now()

    def add_order(self, order):

        self.orders.append(order)

    def remove_order(self, order):

        if order in self.orders:
            self.orders.remove(order)

    def get_orders(self):

        return self.orders

    def number_of_orders(self):

        return len(self.orders)

    def start(self):

        self.status = "EN REPARTO"

    def finish(self):

        self.status = "FINALIZADA"

    def __repr__(self):

        return (
            f"Route("
            f"id_route={self.id_route}, "
            f"id_driver={self.id_driver}, "
            f"orders={len(self.orders)}, "
            f"status='{self.status}'"
            f")"
        )

