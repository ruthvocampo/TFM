class Incident:
    def __init__(
        self,
        id_incident,
        id_order,
        id_driver,
        incident_date,
        incident_reason,
        observations,
        resolved,
        resolution_date,
        resolution_action
    ):
        self.id_incident = id_incident
        self.id_order = id_order
        self.id_driver = id_driver
        self.incident_date = incident_date
        self.incident_reason = incident_reason
        self.observations = observations
        self.resolved = resolved
        self.resolution_date = resolution_date
        self.resolution_action = resolution_action
        
    def resolve(
    self,
    resolution_date,
    resolution_action):
        self.resolved = True
        self.resolution_date = resolution_date
        self.resolution_action = resolution_action
