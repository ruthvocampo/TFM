class Route:
    def __init__(self, id_route, driver, orders):
        self.id_route = id_route
        self.driver = driver
        self.orders = orders
        
    def set_orders(self, orders):
        self.orders = orders
        