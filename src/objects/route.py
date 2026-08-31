class Route:

    def __init__(self, id_route, id_driver, postal_code, street):
        self.id_route = id_route
        self.id_driver = id_driver
        self.postal_code = postal_code
        self.street = street

    def __repr__(self):
        return (
            f"Route("
            f"id_route={self.id_route}, "
            f"id_driver='{self.id_driver}', "
            f"postal_code='{self.postal_code}', "
            f"street='{self.street}'"
            f")"
        )