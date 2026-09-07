from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

ACCOUNT = "dbtfm"
CONTAINER = "tfm"

credential = DefaultAzureCredential()

service = DataLakeServiceClient(
    account_url=f"https://{ACCOUNT}.dfs.core.windows.net",
    credential=credential
)

filesystem = service.get_file_system_client(CONTAINER)


def write_file(path, data):
    file = filesystem.get_file_client(path)
    file.upload_data(data, overwrite=True)