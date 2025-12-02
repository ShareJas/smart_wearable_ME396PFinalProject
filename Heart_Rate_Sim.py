# -*- coding: utf-8 -*-
"""
Created on Tue Dec  2 03:01:50 2025

@author: rocio
"""

import random

class Simulated_HR:
    def __init__(self, start_hr=75):
        self.last_hr = start_hr

    def resting(self):
        """Simulate resting HR with small random fluctuations."""
        delta = random.randint(-3, 3)
        self.last_hr = max(50, min(100, self.last_hr + delta))
        return self.last_hr

    def workout(self, step):
        """
        Simulate a workout HR that ramps up gradually.
        step: seconds since start
        """
        base = 70
        max_increase = 40
        duration = 120  # seconds to reach peak

        target_hr = base + (max_increase * step / duration)
        target_hr = min(base + max_increase, target_hr)

        # smooth transition to target_hr
        if target_hr > self.last_hr:
            self.last_hr += min(3, target_hr - self.last_hr)  # max 3 bpm per second
        elif target_hr < self.last_hr:
            self.last_hr -= min(3, self.last_hr - target_hr)

        return int(self.last_hr)
