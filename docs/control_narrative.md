# Control narrative

This is a training simulation, not a PLC, protection system, or qualified safety system. One scan is one simulated second. The process runs in startup, steady, and shutdown modes. Startup limits fuel according to time since entering the mode; shutdown forces modeled fuel input to zero. Returning to steady removes that limit.

## Drum level

The operator setpoint defaults to 50% and is limited to 30-70%. The feedwater valve demand is steam flow plus 2.5 times the level error, clamped to 0-100%. The steam-flow term is feedforward, while only drum level is used as feedback. This is not a full three-element controller; no feedwater flow feedback or PID integral is implemented. The model includes flow response lag, drift, and seeded noise.

## Gas turbine load

The operator setpoint defaults to 360 MW and is limited to 0-600 MW. Fuel demand is setpoint / 6 plus 0.1 times load error, clamped to 0-100%. The turbine load responds with a first-order lag. Operator setpoint commands travel HMI -> FastAPI -> Modbus FC06 -> controller setpoint -> next controller scan -> modeled valve -> plant response.

## Drum low-low interlock

At or below 20% drum level, the controller latches the low-low alarm, trips the feedwater pump, and opens the modeled bypass in the same scan. Maximum simulated detection latency is one scan (one second) after a crossing between scans. The latch remains set until level is strictly above 25% and a reset is requested. Reset below or at 25% is rejected by the logic; the request is consumed. In this deliberately simple model the bypass is an indicated state and does not add water. The trip action is specified for the exercise and should not be treated as real plant engineering advice.

## Model trade-offs

The simulator uses normalized flows, first-order time constants, a linear fuel/load relationship, and synthetic drift/noise. Fuel flow is an illustrative 0.1 kg/s per percent of effective fuel-valve demand, not a calibrated gas-flow measurement. It has no thermodynamic balances, startup permissives, actuator failure model, pressure-dependent flow, turbine chemistry, or physical safety validation. Frequency, reactive power and breaker state are fixed, and rotor speed is a mode indicator, not rotor dynamics. It is suitable for demonstrating communications and logic, not predicting a real 1,022 MW plant. A first-principles simulator would need calibrated equipment maps, conservation equations, verified operating limits, and considerably more validation.