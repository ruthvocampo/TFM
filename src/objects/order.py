class Order:
    def __init__( self, id_order, id_driver, order_date, order_delivery_date, status, num_products, type_order, pickup_street, pickup_house_number, pickup_floor, pickup_letter, pickup_city, pickup_postal_code, pickup_country, delivery_street, delivery_house_number, delivery_floor, delivery_letter, delivery_city, delivery_postal_code, delivery_country ):
        self.id_order = id_order
        self.id_driver = id_driver
        self.order_date = order_date
        self.order_delivery_date = order_delivery_date
        self.status = status
        self.num_products = num_products
        self.type_order = type_order
        self.pickup_street = pickup_street
        self.pickup_house_number = pickup_house_number
        self.pickup_floor = pickup_floor
        self.pickup_letter = pickup_letter
        self.pickup_city = pickup_city
        self.pickup_postal_code = pickup_postal_code
        self.pickup_country = pickup_country
        self.delivery_street = delivery_street
        self.delivery_house_number = delivery_house_number
        self.delivery_floor = delivery_floor
        self.delivery_letter = delivery_letter
        self.delivery_city = delivery_city
        self.delivery_postal_code = delivery_postal_code
        self.delivery_country = delivery_country
        
    def set_order_delivery_date(self, order_delivery_date):
        self.order_delivery_date = order_delivery_date
    
    def set_status(self, status):
        self.status = status
        
