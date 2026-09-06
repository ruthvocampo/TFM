
class Address:
    def __init__(self, Street, HouseNumber, Locality, Region, Province, PostalCode, Country, Latitude, Longitude, building_type, floor=None, door=None):
        self.Street = Street
        self.HouseNumber = HouseNumber
        self.building_type = building_type
        self.floor = floor
        self.door = door
        self.Locality = Locality
        self.Region = Region
        self.Province = Province
        self.PostalCode = PostalCode
        self.Country = Country
        self.Latitude = Latitude
        self.Longitude = Longitude
    
    def get_full_address(self):
        full_address = f"{self.Street} {self.HouseNumber}"
        if self.building_type == "EDIFICIO_RESIDENCIAL" and self.floor is not None:
            full_address += f", Piso {self.floor}"
        if self.building_type == "EDIFICIO_RESIDENCIAL" and self.door is not None:
            full_address += f", Puerta {self.door}"
        full_address += f", {self.Locality}, {self.Region}, {self.Province}, {self.PostalCode}, {self.Country}"
        return full_address
    

    def get_coordinates(self):
        return (self.Latitude, self.Longitude)
    def get_building_type(self):
        return self.building_type
    def get_floor(self):
        return self.floor
    def get_door(self):
        return self.door
    def get_locality(self):
        return self.Locality
    def get_region(self):
        return self.Region
    def get_province(self):
        return self.Province
    def get_postal_code(self):
        return self.PostalCode
    def get_country(self):
        return self.Country
    def get_street(self):
        return self.Street
    def get_house_number(self):
        return self.HouseNumber 
    
