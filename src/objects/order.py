from datetime import datetime


class Order:
    def __init__( self, id_order, id_driver, order_created_date,  order_expected_date, status, status_modified_date, num_products, type_order, type_service,  pickup_street, pickup_house_number, pickup_floor, pickup_letter, pickup_city, pickup_postal_code, pickup_country, delivery_street, delivery_house_number, delivery_floor, delivery_letter, delivery_city, delivery_postal_code, delivery_country ):
        self.id_order = id_order
        self.id_driver = id_driver
        self.order_created_date = order_created_date
        self.order_expected_date =  order_expected_date
        self.status = status
        self.status_modified_date = status_modified_date
        self.num_products = num_products
        self.type_order = type_order
        self.type_service = type_service
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
        self.status_history = {
            "EN RECOGIDA": None,
            "EN TRANSPORTE": None,
            "LLEGADA A LA NAVE": None,
            "PENDIENTE DE ASIGNACIÓN": None,
            "ASIGNADO": None,
            "RECOGIDO": None,
            "EN REPARTO": None,
            "ENTREGADO": None,
            "RECHAZADO": None,
            "CANCELADO": None,
            "INCIDENTADO": None,
        }
        
    def set_order_expected_date(self, order_expected_date):
        self.order_expected_date =  order_expected_date
    
    def set_order_expected_date(self, order_expected_date):
        self.order_expected_date = order_expected_date

    def set_status(self, status, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()

        self.status = status
        self.status_modified_date = timestamp
        self.status_history[status] = timestamp
