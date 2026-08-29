class Driver:
    def __init__(self, id_driver, name, license_number, vehicle_type, available, zone):
        self.id_driver = id_driver
        self.name = name
        self.license_number = license_number
        self.vehicle_type = vehicle_type
        self.available = available
        self.zone = zone
    
    
    def set_availability(self, available):
        self.available = available
    
    def set_zone(self, zone: list):
        self.zone = zone
    