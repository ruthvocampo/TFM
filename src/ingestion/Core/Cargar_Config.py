import os
import json
from pathlib import Path

class CargarConfig:

    def __init__(self, globals_dict):
        self.config_path = os.path.join("../..", "config", "datasets")
        #self.config_path = Path(__file__).resolve().parent.parent / "config" / "datasets"
        self.globals_dict = globals_dict

    def load_all(self):

        configs = []

        for file in os.listdir(self.config_path):

            if file.endswith(".json"):

                with open(os.path.join(self.config_path, file)) as f:
                    config = json.load(f)

                configs.append(self._resolve(config))

        return configs

    def _resolve(self, config):

        if isinstance(config, dict):
            return {k: self._resolve(v) for k, v in config.items()}

        if isinstance(config, list):
            return [self._resolve(v) for v in config]

        if isinstance(config, str):
            for k, v in self.globals_dict.items():
                config = config.replace(f"${{{k}}}", v)
            return config

        return config