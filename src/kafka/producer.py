import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema

from pathlib import Path

from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.serialization import SerializationContext, MessageField

from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.avro import AvroSerializer


class KafkaProducer:

    def __init__(self):
        self.config = self.read_config()

        # ---------------------------------------------------------
        # Kafka
        # ---------------------------------------------------------
        # CARGAR .ENV DESDE LA RAÍZ DEL PROYECTO

        base_dir = Path(__file__).resolve().parents[2]
        env_path = base_dir / ".env"

        print(f"[ENV] Buscando .env en: {env_path}")

        if not env_path.exists():
            raise FileNotFoundError(
                f"No se ha encontrado el archivo .env: {env_path}"
            )
        print("ENCONTRADO")
        load_dotenv(env_path, override=True)

        # VARIABLES KAFKA

        bootstrap_servers = os.getenv(
            "CONFLUENT_BOOTSTRAP_SERVERS"
        )

        kafka_api_key = os.getenv(
            "CONFLUENT_API_KEY"
        )

        kafka_api_secret = os.getenv(
            "CONFLUENT_API_SECRET"
        )

        # VARIABLES SCHEMA REGISTRY

        schema_registry_url = os.getenv(
            "SCHEMA_REGISTRY_URL"
        )

        schema_registry_api_key = os.getenv(
            "SCHEMA_REGISTRY_API_KEY"
        )

        schema_registry_api_secret = os.getenv(
            "SCHEMA_REGISTRY_API_SECRET"
        )

        # VALIDAR VARIABLES

        required = {
            "CONFLUENT_BOOTSTRAP_SERVERS": bootstrap_servers,
            "CONFLUENT_API_KEY": kafka_api_key,
            "CONFLUENT_API_SECRET": kafka_api_secret,
            "SCHEMA_REGISTRY_URL": schema_registry_url,
            "SCHEMA_REGISTRY_API_KEY": schema_registry_api_key,
            "SCHEMA_REGISTRY_API_SECRET": schema_registry_api_secret,
        }

        missing = [
            name
            for name, value in required.items()
            if not value
        ]

        if missing:
            raise ValueError(
                "Faltan variables de entorno: "
                + ", ".join(missing)
            )

        print("[ENV] Variables de entorno cargadas correctamente")

        # KAFKA CONFIG

        kafka_config = {
            "bootstrap.servers": bootstrap_servers,
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "PLAIN",
            "sasl.username": kafka_api_key,
            "sasl.password": kafka_api_secret,
            "client.id": "logistics-simulator",
        }
        

        self.producer = Producer(kafka_config)
        self.admin_client = AdminClient(kafka_config)

        # ---------------------------------------------------------
        # Schema Registry
        # ---------------------------------------------------------
        schema_registry_config = {
            "url": self.config["SCHEMA_REGISTRY_URL"],
            "basic.auth.user.info": (
                f'{self.config["SCHEMA_REGISTRY_API_KEY"]}:'
                f'{self.config["SCHEMA_REGISTRY_API_SECRET"]}'
            ),
        }

        self.schema_registry_client = SchemaRegistryClient(
            schema_registry_config
        )

        # ---------------------------------------------------------
        # Avro serializers
        # ---------------------------------------------------------
        base_dir = Path(__file__).resolve().parents[2]
        schemas_dir = base_dir / "src"/"kafka"/"schemas"

        self.serializers = {}

        schema_files = {
            "order-events": schemas_dir / "order_event.avsc",
            "gps-events": schemas_dir / "gps_event.avsc",
            "incident-events": schemas_dir / "incident_event.avsc",
       
        }

        for topic, schema_path in schema_files.items():
            self.serializers[topic] = self.create_serializer(
                topic,
                schema_path
            )

    # =============================================================
    # CONFIG
    # =============================================================

    def read_config(self):
        config = {}

        env_path = Path(".env")

        if not env_path.exists():
            raise FileNotFoundError(
                "No se ha encontrado el archivo .env"
            )

        with open(env_path, "r", encoding="utf-8") as fh:

            for line in fh:
                line = line.strip()

                if not line:
                    continue

                if line.startswith("#"):
                    continue

                parameter, value = line.split("=", 1)

                parameter = parameter.strip()
                value = value.strip()

                # Quitar comillas si existen
                if (
                    len(value) >= 2
                    and value[0] == '"'
                    and value[-1] == '"'
                ):
                    value = value[1:-1]

                if (
                    len(value) >= 2
                    and value[0] == "'"
                    and value[-1] == "'"
                ):
                    value = value[1:-1]

                config[parameter] = value

        return config

    # =============================================================
    # SCHEMA REGISTRY / AVRO
    # =============================================================

    def create_serializer(self, topic, schema_path):

        print(
            f"Registrando schema para {topic}: "
            f"{schema_path}"
        )

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_str = f.read()

        # El subject que utilizamos será:
        #
        # order-events-value
        # gps-events-value
   
        subject = f"{topic}-value"

        schema = Schema(
            schema_str,
            "AVRO"
        )

        # Registrar explícitamente antes de producir
        schema_id = self.schema_registry_client.register_schema(
            subject,
            schema
        )

        print(
            f"Schema registrado: {subject} "
            f"(id={schema_id})"
        )

        serializer = AvroSerializer(
            self.schema_registry_client,
            schema_str,
            conf={
                "auto.register.schemas": False
            }
        )

        return serializer

    # =============================================================
    # PRODUCE
    # =============================================================

    def delivery_report(self,err, msg):
        if err is not None:
            print(f"[KAFKA ERROR] {err}")
        else:
            print(
                f"[KAFKA OK] topic={msg.topic()} "
                f"partition={msg.partition()} "
                f"offset={msg.offset()}"
            )


    def produce(self, topic, key, value):
        print(f"[PRODUCE] topic={topic}")
        serializer = self.serializers[topic]
        context = SerializationContext(topic, MessageField.VALUE)

        serialized_value = serializer(value, context)
        
        print(
            f"[AVRO] topic={topic} "
            f"size={len(serialized_value)} "
            f"header={serialized_value[:10].hex()}"
        )

        self.producer.produce(
            topic=topic,
            key=str(key),
            value=serialized_value,
            callback=self.delivery_report
        )

        # Permite que confluent-kafka procese entregas
        self.producer.poll(0)
    # =============================================================
    # FLUSH
    # =============================================================

    def flush(self):
        remaining = self.producer.flush()

        if remaining > 0:
            print(
                f"Advertencia: quedan {remaining} mensajes pendientes."
            )

    # =============================================================
    # TOPICS
    # =============================================================

    def create_topics(self):

        topics = [
            NewTopic(
                "order-events",
                num_partitions=3
            ),
            NewTopic(
                "gps-events",
                num_partitions=3
            ),
            NewTopic(
                "incident-events",
                num_partitions=3
            )
        ]

        existing_topics = (
            self.admin_client
            .list_topics(timeout=10)
            .topics
        )

        topics_to_create = [
            topic
            for topic in topics
            if topic.topic not in existing_topics
        ]

        if not topics_to_create:
            print("Todos los topics ya existen.")
            return

        futures = self.admin_client.create_topics(
            topics_to_create
        )

        for topic, future in futures.items():

            try:
                future.result()

                print(
                    f"Topic creado: {topic}"
                )

            except Exception as e:

                print(
                    f"Error creando topic {topic}: {e}"
                )