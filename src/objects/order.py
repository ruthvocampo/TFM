class Order:
    def __init__(self, id_order, id_driver, order_date, order_delivery_date, status, num_products, type_order, pickup_address, delivery_address):    
        self.id_order = id_order
        self.id_driver = id_driver
        self.order_date = order_date
        self.order_delivery_date = order_delivery_date
        self.status = status
        self.num_products = num_products
        self.type_order = type_order
        self.pickup_address = pickup_address
        self.delivery_address = delivery_address
        
    def set_order_delivery_date(self, order_delivery_date):
        self.order_delivery_date = order_delivery_date
    
    def set_status(self, status):
        self.status = status
        
