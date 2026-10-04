"""Simulated smart-home device registry.

NOT real hardware. Every response is labeled simulated. One registry per
process; the workflow takes its registry by injection so tests stay isolated.
"""


class SimulatedDeviceRegistry:
    def __init__(self, initial=None):
        self._states = dict(initial or {})

    def get(self, device_id):
        return {
            "device_id": device_id,
            "state": self._states.get(device_id, "UNKNOWN"),
            "simulated": True,
        }

    def set(self, device_id, state):
        old = self._states.get(device_id, "UNKNOWN")
        self._states[device_id] = state
        # Read back to verify the transition actually took effect.
        new = self._states.get(device_id, "UNKNOWN")
        return {
            "device_id": device_id,
            "old_state": old,
            "new_state": new,
            "verified": new == state,
            "simulated": True,
        }
