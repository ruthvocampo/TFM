class Route:
    def __init__(self, id_route, id_driver, order_ids, route_date, start_time, end_time):
        self.id_route = id_route
        self.id_driver = id_driver
        self.order_ids = order_ids
        self.route_date = route_date
        self.start_time = start_time
        self.end_time = end_time

    def set_orders(self, order_ids):
        self.order_ids = order_ids
        
    def set_end_time(self, end_time):
        self.end_time = end_time