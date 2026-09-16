class Route:

    def __init__( self, id_route, id_driver, postal_code, street, house_number, qualifier="", latitude=None, longitude=None, priority=0 ):
        self.id_route = id_route
        self.id_driver = id_driver
        self.postal_code = postal_code
        self.street = street
        self.house_number = house_number
        self.qualifier = qualifier
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.priority = priority

    def __repr__(self):
        return (
            f"Route("
            f"id_route={self.id_route}, "
            f"id_driver='{self.id_driver}', "
            f"postal_code='{self.postal_code}', "
            f"street='{self.street}', "
            f"house_number='{self.house_number}', "
            f"latitude={self.latitude}, "
            f"longitude={self.longitude}, "
            f"priority={self.priority}"
            f")"
        )