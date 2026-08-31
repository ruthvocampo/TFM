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

    def __init__(self, address_file, repetitions= 30):

        self.address_file = address_file
        self.repetitions = repetitions

    def get_address_df(self):


        self.address_df = pd.read_csv(DATA_ADDRESS / self.address_file)

        self.address_df = self.address_df.loc[self.address_df.index.repeat(self.repetitions)].reset_index(drop=True)

        self.address_df["building_type"] = [random.choice(BUILDING_TYPES) for _ in range(len(self.address_df))]

        self.address_df["Floor"] = None
        self.address_df["Door"] = None

        mask = (self.address_df["building_type"]== "EDIFICIO_RESIDENCIAL")

        self.address_df.loc[mask, "Floor"] = [random.randint(1, 12)for _ in range(mask.sum())]

        self.address_df.loc[mask, "Door"] = [random.choice(["A", "B", "C", "D", "E", "F"]) for _ in range(mask.sum())]

        return self.address_df
