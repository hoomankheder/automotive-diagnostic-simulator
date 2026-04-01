"""
ECU Internal State
Simulates real ECU data: sensors, session, DTCs, security
"""

import time
import math
import random


# --- Session Types (ISO 14229) ---
SESSION_DEFAULT     = 0x01
SESSION_EXTENDED    = 0x03
SESSION_PROGRAMMING = 0x02

# --- Security Levels ---
SECURITY_LOCKED   = 0x00
SECURITY_UNLOCKED = 0x01

# --- DTC Definitions ---
DTCS = {
    0xC0100: {"name": "CAN Bus Off",         "status": 0x09},
    0xB1200: {"name": "Battery Voltage Low", "status": 0x08},
    0xE0300: {"name": "Engine Misfire",      "status": 0x0F},
}


class ECUState:
    """Central state object shared across all UDS services."""

    def __init__(self):
        self.session      = SESSION_DEFAULT
        self.security     = SECURITY_LOCKED
        self._seed        = None
        self._start_time  = time.time()
        self.dtcs         = dict(DTCS)  # mutable copy
        self.ecu_name     = "SimECU_v1.0"
        self.sw_version   = "SW:1.2.3"

    # Sensor simulation (live, time-varying values)

    def _uptime_s(self) -> float:
        return time.time() - self._start_time

    @property
    def engine_rpm(self) -> int:
        """Simulates engine RPM with a slow sine wave."""
        return int(800 + 200 * math.sin(self._uptime_s() / 5))

    @property
    def coolant_temp_c(self) -> int:
        """Rises from 20 °C to 90 °C over ~60 s, then stabilises."""
        t = min(self._uptime_s() / 60, 1.0)
        return int(20 + 70 * t + random.uniform(-1, 1))

    @property
    def battery_voltage_mv(self) -> int:
        """12 V nominal with small noise (in millivolts)."""
        return int(12_000 + random.randint(-200, 200))

    @property
    def vehicle_speed_kmh(self) -> int:
        return int(abs(60 * math.sin(self._uptime_s() / 20)))


    # Security helpers


    def generate_seed(self) -> int:
        """Generate a random 2-byte seed and cache it."""
        self._seed = random.randint(0x0001, 0xFFFE)
        return self._seed

    def validate_key(self, key: int) -> bool:
        """
        Toy algorithm: key = seed XOR 0xA5B6
        Real ECUs use much stronger derivations.
        """
        if self._seed is None:
            return False
        expected = self._seed ^ 0xA5B6
        return key == expected

    # DTC helpers

    def clear_dtcs(self):
        for code in self.dtcs:
            self.dtcs[code]["status"] = 0x00   # cleared, not present

    def active_dtcs(self) -> list:
        return [(code, info) for code, info in self.dtcs.items()
                if info["status"] != 0x00]
