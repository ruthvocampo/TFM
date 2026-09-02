from src.simulator.simulator import Simulator
from src.generator.weather_event import WeatherEventGenerator
from src.apis.weather_api import WeatherApi
from src.apis.traffic_api import TrafficApi

simulator = Simulator()

""" simulator.generate_initial_data()

events = simulator.create_order_events(10)

print(events)
print("################ 2")
events = simulator.create_order_events(10)
print(events)

gps = simulator.create_gps_events(20)
print(gps) """


"""weather = WeatherEventGenerator()

data = weather.generate_events()
#print(data)
#/dynamicAPI"""

traffic_api = TrafficApi()
xml_data = traffic_api.get_info()
print(xml_data[:1000])