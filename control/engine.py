"""Data-driven simulation controller. This is not a safety system."""

import json
import math
import operator
from pathlib import Path

from control.logger import DecisionLogger

PROGRAMS = Path(__file__).parent / "programs"
COMPARISONS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge, "==": operator.eq}


class ControlEngine:
    def __init__(self, plant, logger=None):
        self.plant = plant
        self.logger = logger if logger is not None else DecisionLogger()
        self.level_setpoint = 50.0
        self.load_setpoint = 360.0
        self.low_low_alarm = False
        self.reset_trip = False
        self.timers = {}
        self.programs = [json.loads((PROGRAMS / name).read_text(encoding="utf-8")) for name in ("drum_level.json", "load_control.json", "interlocks.json")]

    def set_setpoint(self, name, value):
        limits = {"level_setpoint": (30.0, 70.0), "load_setpoint": (0.0, 600.0)}
        if name not in limits or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Invalid setpoint")
        low, high = limits[name]
        if not low <= value <= high:
            raise ValueError(f"{name} must be between {low} and {high}")
        setattr(self, name, float(value))

    def snapshot(self):
        plant = self.plant
        return {"gas_load": plant.gas_load, "exhaust_temp": plant.exhaust_temp, "fuel_valve": plant.fuel_valve, "fuel_flow": plant.fuel_flow,
                "rpm": 3600 if plant.mode != "shutdown" else 0, "load_setpoint": self.load_setpoint, "level_setpoint_batch": self.level_setpoint,
                "drum_level": plant.drum_level, "steam_pressure": plant.steam_pressure, "steam_temp": plant.steam_temp,
                "feedwater_flow": plant.feedwater_flow, "level_setpoint": self.level_setpoint, "feedwater_valve": plant.feedwater_valve,
                "steam_flow": plant.steam_flow, "steam_inlet_pressure": plant.steam_pressure, "steam_load": plant.steam_load,
                "extraction_pressure": plant.extraction_pressure, "generator_mw": plant.generator_mw, "mvar": plant.mvar,
                "frequency": plant.frequency, "breaker_closed": plant.breaker_closed, "pump_running": plant.pump_running,
                "bypass_open": plant.bypass_open, "low_low_alarm": self.low_low_alarm, "reset_trip": False,
                "exhaust_sensor": plant.exhaust_temp, "level_sensor": plant.drum_level, "pressure_sensor": plant.steam_pressure,
                "mode": plant.mode, "simulated_seconds": plant.time}

    def run(self, seconds=1.0):
        inputs = self.snapshot()
        decisions = []
        for program in self.programs:
            variables = {}
            for instruction in program["instructions"]:
                operation = instruction["op"]
                if operation == "read":
                    variables[instruction["as"]] = self.snapshot()[instruction["source"]]
                elif operation == "compare":
                    variables[instruction["as"]] = COMPARISONS[instruction["operator"]](variables[instruction["left"]], instruction["right"])
                elif operation == "proportional":
                    target = variables[instruction["setpoint"]]
                    base = variables[instruction["base"]] if "base" in instruction else target * instruction["base_scale"]
                    variables[instruction["as"]] = max(0.0, min(100.0, base + instruction["gain"] * (target - variables[instruction["input"]])))
                elif operation == "set_output":
                    setattr(self.plant, instruction["target"], variables[instruction["value"]])
                elif operation in ("timer_on", "timer_off"):
                    key = f'{program["name"]}:{instruction["as"]}'
                    active = bool(variables[instruction["condition"]])
                    previous, elapsed = self.timers.get(key, (False, 0.0))
                    if operation == "timer_on":
                        elapsed = elapsed + seconds if active else 0.0
                        result = active and elapsed >= instruction["delay"]
                    else:
                        elapsed = 0.0 if active else elapsed + seconds
                        result = active or (previous and elapsed < instruction["delay"])
                    self.timers[key] = (result, elapsed)
                    variables[instruction["as"]] = result
                elif operation == "latch":
                    if variables[instruction["condition"]]:
                        setattr(self, instruction["target"], True)
                elif operation == "reset":
                    if variables[instruction["condition"]] and getattr(self, instruction["request"]):
                        setattr(self, instruction["target"], False)
                elif operation == "interlock_outputs":
                    trip = getattr(self, instruction["condition"])
                    self.plant.pump_running = not trip
                    self.plant.bypass_open = trip
                else:
                    raise ValueError(f"Unknown instruction: {operation}")
            decisions.append({"program": program["name"], "values": variables})
        self.reset_trip = False
        outputs = self.snapshot()
        self.logger.write({"simulated_seconds": self.plant.time, "inputs": inputs, "decisions": decisions, "outputs": outputs})
        return outputs