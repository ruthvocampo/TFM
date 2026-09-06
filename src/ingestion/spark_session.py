import pyspark

class SparkSession:
    
    def __init__(self):
        self.spark = pyspark.sql.SparkSession.builder.appName("Simulator").getOrCreate()
        
    def get_spark_session(self):
        return self.spark
    