# Logic programming guide

Programs are JSON in `control/programs`; each has a name, a human-readable `comment`, and ordered `instructions`. Restart the service after editing: programs are loaded at controller startup. Each scan executes drum, load, then interlocks, so the trip overrides normal outputs. Every scan logs UTC time, simulated time, input snapshot, per-program intermediate decisions, and final outputs to `logs/control.jsonl`, rotated at 5 MiB with three backups.

Instructions:

| Operation | Fields | Meaning |
| --- | --- | --- |
| `read` | `source`, `as` | Read a named snapshot value into a local variable. |
| `compare` | `left`, `operator`, `right`, `as` | Compare a variable to a numeric constant using `<`, `<=`, `>`, `>=`, `==`. |
| `proportional` | `setpoint`, `input`, `gain`, `as`, plus `base` or `base_scale` | Add proportional error to a variable base or scaled setpoint; clamp to 0-100. |
| `set_output` | `target`, `value` | Write a local variable to a modeled plant output. |
| `timer_on` | `condition`, `delay`, `as` | True after condition remains true for delay seconds; resets immediately when false. |
| `timer_off` | `condition`, `delay`, `as` | True immediately on condition; stays true for delay seconds after it becomes false. |
| `latch` | `condition`, `target` | Set a controller boolean when condition is true. |
| `reset` | `condition`, `request`, `target` | Clear a latch when both condition and controller request are true. |
| `interlock_outputs` | `condition` | Apply the named controller latch to pump and bypass. |

Timers advance by the scan duration supplied to `run`; delays are in simulated seconds. Program files are trusted local configuration, not an untrusted scripting sandbox. Test any change and update the narrative and register map when relevant.