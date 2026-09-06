from src.simulator.simulator import Simulator

from datetime import datetime


now = datetime(2026, 9, 6, 9, 30)


simulator = Simulator(fecha_actual=now)

historical, orders, drivers, routes = simulator.generate_initial_data()
print("historical:", type(historical), len(historical) if historical is not None else None)
print("orders:", type(orders), len(orders) if orders is not None else None)
print("drivers:", type(drivers), len(drivers) if drivers is not None else None)
print("routes:", type(routes), len(routes) if routes is not None else None)

print(len(historical), len(orders), len(drivers), len(routes))

simulator.generate_files(historical, orders, drivers, routes)

events = simulator.create_order_events(10)

print(events)
print("################ 2")
events = simulator.create_order_events(10)
print(events)




gps = simulator.create_gps_events(20)
print(gps)

generator_simulation_events = simulator.generate_simulation_events(num_order_events=10, num_gps_events=20)

generator_real_events = simulator.generate_real_data_files()
