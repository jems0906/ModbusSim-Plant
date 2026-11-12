"""Deliberately simplified, non-safety-rated combined-cycle process model."""

import math
import random


class PlantModel:
    def __init__(self, seed=7):
        self.random = random.Random(seed)
        self.time = 0.0
        self.mode_elapsed = 0.0
        self.mode = "steady"
        self.fuel_valve = 60.0
        self.fuel_flow = 6.0
        self.feedwater_valve = 60.0
        self.pump_running = True
        self.bypass_open = False
        self.gas_load = 360.0
        self.drum_level = 50.0
        self.steam_flow = 60.0
        self.feedwater_flow = 60.0
        self.exhaust_temp = 480.0
        self.steam_pressure = 100.0
        self.steam_temp = 500.0
        self.steam_load = 180.0
        self.extraction_pressure = 20.0
        self.frequency = 60.0
        self.mvar = 0.0
        self.breaker_closed = True

    def step(self, seconds=1.0):
        if seconds <= 0:
            raise ValueError("step duration must be positive")
        self.time += seconds
        self.mode_elapsed += seconds
        fuel = self.fuel_valve if self.mode != "shutdown" else 0.0
        if self.mode == "startup":
            fuel = min(fuel, 20.0 + self.mode_elapsed / 30.0)
        self.fuel_flow = fuel * 0.1
        alpha = 1.0 - math.exp(-seconds / 45.0)
        self.gas_load += (fuel * 6.0 - self.gas_load) * alpha
        self.exhaust_temp += (300.0 + fuel * 3.0 - self.exhaust_temp) * alpha
        target_steam = max(0.0, (self.exhaust_temp - 300.0) / 3.0)
        self.steam_flow += (target_steam - self.steam_flow) * (1.0 - math.exp(-seconds / 90.0))
        target_feed = self.feedwater_valve if self.pump_running else 0.0
        self.feedwater_flow += (target_feed - self.feedwater_flow) * (1.0 - math.exp(-seconds / 15.0))
        drift = 0.004 * math.sin(self.time / 240.0)
        noise = self.random.uniform(-0.002, 0.002)
        self.drum_level = max(0.0, min(100.0, self.drum_level + ((self.feedwater_flow - self.steam_flow) * 0.008 + drift + noise) * seconds))
        self.steam_pressure += (self.steam_flow * 1.667 - self.steam_pressure) * alpha
        self.steam_temp += (350.0 + self.steam_flow * 2.5 - self.steam_temp) * alpha
        self.steam_load += (self.steam_flow * 3.0 - self.steam_load) * alpha
        self.extraction_pressure = self.steam_pressure * 0.2

    @property
    def generator_mw(self):
        return (self.gas_load + self.steam_load) if self.breaker_closed else 0.0