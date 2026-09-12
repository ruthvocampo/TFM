import json
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
from src.setup import *


class OnelakeClient():
    
    def __init__(self):
        # AUTENTICACIÓN
        self.credential = DefaultAzureCredential()
        self.service_client = DataLakeServiceClient(account_url="https://onelake.dfs.fabric.microsoft.com",credential=self.credential)
        # ACCESO AL WORKSPACE
        self.filesystem_client = self.service_client.get_file_system_client(WORKSPACE)
        
    def load_file(self,load_to_folder,dir_file_to_load):
        # Convertimos a PATH
        local_file = Path(dir_file_to_load)
        local_name= local_file.name
        print()
        print("=" * 70)
        print("[ONELAKE] SUBIDA")
        print(f"[ONELAKE] Workspace: {WORKSPACE}")
        print(f"[ONELAKE] Carpeta:   {load_to_folder}")
        print(f"[ONELAKE] Fichero:   {local_name}")
        # ACCESO AL LAKEHOUSE
        self.directory_client = self.filesystem_client.get_directory_client(load_to_folder)
        file_client = self.directory_client.get_file_client(local_name)
       
        # SUBIMOS EL FICHERO
        with open(dir_file_to_load, "rb") as file:
            file_client.upload_data(file, overwrite=True)
            
            
