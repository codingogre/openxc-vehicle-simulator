from .data_calc import DataCalc

class TorqueCalc(DataCalc):
    def __init__(self):
        self.initialize_data()

    def initialize_data(self):
        self.data = 0.0
        self.engine_to_torque = 500.0 / 16382.0

    def iterate(self, accelerator, engine_speed):  # Any necessary data should be passed in
        drag = engine_speed * self.engine_to_torque
        power = accelerator * 15
        self.data = power - drag
        return

