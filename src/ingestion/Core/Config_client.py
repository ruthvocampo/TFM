class ConfigClient:
    def __init__(self, path_config="/dbfs/FileStore/client_properties"):
        self.path_config=path_config
        self.config= self._load()

    def _load(self):
        conf = {}

        with open(self.path_config) as f:
            for line in f:
                line = line.strip()

                if line and not line.startswith("#"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        conf[k.strip()] = v.strip()

        return conf

    # CONFIGURACIÓN DE KAFKA
    def kafka(self):
        return {
            "kafka.bootstrap.servers": self.config["bootstrap.servers"],
            "kafka.security.protocol": self.config["security.protocol"],
            "kafka.sasl.mechanisms": self.config["sasl.mechanisms"],
            "kafka.sasl.username": self.config["sasl.username"],
            "kafka.sasl.password": self.config["sasl.password"],
            "kafka.session.timeout.ms" : self.config["session.timeout.ms"],
            "client.id": self.config["client.id"]
        }


    # CONFIGURACIÓN DE SCHEMA REGISTRY
    def schema_registry(self):
        return {
            "url": self.config["schema.registry.url"],
            "basic.auth.user.info": (
                f'{self.config["schema.registry.username"]}:'
                f'{self.config["schema.registry.password"]}'
            )
        }
