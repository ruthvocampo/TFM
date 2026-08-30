import pandas as pd
from src.config.setup import DATA_ADDRESS
import random


BUILDING_TYPES = [
    "CHALET",
    "EDIFICIO_RESIDENCIAL",
    "LOCAL_COMERCIAL",
    "OFICINA"
]


class AddressGenerator:
    def __init__(self, address_file):
        self.address_df = pd.read_csv(DATA_ADDRESS / address_file)
        self.address_df['building_type'] = [random.choice(BUILDING_TYPES)  for _ in range(len(self.address_df))]
        mask = self.address_df['building_type']=='EDIFICIO_RESIDENCIAL'
        self.address_df.loc[mask,'Floor'] = random.randint(1, 12)
        self.address_df.loc[mask,'Door'] = random.choice(['A','B','C','D','E','F'])


    def get_address_df(self):
        return self.address_df