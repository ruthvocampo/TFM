class Driver:
    def __init__(self, id_driver, username, name, license_number, vehicle_type, available, zone, location):
        self.id_driver = id_driver
        self.username = username
        self.name = name
        self.license_number = license_number
        self.vehicle_type = vehicle_type
        self.available = available
        self.location = location
        self.zone = zone
    
    
    def set_availability(self, available):
        self.available = available
    
    def set_zone(self, zone: list):
        self.zone = zone
        
    def set_location(self,location):
        self.location = location
    