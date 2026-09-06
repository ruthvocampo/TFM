import json
from pyspark.sql import DataFrame as DF, functions as F, SparkSession


class MotorIngesta:
    
    def __init__(self, config: dict):
        self.config = config
        self.spark = SparkSession.builder.getOrCreate("MotorIngesta")

    def ingesta_fichero(self) -> DF:
        # Obtenemos la información de la configuración
        source = self.config["source"]

        file_format = source["format"]
        path = source["path"]

        options = source.get("options", {})
        
        
        # Leemos el fichero recibido
        reader = self.spark.read.format(file_format)
        
        for key, value in options.items():
            reader = reader.option(key, value)

        df = reader.load(path)


        # METADATOS
        # Añadimos hora de ingestión
        df = df.withColumn('_ingestion_timestamp', F.current_timestamp())

        return df

