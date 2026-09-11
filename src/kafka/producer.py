from confluent_kafka import Producer
from confluent_kafka import admin
from confluent_kafka.admin import AdminClient, NewTopic


class KafkaProducer:
    
    def __init__(self):
        
        self.config= self.read_config()
        # creates a new producer instance
        self.producer = Producer(self.config)
        # AdminClient para gestionar topics
        self.admin_client = AdminClient(self.config)
        
    def read_config(self):
        # reads the client configuration from client.properties
        # and returns it as a key-value map
        config = {}
        with open(".env") as fh:
            for line in fh:
                line = line.strip()
                if len(line) != 0 and line[0] != "#":
                    parameter, value = line.strip().split('=', 1)
                    config[parameter] = value.strip()
        return config

    def produce(self, topic, key, value):
       

        # produces message
        self.producer.produce(topic, key=key, value=value)
        print(f"Produced message to topic {topic}: key = {key:12} value = {value:12}")

        # send any outstanding or buffered messages to the Kafka broker
        self.producer.flush()
        
        
    def create_topics(self):
    
            topics = [
                NewTopic("order-events", num_partitions=3),
                NewTopic("gps-events", num_partitions=3),
                NewTopic("incident-events", num_partitions=3),
                NewTopic("traffic-events", num_partitions=3),
                NewTopic("weather-events", num_partitions=3)
            ]
    
            existing_topics = self.admin_client.list_topics(timeout=10).topics
    
            topics_to_create = [
                topic
                for topic in topics
                if topic.topic not in existing_topics
            ]
    
            if not topics_to_create:
                print("Todos los topics ya existen.")
                return
    
            futures = self.admin_client.create_topics(topics_to_create)
    
            for topic, future in futures.items():
                try:
                    future.result()
                    print(f"Topic creado: {topic}")
                except Exception as e:
                    print(f"Error creando topic {topic}: {e}")
