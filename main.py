from datetime import datetime

from src.simulator.simulator import Simulator


now = datetime(2026,9,6,6,0)

simulator = Simulator(fecha_actual=now)

simulator.run()