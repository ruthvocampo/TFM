from pyspark.sql import DataFrame as DF, functions as F, SparkSession
from pyspark.sql.avro.functions import from_avro
from Core.Config_client import ConfigClient


class MotorIngesta:
    
    def __init__(self, ingestion_config: dict, landing_path: str, bronze_path: str, schema_registry, kafka_opts):
        self.ingestion_config = ingestion_config
        self.spark = SparkSession.builder.appName("MotorIngesta").getOrCreate()
        self.landing_path = landing_path
        self.bronze_path = bronze_path

        
    def read_batch_file(self) -> DF:
        # Obtenemos la información de la configuración
        source = self.ingestion_config["source"]

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
    
    
    """ 
    def read_streaming_file(self) -> DF:
        datasource = self.ingestion_config.get("datasource")
        dataset = self.ingestion_config.get("dataset")
        source = self.ingestion_config.get("source")
        format = source.get("format")
        # schema = source.get("schema")

        if "kafka" == format:
            opts = self.kafka_spark_opts.copy()
            opts.update(source.get("options"))
            topic = source.get("options").get("subscribe")
            value_format = source.get("value_format")
            df = (self.spark.readStream
                  .format(format)
                  .options(**opts)
                  .load())
            df = df.withColumn("key", F.expr("cast(key as string)"))
            if "avro" == value_format:
                value_subject = f"{topic}-value"
                value_schema = self.schema_registry_client.get_latest_version(value_subject).schema.schema_str
                df = df.withColumn("value", from_avro(F.expr("substring(value,6,length(value)-5)"), value_schema)).select(
                    "*", "value.*").drop("value")
            elif "json" == value_format:
                json_schema = source.get("json_schema")
                df = df.withColumn("value", F.from_json(F.col("value").cast("string"), json_schema)).select("*",
                                                                                                            "value.*").drop(
                    "value")
            else:
                raise Exception(f"Unsupported value format {value_format}")
        else:
            raise Exception(f'No source format "{format}" implemented!') 

        return df.withColumn("_ingested_at", F.current_timestamp())"""
    
    
    def read(self, mode):
        if mode == "batch":
            df = self.read_batch_file()
            """ elif mode == "streaming":
                df = self.read_streaming_file()"""
        else:
            raise Exception("ERROR: No se ha especificado el modo del procesamiento")
        return df
